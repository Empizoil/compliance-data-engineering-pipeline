from sqlalchemy import text

from data_engineering.db import get_db


def test_database_connection():
    with get_db() as db:
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1