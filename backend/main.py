import csv
import io
from openpyxl import Workbook
import base64
from pathlib import Path
from io import BytesIO
from PIL import Image
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models, schemas, security
from .db import Base, engine, get_db

app = FastAPI(title="Team Effort Tracker", version="0.2.0")

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

auth_scheme = HTTPBearer(auto_error=False)


def ensure_lead(actor: Optional[models.Member]):
    if actor is None or not actor.is_lead:
        raise HTTPException(status_code=403, detail="Team lead privileges required")


def get_current_member(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: Session = Depends(get_db),
) -> models.Member:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Auth token required")
    token = credentials.credentials
    session = (
        db.query(models.SessionToken)
        .filter(
            models.SessionToken.token == token,
            models.SessionToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return session.member


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        # Ensure standard teams exist (OPS, DevOPS, Infra). Create any that are missing.
        standard_names = ("OPS", "DevOPS", "Infra")
        created_any = False
        existing = {t.name for t in db.query(models.Team).all()}
        teams_map = {}
        for tname in standard_names:
            team = db.query(models.Team).filter(models.Team.name == tname).first()
            if not team:
                team = models.Team(name=tname)
                db.add(team)
                db.flush()
                created_any = True
            teams_map[tname] = team

        # If the DB was empty before, also seed a lead and sample members and task
        if db.query(models.Team).count() == len(standard_names) and created_any:
            lead = models.Member(
                username="alex.lead",
                password_hash=security.hash_password("changeme"),
                name="Alex Lead",
                career_level="Lead",
                is_lead=True,
                team_id=teams_map["OPS"].id,
            )
            member_a = models.Member(
                username="bailey.dev",
                password_hash=security.hash_password("changeme"),
                name="Bailey Dev",
                career_level="Senior",
                team_id=teams_map["OPS"].id,
            )
            member_b = models.Member(
                username="casey.analyst",
                password_hash=security.hash_password("changeme"),
                name="Casey Analyst",
                career_level="Associate",
                team_id=teams_map["OPS"].id,
            )
            db.add_all([lead, member_a, member_b])
            db.flush()
            sample_task = models.Task(
                title="Onboard new feature",
                details="Initial scaffolding and environment setup",
                hours_spent=3.5,
                due_date=datetime.utcnow().date() + timedelta(days=2),
                comments="Need API keys",
                assignee_id=member_a.id,
                creator_id=lead.id,
            )
            db.add(sample_task)
            db.commit()

        # Ensure all members are currently assigned to OPS (as requested)
        ops = db.query(models.Team).filter(models.Team.name == 'OPS').first()
        if ops:
            db.query(models.Member).update({models.Member.team_id: ops.id})
            db.commit()


@app.get("/", response_class=FileResponse)
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    return FileResponse(index_path)


# Auth endpoints
@app.post("/api/auth/login", response_model=schemas.AuthResponse)
def login(payload: schemas.MemberLogin, db: Session = Depends(get_db)):
    user = db.query(models.Member).filter(models.Member.username == payload.username).first()
    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Block login for locked accounts
    if getattr(user, "is_locked", False):
        raise HTTPException(status_code=403, detail="Account locked")
    token = security.issue_token()
    session = models.SessionToken(
        token=token,
        member_id=user.id,
        expires_at=security.token_expiry(),
    )
    db.add(session)
    db.commit()
    return schemas.AuthResponse(access_token=token, member=user)


@app.post("/api/auth/change-password")
def change_password(
    payload: schemas.PasswordChange,
    current: models.Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    if not security.verify_password(payload.current_password, current.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    current.password_hash = security.hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@app.post("/api/members/{member_id}/avatar")
def upload_member_avatar(
    member_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    # only the member themselves or a lead may upload an avatar for the member
    if not current.is_lead and current.id != member_id:
        raise HTTPException(status_code=403, detail="Not allowed to upload avatar for this member")

    data_url = payload.get("data_url")
    if not data_url:
        raise HTTPException(status_code=400, detail="data_url required")

    # expected format: data:<mime>;base64,<data>
    try:
        header, b64 = data_url.split(",", 1)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid data_url format")

    # parse mime-type
    try:
        mime = header.split(";")[0].split(":")[1]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid data_url header")

    allowed = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp"}
    if mime not in allowed:
        raise HTTPException(status_code=415, detail="Unsupported image type")

    try:
        data = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data")

    max_bytes = 3_000_000  # 3 MB raw limit before processing
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="Image too large (max 3MB)")

    # process image with Pillow and resize to a reasonable max dimension
    try:
        img = Image.open(BytesIO(data))
        # ensure RGB/RGBA where appropriate
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        # resize preserving aspect ratio
        max_dim = 512
        img.thumbnail((max_dim, max_dim))
        # save into bytes buffer with appropriate format
        ext = allowed[mime]
        out_buf = BytesIO()
        pil_format = "PNG" if ext == "png" else "JPEG" if ext in ("jpg", "jpeg") else "WEBP"
        save_kwargs = {"optimize": True}
        if pil_format == "JPEG":
            save_kwargs["quality"] = 85
        img.save(out_buf, format=pil_format, **save_kwargs)
        out_data = out_buf.getvalue()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {e}")

    if len(out_data) > 1_500_000:
        raise HTTPException(status_code=413, detail="Processed image too large (max 1.5MB)")

    # save under frontend/avatars/<member_id>.<ext>
    avatars_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "avatars"))
    avatars_dir.mkdir(parents=True, exist_ok=True)
    out_path = avatars_dir / f"{member_id}.{ext}"
    try:
        with open(out_path, "wb") as f:
            f.write(out_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save avatar: {e}")

    return {"url": f"/static/avatars/{member_id}.{ext}"}


@app.get("/api/members/{member_id}/avatar")
def get_member_avatar(member_id: int):
    avatars_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "avatars"))
    for ext in ("png", "jpg", "webp"):
        p = avatars_dir / f"{member_id}.{ext}"
        if p.exists():
            return {
                "exists": True,
                "url": f"/static/avatars/{member_id}.{ext}",
                "size": p.stat().st_size,
                "modified_at": p.stat().st_mtime,
            }
    return {"exists": False}


@app.delete("/api/members/{member_id}/avatar")
def delete_member_avatar(member_id: int, current: models.Member = Depends(get_current_member)):
    # only the member themselves or a lead may delete an avatar
    if not current.is_lead and current.id != member_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete avatar for this member")
    avatars_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "avatars"))
    deleted = False
    for ext in ("png", "jpg", "webp"):
        p = avatars_dir / f"{member_id}.{ext}"
        if p.exists():
            p.unlink()
            deleted = True
    if not deleted:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return {"detail": "deleted"}


