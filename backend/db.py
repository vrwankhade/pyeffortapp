import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# default to a local SQLite database file in the project root
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./effort.db")
# if you prefer another location you can set DATABASE_URL to any SQLAlchemy
# compatible URL (e.g. "postgresql://user:pass@host/dbname").

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

