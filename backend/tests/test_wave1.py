import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from conftest import PW, VEC, login, mk_engagement
from docx import Document
from PIL import Image

import app.notes_service as notes_service

BACKEND = Path(__file__).resolve().parent.parent
FIND = {"title": "IDOR pada /api/orders", "description": "Akses objek lain", "impact": "Data bocor",
        "recommendation": "Validasi kepemilikan", "cvss_vector": VEC}


def png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), "blue").save(buf, "PNG")
    return buf.getvalue()


def docx_bytes(*paragraphs) -> bytes:
    d = Document()
    for p in paragraphs:
        d.add_paragraph(p)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def text_of(resp) -> list[str]:
    return [p.text for p in Document(io.BytesIO(resp.content)).paragraphs]


def new_finding(client, h, eid, **over):
    r = client.post(f"/api/engagements/{eid}/findings", headers=h, json={**FIND, **over})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------- B1: Technical Writer ----------------
def test_writer_permissions(client, tokens):
    eid = mk_engagement(client, tokens)
    f = new_finding(client, tokens["tester"], eid)
    client.post(f"/api/findings/{f['id']}/evidence", headers=tokens["tester"], files={"file": ("a.png", png())})
    w = tokens["writer"]
    got = client.get(f"/api/findings/{f['id']}", headers=w).json()
    assert got["evidence"] == []  # tanpa akses bukti mentah
    ev_id = client.get(f"/api/findings/{f['id']}", headers=tokens["tester"]).json()["evidence"][0]["id"]
    assert client.get(f"/api/evidence/{ev_id}/download", headers=w).status_code == 403
    assert client.get(f"/api/engagements/{eid}/findings", headers=w).json()[0]["evidence"] == []
    # boleh menyunting teks, bukan CVSS/tenggat/status; tidak boleh membuat temuan atau bukti
    r = client.patch(f"/api/findings/{f['id']}", headers=w, json={"description": "Narasi lebih jelas"})
    assert r.status_code == 200 and r.json()["description"] == "Narasi lebih jelas"
    assert client.patch(f"/api/findings/{f['id']}", headers=w, json={"cvss_vector": VEC}).status_code == 403
    assert client.patch(f"/api/findings/{f['id']}", headers=w, json={"due_date": "2030-01-01"}).status_code == 403
    assert client.post(f"/api/engagements/{eid}/findings", headers=w, json=FIND).status_code == 403
    assert client.post(f"/api/findings/{f['id']}/status", headers=w, json={"status": "fixed"}).status_code == 403
    assert client.post(f"/api/findings/{f['id']}/evidence", headers=w, files={"file": ("a.png", png())}).status_code == 403
    assert client.get(f"/api/engagements/{eid}/notes", headers=w).status_code == 403  # catatan pentester
    assert client.get("/api/users", headers=w).status_code == 403
    # setelah pengujian selesai, writer tetap bisa menyunting teks
    client.post(f"/api/engagements/{eid}/status", headers=tokens["lead"], json={"status": "completed"})
    assert client.patch(f"/api/findings/{f['id']}", headers=w, json={"impact": "Dampak final"}).status_code == 200
    assert client.patch(f"/api/findings/{f['id']}", headers=tokens["tester"], json={"impact": "x"}).status_code == 409
    # laporan untuk writer tidak memuat bukti mentah
    r = client.get(f"/api/engagements/{eid}/report?include_unapproved=true", headers=w)
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert not [n for n in z.namelist() if n.startswith("word/media/")]
    r = client.get(f"/api/engagements/{eid}/report?include_unapproved=true", headers=tokens["tester"])
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert [n for n in z.namelist() if n.startswith("word/media/")]
    # writer di luar engagement -> 404
    assert client.get(f"/api/findings/{f['id']}", headers=tokens["tester2"]).status_code == 404


