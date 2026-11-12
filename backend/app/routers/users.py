from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import ADMIN, require_roles
from ..models import User
from ..schemas import UserCreate, UserOut, UserUpdate
from ..security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles(*ADMIN))):
    return db.query(User).order_by(User.username).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(*ADMIN))):
    user = User(username=data.username, full_name=data.full_name, role=data.role,
                password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Nama pengguna sudah dipakai")
    audit.log(db, actor, "user_created", "user", user.id, f"{user.username} ({user.role})")
    db.commit()
    return user


@router.patch("/{uid}", response_model=UserOut)
def update_user(uid: int, data: UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(require_roles(*ADMIN))):
    user = db.get(User, uid)
    if not user:
        raise HTTPException(404, "Pengguna tidak ditemukan")
    if user.id == actor.id and (data.role not in (None, user.role) or data.is_active is False):
        raise HTTPException(400, "Tidak dapat mengubah peran atau menonaktifkan akun sendiri")
    changes = []
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None and data.role != user.role:
        changes.append(f"peran {user.role}->{data.role}")
        user.role = data.role
        user.token_version += 1
    if data.is_active is not None and data.is_active != user.is_active:
        changes.append("aktif" if data.is_active else "nonaktif")
        user.is_active = data.is_active
        user.token_version += 1
    if data.password:
        user.password_hash = hash_password(data.password)
        user.token_version += 1
        changes.append("kata sandi direset")
    audit.log(db, actor, "user_updated", "user", user.id, "; ".join(changes))
    db.commit()
    return user
