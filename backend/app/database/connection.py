from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def migrate_schema(bind=engine) -> None:
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "transactions" in tables:
        columns = {column["name"] for column in inspector.get_columns("transactions")}
        indexes = {index["name"] for index in inspector.get_indexes("transactions")}
        if "label_known" not in columns:
            with bind.begin() as connection:
                connection.exec_driver_sql(
                    "ALTER TABLE transactions "
                    "ADD COLUMN label_known BOOLEAN NOT NULL DEFAULT FALSE"
                )
        if "source" not in columns:
            with bind.begin() as connection:
                connection.exec_driver_sql(
                    "ALTER TABLE transactions "
                    "ADD COLUMN source VARCHAR(24) NOT NULL DEFAULT 'csv'"
                )
        if "ix_transactions_source" not in indexes:
            with bind.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE INDEX ix_transactions_source ON transactions (source)"
                )
    if "risk_assessments" not in tables:
        return
    assessment_columns = {
        column["name"] for column in inspector.get_columns("risk_assessments")
    }
    new_columns = (
        ("model_classification", "VARCHAR(16) NOT NULL DEFAULT 'unknown'"),
        ("classification_threshold", "FLOAT NOT NULL DEFAULT 0.5"),
        ("anomaly_status", "VARCHAR(24) NOT NULL DEFAULT 'unavailable'"),
        ("anomaly_reason", "TEXT NOT NULL DEFAULT 'Not calculated.'"),
        ("behavior_status", "VARCHAR(24) NOT NULL DEFAULT 'unavailable'"),
        ("behavior_findings", "JSON NOT NULL DEFAULT '[]'"),
    )
    for column, definition in new_columns:
        if column not in assessment_columns:
            with bind.begin() as connection:
                connection.exec_driver_sql(
                    f"ALTER TABLE risk_assessments ADD COLUMN {column} {definition}"
                )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()