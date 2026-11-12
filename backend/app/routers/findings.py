import csv
import io
import re
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..cvss import CvssError, calculate, nomenclature, normalize_vector
from ..database import get_db
from ..deps import AUTHORS, REVIEWERS, STAFF, TEXT_EDITORS, WRITERS, current_user, load_engagement, require_roles
from ..models import AuditLog, Engagement, Evidence, Finding, FindingTemplate, Retest, User
from ..schemas import CvssIn, FindingIn, FindingStatusIn, FindingUpdate, RetestIn, ReviewIn, TemplateIn

router = APIRouter(prefix="/api", tags=["findings"])

ALLOWED_UPLOAD = {
    "png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    "jpg": ("image/jpeg", b"\xff\xd8\xff"),
    "jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    "gif": ("image/gif", b"GIF8"),
    "pdf": ("application/pdf", b"%PDF-"),
    "txt": ("text/plain", None),
    "log": ("text/plain", None),
}
MAX_EVIDENCE_PER_FINDING = 20


TEXT_FIELDS = {"title", "description", "impact", "recommendation"}


def _ev_out(ev: Evidence, blobs: bool = False) -> dict:
    out = {"id": ev.id, "filename": ev.filename, "size": ev.size, "content_type": ev.content_type}
    if blobs:  # hanya untuk mesin laporan
        out["stored_name"], out["data"] = ev.stored_name, ev.data
    return out


def retest_out(r: Retest, with_evidence: bool = True, blobs: bool = False) -> dict:
    return {"id": r.id, "round_no": r.round_no, "result": r.result, "tested_at": r.tested_at, "notes": r.notes,
            "tester": r.tester.full_name if r.tester else None, "created_at": r.created_at,
            "evidence": [_ev_out(ev, blobs) for ev in r.evidence] if with_evidence else []}


def finding_out(f: Finding, with_evidence: bool = True, blobs: bool = False) -> dict:
    """with_evidence=False dipakai untuk Technical Writer (tanpa akses bukti mentah)."""
    return {
        "id": f.id, "engagement_id": f.engagement_id, "number": f.number, "code": f"F-{f.number:03d}",
        "title": f.title, "description": f.description, "impact": f.impact,
        "recommendation": f.recommendation, "cvss_vector": f.cvss_vector, "cvss_version": f.cvss_version,
        "cvss_nomenclature": nomenclature(f.cvss_vector) if f.cvss_version == "4.0" else "CVSS v3.1",
        "cvss_score": f.cvss_score, "severity": f.severity,
        "cvss_legacy_vector": f.cvss_legacy_vector, "cvss_legacy_score": f.cvss_legacy_score,
        "cvss_legacy_severity": f.cvss_legacy_severity, "cvss_legacy_version": f.cvss_legacy_version,
        "status": f.status, "retest_notes": f.retest_notes,
        "review_status": f.review_status, "review_note": f.review_note, "created_by_id": f.created_by_id,
        "due_date": f.due_date, "created_at": f.created_at, "updated_at": f.updated_at,
        "evidence": [_ev_out(ev, blobs) for ev in f.evidence if ev.retest_id is None] if with_evidence else [],
        "retests": [retest_out(r, with_evidence, blobs) for r in f.retests],
    }


def _out(f: Finding, user: User) -> dict:
    return finding_out(f, with_evidence=user.role not in ("writer", "admin"))


def _score(vector: str) -> tuple[float, str]:
    try:
        return calculate(vector)
    except CvssError as exc:
        raise HTTPException(422, str(exc))


def _ensure_active(e: Engagement) -> None:
    if e.status != "active" or not e.roe_approved:
        raise HTTPException(409, "Temuan hanya dapat diubah saat engagement aktif dan RoE disetujui")


def _ensure_reportable(e: Engagement) -> None:
    """Review dan penyuntingan teks laporan boleh berlangsung juga setelah pengujian selesai."""
    if e.status not in ("active", "completed") or not e.roe_approved:
        raise HTTPException(409, "Aksi ini hanya dapat dilakukan pada engagement aktif/selesai dengan RoE disetujui")


def _load_finding(db: Session, user: User, fid: int) -> tuple[Finding, Engagement]:
    f = db.get(Finding, fid)
    if not f:
        raise HTTPException(404, "Temuan tidak ditemukan")
    return f, load_engagement(db, user, f.engagement_id)  # 404 bila tidak ditugaskan