# ---------------- C1: alur review ----------------
def test_review_workflow(client, tokens):
    eid = mk_engagement(client, tokens)
    t, rv, lead = tokens["tester"], tokens["reviewer"], tokens["lead"]
    f = new_finding(client, t, eid)
    fid = f["id"]
    assert f["review_status"] == "draft"
    review = lambda h, action, note="": client.post(f"/api/findings/{fid}/review", headers=h,  # noqa: E731
                                                    json={"action": action, "note": note})
    assert review(rv, "approve").status_code == 409  # belum diajukan
    assert review(rv, "submit").status_code == 403  # peninjau bukan penulis
    assert review(t, "submit").json()["review_status"] == "in_review"
    assert review(t, "submit").status_code == 409
    assert review(t, "approve").status_code == 403  # penguji tidak boleh menyetujui
    assert review(rv, "request_changes").status_code == 422  # catatan wajib
    r = review(rv, "request_changes", "Perjelas langkah reproduksi")
    assert r.json()["review_status"] == "changes_requested" and r.json()["review_note"].startswith("Perjelas")
    assert client.patch(f"/api/findings/{fid}", headers=tokens["writer"], json={"description": "Langkah 1..3"}).status_code == 200
    assert review(tokens["writer"], "submit").json()["review_status"] == "in_review"
    assert review(rv, "approve", "OK").json()["review_status"] == "approved"
    # mengubah isi temuan yang sudah disetujui mengembalikannya ke draf
    r = client.patch(f"/api/findings/{fid}", headers=t, json={"title": "IDOR (revisi)"})
    assert r.json()["review_status"] == "draft"
    # perubahan tanpa efek pada isi (due date) tidak mereset review
    review(t, "submit")
    review(rv, "approve")
    assert client.patch(f"/api/findings/{fid}", headers=t, json={"due_date": "2031-01-01"}).json()["review_status"] == "approved"
    # empat mata: pembuat tidak dapat menyetujui temuannya sendiri, walau Lead
    f2 = new_finding(client, lead, eid, title="Dibuat Lead")
    client.post(f"/api/findings/{f2['id']}/review", headers=lead, json={"action": "submit"})
    r = client.post(f"/api/findings/{f2['id']}/review", headers=lead, json={"action": "approve"})
    assert r.status_code == 403
    assert client.post(f"/api/findings/{f2['id']}/review", headers=rv, json={"action": "approve"}).status_code == 200
    # dasbor menghitung status review
    assert "pending_review" in client.get("/api/dashboard", headers=lead).json()


# ---------------- C2: ronde retest ----------------
def test_retest_rounds(client, tokens):
    eid = mk_engagement(client, tokens)
    t = tokens["tester"]
    f = new_finding(client, t, eid)
    fid = f["id"]
    client.post(f"/api/findings/{fid}/status", headers=t, json={"status": "fixed", "notes": "patch"})
    rt = lambda result, **kw: client.post(f"/api/findings/{fid}/retests", headers=t, json={"result": result, **kw})  # noqa: E731
    assert client.post(f"/api/findings/{fid}/retests", headers=tokens["reviewer"], json={"result": "passed"}).status_code == 403
    assert rt("bogus").status_code == 422
    r1 = rt("failed", notes="Masih bisa di-bypass", tested_at="2026-03-01").json()
    assert r1["status"] == "open" and r1["retests"][0]["round_no"] == 1 and r1["retests"][0]["tester"] == "Tester"
    r2 = rt("partial").json()
    assert r2["status"] == "open" and [x["round_no"] for x in r2["retests"]] == [1, 2]
    r3 = rt("passed", notes="Sudah ditutup").json()
    assert r3["status"] == "retest_passed" and r3["retests"][2]["tested_at"]
    # bukti per ronde
    rid = r3["retests"][2]["id"]
    up = client.post(f"/api/retests/{rid}/evidence", headers=t, files={"file": ("retest.png", png())})
    assert up.status_code == 201
    out = up.json()
    assert out["evidence"] == [] and out["retests"][2]["evidence"][0]["filename"] == "retest.png"
    ev_id = out["retests"][2]["evidence"][0]["id"]
    assert client.get(f"/api/evidence/{ev_id}/download", headers=t).content == png()
    assert client.get(f"/api/findings/{fid}", headers=tokens["writer"]).json()["retests"][2]["evidence"] == []
    assert client.post(f"/api/retests/{rid}/evidence", headers=tokens["tester2"], files={"file": ("x.png", png())}).status_code == 404
    assert client.post("/api/retests/99999/evidence", headers=t, files={"file": ("x.png", png())}).status_code == 404
    # menghapus temuan ikut menghapus ronde & buktinya (foreign key ditegakkan)
    assert client.delete(f"/api/findings/{fid}", headers=tokens["lead"]).status_code == 204
    assert client.get(f"/api/evidence/{ev_id}/download", headers=t).status_code == 404
    # retest hanya saat engagement aktif
    f2 = new_finding(client, t, eid)
    client.post(f"/api/engagements/{eid}/status", headers=tokens["lead"], json={"status": "completed"})
    assert client.post(f"/api/findings/{f2['id']}/retests", headers=t, json={"result": "passed"}).status_code == 409


