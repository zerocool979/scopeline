"""Menjalankan migrasi Alembic saat start; mengadopsi database lama yang dibuat oleh create_all."""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from .database import engine

log = logging.getLogger("scopeline.migrate")


def alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    return cfg


def _adopt_legacy_schema() -> None:
    """Database dari versi sebelum Alembic: pastikan kolom evidence.data ada (migrasi ringan lama), lalu stamp."""
    cols = {c["name"] for c in inspect(engine).get_columns("evidence")}
    if "data" not in cols:
        col_type = "BYTEA" if engine.dialect.name == "postgresql" else "BLOB"
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE evidence ADD COLUMN data {col_type}"))
    log.warning("Database lama terdeteksi tanpa alembic_version: di-stamp ke baseline 0001")
    command.stamp(alembic_config(), "0001")


def run_migrations() -> None:
    # Vercel may cold-start multiple function instances concurrently. Serialize schema upgrades
    # across PostgreSQL connections; the lock is released automatically if a connection drops.
    if engine.dialect.name == "postgresql":
        with engine.connect() as lock_connection:
            lock_connection.execute(text("SELECT pg_advisory_lock(1396911952)"))
            try:
                _run_migrations_locked()
            finally:
                lock_connection.execute(text("SELECT pg_advisory_unlock(1396911952)"))
    else:
        _run_migrations_locked()


def _run_migrations_locked() -> None:
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and "users" in tables:
        _adopt_legacy_schema()
    command.upgrade(alembic_config(), "head")
