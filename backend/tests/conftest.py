import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="scopeline-test-")
os.environ.update({
    "SECRET_KEY": "x" * 48, "DATA_DIR": _tmp,
    # TEST_DATABASE_URL: jalankan suite pada PostgreSQL (mis. di CI) alih-alih SQLite
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db",
    "ADMIN_PASSWORD": "Admin-Password-123", "LOGIN_RATE_PER_MIN": "100000",
})

import pytest
from fastapi.testclient import TestClient

from app.main import app

PW = "Password-Uji-12345"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, username, password=PW, otp=None):
    r = client.post("/api/auth/login", json={"username": username, "password": password, "otp": otp})
    return r


@pytest.fixture(scope="session")
def tokens(client):
    admin = login(client, "admin", "Admin-Password-123").json()["access_token"]
    h = {"Authorization": f"Bearer {admin}"}
    out = {"admin": h}
    for role in ("lead", "tester", "tester2", "reviewer", "writer"):
        r = client.post("/api/users", headers=h, json={
            "username": role, "full_name": role.title(), "password": PW,
            "role": "tester" if role == "tester2" else role})
        assert r.status_code == 201, r.text
        out[role] = {"Authorization": f"Bearer {login(client, role).json()['access_token']}"}
    out["ids"] = {u["username"]: u["id"] for u in client.get("/api/users", headers=h).json()}
    return out


VEC = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:N"


@pytest.fixture(scope="session")
def eng(client, tokens):
    """Engagement aktif dengan tester1 sebagai anggota; tester2 tidak ditugaskan."""
    lead = tokens["lead"]
    r = client.post("/api/engagements", headers=lead, json={
        "name": "Uji Fiktif ACME", "client": "PT ACME (fiktif)", "scope": "app.acme.example",
        "start_date": "2026-01-01", "end_date": "2030-12-31", "roe_text": "Hanya jam kerja."})
    assert r.status_code == 201
    eid = r.json()["id"]
    ids = tokens["ids"]
    client.put(f"/api/engagements/{eid}/members", headers=lead,
               json={"user_ids": [ids["tester"], ids["reviewer"], ids["writer"]]})
    client.post(f"/api/engagements/{eid}/roe/approve", headers=lead)
    client.post(f"/api/engagements/{eid}/roe/approve", headers=tokens["reviewer"])
    r = client.post(f"/api/engagements/{eid}/status", headers=lead, json={"status": "active"})
    assert r.status_code == 200
    return eid


def mk_engagement(client, tokens, members=("tester", "reviewer", "writer"), name="Engagement Uji"):
    """Engagement aktif (RoE disetujui) dengan anggota yang diminta."""
    lead = tokens["lead"]
    eid = client.post("/api/engagements", headers=lead, json={
        "name": name, "client": "Klien Fiktif", "scope": "host.example", "start_date": "2026-01-01",
        "end_date": "2030-12-31", "roe_text": "RoE uji"}).json()["id"]
    client.put(f"/api/engagements/{eid}/members", headers=lead,
               json={"user_ids": [tokens["ids"][m] for m in members]})
    assert client.post(f"/api/engagements/{eid}/roe/approve", headers=lead).status_code == 200
    assert client.post(f"/api/engagements/{eid}/roe/approve", headers=tokens["reviewer"]).status_code == 200
    assert client.post(f"/api/engagements/{eid}/status", headers=lead, json={"status": "active"}).status_code == 200
    return eid
