"""Konfigurasi aplikasi. Seluruh rahasia dibaca dari variabel lingkungan."""
import os
import secrets
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        is_vercel = os.getenv("VERCEL") == "1"
        raw_url = os.getenv("DATABASE_URL", "")
        if is_vercel and not raw_url:
            raise RuntimeError("DATABASE_URL wajib diatur ke PostgreSQL persisten pada deployment Vercel.")
        if is_vercel and raw_url.startswith("sqlite"):
            raise RuntimeError("SQLite lokal tidak didukung untuk data production di Vercel.")
        url = raw_url or "sqlite:///./data/scopeline.db"
        for prefix in ("postgres://", "postgresql://"):  # URL PostgreSQL -> driver psycopg
            if url.startswith(prefix):
                url = "postgresql+psycopg://" + url[len(prefix):]
        self.database_url = url
        self.evidence_in_db = os.getenv("EVIDENCE_IN_DB", "0") == "1"  # untuk hosting tanpa disk persisten
        if is_vercel and not self.evidence_in_db:
            raise RuntimeError("EVIDENCE_IN_DB=1 wajib pada Vercel agar bukti tidak hilang dari filesystem sementara.")
        self.enable_pdf = os.getenv("ENABLE_PDF", "1") == "1"
        if is_vercel and self.enable_pdf:
            raise RuntimeError("ENABLE_PDF=0 wajib pada Vercel; LibreOffice tidak dibundel pada runtime ini.")
        default_data_dir = "/tmp/scopeline" if is_vercel else "./data"
        self.data_dir = Path(os.getenv("DATA_DIR", default_data_dir))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.secret_key = os.getenv("SECRET_KEY", "")
        if is_vercel and len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY minimal 32 karakter dan harus disimpan sebagai Environment Variable Vercel.")
        if not self.secret_key:  # buat sekali dan simpan agar instalasi satu perintah tetap aman
            key_file = self.data_dir / "secret.key"
            if not key_file.is_file():
                key_file.write_text(secrets.token_urlsafe(48))
                key_file.chmod(0o600)
            self.secret_key = key_file.read_text().strip()
        if len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY minimal 32 karakter.")
        self.token_minutes = int(os.getenv("TOKEN_MINUTES", "60"))
        # Vercel Functions membatasi request body hingga 4.5 MB; sisakan ruang untuk multipart headers.
        default_upload_mb = "4" if is_vercel else "5"
        upload_mb = int(os.getenv("MAX_UPLOAD_MB", default_upload_mb))
        self.max_upload_bytes = min(upload_mb, 4) * 1024 * 1024 if is_vercel else upload_mb * 1024 * 1024
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        if is_vercel and len(self.admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD minimal 12 karakter dan wajib disetel pada Environment Variable Vercel.")
        self.max_failed_logins = int(os.getenv("MAX_FAILED_LOGINS", "5"))
        self.lock_minutes = int(os.getenv("LOCK_MINUTES", "15"))
        self.login_rate_per_min = int(os.getenv("LOGIN_RATE_PER_MIN", "20"))
        self.enable_docs = os.getenv("ENABLE_DOCS", "0") == "1"
        (self.data_dir / "evidence").mkdir(parents=True, exist_ok=True)

    @property
    def evidence_dir(self) -> Path:
        return self.data_dir / "evidence"

    @property
    def report_template_path(self) -> Path:
        return self.data_dir / "report_template.docx"


settings = Settings()
