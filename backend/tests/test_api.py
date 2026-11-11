import io
import zipfile

import pyotp
import pytest
from conftest import PW, login

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
VEC = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:N"
FIND = {"title": "SQL Injection pada /login", "description": "Parameter user", "impact": "Data bocor",
        "recommendation": "Gunakan parameterized query", "cvss_vector": VEC}


def test_auth_required(client):
    assert client.get("/api/engagements").status_code == 401
    assert client.get("/api/engagements", headers={"Authorization": "Bearer abc"}).status_code == 401


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert client.get("/").status_code == 200


def test_login_lockout_and_generic_error(client, tokens):
    client.post("/api/users", headers=tokens["admin"], json={
        "username": "victim", "full_name": "V", "password": PW, "role": "tester"})
    msgs = set()
    for _ in range(5):
        r = login(client, "victim", "salah-salah-salah")
        assert r.status_code == 401
        msgs.add(r.json()["detail"])
    assert login(client, "tidak-ada", "x").json()["detail"] in msgs  # pesan sama
    assert login(client, "victim", PW).status_code == 429  # terkunci


def test_password_policy_and_rbac_users(client, tokens):
    h = tokens["admin"]
    r = client.post("/api/users", headers=h, json={"username": "pendek", "full_name": "P", "password": "abc", "role": "tester"})
    assert r.status_code == 422
    assert client.post("/api/users", headers=tokens["tester"], json={
        "username": "x1x", "full_name": "P", "password": PW, "role": "admin"}).status_code == 403
    assert client.post("/api/users", headers=h, json={
        "username": "lead", "full_name": "dup", "password": PW, "role": "lead"}).status_code == 409
    me = client.get("/api/auth/me", headers=h).json()
    assert client.patch(f"/api/users/{me['id']}", headers=h, json={"is_active": False}).status_code == 400