def _create_finding(db: Session, e: Engagement, user: User, data: FindingIn) -> Finding:
    score, sev = _score(data.cvss_vector)
    vector = normalize_vector(data.cvss_vector)
    nxt = (db.query(func.max(Finding.number)).filter(Finding.engagement_id == e.id).scalar() or 0) + 1
    f = Finding(engagement_id=e.id, number=nxt, created_by_id=user.id, cvss_score=score, severity=sev,
                cvss_version="4.0", **data.model_dump(exclude={"cvss_vector"}), cvss_vector=vector)
    db.add(f)
    db.flush()
    audit.log(db, user, "finding_created", "finding", f.id, f"{e.name}: {f.title}")
    return f


@router.post("/cvss/calc")
def cvss_calc(data: CvssIn, _: User = Depends(current_user)):
    score, sev = _score(data.vector)
    return {"vector": normalize_vector(data.vector), "version": "4.0",
            "nomenclature": nomenclature(data.vector), "score": score, "severity": sev}


@router.get("/engagements/{eid}/findings")
def list_findings(eid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    e = load_engagement(db, user, eid)
    return [_out(f, user) for f in e.findings]


@router.post("/engagements/{eid}/findings", status_code=201)
def create_finding(eid: int, data: FindingIn, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(*WRITERS))):
    e = load_engagement(db, user, eid)
    _ensure_active(e)
    f = _create_finding(db, e, user, data)
    db.commit()
    return _out(f, user)


@router.post("/engagements/{eid}/findings/import")
def import_findings(eid: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                    user: User = Depends(require_roles(*WRITERS))):
    """Impor CSV (kolom: title,description,impact,recommendation,cvss_vector). Hanya data temuan."""
    e = load_engagement(db, user, eid)
    _ensure_active(e)
    raw = file.file.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise HTTPException(413, "Berkas CSV terlalu besar (maks 1 MB)")
    try:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error):
        raise HTTPException(422, "CSV tidak valid (gunakan UTF-8)")
    if len(rows) > 500:
        raise HTTPException(413, "Maksimal 500 baris per impor")
    created, errors = 0, []
    for i, row in enumerate(rows, start=2):
        try:
            data = FindingIn(**{k: (row.get(k) or "") for k in
                                ("title", "description", "impact", "recommendation", "cvss_vector")})
            _create_finding(db, e, user, data)
            created += 1
        except (ValidationError, HTTPException) as exc:
            msg = exc.detail if isinstance(exc, HTTPException) else "data tidak valid"
            errors.append({"line": i, "error": str(msg)})
    audit.log(db, user, "findings_imported", "engagement", e.id, f"{created} dibuat, {len(errors)} gagal")
    db.commit()
    return {"created": created, "errors": errors}


@router.get("/findings/{fid}")
def get_finding(fid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f, _ = _load_finding(db, user, fid)
    return _out(f, user)


@router.patch("/findings/{fid}")
def update_finding(fid: int, data: FindingUpdate, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(*TEXT_EDITORS))):
    f, e = _load_finding(db, user, fid)
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k == "due_date"}
    if user.role == "writer":
        if set(changes) - TEXT_FIELDS:
            raise HTTPException(403, "Technical Writer hanya dapat mengubah teks temuan")
        _ensure_reportable(e)
    else:
        _ensure_active(e)
    if "cvss_vector" in changes:
        changes["cvss_vector"] = normalize_vector(changes["cvss_vector"])
        if f.cvss_version == "3.1" and f.cvss_legacy_vector is None:
            f.cvss_legacy_vector = f.cvss_vector
            f.cvss_legacy_score = f.cvss_score
            f.cvss_legacy_severity = f.severity
            f.cvss_legacy_version = "3.1"
        f.cvss_version = "4.0"
    content_changed = any(k in changes and changes[k] != getattr(f, k) for k in TEXT_FIELDS | {"cvss_vector"})
    if "cvss_vector" in changes:
        f.cvss_score, f.severity = _score(changes["cvss_vector"])
    for k, v in changes.items():
        setattr(f, k, v)
    if content_changed and f.review_status in ("approved", "in_review"):
        f.review_status = "draft"  # isi berubah -> perlu ditinjau ulang
        audit.log(db, user, "finding_review_reset", "finding", f.id, "isi berubah, kembali ke draf")
    audit.log(db, user, "finding_updated", "finding", f.id, ", ".join(changes))
    db.commit()
    return _out(f, user)


