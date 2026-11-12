from conftest import VEC


def test_admin_is_not_an_operational_role(client, tokens, eng):
    admin = tokens["admin"]
    # Admin hanya mengelola akun dan administrasi, bukan data engagement.
    assert client.get("/api/engagements", headers=admin).json() == []
    assert client.get(f"/api/engagements/{eng}", headers=admin).status_code == 404
    payload = {
        "name": "Tidak boleh dibuat Admin",
        "client": "Klien Uji",
        "scope": "app.example.test",
        "start_date": "2026-01-01",
        "end_date": "2030-01-01",
        "roe_text": "RoE pengujian",
    }
    assert client.post("/api/engagements", headers=admin, json=payload).status_code == 403
    assert client.get("/api/users", headers=admin).status_code == 200
    assert client.get("/api/audit", headers=admin).status_code == 200


def test_project_manager_owns_engagement_changes(client, tokens, eng):
    lead = tokens["lead"]
    reviewer = tokens["reviewer"]
    assert client.get(f"/api/engagements/{eng}", headers=lead).status_code == 200
    assert client.patch(
        f"/api/engagements/{eng}", headers=reviewer, json={"scope": "changed.example.test"}
    ).status_code == 403
    assert client.post(
        f"/api/engagements/{eng}/status", headers=reviewer, json={"status": "completed"}
    ).status_code == 403


def test_finding_approval_is_reserved_for_offensive_security_head(client, tokens, eng):
    tester = tokens["tester"]
    lead = tokens["lead"]
    reviewer = tokens["reviewer"]
    created = client.post(
        f"/api/engagements/{eng}/findings",
        headers=tester,
        json={
            "title": "Temuan uji role",
            "description": "Deskripsi",
            "impact": "Dampak",
            "recommendation": "Rekomendasi",
            "cvss_vector": VEC,
        },
    )
    assert created.status_code == 201, created.text
    fid = created.json()["id"]
    assert client.post(f"/api/findings/{fid}/review", headers=tester, json={"action": "submit"}).status_code == 200
    assert client.post(f"/api/findings/{fid}/review", headers=lead, json={"action": "approve"}).status_code == 403
    assert client.post(f"/api/findings/{fid}/review", headers=reviewer, json={"action": "approve"}).status_code == 200