# ---------------- D3: perbandingan pretest vs retest + laporan retest ----------------
def test_comparison_and_retest_report(client, tokens):
    from app.reporting import compare_findings
    eid = mk_engagement(client, tokens, name="Perbandingan")
    t = tokens["tester"]
    a, b, c = (new_finding(client, t, eid, title=x) for x in ("A tutup", "B tetap", "C belum diverifikasi"))
    client.post(f"/api/findings/{c['id']}/status", headers=t, json={"status": "fixed"})
    client.post(f"/api/findings/{a['id']}/retests", headers=t, json={"result": "passed"})
    client.post(f"/api/findings/{b['id']}/retests", headers=t, json={"result": "failed", "notes": "gagal"})
    d = new_finding(client, t, eid, title="D baru saat retest")  # muncul setelah retest pertama
    r = client.get(f"/api/engagements/{eid}/comparison?include_unapproved=true", headers=t).json()
    assert r["counts"] == {"closed": 1, "still_open": 1, "unverified": 1, "new": 1}
    assert [x["title"] for x in r["buckets"]["new"]] == [d["title"]]
    # tanpa persetujuan, perbandingan final kosong dan jumlah tersembunyi dilaporkan
    r = client.get(f"/api/engagements/{eid}/comparison", headers=t).json()
    assert sum(r["counts"].values()) == 0 and r["hidden_unapproved"] == 4
    assert client.get(f"/api/engagements/{eid}/comparison", headers=tokens["tester2"]).status_code == 404
    # laporan retest
    rep = client.get(f"/api/engagements/{eid}/report?kind=retest&include_unapproved=true", headers=t)
    assert rep.status_code == 200
    txt = "\n".join(text_of(rep))
    assert "Laporan Retest" in txt and "Perbandingan Pretest dan Retest" in txt and "1 (33%) telah tertutup" in txt
    rows = [[c.text for c in row.cells] for tb in Document(io.BytesIO(rep.content)).tables for row in tb.rows]
    assert ["Tertutup (lulus retest)", "1"] in rows and ["Baru (muncul saat retest)", "1"] in rows
    assert any(r[1] == "B tetap" and r[4] == "1" and r[5] == "Gagal" for r in rows if len(r) == 6)
    assert compare_findings([]) == {"closed": [], "still_open": [], "unverified": [], "new": []}


# ---------------- A3/A4/A5: templat laporan berversi ----------------
def test_report_template_versioning(client, tokens):
    L, W = tokens["lead"], tokens["writer"]
    up = lambda h, data, kind="retest", name="x.docx": client.post(  # noqa: E731
        "/api/report-templates", headers=h, data={"kind": kind, "notes": f"cat {kind}"},
        files={"file": (name, data)})
    assert up(tokens["reviewer"], docx_bytes("x")).status_code == 403
    assert up(W, b"PK-bukan-docx").status_code == 422
    v1 = up(W, docx_bytes("v1 {{client}}")).json()  # Technical Writer boleh mengunggah
    v2 = up(L, docx_bytes("v2 {{client}}")).json()
    p1 = up(L, docx_bytes("pretest {{client}}"), kind="pretest").json()
    assert (v1["version"], v2["version"], p1["version"]) == (v1["version"], v1["version"] + 1, p1["version"])
    assert v1["created_by"] == "writer" and v1["status"] == "draft"
    act = lambda tid, h=L: client.post(f"/api/report-templates/{tid}/activate", headers=h)  # noqa: E731
    assert act(v1["id"], tokens["tester"]).status_code == 403
    act(v1["id"])
    act(v2["id"])  # v1 -> arsip
    states = {t["version"]: t["status"] for t in client.get("/api/report-templates?kind=retest", headers=W).json()}
    assert states[v1["version"]] == "archived" and states[v2["version"]] == "active"
    act(v1["id"])  # rollback
    states = {t["version"]: t["status"] for t in client.get("/api/report-templates?kind=retest", headers=W).json()}
    assert states[v1["version"]] == "active" and states[v2["version"]] == "archived"
    assert client.get("/api/report-templates/active", headers=tokens["tester"]).json()["retest"]["id"] == v1["id"]
    # kind lain tidak terpengaruh
    assert [t["status"] for t in client.get("/api/report-templates?kind=pretest", headers=L).json()
            if t["id"] == p1["id"]] == ["draft"]
    # arsip/aktif tidak bisa dihapus; draf bisa
    assert client.delete(f"/api/report-templates/{v2['id']}", headers=L).status_code == 409
    v3 = up(L, docx_bytes("v3")).json()
    assert client.delete(f"/api/report-templates/{v3['id']}", headers=L).status_code == 204
    assert client.get(f"/api/report-templates/{v1['id']}/download", headers=W).status_code == 200
    assert client.get(f"/api/report-templates/{v1['id']}/download", headers=tokens["tester"]).status_code == 403
    assert client.get(f"/api/report-templates/{v1['id']}/validate", headers=W).json()["placeholders"] == ["client"]
    # laporan mencatat versi templat yang dipakai
    eid = mk_engagement(client, tokens, name="Versi Templat")
    assert client.post(f"/api/engagements/{eid}/reports/retest/approve", headers=L).status_code == 200
    assert client.post(f"/api/engagements/{eid}/reports/retest/approve", headers=tokens["reviewer"]).status_code == 200
    rep = client.get(f"/api/engagements/{eid}/report?kind=retest", headers=tokens["tester"])
    assert any(f"templat retest: v{v1['version']}" in p for p in text_of(rep))
    assert text_of(rep)[0].startswith("v1 Klien Fiktif")
    audit = client.get("/api/audit", headers=L).json()
    assert any(a["action"] == "report_template_activated" for a in audit)


def test_content_marker_in_template(client, tokens):
    eid = mk_engagement(client, tokens, name="Penanda")
    data = docx_bytes("BAGIAN ATAS {{engagement}}", "{{content}}", "BAGIAN BAWAH")
    r = client.post("/api/report-templates", headers=tokens["lead"], data={"kind": "pretest"},
                    files={"file": ("m.docx", data)}).json()
    assert r["validation"]["has_content_marker"] is True and r["validation"]["unknown"] == []
    client.post(f"/api/report-templates/{r['id']}/activate", headers=tokens["lead"])
    assert client.post(f"/api/engagements/{eid}/reports/pretest/approve", headers=tokens["lead"]).status_code == 200
    assert client.post(f"/api/engagements/{eid}/reports/pretest/approve", headers=tokens["reviewer"]).status_code == 200
    paras = text_of(client.get(f"/api/engagements/{eid}/report", headers=tokens["tester"]))
    top, mid, bottom = (next(i for i, p in enumerate(paras) if k in p)
                        for k in ("BAGIAN ATAS Penanda", "1. Ringkasan Engagement", "BAGIAN BAWAH"))
    assert top < mid < bottom
    assert "{{content}}" not in "\n".join(paras)


# ---------------- A1/A2: catatan Markdown ----------------
def test_note_templates_and_notes(client, tokens, monkeypatch):
    L, T, R, W = tokens["lead"], tokens["tester"], tokens["reviewer"], tokens["writer"]
    md = "# Catatan Kustom\n\n- [ ] recon\n".encode()
    up = lambda h, name="kustom.md", data=md, **form: client.post(  # noqa: E731
        "/api/note-templates/upload", headers=h, data=form, files={"file": (name, data)})
    assert up(T).status_code == 403
    assert up(L, name="x.txt").status_code == 415
    assert up(L, data=b"\xff\xfe\x00bad").status_code == 422
    assert up(L, data=b"a" * 200_001).status_code == 413
    r = up(L, make_default="true")
    assert r.status_code == 201 and r.json()["is_default"] is True
    assert up(L).status_code == 409  # nama sama
    tpls = client.get("/api/note-templates", headers=T).json()["templates"]
    assert [t["name"] for t in tpls] == ["kustom"]
    assert client.get("/api/note-templates", headers=W).status_code == 403
    assert client.get("/api/note-templates/builtin", headers=T).json()["content"].startswith("# Catatan Pentester")
    # engagement baru otomatis mendapat catatan tim + catatan pribadi penguji dari templat default
    eid = mk_engagement(client, tokens, members=("tester", "tester2", "reviewer", "writer"), name="Catatan")
    lst = lambda h: client.get(f"/api/engagements/{eid}/notes", headers=h)  # noqa: E731
    assert [n["scope"] for n in lst(L).json()] == ["team", "personal", "personal"]
    assert [n["scope"] for n in lst(T).json()] == ["team", "personal"]
    assert [n["scope"] for n in lst(R).json()] == ["team"]
    assert lst(W).status_code == 403
    assert lst(tokens["lead"]).status_code == 200
    team = next(n for n in lst(T).json() if n["scope"] == "team")
    mine = next(n for n in lst(T).json() if n["scope"] == "personal")
    assert client.get(f"/api/notes/{team['id']}", headers=T).json()["content"].startswith("# Catatan Kustom")
    # akses: penguji lain tak melihat catatan pribadi; peninjau hanya baca catatan tim
    other = next(n for n in lst(L).json() if n["scope"] == "personal" and n["owner_id"] != mine["owner_id"])
    assert client.get(f"/api/notes/{other['id']}", headers=T).status_code == 404
    assert client.get(f"/api/notes/{mine['id']}", headers=L).status_code == 200  # Lead/Admin boleh baca
    assert client.put(f"/api/notes/{mine['id']}", headers=L, json={"content": "x", "base_version": 1}).status_code == 403
    assert client.put(f"/api/notes/{team['id']}", headers=R, json={"content": "x", "base_version": 1}).status_code == 403
    assert client.get(f"/api/notes/{mine['id']}", headers=tokens["tester2"]).status_code in (200, 404)
    # penyimpanan berversi + kontrol konflik
    body = "# Hasil recon\n\n**host** 10.0.0.1 `ssh` <script>alert(1)</script>\n"
    r = client.put(f"/api/notes/{mine['id']}", headers=T, json={"content": body, "base_version": 1})
    assert r.status_code == 200 and r.json()["version"] == 2
    assert client.put(f"/api/notes/{mine['id']}", headers=T, json={"content": "lama", "base_version": 1}).status_code == 409
    assert client.put(f"/api/notes/{mine['id']}", headers=T, json={"content": body, "base_version": 2}).json()["version"] == 2
    vers = client.get(f"/api/notes/{mine['id']}/versions", headers=T).json()
    assert [v["version"] for v in vers] == [2, 1]
    assert client.get(f"/api/notes/{mine['id']}/versions/1", headers=T).json()["content"].startswith("# Catatan Kustom")
    assert client.get(f"/api/notes/{mine['id']}/versions/9", headers=T).status_code == 404
    ex = client.get(f"/api/notes/{mine['id']}/export", headers=T)
    assert ex.headers["content-type"].startswith("text/markdown") and ex.headers["content-disposition"].startswith("attachment")
    assert ex.content.decode() == body
    # catatan pribadi tambahan, pemangkasan versi, penghapusan
    n2 = client.post(f"/api/engagements/{eid}/notes", headers=T, json={"title": "Recon web"})
    assert n2.status_code == 201 and n2.json()["content"].startswith("# Catatan Kustom")
    assert client.post(f"/api/engagements/{eid}/notes", headers=R, json={"title": "x"}).status_code == 403
    monkeypatch.setattr(notes_service, "MAX_VERSIONS", 3)
    nid = n2.json()["id"]
    for i in range(6):
        assert client.put(f"/api/notes/{nid}", headers=T, json={"content": f"rev {i}", "base_version": i + 1}).status_code == 200
    assert len(client.get(f"/api/notes/{nid}/versions", headers=T).json()) == 3
    assert client.delete(f"/api/notes/{team['id']}", headers=L).status_code == 403
    assert client.delete(f"/api/notes/{nid}", headers=T).status_code == 204
    # templat: ubah, set default, hapus -> kembali ke bawaan
    tid = r_id = client.get("/api/note-templates", headers=T).json()["templates"][0]["id"]
    assert client.put(f"/api/note-templates/{tid}", headers=L, json={"content": "# Baru"}).status_code == 200
    assert client.post(f"/api/note-templates/{tid}/default", headers=L).json()["is_default"] is True
    assert client.delete(f"/api/note-templates/{tid}", headers=L).status_code == 204
    assert client.get(f"/api/note-templates/{r_id}", headers=L).status_code == 404
    eid2 = mk_engagement(client, tokens, name="Catatan bawaan")
    t2 = next(n for n in client.get(f"/api/engagements/{eid2}/notes", headers=T).json() if n["scope"] == "team")
    assert client.get(f"/api/notes/{t2['id']}", headers=T).json()["content"].startswith("# Catatan Pentester")
    created = client.post("/api/note-templates", headers=L, json={"name": "Via JSON", "content": "# J", "make_default": True})
    assert created.status_code == 201


