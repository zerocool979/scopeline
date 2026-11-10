import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Engagement, User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)
ADMIN = ("admin",)
STAFF = ("admin", "lead")
WRITERS = ("admin", "lead", "tester")  # pelaksana pengujian: temuan, bukti, retest
TEXT_EDITORS = ("admin", "lead", "tester", "writer")  # boleh menyunting teks temuan
AUTHORS = TEXT_EDITORS  # boleh mengajukan review
REVIEWERS = ("admin", "lead", "reviewer")  # boleh menyetujui / meminta perubahan
TEMPLATE_ROLES = ("admin", "lead", "writer")  # boleh mengelola templat laporan
NOTE_ROLES = ("admin", "lead", "tester", "reviewer")  # boleh melihat catatan pentester


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Belum masuk")
    try:
        payload = decode_token(creds.credentials)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Token tidak valid")
    if not user or not user.is_active or payload.get("tv") != user.token_version:
        raise HTTPException(401, "Sesi tidak valid")
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Anda tidak memiliki izin untuk tindakan ini")
        return user
    return dep


def load_engagement(db: Session, user: User, eid: int) -> Engagement:
    """Kontrol akses objek: penguji/peninjau hanya melihat engagement yang ditugaskan."""
    e = db.get(Engagement, eid)
    if not e or not (user.role in STAFF or any(m.id == user.id for m in e.members)):
        raise HTTPException(404, "Engagement tidak ditemukan")
    return e


def accessible_engagements(db: Session, user: User) -> list[Engagement]:
    rows = db.query(Engagement).order_by(Engagement.id.desc()).all()
    return [e for e in rows if user.role in STAFF or any(m.id == user.id for m in e.members)]