def test_password_change_invalidates_token(client, tokens):
    h = tokens["admin"]
    client.post("/api/users", headers=h, json={"username": "pwchg", "full_name": "P", "password": PW, "role": "reviewer"})
    tok = {"Authorization": f"Bearer {login(client, 'pwchg').json()['access_token']}"}
    assert client.post("/api/auth/change-password", headers=tok, json={
        "current_password": "salah-salah-salah", "new_password": PW + "x"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=tok, json={
        "current_password": PW, "new_password": PW + "x"}).status_code == 200
    assert client.get("/api/auth/me", headers=tok).status_code == 401
    assert login(client, "pwchg", PW + "x").status_code == 200


def test_mfa_flow(client, tokens):
    h = tokens["admin"]
    client.post("/api/users", headers=h, json={"username": "mfauser", "full_name": "M", "password": PW, "role": "lead"})
    tok = {"Authorization": f"Bearer {login(client, 'mfauser').json()['access_token']}"}
    secret = client.post("/api/auth/mfa/setup", headers=tok).json()["secret"]
    assert client.post("/api/auth/mfa/enable", headers=tok, json={"code": "000000"}).status_code == 400
    assert client.post("/api/auth/mfa/enable", headers=tok, json={"code": pyotp.TOTP(secret).now()}).status_code == 200
    assert login(client, "mfauser").status_code == 401  # tanpa OTP
    assert login(client, "mfauser", otp=pyotp.TOTP(secret).now()).status_code == 200
    assert client.post("/api/auth/mfa/disable", headers=tok, json={"password": PW}).status_code == 200


def test_roe_gating(client, tokens):
    lead = tokens["lead"]
    r = client.post("/api/engagements", headers=lead, json={
        "name": "Gating", "client": "X", "scope": "s", "start_date": "2026-01-01",
        "end_date": "2026-02-01", "roe_text": "r"})
    eid = r.json()["id"]
    assert r.json()["roe_approved"] is False
    assert client.post(f"/api/engagements/{eid}/status", headers=lead, json={"status": "active"}).status_code == 409
    assert client.post(f"/api/engagements/{eid}/roe/approve", headers=tokens["tester"]).status_code == 403
    assert client.post(f"/api/engagements/{eid}/roe/approve", headers=lead).json()["roe_approved"] is True
    assert client.post(f"/api/engagements/{eid}/status", headers=lead, json={"status": "active"}).status_code == 200
    # mengubah RoE membatalkan persetujuan dan menjeda pengujian
    r = client.patch(f"/api/engagements/{eid}", headers=lead, json={"roe_text": "baru"}).json()
    assert r["roe_approved"] is False and r["status"] == "draft"
    assert client.post(f"/api/engagements/{eid}/findings", headers=lead, json=FIND).status_code == 409
    assert client.post(f"/api/engagements/{eid}/roe/approve", headers=lead).status_code == 200
    assert client.post(f"/api/engagements/{eid}/status", headers=lead, json={"status": "completed"}).status_code == 409


def test_engagement_validation(client, tokens):
    r = client.post("/api/engagements", headers=tokens["lead"], json={
        "name": "Tanggal", "client": "X", "start_date": "2026-05-01", "end_date": "2026-01-01"})
    assert r.status_code == 422
    assert client.post("/api/engagements", headers=tokens["tester"], json={
        "name": "x", "client": "x", "start_date": "2026-01-01", "end_date": "2026-01-02"}).status_code == 403


def test_object_level_access(client, tokens, eng):
    assert client.get(f"/api/engagements/{eng}", headers=tokens["tester"]).status_code == 200
    assert client.get(f"/api/engagements/{eng}", headers=tokens["tester2"]).status_code == 404
    assert client.get(f"/api/engagements/{eng}/findings", headers=tokens["tester2"]).status_code == 404
    assert client.get(f"/api/engagements/{eng}/report", headers=tokens["tester2"]).status_code == 404
    assert eng not in [e["id"] for e in client.get("/api/engagements", headers=tokens["tester2"]).json()]


def test_findings_lifecycle(client, tokens, eng):
    t = tokens["tester"]
    assert client.post(f"/api/engagements/{eng}/findings", headers=tokens["reviewer"], json=FIND).status_code == 403
    assert client.post(f"/api/engagements/{eng}/findings", headers=tokens["tester2"], json=FIND).status_code == 404
    bad = dict(FIND, cvss_vector="CVSS:4.0/AV:Z")
    assert client.post(f"/api/engagements/{eng}/findings", headers=t, json=bad).status_code == 422
    r = client.post(f"/api/engagements/{eng}/findings", headers=t, json=dict(FIND, cvss_score=0.1))
    assert r.status_code == 201
    f = r.json()
    assert f["cvss_score"] == 9.9 and f["severity"] == "critical" and f["cvss_version"] == "4.0"
    assert f["code"].startswith("F-")
    assert f["cvss_vector"].startswith("CVSS:4.0/")
    template = client.post("/api/finding-templates", headers=tokens["lead"], json=FIND)
    assert template.status_code == 201
    saved_template = next(x for x in client.get("/api/finding-templates", headers=t).json() if x["id"] == template.json()["id"])
    assert saved_template["cvss_version"] == "4.0" and saved_template["cvss_vector"].startswith("CVSS:4.0/")
    calc = client.post("/api/cvss/calc", headers=t, json={"vector": VEC}).json()
    assert calc["version"] == "4.0" and calc["nomenclature"] == "CVSS-B" and calc["score"] == 9.9
    report = client.get(f"/api/engagements/{eng}/report?include_unapproved=true", headers=t)
    assert report.status_code == 200
    from docx import Document
    doc = Document(io.BytesIO(report.content))
    report_text = "\\n".join(p.text for p in doc.paragraphs) + " " + " ".join(
        cell.text for table in doc.tables for row in table.rows for cell in row.cells)
    assert "CVSS-B v4.0" in report_text and "CVSS:4.0/" in report_text
    r = client.patch(f"/api/findings/{f['id']}", headers=t, json={"cvss_vector": "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:A/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"})
    assert r.json()["cvss_version"] == "4.0" and r.json()["severity"] == "medium"
    r = client.post(f"/api/findings/{f['id']}/status", headers=t, json={"status": "fixed", "notes": "patch v2"})
    assert r.json()["status"] == "fixed"
    # "lulus retest" tidak dapat diset manual, hanya lewat ronde retest
    assert client.post(f"/api/findings/{f['id']}/status", headers=t, json={"status": "retest_passed"}).status_code == 422
    r = client.post(f"/api/findings/{f['id']}/retests", headers=t, json={"result": "passed", "notes": "ok"})
    assert r.status_code == 201 and r.json()["status"] == "retest_passed" and r.json()["retests"][0]["round_no"] == 1
    hist = client.get(f"/api/findings/{f['id']}/history", headers=t).json()
    assert [h["action"] for h in hist][:2] == ["retest_recorded", "finding_status"]
    assert client.delete(f"/api/findings/{f['id']}", headers=t).status_code == 403
    assert client.delete(f"/api/findings/{f['id']}", headers=tokens["lead"]).status_code == 204
    assert client.get(f"/api/findings/{f['id']}", headers=t).status_code == 404


def test_evidence_upload_rules(client, tokens, eng):
    t = tokens["tester"]
    fid = client.post(f"/api/engagements/{eng}/findings", headers=t, json=FIND).json()["id"]
    up = lambda name, data, h=t: client.post(f"/api/findings/{fid}/evidence", headers=h, files={"file": (name, data)})
    assert up("shell.php", b"<?php ?>").status_code == 415
    assert up("fake.png", b"bukan png").status_code == 415
    assert up("a.txt", b"abc\x00def").status_code == 415
    assert up("big.png", PNG + b"0" * (6 * 1024 * 1024)).status_code == 413
    assert up("ok.png", PNG, tokens["reviewer"]).status_code == 403
    r = up("../../etc/pa ss.png", PNG)
    assert r.status_code == 201
    ev = r.json()["evidence"][0]
    assert "/" not in ev["filename"]
    d = client.get(f"/api/evidence/{ev['id']}/download", headers=t)
    assert d.status_code == 200 and d.content == PNG
    assert d.headers["content-disposition"].startswith("attachment")
    assert client.get(f"/api/evidence/{ev['id']}/download", headers=tokens["tester2"]).status_code == 404
    assert client.delete(f"/api/evidence/{ev['id']}", headers=t).status_code == 204


def test_csv_import(client, tokens, eng):
    csv_data = ("title,description,impact,recommendation,cvss_vector\n"
                f"XSS,d,i,r,CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N\n"
                "Rusak,d,i,r,CVSS:3.1/XX\n"
                f",kosong,i,r,{VEC}\n").encode()
    r = client.post(f"/api/engagements/{eng}/findings/import", headers=tokens["tester"],
                    files={"file": ("x.csv", csv_data)})
    assert r.status_code == 200
    assert r.json()["created"] == 1 and len(r.json()["errors"]) == 2


def test_templates_and_cvss_endpoint(client, tokens):
    assert client.post("/api/cvss/calc", headers=tokens["tester"], json={"vector": VEC}).json()["score"] == 9.8
    assert client.post("/api/cvss/calc", headers=tokens["tester"], json={"vector": "x"}).status_code == 422
    body = {"title": "Header keamanan hilang", "description": "d", "impact": "i", "recommendation": "r",
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N"}
    assert client.post("/api/finding-templates", headers=tokens["tester"], json=body).status_code == 403
    r = client.post("/api/finding-templates", headers=tokens["lead"], json=body)
    assert r.status_code == 201
    assert len(client.get("/api/finding-templates", headers=tokens["tester"]).json()) >= 1
    assert client.delete(f"/api/finding-templates/{r.json()['id']}", headers=tokens["lead"]).status_code == 204


def _approve(client, tokens, fid):
    assert client.post(f"/api/findings/{fid}/review", headers=tokens["tester"], json={"action": "submit"}).status_code == 200
    r = client.post(f"/api/findings/{fid}/review", headers=tokens["reviewer"], json={"action": "approve"})
    assert r.status_code == 200 and r.json()["review_status"] == "approved"


def test_report_docx_and_template(client, tokens, eng):
    t = tokens["tester"]
    fid = client.post(f"/api/engagements/{eng}/findings", headers=t, json=dict(FIND, title="Judul \x07 ctrl")).json()["id"]
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(buf, "PNG")
    assert client.post(f"/api/findings/{fid}/evidence", headers=t, files={"file": ("a.png", buf.getvalue())}).status_code == 201
    base = f"/api/engagements/{eng}/report"
    from docx import Document
    def text_of(resp):
        return "\n".join(p.text for p in Document(io.BytesIO(resp.content)).paragraphs)
    # laporan final hanya memuat temuan yang disetujui
    r = client.get(f"{base}?format=docx", headers=tokens["reviewer"])
    assert r.status_code == 200 and zipfile.is_zipfile(io.BytesIO(r.content))
    assert "belum disetujui" in text_of(r)
    r = client.get(f"{base}?format=docx&include_unapproved=true", headers=t)
    assert "DRAF" in text_of(r) and "Judul  ctrl" in text_of(r)
    _approve(client, tokens, fid)
    r = client.get(f"{base}?format=docx", headers=tokens["reviewer"])
    assert "Ruang Lingkup" in text_of(r) and "Judul  ctrl" in text_of(r)
    assert client.get(f"{base}?format=exe", headers=t).status_code == 422
    assert client.get(f"{base}?format=docx&kind=bogus", headers=t).status_code == 422
    # templat kustom dengan placeholder (versi 1, aktif)
    tpl = Document()
    tpl.add_paragraph("LAPORAN {{client}} - {{ engagement }} [{{template_version}}] {{foo}}")
    b = io.BytesIO()
    tpl.save(b)
    up = lambda h, name="t.docx", data=None, kind="pretest": client.post(  # noqa: E731
        "/api/report-templates", headers=h, data={"kind": kind, "notes": "uji"}, files={"file": (name, data or b.getvalue())})
    assert up(tokens["tester"]).status_code == 403
    assert up(tokens["lead"], name="t.txt").status_code == 415
    assert up(tokens["lead"], data=b"bukan docx").status_code == 422
    assert up(tokens["lead"], kind="xx").status_code == 422
    r = up(tokens["lead"])
    assert r.status_code == 201 and r.json()["version"] == 1 and r.json()["status"] == "draft"
    assert r.json()["validation"]["unknown"] == ["foo"]
    tid = r.json()["id"]
    assert client.post(f"/api/report-templates/{tid}/activate", headers=tokens["lead"]).json()["status"] == "active"
    r = client.get(f"{base}?format=docx", headers=t)
    assert "LAPORAN PT ACME (fiktif) - Uji Fiktif ACME [v1] {{foo}}" in text_of(r)
    assert client.delete(f"/api/report-templates/{tid}", headers=tokens["lead"]).status_code == 409  # aktif


def test_report_pdf(client, tokens, eng):
    import shutil
    if not (shutil.which("soffice") or shutil.which("libreoffice")):
        pytest.skip("LibreOffice tidak tersedia")
    r = client.get(f"/api/engagements/{eng}/report?format=pdf", headers=tokens["lead"])
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_dashboard_and_audit(client, tokens, eng):
    d = client.get("/api/dashboard", headers=tokens["lead"]).json()
    assert d["findings"] >= 1 and sum(d["by_severity"].values()) == d["findings"]
    assert client.get("/api/dashboard", headers=tokens["tester2"]).json()["findings"] == 0
    assert client.get("/api/audit", headers=tokens["tester"]).status_code == 403
    actions = {a["action"] for a in client.get("/api/audit", headers=tokens["lead"]).json()}
    assert {"roe_approved", "report_exported", "finding_created", "login_failed"} <= actions


def test_user_management_paths(client, tokens):
    h = tokens["admin"]
    uid = client.post("/api/users", headers=h, json={"username": "mgmt", "full_name": "M", "password": PW, "role": "tester"}).json()["id"]
    tok = {"Authorization": f"Bearer {login(client, 'mgmt').json()['access_token']}"}
    r = client.patch(f"/api/users/{uid}", headers=h, json={"role": "reviewer", "full_name": "Baru", "password": PW + "z"})
    assert r.json()["role"] == "reviewer" and r.json()["full_name"] == "Baru"
    assert client.get("/api/auth/me", headers=tok).status_code == 401  # token lama dicabut
    assert client.patch(f"/api/users/{uid}", headers=h, json={"is_active": False}).status_code == 200
    assert login(client, "mgmt", PW + "z").status_code == 401
    assert client.patch("/api/users/99999", headers=h, json={"is_active": True}).status_code == 404


def test_evidence_stored_in_database_and_pdf_toggle(client, tokens, eng, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "evidence_in_db", True)
    t = tokens["tester"]
    fid = client.post(f"/api/engagements/{eng}/findings", headers=t, json=FIND).json()["id"]
    r = client.post(f"/api/findings/{fid}/evidence", headers=t, files={"file": ("db.png", PNG)})
    assert r.status_code == 201
    ev = r.json()["evidence"][0]
    assert not (settings.evidence_dir / "db.png").exists()
    assert client.get(f"/api/evidence/{ev['id']}/download", headers=t).content == PNG
    assert client.get(f"/api/engagements/{eng}/report?format=docx", headers=t).status_code == 200
    monkeypatch.setattr(settings, "enable_pdf", False)
    assert client.get(f"/api/engagements/{eng}/report?format=pdf", headers=t).status_code == 503



def test_legacy_cvss_history_survives_v4_reassessment(client, tokens, eng):
    from app.database import SessionLocal
    from app.models import Finding

    with SessionLocal() as db:
        old = Finding(
            engagement_id=eng, number=900, title="Legacy finding", description="old",
            impact="old impact", recommendation="old recommendation",
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            cvss_version="3.1", cvss_score=9.8, severity="critical",
            status="open", retest_notes="", review_status="draft", review_note="",
            created_by_id=None,
        )
        db.add(old)
        db.commit()
        fid = old.id

    r = client.patch(f"/api/findings/{fid}", headers=tokens["tester"], json={"cvss_vector": VEC})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["cvss_version"] == "4.0"
    assert out["cvss_legacy_version"] == "3.1"
    assert out["cvss_legacy_score"] == 9.8
    assert out["cvss_legacy_vector"].startswith("CVSS:3.1/")
    assert out["cvss_score"] == 9.9
    assert out["cvss_legacy_severity"] == "critical"
