import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


def build_oracle_url() -> str:
    """
    Construct an Oracle SQLAlchemy URL from environment variables.
    Expected:
    - ORACLE_USER
    - ORACLE_PASSWORD
    - ORACLE_DSN (e.g. "host:1521/ORCLCDB" or EZConnect string)
    """
    user = os.getenv("ORACLE_USER", "appuser")
    password = os.getenv("ORACLE_PASSWORD", "app_password")
    dsn = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")
    return f"oracle+cx_oracle://{user}:{password}@{dsn}"


DATABASE_URL = os.getenv("DATABASE_URL", build_oracle_url())

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

