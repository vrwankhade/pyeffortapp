from datetime import datetime, timedelta
import csv
import io
import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Header, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models, schemas
from .db import Base, engine, get_db

app = FastAPI(title="Team Effort Tracker", version="0.1.0")

# Serve the static frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


def get_actor(db: Session, actor_id: Optional[int]) -> Optional[models.Member]:
    if actor_id is None:
        return None
    actor = db.query(models.Member).filter(models.Member.id == actor_id).first()
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


def ensure_lead(actor: Optional[models.Member]):
    if actor is None or not actor.is_lead:
        raise HTTPException(status_code=403, detail="Team lead privileges required")


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        if db.query(models.Team).count() == 0:
            team = models.Team(name="Orange Tigers")
            db.add(team)
            db.flush()
            lead = models.Member(
                name="Alex Lead",
                career_level="Lead",
                is_lead=True,
                team_id=team.id,
            )
            member_a = models.Member(
                name="Bailey Dev", career_level="Senior", team_id=team.id
            )
            member_b = models.Member(
                name="Casey Analyst", career_level="Associate", team_id=team.id
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


@app.get("/", response_class=FileResponse)
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    return FileResponse(index_path)


@app.get("/api/teams", response_model=List[schemas.TeamCreate])
def list_teams(db: Session = Depends(get_db)):
    teams = db.query(models.Team).all()
    return teams


@app.get("/api/members", response_model=List[schemas.Member])
def list_members(db: Session = Depends(get_db)):
    return db.query(models.Member).order_by(models.Member.name).all()


@app.post("/api/members", response_model=schemas.Member, status_code=201)
def create_member(
    payload: schemas.MemberCreate,
    db: Session = Depends(get_db),
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    ensure_lead(actor)
    member = models.Member(**payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@app.put("/api/members/{member_id}", response_model=schemas.Member)
def update_member(
    member_id: int,
    payload: schemas.MemberUpdate,
    db: Session = Depends(get_db),
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    ensure_lead(actor)
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, key, value)
    db.commit()
    db.refresh(member)
    return member


@app.delete("/api/members/{member_id}", status_code=204)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    ensure_lead(actor)
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
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    query = db.query(models.Task).order_by(models.Task.created_at.desc())

    if member_id:
        query = query.filter(models.Task.assignee_id == member_id)
    elif actor and not actor.is_lead:
        query = query.filter(
            (models.Task.assignee_id == actor.id) | (models.Task.creator_id == actor.id)
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
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    if actor is None:
        raise HTTPException(status_code=403, detail="Actor required to create tasks")

    # Only leads can assign tasks to other members
    if payload.assignee_id and payload.assignee_id != actor.id and not actor.is_lead:
        raise HTTPException(status_code=403, detail="Only leads can assign tasks to others")

    task = models.Task(
        title=payload.title,
        details=payload.details,
        hours_spent=payload.hours_spent,
        due_date=payload.due_date,
        blockers=payload.blockers,
        comments=payload.comments,
        status=payload.status,
        assignee_id=payload.assignee_id or actor.id,
        creator_id=actor.id,
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
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    if actor is None:
        raise HTTPException(status_code=403, detail="Actor required")

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Non-leads can only edit their own tasks
    if not actor.is_lead and task.assignee_id != actor.id and task.creator_id != actor.id:
        raise HTTPException(status_code=403, detail="Not allowed to edit this task")

    changes = payload.model_dump(exclude_unset=True)
    if "assignee_id" in changes and changes["assignee_id"] != task.assignee_id:
        ensure_lead(actor)

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
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    if actor is None:
        raise HTTPException(status_code=403, detail="Actor required")

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    x_actor_id: Optional[int] = Header(None),
):
    actor = get_actor(db, x_actor_id)
    ensure_lead(actor)

    today = datetime.utcnow().date()
    if period == "weekly":
        start_date = today - timedelta(days=7)
    elif period == "monthly":
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=182)

    tasks = (
        db.query(models.Task)
        .filter(models.Task.created_at >= datetime.combine(start_date, datetime.min.time()))
        .all()
    )

    report_rows = []
    for task in tasks:
        row = {
            "task_id": task.id,
            "title": task.title,
            "assignee": task.assignee.name if task.assignee else None,
            "hours_spent": float(task.hours_spent) if task.hours_spent else None,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat(),
        }
        report_rows.append(row)

    if format == "json":
        return {"period": period, "count": len(report_rows), "rows": report_rows}

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(report_rows[0].keys()) if report_rows else [])
    writer.writeheader()
    for row in report_rows:
        writer.writerow(row)
    output.seek(0)
    filename = f"report_{period}.csv"
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

