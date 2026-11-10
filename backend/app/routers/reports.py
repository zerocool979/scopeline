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
from ..models import AuditLog, ReportTemplate, User
from ..reporting import BUCKET_LABEL, PdfUnavailable, build_docx, compare_findings, docx_to_pdf
from .engagements import eng_out
from .findings import finding_out

router = APIRouter(prefix="/api", tags=["reports"])
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _selected(e, include_unapproved: bool):
    """Laporan final hanya memuat temuan yang sudah disetujui peninjau."""
    chosen = [f for f in e.findings if include_unapproved or f.review_status == "approved"]
    return chosen, len(e.findings) - len(chosen)


@router.get("/engagements/{eid}/report")
def export_report(eid: int, format: str = Query("docx", pattern="^(docx|pdf)$"),
                  kind: str = Query("pretest", pattern="^(pretest|retest)$"), include_unapproved: bool = False,
                  db: Session = Depends(get_db), user: User = Depends(current_user)):
    e = load_engagement(db, user, eid)
    chosen, hidden = _selected(e, include_unapproved)
    with_ev = user.role != "writer"  # Technical Writer: laporan tanpa bukti mentah
    findings = [finding_out(f, with_evidence=with_ev, blobs=True) for f in chosen]
    draft = any(f["review_status"] != "approved" for f in findings)
    tpl = (db.query(ReportTemplate).options(undefer(ReportTemplate.data))
           .filter(ReportTemplate.kind == kind, ReportTemplate.status == "active").first())
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
