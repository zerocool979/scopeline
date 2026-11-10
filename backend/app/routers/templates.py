"""Templat laporan DOCX berversi (pretest / retest). Disimpan di database."""
import io
import re
import zipfile

from docx import Document
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session, undefer

from .. import audit
from ..config import settings
from ..database import get_db
from ..deps import TEMPLATE_ROLES, current_user, require_roles
from ..models import ReportTemplate, User, utcnow
from ..reporting import scan_placeholders

router = APIRouter(prefix="/api/report-templates", tags=["report-templates"])
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def tpl_out(t: ReportTemplate) -> dict:
    return {"id": t.id, "kind": t.kind, "version": t.version, "status": t.status, "filename": t.filename,
            "notes": t.notes, "size": t.size, "created_by": t.created_by.username if t.created_by else None,
            "created_at": t.created_at, "activated_at": t.activated_at}


def _get(db: Session, tid: int, with_data: bool = False) -> ReportTemplate:
    q = db.query(ReportTemplate).filter(ReportTemplate.id == tid)
    if with_data:
        q = q.options(undefer(ReportTemplate.data))
    t = q.first()
    if not t:
        raise HTTPException(404, "Templat tidak ditemukan")
    return t


def _validate_docx(data: bytes) -> dict:
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise HTTPException(422, "Berkas bukan DOCX yang valid")
    try:
        return scan_placeholders(Document(io.BytesIO(data)))
    except Exception:  # noqa: BLE001
        raise HTTPException(422, "Berkas bukan DOCX yang valid")


@router.get("/active")
def active_templates(db: Session = Depends(get_db), _: User = Depends(current_user)):
    out: dict = {"pretest": None, "retest": None}
    for t in db.query(ReportTemplate).filter(ReportTemplate.status == "active").all():
        out[t.kind] = {"id": t.id, "version": t.version}
    return out


@router.get("")
def list_templates(kind: str | None = None, db: Session = Depends(get_db),
                   _: User = Depends(require_roles(*TEMPLATE_ROLES))):
    q = db.query(ReportTemplate)
    if kind in ("pretest", "retest"):
        q = q.filter(ReportTemplate.kind == kind)
    rows = q.order_by(ReportTemplate.kind, ReportTemplate.version.desc()).all()
    return [tpl_out(t) for t in rows]


@router.post("", status_code=201)
def upload_template(kind: str = Form(...), notes: str = Form(""), file: UploadFile = File(...),
                    db: Session = Depends(get_db), user: User = Depends(require_roles(*TEMPLATE_ROLES))):
    if kind not in ("pretest", "retest"):
        raise HTTPException(422, "Jenis templat harus 'pretest' atau 'retest'")
    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(415, "Templat harus berformat .docx")
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "Templat terlalu besar")
    validation = _validate_docx(data)
    last = db.query(ReportTemplate.version).filter(ReportTemplate.kind == kind) \
        .order_by(ReportTemplate.version.desc()).first()
    safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", file.filename.split("/")[-1].split("\\")[-1])[:200]
    t = ReportTemplate(kind=kind, version=(last[0] if last else 0) + 1, status="draft", filename=safe_name,
                       notes=notes.strip()[:500], size=len(data), data=data, created_by_id=user.id)
    db.add(t)
    db.flush()
    audit.log(db, user, "report_template_uploaded", "report_template", t.id, f"{kind} v{t.version} {safe_name}")
    db.commit()
    return {**tpl_out(t), "validation": validation}


@router.get("/{tid}/validate")
def validate_template(tid: int, db: Session = Depends(get_db), _: User = Depends(require_roles(*TEMPLATE_ROLES))):
    t = _get(db, tid, with_data=True)
    return _validate_docx(t.data)


@router.post("/{tid}/activate")
def activate_template(tid: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*TEMPLATE_ROLES))):
    t = _get(db, tid)
    if t.status != "active":
        for other in db.query(ReportTemplate).filter(ReportTemplate.kind == t.kind,
                                                      ReportTemplate.status == "active").all():
            other.status = "archived"
        t.status, t.activated_at = "active", utcnow()
        audit.log(db, user, "report_template_activated", "report_template", t.id, f"{t.kind} v{t.version}")
        db.commit()
    return tpl_out(t)


@router.delete("/{tid}", status_code=204)
def delete_template(tid: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*TEMPLATE_ROLES))):
    t = _get(db, tid)
    if t.status != "draft":
        raise HTTPException(409, "Hanya versi draf yang dapat dihapus (aktif/arsip dipertahankan sebagai jejak)")
    audit.log(db, user, "report_template_deleted", "report_template", t.id, f"{t.kind} v{t.version}")
    db.delete(t)
    db.commit()
    return Response(status_code=204)


@router.get("/{tid}/download")
def download_template(tid: int, db: Session = Depends(get_db), _: User = Depends(require_roles(*TEMPLATE_ROLES))):
    t = _get(db, tid, with_data=True)
    return Response(t.data, media_type=DOCX_MIME, headers={
        "Content-Disposition": f'attachment; filename="{t.kind}-v{t.version}.docx"',
        "X-Content-Type-Options": "nosniff"})