@app.post("/api/auth/users", response_model=schemas.Member, status_code=201)
def create_user(
    payload: schemas.MemberCreate,
    current: models.Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    ensure_lead(current)
    if not payload.password:
        raise HTTPException(status_code=400, detail="Password required")
    if db.query(models.Member).filter(models.Member.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    member = models.Member(
        username=payload.username,
        password_hash=security.hash_password(payload.password),
        name=payload.name,
        career_level=payload.career_level,
        is_lead=payload.is_lead,
        team_id=payload.team_id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@app.get("/api/teams", response_model=List[schemas.Team])
def list_teams(db: Session = Depends(get_db)):
    # return teams including their IDs so the frontend can build selects
    return db.query(models.Team).all()


@app.get("/api/members", response_model=List[schemas.Member])
def list_members(db: Session = Depends(get_db), current: models.Member = Depends(get_current_member)):
    return db.query(models.Member).order_by(models.Member.name).all()


@app.put("/api/members/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    ensure_lead(current)
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    changes = payload.model_dump(exclude_unset=True)
    if "username" in changes and changes["username"]:
        member.username = changes["username"]
    if "password" in changes and changes["password"]:
        member.password_hash = security.hash_password(changes["password"])

    for key, value in changes.items():
        if key in {"username", "password"}:
            continue
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return member

@app.delete("/api/members/{member_id}", status_code=204)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    ensure_lead(current)
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    return None


@app.get("/api/tasks", response_model=List[schemas.Task])
def list_tasks(
    member_id: Optional[int] = Query(None, description="Filter by assignee"),
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    query = db.query(models.Task).order_by(models.Task.created_at.desc())

    if member_id:
        query = query.filter(models.Task.assignee_id == member_id)
    elif not current.is_lead:
        query = query.filter(
            (models.Task.assignee_id == current.id) | (models.Task.creator_id == current.id)
        )

    tasks = query.all()
    result = []
    for task in tasks:
        tag_member_ids = [t.member_id for t in task.tags]
        item = schemas.Task(
            id=task.id,
            title=task.title,
            details=task.details,
            hours_spent=float(task.hours_spent) if task.hours_spent is not None else None,
            due_date=task.due_date,
            blockers=task.blockers,
            comments=task.comments,
            status=task.status,
            assignee_id=task.assignee_id,
            creator_id=task.creator_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
            tags=tag_member_ids,
        )
        result.append(item)
    return result


@app.post("/api/tasks", response_model=schemas.Task, status_code=201)
def create_task(
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    assignee_id = payload.assignee_id or current.id
    if not current.is_lead and assignee_id != current.id:
        raise HTTPException(status_code=403, detail="Members can only create tasks for themselves")

    task = models.Task(
        title=payload.title,
        details=payload.details,
        hours_spent=payload.hours_spent,
        due_date=payload.due_date,
        blockers=payload.blockers,
        comments=payload.comments,
        status=payload.status,
        assignee_id=assignee_id,
        creator_id=current.id,
    )
    db.add(task)
    db.flush()
    for member_id in payload.tags:
        db.add(models.TaskTag(task_id=task.id, member_id=member_id))
    db.commit()
    db.refresh(task)
    tag_ids = [t.member_id for t in task.tags]
    return schemas.Task(
        id=task.id,
        title=task.title,
        details=task.details,
        hours_spent=float(task.hours_spent) if task.hours_spent is not None else None,
        due_date=task.due_date,
        blockers=task.blockers,
        comments=task.comments,
        status=task.status,
        assignee_id=task.assignee_id,
        creator_id=task.creator_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        tags=tag_ids,
    )


@app.put("/api/tasks/{task_id}", response_model=schemas.Task)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not current.is_lead and task.assignee_id != current.id and task.creator_id != current.id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this task")

    changes = payload.model_dump(exclude_unset=True)
    if "assignee_id" in changes and changes["assignee_id"] != task.assignee_id:
        ensure_lead(current)

    for key, value in changes.items():
        if key == "tags" and value is not None:
            db.query(models.TaskTag).filter(models.TaskTag.task_id == task.id).delete()
            for member_id in value:
                db.add(models.TaskTag(task_id=task.id, member_id=member_id))
        else:
            setattr(task, key, value)

    db.commit()
    db.refresh(task)
    tag_ids = [t.member_id for t in task.tags]
    return schemas.Task(
        id=task.id,
        title=task.title,
        details=task.details,
        hours_spent=float(task.hours_spent) if task.hours_spent is not None else None,
        due_date=task.due_date,
        blockers=task.blockers,
        comments=task.comments,
        status=task.status,
        assignee_id=task.assignee_id,
        creator_id=task.creator_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        tags=tag_ids,
    )


@app.post("/api/tasks/{task_id}/tag", status_code=201)
def tag_task(
    task_id: int,
    payload: schemas.TaskTagCreate,
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not current.is_lead and task.assignee_id != current.id and task.creator_id != current.id:
        raise HTTPException(status_code=403, detail="Not allowed to tag this task")

    existing = (
        db.query(models.TaskTag)
        .filter(models.TaskTag.task_id == task_id, models.TaskTag.member_id == payload.member_id)
        .first()
    )
    if existing:
        return {"detail": "Already tagged"}

    db.add(models.TaskTag(task_id=task_id, member_id=payload.member_id))
    db.commit()
    return {"detail": "Tagged"}


@app.get("/api/reports")
def reports(
    period: str = Query("weekly", pattern="^(weekly|monthly|semester)$"),
    format: str = Query("json", pattern="^(json|csv|xlsx)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    member_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current: models.Member = Depends(get_current_member),
):
    # allow leads to run reports for anyone; non-leads may only run reports for themselves
    if not current.is_lead:
        # if a non-lead requests another member's report, deny
        if member_id and member_id != current.id:
            raise HTTPException(status_code=403, detail="Team lead privileges required to view other members' reports")
        # force member_id to current user so non-leads only see their own data
        member_id = current.id

    today = datetime.utcnow().date()

    # determine date range: explicit start/end override period
    if start_date:
        try:
            s_date = datetime.fromisoformat(start_date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid start_date format, use YYYY-MM-DD")
    else:
        if period == "weekly":
            s_date = today - timedelta(days=7)
        elif period == "monthly":
            s_date = today - timedelta(days=30)
        else:
            s_date = today - timedelta(days=182)

    if end_date:
        try:
            e_date = datetime.fromisoformat(end_date).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid end_date format, use YYYY-MM-DD")
    else:
        e_date = today

    # Build base query
    q = db.query(models.Task)
    # filter by created_at in range
    q = q.filter(models.Task.created_at >= datetime.combine(s_date, datetime.min.time()))
    q = q.filter(models.Task.created_at <= datetime.combine(e_date, datetime.max.time()))

    if member_id:
        q = q.filter(models.Task.assignee_id == member_id)

    if status:
        # allow comma-separated statuses
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        q = q.filter(models.Task.status.in_(statuses))

    tasks = q.all()

    report_rows = []
    total_hours = 0.0
    total_blockers = 0
    tasks_past_due = 0
    tasks_completed_past_due = 0

    for task in tasks:
        hours = float(task.hours_spent) if task.hours_spent else 0.0
        total_hours += hours
        has_blockers = bool(task.blockers and task.blockers.strip())
        if has_blockers:
            total_blockers += 1

        past_due = False
        completed_past_due = False
        color_key = "in_progress"

        if task.due_date:
            if task.status != "completed" and task.due_date < today:
                past_due = True
            if task.status == "completed":
                # use updated_at as completion time
                comp_date = task.updated_at.date() if task.updated_at else task.created_at.date()
                if task.due_date and comp_date > task.due_date:
                    completed_past_due = True

        # determine color key
        if task.status == "completed":
            color_key = "completed_past_due" if completed_past_due else "completed_on_time"
        else:
            if task.due_date:
                days_to_due = (task.due_date - today).days
                if task.due_date < today:
                    color_key = "past_due"
                elif days_to_due <= 2:
                    color_key = "nearing_deadline"
                else:
                    # just started if created recently
                    if (datetime.utcnow().date() - task.created_at.date()).days <= 3:
                        color_key = "just_started"
                    else:
                        color_key = "in_progress"
            else:
                color_key = "in_progress"

        if past_due:
            tasks_past_due += 1
        if completed_past_due:
            tasks_completed_past_due += 1

        row = {
            "task_id": task.id,
            "title": task.title,
            "assignee_id": task.assignee_id,
            "assignee": task.assignee.name if task.assignee else None,
            "hours_spent": hours if hours else None,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "has_blockers": has_blockers,
            "color_key": color_key,
        }
        report_rows.append(row)

    summary = {
        "total_tasks": len(report_rows),
        "total_hours": total_hours,
        "total_blockers": total_blockers,
        "tasks_past_due": tasks_past_due,
        "tasks_completed_past_due": tasks_completed_past_due,
        "start_date": s_date.isoformat(),
        "end_date": e_date.isoformat(),
    }

    if format == "json":
        return {"summary": summary, "rows": report_rows}

    if format == "xlsx":
        wb = Workbook()
        ws = wb.active
        headers = ["task_id", "title", "assignee", "hours_spent", "status", "due_date", "created_at"]
        ws.append(headers)
        for row in report_rows:
            ws.append([row.get(h) for h in headers])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        filename = f"report_{s_date.isoformat()}_{e_date.isoformat()}.xlsx"
        return StreamingResponse(
            iter([bio.read()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # CSV output
    output = io.StringIO()
    fieldnames = ["task_id", "title", "assignee", "hours_spent", "status", "due_date", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in report_rows:
        writer.writerow({k: row.get(k) for k in fieldnames})
    output.seek(0)
    filename = f"report_{s_date.isoformat()}_{e_date.isoformat()}.csv"
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )