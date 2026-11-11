"""Mesin laporan: DOCX via python-docx (pretest & retest), PDF via LibreOffice (headless)."""
import io
import logging
import re
import shutil
import subprocess  # nosec B404 - argumen tetap, tanpa shell
import tempfile
from datetime import date
from pathlib import Path

from docx import Document

from .cvss import nomenclature
from docx.shared import Inches, Pt

log = logging.getLogger("scopeline.report")
SEV_LABEL = {"critical": "Kritis", "high": "Tinggi", "medium": "Sedang", "low": "Rendah", "none": "Informasional"}
STATUS_LABEL = {"open": "Terbuka", "fixed": "Diperbaiki", "retest_passed": "Lulus retest"}
ENG_LABEL = {"draft": "Draf", "active": "Aktif", "completed": "Selesai"}
REVIEW_LABEL = {"draft": "Draf", "in_review": "Menunggu review", "approved": "Disetujui",
                "changes_requested": "Perlu perubahan"}
RESULT_LABEL = {"passed": "Lulus", "failed": "Gagal", "partial": "Sebagian"}
KIND_LABEL = {"pretest": "Laporan Pretest (Awal)", "retest": "Laporan Retest (Verifikasi)"}
BUCKET_LABEL = {"closed": "Tertutup (lulus retest)", "still_open": "Masih terbuka",
                "unverified": "Diperbaiki, belum diverifikasi", "new": "Baru (muncul saat retest)"}
KNOWN_PLACEHOLDERS = {"client", "engagement", "period", "date", "report_type", "template_version", "status",
                      "content"}
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_]+)\s*\}\}")


class PdfUnavailable(RuntimeError):
    pass


def clean(text) -> str:
    return _CTRL.sub("", str(text if text is not None else ""))


# ---------------- perbandingan pretest vs retest ----------------
def compare_findings(findings: list[dict]) -> dict:
    """Kelompokkan temuan: tertutup / masih terbuka / belum diverifikasi / baru (muncul setelah retest pertama)."""
    starts = [r["created_at"] for f in findings for r in f["retests"]]
    cutoff = min(starts) if starts else None
    buckets: dict[str, list[dict]] = {"closed": [], "still_open": [], "unverified": [], "new": []}
    for f in findings:
        if cutoff is not None and f["created_at"] > cutoff:
            buckets["new"].append(f)
        elif f["status"] == "retest_passed":
            buckets["closed"].append(f)
        elif f["status"] == "fixed":
            buckets["unverified"].append(f)
        else:
            buckets["still_open"].append(f)
    return buckets


# ---------------- templat ----------------
def _containers(doc):
    yield doc
    for s in doc.sections:
        yield s.header
        yield s.footer


def _paragraphs(doc):
    for c in _containers(doc):
        yield from c.paragraphs
        for table in c.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from cell.paragraphs


def scan_placeholders(doc) -> dict:
    """Validasi templat: placeholder yang ditemukan, yang tidak dikenal, dan keberadaan penanda {{content}}."""
    found: set[str] = set()
    for p in _paragraphs(doc):
        found.update(m.group(1).lower() for m in _PLACEHOLDER.finditer(p.text))
    return {"placeholders": sorted(found), "unknown": sorted(found - KNOWN_PLACEHOLDERS),
            "has_content_marker": "content" in found, "known": sorted(KNOWN_PLACEHOLDERS)}


def _replace_placeholders(doc, mapping: dict) -> None:
    def repl(m):
        key = m.group(1).lower()
        return clean(mapping[key]) if key in mapping and key != "content" else m.group(0)
    for p in _paragraphs(doc):
        if "{{" in p.text:
            new = _PLACEHOLDER.sub(repl, p.text)
            if new != p.text and p.runs:
                p.runs[0].text = new
                for r in p.runs[1:]:
                    r.text = ""


def _find_marker(doc):
    for p in doc.paragraphs:
        m = _PLACEHOLDER.fullmatch(p.text.strip())
        if m and m.group(1).lower() == "content":
            return p
    return None


def _body_children(doc):
    return [el for el in doc.element.body.iterchildren() if not el.tag.endswith("}sectPr")]


# ---------------- komponen dokumen ----------------
def _heading(doc, text: str, level: int):
    try:
        return doc.add_heading(clean(text), level=level)
    except KeyError:  # templat kustom tanpa gaya heading
        p = doc.add_paragraph()
        p.add_run(clean(text)).bold = True
        return p


def _table(doc, rows: int, cols: int):
    try:
        return doc.add_table(rows=rows, cols=cols, style="Table Grid")
    except KeyError:
        return doc.add_table(rows=rows, cols=cols)


def _kv_table(doc, pairs):
    t = _table(doc, len(pairs), 2)
    for i, (k, v) in enumerate(pairs):
        t.cell(i, 0).text, t.cell(i, 1).text = k, clean(v)
        t.cell(i, 0).paragraphs[0].runs[0].bold = True


def _grid(doc, header, rows):
    t = _table(doc, len(rows) + 1, len(header))
    for i, h in enumerate(header):
        t.cell(0, i).text = h
        t.cell(0, i).paragraphs[0].runs[0].bold = True
    for r, row in enumerate(rows, start=1):
        for c, v in enumerate(row):
            t.cell(r, c).text = clean(v)
    return t


def _evidence_block(doc, items, evidence_dir: Path, title: str = "Bukti"):
    if not items:
        return
    doc.add_paragraph().add_run(title).bold = True
    for ev in items:
        blob = ev.get("data")
        path = evidence_dir / ev.get("stored_name", "")
        if blob is None and ev.get("stored_name") and path.is_file():
            blob = path.read_bytes()
        if ev["content_type"] in ("image/png", "image/jpeg", "image/gif") and blob is not None:
            try:
                doc.add_picture(io.BytesIO(blob), width=Inches(5.5))
                cap = doc.add_paragraph(clean(ev["filename"]))
                cap.runs[0].font.size = Pt(8)
                continue
            except Exception:  # noqa: BLE001 - gambar rusak: cukup cantumkan nama
                log.warning("Gambar bukti tidak dapat disisipkan: %s", ev["filename"])
        doc.add_paragraph(f"• {clean(ev['filename'])}")


def _finding_detail(doc, f: dict, evidence_dir: Path, *, show_review: bool, with_retests: bool):
    _heading(doc, f"{f['code']} [{SEV_LABEL[f['severity']]}] {f['title']}", 2)
    cvss_label = (nomenclature(f["cvss_vector"]) + " v4.0") if f.get("cvss_version") == "4.0" else "CVSS v3.1 (historis)"
    meta = [(cvss_label, f"{f['cvss_score']} ({SEV_LABEL[f['severity']]})"), ("Vektor", f["cvss_vector"]),
            ("Status", STATUS_LABEL.get(f["status"], f["status"])),
            ("Tenggat perbaikan", str(f["due_date"] or "-"))]
    if show_review:
        meta.append(("Status review", REVIEW_LABEL.get(f["review_status"], f["review_status"])))
    if f.get("cvss_legacy_vector"):
        legacy_severity = f.get("cvss_legacy_severity")
        legacy_label = SEV_LABEL.get(legacy_severity, legacy_severity)
        legacy_version = f.get("cvss_legacy_version") or "CVSS v3.1"
        meta.extend([
            (f"Riwayat {legacy_version}", f"{f.get('cvss_legacy_score')} ({legacy_label})"),
            ("Vektor historis", f["cvss_legacy_vector"]),
        ])
    _kv_table(doc, meta)
    for label, key in (("Deskripsi", "description"), ("Dampak", "impact"), ("Rekomendasi", "recommendation")):
        doc.add_paragraph().add_run(label).bold = True
        doc.add_paragraph(clean(f[key]) or "-")
    if f["retest_notes"] and not with_retests:
        p = doc.add_paragraph()
        p.add_run("Catatan perbaikan: ").bold = True
        p.add_run(clean(f["retest_notes"]))
    _evidence_block(doc, f["evidence"], evidence_dir)
    if with_retests and f["retests"]:
        doc.add_paragraph().add_run("Riwayat retest").bold = True
        _grid(doc, ["Ronde", "Tanggal", "Penguji", "Hasil", "Catatan"],
              [[r["round_no"], r["tested_at"], r["tester"] or "-", RESULT_LABEL.get(r["result"], r["result"]),
                r["notes"] or "-"] for r in f["retests"]])
        for r in f["retests"]:
            _evidence_block(doc, r["evidence"], evidence_dir, f"Bukti retest ronde {r['round_no']}")


def _severity_summary(doc, findings):
    counts = {s: 0 for s in SEV_LABEL}
    for f in findings:
        counts[f["severity"]] += 1
    doc.add_paragraph(f"Total temuan: {len(findings)}")
    t = _table(doc, 2, len(SEV_LABEL))
    for i, s in enumerate(SEV_LABEL):
        t.cell(0, i).text, t.cell(1, i).text = SEV_LABEL[s], str(counts[s])
        t.cell(0, i).paragraphs[0].runs[0].bold = True


def _common_header(doc, eng, period, findings, hidden):
    _heading(doc, "1. Ringkasan Engagement", 1)
    _kv_table(doc, [("Engagement", eng["name"]), ("Klien", eng["client"]), ("Periode", period),
                    ("Status", ENG_LABEL.get(eng["status"], eng["status"])),
                    ("Tim", ", ".join(m["full_name"] for m in eng["members"]) or "-")])
    doc.add_paragraph()
    _severity_summary(doc, findings)
    if hidden:
        doc.add_paragraph(f"Catatan: {hidden} temuan belum disetujui peninjau dan tidak disertakan dalam laporan ini.")


def _scope_roe(doc, eng):
    _heading(doc, "2. Ruang Lingkup", 1)
    doc.add_paragraph(clean(eng["scope"]) or "-")
    _heading(doc, "3. Rules of Engagement", 1)
    doc.add_paragraph(clean(eng["roe_text"]) or "-")
    if eng["roe_approved"]:
        when = f"{eng['roe_approved_at']:%Y-%m-%d %H:%M}"
        doc.add_paragraph(f"Disetujui oleh {clean(eng['roe_approved_by'])} pada {when} UTC.")


def _content_pretest(doc, eng, findings, period, evidence_dir, hidden, draft):
    _common_header(doc, eng, period, findings, hidden)
    _scope_roe(doc, eng)
    _heading(doc, "4. Temuan", 1)
    if not findings:
        doc.add_paragraph("Tidak ada temuan yang disertakan.")
    for f in sorted(findings, key=lambda x: (-x["cvss_score"], x["number"])):
        _finding_detail(doc, f, evidence_dir, show_review=draft, with_retests=False)


def _content_retest(doc, eng, findings, period, evidence_dir, hidden, draft):
    _common_header(doc, eng, period, findings, hidden)
    buckets = compare_findings(findings)
    _heading(doc, "2. Perbandingan Pretest dan Retest", 1)
    _grid(doc, ["Kategori", "Jumlah"], [[BUCKET_LABEL[k], len(v)] for k, v in buckets.items()])
    doc.add_paragraph()
    baseline = len(findings) - len(buckets["new"])
    pct = round(len(buckets["closed"]) * 100 / baseline) if baseline else 0
    closed = len(buckets["closed"])
    doc.add_paragraph(f"Dari {baseline} temuan awal, {closed} ({pct}%) telah tertutup dan lulus retest.")
    n = 3
    for key, items in buckets.items():
        if not items:
            continue
        _heading(doc, f"{n}. {BUCKET_LABEL[key]}", 1)
        n += 1
        _grid(doc, ["ID", "Judul", "Keparahan", "CVSS (versi)", "Ronde retest", "Hasil terakhir"],
              [[f["code"], f["title"], SEV_LABEL[f["severity"]],
                f"{f['cvss_score']} (v{f.get('cvss_version', '3.1')})", len(f["retests"]),
                RESULT_LABEL.get(f["retests"][-1]["result"], "-") if f["retests"] else "-"]
               for f in sorted(items, key=lambda x: (-x["cvss_score"], x["number"]))])
    _heading(doc, f"{n}. Rincian Temuan dan Riwayat Retest", 1)
    for f in sorted(findings, key=lambda x: (-x["cvss_score"], x["number"])):
        _finding_detail(doc, f, evidence_dir, show_review=draft, with_retests=True)
    if not findings:
        doc.add_paragraph("Tidak ada temuan yang disertakan.")


def build_docx(kind: str, eng: dict, findings: list[dict], *, evidence_dir: Path,
               template_bytes: bytes | None = None, template_label: str = "bawaan",
               hidden: int = 0, draft: bool = False) -> bytes:
    doc = Document(io.BytesIO(template_bytes)) if template_bytes else Document()
    period = f"{eng['start_date']} s.d. {eng['end_date']}"
    today = date.today().isoformat()
    _replace_placeholders(doc, {
        "engagement": eng["name"], "client": eng["client"], "period": period, "date": today,
        "report_type": KIND_LABEL[kind] + (" - DRAF" if draft else ""), "template_version": template_label,
        "status": ENG_LABEL.get(eng["status"], eng["status"])})
    marker = _find_marker(doc) if template_bytes else None
    if not template_bytes:
        doc.add_heading(KIND_LABEL[kind], 0)
    if draft:
        p = doc.add_paragraph()
        p.add_run("DRAF - memuat temuan yang belum disetujui peninjau. Bukan dokumen final.").bold = True

    before = len(_body_children(doc))
    body = _content_retest if kind == "retest" else _content_pretest
    body(doc, eng, findings, period, evidence_dir, hidden, draft)
    if marker is not None:  # sisipkan konten di posisi penanda {{content}} pada templat
        for el in _body_children(doc)[before:]:
            marker._p.addprevious(el)
        marker._p.getparent().remove(marker._p)

    foot = doc.add_paragraph(f"Dibuat oleh SCOPELINE | templat {kind}: {template_label} | {today} | CVSS owned by FIRST and used by permission.")
    foot.runs[0].font.size = Pt(8)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def docx_to_pdf(data: bytes) -> bytes:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise PdfUnavailable("LibreOffice tidak tersedia pada server")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "report.docx"
        src.write_bytes(data)
        try:
            subprocess.run([soffice, "--headless", "--norestore",  # nosec B603
                            f"-env:UserInstallation=file://{tmp}/profile",
                            "--convert-to", "pdf", "--outdir", tmp, str(src)],
                           check=True, timeout=180, capture_output=True)
        except (subprocess.SubprocessError, OSError) as exc:
            raise PdfUnavailable("Konversi PDF gagal") from exc
        out = Path(tmp) / "report.pdf"
        if not out.is_file():
            raise PdfUnavailable("Konversi PDF gagal")
        return out.read_bytes()
