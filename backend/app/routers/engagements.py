from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import (
    STAFF,
    accessible_engagements,
    current_user,
    load_engagement,
    require_roles,
)
from ..models import Engagement, User, utcnow
from ..notes_service import ensure_personal_note, ensure_team_note
from ..schemas import EngagementIn, EngagementStatusIn, EngagementUpdate, MembersIn

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


def eng_out(e: Engagement) -> dict:
    today = date.today()
    return {
        "id": e.id, "name": e.name, "client": e.client, "scope": e.scope,
        "start_date": e.start_date, "end_date": e.end_date, "roe_text": e.roe_text,
        "roe_approved": e.roe_approved,
        "roe_approved_by": e.roe_approved_by.username if e.roe_approved_by else None,
        "roe_approved_at": e.roe_approved_at,\n        "roe_approvals": {\n            "project_manager": {"approved": bool(e.roe_project_manager_approved_by_id), "approved_at": e.roe_project_manager_approved_at},\n            "engineer_head_offensive_security": {"approved": bool(e.roe_head_approved_by_id), "approved_at": e.roe_head_approved_at},\n        }, "status": e.status,
        "in_window": e.start_date <= today <= e.end_date,
        "members": [{"id": m.id, "username": m.username, "full_name": m.full_name} for m in e.members],
        "finding_count": len(e.findings),
    }


@router.get("")
def list_engagements(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [eng_out(e) for e in accessible_engagements(db, user)]


@router.post("", status_code=201)
def create_engagement(data: EngagementIn, db: Session = Depends(get_db),
                      user: User = Depends(require_roles(*STAFF))):
    e = Engagement(**data.model_dump(), created_by_id=user.id)
    db.add(e)
    db.flush()
    ensure_team_note(db, e, user)  # catatan tim dari templat catatan default
    audit.log(db, user, "engagement_created", "engagement", e.id, e.name)
    db.commit()
    return eng_out(e)


@router.get("/{eid}")
def get_engagement(eid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return eng_out(load_engagement(db, user, eid))


@router.patch("/{eid}")
def update_engagement(eid: int, data: EngagementUpdate, db: Session = Depends(get_db),
                      user: User = Depends(require_roles(*STAFF))):
    e = load_engagement(db, user, eid)
    changes = data.model_dump(exclude_unset=True)
    changes = {k: v for k, v in changes.items() if v is not None}
    sensitive = [k for k in ("scope", "roe_text") if k in changes and changes[k] != getattr(e, k)]
    if sensitive and e.status == "completed":
        raise HTTPException(409, "Ruang lingkup/RoE tidak dapat diubah pada engagement yang selesai")
    for k, v in changes.items():
        setattr(e, k, v)
    if e.end_date < e.start_date:
        db.rollback()
        raise HTTPException(422, "Tanggal selesai tidak boleh sebelum tanggal mulai")
    if sensitive and e.roe_approved:
        e.roe_approved, e.roe_approved_by_id, e.roe_approved_at = False, None, None
        e.roe_project_manager_approved_by_id = e.roe_head_approved_by_id = None
        e.roe_project_manager_approved_at = e.roe_head_approved_at = None
        if e.status == "active":
            e.status = "draft"  # pengujian dijeda hingga RoE disetujui ulang
        audit.log(db, user, "roe_approval_reset", "engagement", e.id, "scope/RoE berubah")
    audit.log(db, user, "engagement_updated", "engagement", e.id, ", ".join(changes))
    db.commit()
    return eng_out(e)


@router.put("/{eid}/members")
def set_members(eid: int, data: MembersIn, db: Session = Depends(get_db),
                user: User = Depends(require_roles(*STAFF))):
    e = load_engagement(db, user, eid)
    users = db.query(User).filter(User.id.in_(data.user_ids), User.is_active.is_(True)).all()
    e.members = list(users)
    for member in e.members:
        if member.role == "tester":  # tiap penguji otomatis mendapat catatan pribadi dari templat default
            ensure_personal_note(db, e, member, user)
    audit.log(db, user, "members_set", "engagement", e.id, ",".join(u.username for u in e.members))
    db.commit()
    return eng_out(e)


@router.post("/{eid}/roe/approve")
def approve_roe(eid: int, db: Session = Depends(get_db),
                user: User = Depends(require_roles("lead", "reviewer"))):
    e = load_engagement(db, user, eid)
    if not e.scope.strip() or not e.roe_text.strip():
        raise HTTPException(409, "Ruang lingkup dan RoE harus diisi sebelum disetujui")
    now = utcnow()
    if user.role == "lead":
        e.roe_project_manager_approved_by_id, e.roe_project_manager_approved_at = user.id, now
        role_label = "project_manager"
    else:
        e.roe_head_approved_by_id, e.roe_head_approved_at = user.id, now
        role_label = "engineer_head_offensive_security"
    e.roe_approved = bool(e.roe_project_manager_approved_by_id and e.roe_head_approved_by_id)
    e.roe_approved_by_id, e.roe_approved_at = user.id, now
    audit.log(db, user, "roe_approved", "engagement", e.id, role_label)
    db.commit()
    return eng_out(e)


@router.post("/{eid}/status")
def set_status(eid: int, data: EngagementStatusIn, db: Session = Depends(get_db),
               user: User = Depends(require_roles(*STAFF))):
    e = load_engagement(db, user, eid)
    allowed = {"draft": ("active",), "active": ("completed", "draft"), "completed": ("active",)}
    if data.status == e.status:
        return eng_out(e)
    if data.status not in allowed[e.status]:
        raise HTTPException(409, f"Transisi {e.status} -> {data.status} tidak diizinkan")
    if data.status == "active" and not e.roe_approved:
        raise HTTPException(409, "Pengujian hanya dapat dimulai setelah RoE disetujui")
    audit.log(db, user, "engagement_status", "engagement", e.id, f"{e.status}->{data.status}")
    e.status = data.status
    db.commit()
    return eng_out(e)
