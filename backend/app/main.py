import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import SessionLocal
from .migrate import run_migrations
from .models import ReportTemplate, User, utcnow
from .routers import auth, engagements, findings, notes, reports, templates, users
from .security import hash_password

log = logging.getLogger("scopeline")
STATIC = Path(__file__).parent / "static"


def bootstrap_admin() -> None:
    with SessionLocal() as db:
        if db.query(User).count():
            return
        password = settings.admin_password
        if not password:
            password = secrets.token_urlsafe(14)
            log.warning("ADMIN_PASSWORD kosong. Kata sandi awal '%s': %s (segera ganti)",
                        settings.admin_username, password)
        db.add(User(username=settings.admin_username, full_name="Administrator",
                    password_hash=hash_password(password), role="admin"))
        db.commit()


def import_legacy_report_template() -> None:
    """Templat tunggal v1.0 (berkas di disk) diimpor sebagai templat pretest versi 1 yang aktif."""
    path = settings.report_template_path
    if not path.is_file():
        return
    with SessionLocal() as db:
        if db.query(ReportTemplate).count() == 0:
            data = path.read_bytes()
            db.add(ReportTemplate(kind="pretest", version=1, status="active", filename="report_template.docx",
                                  notes="Diimpor dari templat v1.0", size=len(data), data=data,
                                  activated_at=utcnow()))
            db.commit()
            log.warning("Templat laporan v1.0 diimpor sebagai pretest v1 (aktif)")
    path.rename(path.with_suffix(".docx.imported"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations()
    bootstrap_admin()
    import_legacy_report_template()
    yield


app = FastAPI(title="SCOPELINE", version="1.1.0", lifespan=lifespan,
              docs_url="/api/docs" if settings.enable_docs else None,
              redoc_url=None, openapi_url="/api/openapi.json" if settings.enable_docs else None)

CSP = ("default-src 'self'; img-src 'self' blob: data:; style-src 'self'; script-src 'self'; "
       "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if not settings.enable_docs or not request.url.path.startswith("/api/docs"):
        response.headers["Content-Security-Policy"] = CSP
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


for r in (auth, users, engagements, findings, notes, templates, reports):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
