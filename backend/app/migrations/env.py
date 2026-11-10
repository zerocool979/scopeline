"""Lingkungan Alembic: memakai engine aplikasi (DATABASE_URL), tanpa alembic.ini saat runtime."""
from alembic import context

try:  # Vercel entrypoint: backend.app.main
    from backend.app import models  # noqa: F401
    from backend.app.database import Base, engine
except ModuleNotFoundError:  # local Docker / `cd backend`
    from app import models  # noqa: F401
    from app.database import Base, engine

target_metadata = Base.metadata


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
