import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def issue_token() -> str:
    return secrets.token_urlsafe(32)

def token_expiry(days: int = 7) -> datetime:
    return datetime.utcnow() + timedelta(days=days)