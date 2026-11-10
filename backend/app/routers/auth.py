import time
from collections import defaultdict

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..database import get_db
from ..deps import current_user
from ..models import User, utcnow
from ..schemas import LoginIn, OtpIn, PasswordChange, PasswordIn, UserOut
from ..security import DUMMY_HASH, create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
_hits: dict[str, list[float]] = defaultdict(list)


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "?"
    now = time.time()
    recent = [t for t in _hits[ip] if now - t < 60]
    if len(recent) >= settings.login_rate_per_min:
        _hits[ip] = recent
        raise HTTPException(429, "Terlalu banyak percobaan. Coba lagi sebentar lagi.")
    recent.append(now)
    _hits[ip] = recent


@router.post("/login")
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    _rate_limit(request)
    now = utcnow()
    user = db.query(User).filter(User.username == data.username).first()
    if user is None:
        verify_password(DUMMY_HASH, data.password)  # samakan waktu respons
        audit.log(db, None, "login_failed", "user", detail="pengguna tidak dikenal", username=data.username)
        db.commit()
        raise HTTPException(401, "Kredensial tidak valid")
    if user.locked_until and user.locked_until > now:
        raise HTTPException(429, "Akun terkunci sementara karena terlalu banyak percobaan gagal")
    ok = user.is_active and verify_password(user.password_hash, data.password)
    if ok and user.totp_enabled:
        ok = bool(data.otp) and pyotp.TOTP(user.totp_secret).verify(data.otp, valid_window=1)
    if not ok:
        user.failed_attempts += 1
        if user.failed_attempts >= settings.max_failed_logins:
            from datetime import timedelta
            user.locked_until = now + timedelta(minutes=settings.lock_minutes)
            user.failed_attempts = 0
        audit.log(db, user, "login_failed", "user", user.id)
        db.commit()
        raise HTTPException(401, "Kredensial tidak valid")
    user.failed_attempts = 0
    user.locked_until = None
    audit.log(db, user, "login", "user", user.id)
    db.commit()
    return {"access_token": create_token(user), "user": UserOut.model_validate(user).model_dump()}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/change-password")
def change_password(data: PasswordChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(user.password_hash, data.current_password):
        raise HTTPException(400, "Kata sandi saat ini salah")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    audit.log(db, user, "password_changed", "user", user.id)
    db.commit()
    return {"detail": "Kata sandi diubah. Silakan masuk kembali."}


@router.post("/mfa/setup")
def mfa_setup(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.totp_enabled:
        raise HTTPException(409, "MFA sudah aktif")
    user.totp_secret = pyotp.random_base32()
    db.commit()
    uri = pyotp.TOTP(user.totp_secret).provisioning_uri(name=user.username, issuer_name="SCOPELINE")
    return {"secret": user.totp_secret, "uri": uri}


@router.post("/mfa/enable")
def mfa_enable(data: OtpIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not user.totp_secret or not pyotp.TOTP(user.totp_secret).verify(data.code, valid_window=1):
        raise HTTPException(400, "Kode tidak valid")
    user.totp_enabled = True
    audit.log(db, user, "mfa_enabled", "user", user.id)
    db.commit()
    return {"detail": "MFA diaktifkan"}


@router.post("/mfa/disable")
def mfa_disable(data: PasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(user.password_hash, data.password):
        raise HTTPException(400, "Kata sandi salah")
    user.totp_enabled = False
    user.totp_secret = None
    audit.log(db, user, "mfa_disabled", "user", user.id)
    db.commit()
    return {"detail": "MFA dinonaktifkan"}
