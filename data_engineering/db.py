import structlog
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pgvector.sqlalchemy import Vector
from data_engineering.config import get_settings

logger = structlog.get_logger(__name__)

_settings = get_settings()
_engine = create_engine(
    _settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,            # Recycles stale connections
    pool_recycle=3600,
    echo=False,                    # Set to True for SQL debug logging
)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


@contextmanager
def get_db() -> Session:
    """Context manager yielding a database session. Rolls back on exception."""
    db = SessionLocal()

    try:
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise
    
    finally:
        db.close()


def set_ivfflat_probes(db: Session, probes: int = 10) -> None:
    """
    Set ivfflat.probes for the session.
    Higher probes = better recall at the cost of query speed.
    10 is a good default for datasets < 100k rows.
    """
    db.execute(text(f"SET ivfflat.probes = {probes}"))