@router.post("/findings/{fid}/status")
def set_finding_status(fid: int, data: FindingStatusIn, db: Session = Depends(get_db),
                       user: User = Depends(require_roles(*WRITERS))):
    f, e = _load_finding(db, user, fid)
    _ensure_active(e)
    old = f.status
    f.status = data.status
    if data.notes:
        f.retest_notes = data.notes
    audit.log(db, user, "finding_status", "finding", f.id, f"{old}->{data.status}: {data.notes}")
    db.commit()
    return _out(f, user)


@router.post("/findings/{fid}/review")
def review_finding(fid: int, data: ReviewIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Alur review: draf -> menunggu review -> disetujui / perlu perubahan (prinsip empat mata)."""
    f, e = _load_finding(db, user, fid)
    _ensure_reportable(e)
    if data.action == "submit":
        if user.role not in AUTHORS:
            raise HTTPException(403, "Anda tidak dapat mengajukan review")
        if f.review_status not in ("draft", "changes_requested"):
            raise HTTPException(409, "Temuan sudah diajukan atau disetujui")
        f.review_status, f.review_note = "in_review", data.note.strip()
    else:
        if user.role not in REVIEWERS:
            raise HTTPException(403, "Hanya Peninjau/Lead/Admin yang dapat meninjau temuan")
        if f.review_status != "in_review":
            raise HTTPException(409, "Temuan belum diajukan untuk review")
        if data.action == "approve":
            if f.created_by_id == user.id:
                raise HTTPException(403, "Tidak dapat menyetujui temuan buatan sendiri (empat mata)")
            f.review_status = "approved"
        else:
            if not data.note.strip():
                raise HTTPException(422, "Catatan wajib diisi saat meminta perubahan")
            f.review_status = "changes_requested"
        f.review_note = data.note.strip()
    audit.log(db, user, f"finding_review_{data.action}", "finding", f.id, data.note[:300])
    db.commit()
    return _out(f, user)


@router.post("/findings/{fid}/retests", status_code=201)
def add_retest(fid: int, data: RetestIn, db: Session = Depends(get_db),
               user: User = Depends(require_roles(*WRITERS))):
    """Catat satu ronde retest. Hasil 'passed' -> status lulus retest; 'failed'/'partial' -> terbuka kembali."""
    f, e = _load_finding(db, user, fid)
    _ensure_active(e)
    nxt = (db.query(func.max(Retest.round_no)).filter(Retest.finding_id == f.id).scalar() or 0) + 1
    r = Retest(finding_id=f.id, round_no=nxt, result=data.result, tested_at=data.tested_at or date.today(),
               notes=data.notes.strip(), tester_id=user.id)
    db.add(r)
    old = f.status
    f.status = "retest_passed" if data.result == "passed" else "open"
    db.flush()
    audit.log(db, user, "retest_recorded", "finding", f.id, f"ronde {nxt}: {data.result}; {old}->{f.status}")
    db.commit()
    return _out(f, user)


@router.post("/retests/{rid}/evidence", status_code=201)
def upload_retest_evidence(rid: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                           user: User = Depends(require_roles("lead", "tester"))):
    r = db.get(Retest, rid)
    if not r:
        raise HTTPException(404, "Ronde retest tidak ditemukan")
    f, e = _load_finding(db, user, r.finding_id)
    _ensure_active(e)
    _store_evidence(db, user, f, file, retest=r)
    db.commit()
    return _out(f, user)


@router.get("/findings/{fid}/history")
def finding_history(fid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    f, _ = _load_finding(db, user, fid)
    rows = (db.query(AuditLog).filter(AuditLog.entity == "finding", AuditLog.entity_id == f.id)
            .order_by(AuditLog.id.desc()).limit(100).all())
    return [{"created_at": r.created_at, "username": r.username, "action": r.action, "detail": r.detail}
            for r in rows]


@router.delete("/findings/{fid}", status_code=204)
def delete_finding(fid: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    f, e = _load_finding(db, user, fid)
    _ensure_active(e)
    for ev in f.evidence:
        (settings.evidence_dir / ev.stored_name).unlink(missing_ok=True)
    audit.log(db, user, "finding_deleted", "finding", f.id, f.title)
    db.delete(f)
    db.commit()
    return Response(status_code=204)


# ---- Bukti ----
def _store_evidence(db: Session, user: User, f: Finding, file: UploadFile, retest: Retest | None = None) -> Evidence:
    if len([ev for ev in f.evidence if ev.retest_id is None]) + len(
            [ev for r in f.retests for ev in r.evidence]) >= MAX_EVIDENCE_PER_FINDING:
        raise HTTPException(409, "Jumlah bukti per temuan sudah maksimum")
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if ext not in ALLOWED_UPLOAD:
        raise HTTPException(415, "Tipe berkas tidak diizinkan (png, jpg, gif, pdf, txt, log)")
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"Ukuran berkas melebihi {settings.max_upload_bytes // 1024 // 1024} MB")
    ctype, magic = ALLOWED_UPLOAD[ext]
    if (magic and not data.startswith(magic)) or (magic is None and b"\x00" in data):
        raise HTTPException(415, "Isi berkas tidak sesuai dengan ekstensinya")
    stored = uuid.uuid4().hex
    if not settings.evidence_in_db:
        (settings.evidence_dir / stored).write_bytes(data)
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(file.filename).name)[:100] or f"bukti.{ext}"
    ev = Evidence(finding_id=f.id, retest_id=retest.id if retest else None, filename=name, stored_name=stored,
                  content_type=ctype, size=len(data), uploaded_by_id=user.id,
                  data=data if settings.evidence_in_db else None)
    db.add(ev)
    db.flush()
    db.refresh(f)
    where = f"retest ronde {retest.round_no}" if retest else "temuan"
    audit.log(db, user, "evidence_uploaded", "finding", f.id, f"{name} ({len(data)} B) -> {where}")
    return ev


@router.post("/findings/{fid}/evidence", status_code=201)
def upload_evidence(fid: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                    user: User = Depends(require_roles("lead", "tester"))):
    f, e = _load_finding(db, user, fid)
    _ensure_active(e)
    _store_evidence(db, user, f, file)
    db.commit()
    return _out(f, user)


def _load_evidence(db: Session, user: User, evid: int) -> tuple[Evidence, Finding, Engagement]:
    ev = db.get(Evidence, evid)
    if not ev:
        raise HTTPException(404, "Bukti tidak ditemukan")
    f, e = _load_finding(db, user, ev.finding_id)
    return ev, f, e


@router.get("/evidence/{evid}/download")
def download_evidence(evid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role in ("writer", "admin"):
        raise HTTPException(403, "Role ini tidak memiliki akses ke bukti mentah")
    ev, _, _ = _load_evidence(db, user, evid)
    path = settings.evidence_dir / ev.stored_name
    if ev.data is not None:
        content = ev.data
    elif path.is_file():
        content = path.read_bytes()
    else:
        raise HTTPException(404, "Berkas bukti hilang dari penyimpanan")
    return Response(content, media_type=ev.content_type, headers={
        "Content-Disposition": f'attachment; filename="{ev.filename}"', "X-Content-Type-Options": "nosniff"})


@router.delete("/evidence/{evid}", status_code=204)
def delete_evidence(evid: int, db: Session = Depends(get_db), user: User = Depends(require_roles("lead", "tester"))):
    ev, f, e = _load_evidence(db, user, evid)
    _ensure_active(e)
    (settings.evidence_dir / ev.stored_name).unlink(missing_ok=True)
    audit.log(db, user, "evidence_deleted", "finding", f.id, ev.filename)
    db.delete(ev)
    db.commit()
    return Response(status_code=204)


# ---- Pustaka templat temuan ----
@router.get("/finding-templates")
def list_templates(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = db.query(FindingTemplate).order_by(FindingTemplate.title).all()
    return [{"id": t.id, "title": t.title, "description": t.description, "impact": t.impact,
             "recommendation": t.recommendation, "cvss_vector": t.cvss_vector,
             "cvss_version": t.cvss_version} for t in rows]


@router.post("/finding-templates", status_code=201)
def create_template(data: TemplateIn, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    _score(data.cvss_vector)
    t = FindingTemplate(
        **data.model_dump(exclude={"cvss_vector"}),
        cvss_vector=normalize_vector(data.cvss_vector),
        cvss_version="4.0",
    )
    db.add(t)
    db.flush()
    audit.log(db, user, "template_created", "template", t.id, t.title)
    db.commit()
    return {"id": t.id}


@router.delete("/finding-templates/{tid}", status_code=204)
def delete_template(tid: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    t = db.get(FindingTemplate, tid)
    if not t:
        raise HTTPException(404, "Templat tidak ditemukan")
    audit.log(db, user, "template_deleted", "template", t.id, t.title)
    db.delete(t)
    db.commit()
    return Response(status_code=204)
