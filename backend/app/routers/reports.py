import hashlib
import json
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, undefer

from .. import audit
from ..config import settings
from ..database import get_db
from ..deps import (
    STAFF,
    accessible_engagements,
    current_user,
    load_engagement,
    require_roles,
)
from ..models import AuditLog, ReportApproval, ReportTemplate, User, utcnow
from ..reporting import BUCKET_LABEL, PdfUnavailable, build_docx, compare_findings, docx_to_pdf
from .engagements import eng_out
from .findings import finding_out

router = APIRouter(prefix="/api", tags=["reports"])
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _active_template(db: Session, kind: str):
    return (db.query(ReportTemplate).options(undefer(ReportTemplate.data))
            .filter(ReportTemplate.kind == kind, ReportTemplate.status == "active").first())


def _report_fingerprint(e, kind: str, tpl) -> str:
    payload = {
        "kind": kind,
        "template": None if tpl is None else {
            "id": tpl.id, "version": tpl.version,
            "sha256": hashlib.sha256(tpl.data).hexdigest(),
        },
        "engagement": {
            "id": e.id, "name": e.name, "client": e.client, "scope": e.scope,
            "start_date": e.start_date.isoformat(), "end_date": e.end_date.isoformat(),
            "roe_text": e.roe_text, "status": e.status,
        },
        "findings": [{
            "id": f.id, "number": f.number, "title": f.title, "description": f.description,
            "impact": f.impact, "recommendation": f.recommendation, "cvss_vector": f.cvss_vector,
            "cvss_version": f.cvss_version, "cvss_score": f.cvss_score, "severity": f.severity,
            "status": f.status, "review_status": f.review_status, "review_note": f.review_note,
            "retests": [{"round_no": rt.round_no, "result": rt.result,
                         "tested_at": rt.tested_at.isoformat(), "notes": rt.notes}
                        for rt in f.retests],
            "evidence": [{"filename": ev.filename, "size": ev.size}
                         for ev in f.evidence if ev.retest_id is None],
        } for f in e.findings if f.review_status == "approved"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _selected(e, include_unapproved: bool):
    """Laporan final hanya memuat temuan yang sudah disetujui peninjau."""
    chosen = [f for f in e.findings if include_unapproved or f.review_status == "approved"]
    return chosen, len(e.findings) - len(chosen)


@router.post("/engagements/{eid}/reports/{kind}/approve")
def approve_report(eid: int, kind: str, db: Session = Depends(get_db),
                   user: User = Depends(require_roles("lead", "reviewer"))):
    if kind not in ("pretest", "retest"):
        raise HTTPException(422, "Jenis laporan tidak valid")
    e = load_engagement(db, user, eid)
    if e.status not in ("active", "completed") or not e.roe_approved:
        raise HTTPException(409, "Laporan hanya dapat disetujui pada engagement aktif/selesai dengan RoE disetujui")
    fingerprint = _report_fingerprint(e, kind, _active_template(db, kind))
    row = db.query(ReportApproval).filter_by(
        engagement_id=e.id, kind=kind, approver_role=user.role).first()
    if row is None:
        row = ReportApproval(engagement_id=e.id, kind=kind, approver_role=user.role,
                             approved_by_id=user.id, fingerprint=fingerprint, approved_at=utcnow())
        db.add(row)
    else:
        row.approved_by_id, row.fingerprint, row.approved_at = user.id, fingerprint, utcnow()
    audit.log(db, user, "report_approved", "engagement", e.id, f"{kind}:{user.role}:{fingerprint[:12]}")
    db.commit()
    return {"kind": kind, "role": user.role, "approved": True, "fingerprint": fingerprint}


@router.get("/engagements/{eid}/reports/{kind}/approvals")
def report_approvals(eid: int, kind: str, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    if kind not in ("pretest", "retest"):
        raise HTTPException(422, "Jenis laporan tidak valid")
    e = load_engagement(db, user, eid)
    fingerprint = _report_fingerprint(e, kind, _active_template(db, kind))
    rows = db.query(ReportApproval).filter_by(
        engagement_id=e.id, kind=kind, fingerprint=fingerprint).all()
    roles = {row.approver_role for row in rows}
    return {
        "kind": kind, "fingerprint": fingerprint,
        "project_manager": {"approved": "lead" in roles},
        "engineer_head_offensive_security": {"approved": "reviewer" in roles},
        "final_approved": {"lead", "reviewer"}.issubset(roles),
    }


@router.get("/engagements/{eid}/report")
def export_report(eid: int, format: str = Query("docx", pattern="^(docx|pdf)$"),
                  kind: str = Query("pretest", pattern="^(pretest|retest)$"), include_unapproved: bool = False,
                  db: Session = Depends(get_db), user: User = Depends(current_user)):
    e = load_engagement(db, user, eid)
    chosen, hidden = _selected(e, include_unapproved)
    tpl = _active_template(db, kind)
    if not include_unapproved:
        fingerprint = _report_fingerprint(e, kind, tpl)
        roles = {a.approver_role for a in db.query(ReportApproval).filter_by(
            engagement_id=e.id, kind=kind, fingerprint=fingerprint).all()}
        if not {"lead", "reviewer"}.issubset(roles):
            raise HTTPException(409, "Laporan final memerlukan persetujuan Project Manager dan Engineer-Head Offensive Security untuk versi data saat ini")
    with_ev = user.role not in ("writer", "admin")  # Admin dan Technical Writer tidak mendapat raw evidence
    findings = [finding_out(f, with_evidence=with_ev, blobs=True) for f in chosen]
    draft = any(f["review_status"] != "approved" for f in findings)
    label = f"v{tpl.version}" if tpl else "bawaan"
    docx = build_docx(kind, eng_out(e), findings, evidence_dir=settings.evidence_dir,
                      template_bytes=tpl.data if tpl else None, template_label=label, hidden=hidden, draft=draft)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", e.name).strip("-")[:40] or f"engagement-{e.id}"
    if format == "pdf":
        if not settings.enable_pdf:
            raise HTTPException(503, "Ekspor PDF dinonaktifkan di server ini. Gunakan DOCX.")
        try:
            body, mime = docx_to_pdf(docx), "application/pdf"
        except PdfUnavailable as exc:
            raise HTTPException(503, str(exc))
    else:
        body, mime = docx, DOCX_MIME
    audit.log(db, user, "report_exported", "engagement", e.id,
              f"{format} {kind} templat={label} draf={draft} disembunyikan={hidden}")
    db.commit()
    return Response(body, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="laporan-{kind}-{slug}.{format}"'})


@router.get("/engagements/{eid}/comparison")
def comparison(eid: int, include_unapproved: bool = False, db: Session = Depends(get_db),
               user: User = Depends(current_user)):
    """Perbandingan pretest vs retest: tertutup, masih terbuka, belum diverifikasi, baru."""
    e = load_engagement(db, user, eid)
    chosen, hidden = _selected(e, include_unapproved)
    buckets = compare_findings([finding_out(f, with_evidence=False) for f in chosen])
    slim = {k: [{"id": f["id"], "code": f["code"], "title": f["title"], "severity": f["severity"],
                 "cvss_score": f["cvss_score"], "status": f["status"], "rounds": len(f["retests"])} for f in v]
            for k, v in buckets.items()}
    return {"buckets": slim, "counts": {k: len(v) for k, v in slim.items()}, "labels": BUCKET_LABEL,
            "hidden_unapproved": hidden}


# ---- Dasbor & log audit ----
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    engs = accessible_engagements(db, user)
    sev = {s: 0 for s in ("critical", "high", "medium", "low", "none")}
    status = {s: 0 for s in ("open", "fixed", "retest_passed")}
    eng_status = {s: 0 for s in ("draft", "active", "completed")}
    month_keys = []
    y, m = date.today().year, date.today().month
    for _ in range(6):
        month_keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    monthly = {k: 0 for k in reversed(month_keys)}
    review = {s: 0 for s in ("draft", "in_review", "approved", "changes_requested")}
    overdue = open_high = total = 0
    for e in engs:
        eng_status[e.status] += 1
        for f in e.findings:
            total += 1
            sev[f.severity] += 1
            status[f.status] += 1
            review[f.review_status] += 1
            key = f"{f.created_at:%Y-%m}"
            if key in monthly:
                monthly[key] += 1
            if f.status == "open" and f.severity in ("critical", "high"):
                open_high += 1
            if f.status == "open" and f.due_date and f.due_date < date.today():
                overdue += 1
    return {"engagements": len(engs), "findings": total, "open_critical_high": open_high,
            "overdue": overdue, "by_severity": sev, "by_status": status, "by_review": review,
            "pending_review": review["in_review"],
            "engagements_by_status": eng_status, "findings_per_month": monthly}


@router.get("/audit")
def audit_log(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db),
              _: User = Depends(require_roles(*STAFF))):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return [{"id": r.id, "created_at": r.created_at, "username": r.username, "action": r.action,
             "entity": r.entity, "entity_id": r.entity_id, "detail": r.detail} for r in rows]
