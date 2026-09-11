import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def _clean_env(name: str, default: str = "") -> str:
    """Get an environment variable with aggressive whitespace/newline stripping."""
    value = os.getenv(name, default)
    if value:
        value = value.strip().strip("'\"").strip()
    return value


def get_database_url() -> str:
    database_url = _clean_env("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    user = _clean_env("POSTGRES_USER", "postgres")
    password = _clean_env("POSTGRES_PASSWORD", "postgres")
    host = _clean_env("POSTGRES_HOST", "localhost")
    port = _clean_env("POSTGRES_PORT", "5432")
    db = _clean_env("POSTGRES_DB", "ai_news_aggregator")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

engine = create_engine(get_database_url(), connect_args={"connect_timeout": 10})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    return SessionLocal()