# ---------------- E1: migrasi Alembic ----------------
def _run(code: str, db_url: str, data_dir: Path) -> str:
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "SECRET_KEY": "k" * 48, "DATABASE_URL": db_url,
           "DATA_DIR": str(data_dir)}
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout.strip()


DRIFT = """
import json
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.database import Base, engine
from app import models
from app.migrate import run_migrations
run_migrations()
with engine.connect() as c:
    diffs = compare_metadata(MigrationContext.configure(c, opts={"compare_type": False}), Base.metadata)
    print(json.dumps([str(d) for d in diffs]))
"""


def test_migrations_match_models(tmp_path):
    out = _run(DRIFT, f"sqlite:///{tmp_path}/fresh.db", tmp_path)
    assert json.loads(out.splitlines()[-1]) == []  # skema hasil migrasi == model


LEGACY = """
import sqlalchemy as sa
from alembic import command
from app.database import engine
from app.migrate import alembic_config, run_migrations
command.upgrade(alembic_config(), "0001")            # skema v1.0
with engine.begin() as c:
    c.execute(sa.text("DROP TABLE alembic_version"))   # meniru DB buatan create_all (tanpa Alembic)
    if %(drop_data)s:
        c.execute(sa.text("ALTER TABLE evidence DROP COLUMN data"))
    c.execute(sa.text("INSERT INTO users (id,username,full_name,password_hash,role,is_active,failed_attempts,totp_enabled,token_version,created_at) VALUES (1,'lama','Lama','x','lead',1,0,0,0,'2026-01-01')"))
    c.execute(sa.text("INSERT INTO engagements (id,name,client,scope,start_date,end_date,roe_text,roe_approved,status,created_at) VALUES (1,'E','K','s','2026-01-01','2026-02-01','r',1,'active','2026-01-01')"))
    c.execute(sa.text("INSERT INTO findings (id,engagement_id,number,title,description,impact,recommendation,cvss_vector,cvss_score,severity,status,retest_notes,created_at,updated_at) VALUES (1,1,1,'Lama','','','','CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',9.8,'critical','open','','2026-01-01','2026-01-01')"))
run_migrations()
with engine.connect() as c:
    row = c.execute(sa.text("SELECT title, review_status FROM findings")).one()
    ver = c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()
    cols = [r[1] for r in c.execute(sa.text("PRAGMA table_info(evidence)"))]
    roe = c.execute(sa.text("SELECT roe_approved FROM engagements WHERE id=1")).scalar()
    print(row[0], row[1], ver, roe, "data" in cols, "retest_id" in cols)
"""


@pytest.mark.parametrize("drop_data", [False, True])
def test_legacy_database_is_adopted(tmp_path, drop_data):
    out = _run(LEGACY % {"drop_data": drop_data}, f"sqlite:///{tmp_path}/legacy.db", tmp_path)
    assert out.splitlines()[-1] == "Lama approved 0004 0 True True"  # data utuh, temuan lama dianggap sudah disetujui


def test_login_with_new_roles(client, tokens):
    assert login(client, "writer", PW).status_code == 200
    assert tokens["ids"]["writer"]
