from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_args, pool_pre_ping=True, pool_recycle=300)
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_conn, _):  # samakan perilaku dengan PostgreSQL: tegakkan foreign key
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
