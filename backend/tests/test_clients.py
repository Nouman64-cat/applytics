import uuid

from sqlmodel import select

from db.models import Application, ComparisonRun, Job, JobSource, KeywordAnalysis, Profile, TargetRole
from db.models.enums import AnalysisStatus
from tests.conftest import API


async def _make_job(db_session, external_id: str) -> Job:
    source = (await db_session.exec(select(JobSource).where(JobSource.name == "adzuna"))).first()
    job = Job(job_source_id=source.id, external_id=external_id, title="Test Job")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_create_and_list_client(client, auth_headers):
    resp = await client.post(
        f"{API}/clients", json={"full_name": "Jane", "email": "jane@example.com"}, headers=auth_headers
    )
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    resp = await client.get(f"{API}/clients", headers=auth_headers)
    assert resp.status_code == 200
    assert any(c["id"] == client_id for c in resp.json())


async def test_cross_bd_client_access_is_scoped(client, auth_headers):
    resp = await client.post(
        f"{API}/clients", json={"full_name": "Jane", "email": "jane2@example.com"}, headers=auth_headers
    )
    client_id = resp.json()["id"]

    await client.post(
        f"{API}/auth/register",
        json={"email": "other@example.com", "password": "testpass123", "full_name": "Other"},
    )
    login = await client.post(f"{API}/auth/login", json={"email": "other@example.com", "password": "testpass123"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get(f"{API}/clients/{client_id}", headers=other_headers)
    assert resp.status_code == 404

    resp = await client.get(f"{API}/clients", headers=other_headers)
    assert resp.json() == []


async def test_target_role_create_and_list(client, auth_headers):
    client_resp = await client.post(
        f"{API}/clients", json={"full_name": "Jane", "email": "jane3@example.com"}, headers=auth_headers
    )
    client_id = client_resp.json()["id"]

    resp = await client.post(
        f"{API}/clients/{client_id}/target-roles",
        json={"title": "Backend Engineer", "must_have_keywords": ["python", "fastapi"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["must_have_keywords"] == ["python", "fastapi"]

    resp = await client.get(f"{API}/clients/{client_id}/target-roles", headers=auth_headers)
    assert len(resp.json()) == 1


async def test_client_update(client, auth_headers):
    resp = await client.post(
        f"{API}/clients", json={"full_name": "Jane", "email": "jane-update@example.com"}, headers=auth_headers
    )
    client_id = resp.json()["id"]

    patch_resp = await client.patch(
        f"{API}/clients/{client_id}", json={"full_name": "Jane Updated", "status": "placed"}, headers=auth_headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["full_name"] == "Jane Updated"
    assert patch_resp.json()["status"] == "placed"
    assert patch_resp.json()["email"] == "jane-update@example.com"


async def test_client_delete_cascades(client, auth_headers, db_session):
    resp = await client.post(
        f"{API}/clients", json={"full_name": "Delete Me", "email": "delete-me@example.com"}, headers=auth_headers
    )
    client_id = resp.json()["id"]

    tr_resp = await client.post(
        f"{API}/clients/{client_id}/target-roles", json={"title": "Backend Engineer"}, headers=auth_headers
    )
    target_role_id = tr_resp.json()["id"]

    profile_resp = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "target_role_id": target_role_id, "type": "resume", "variant_label": "A"},
        headers=auth_headers,
    )
    profile_id = profile_resp.json()["id"]

    job = await _make_job(db_session, "delete-cascade-job")
    app_resp = await client.post(
        f"{API}/applications",
        json={"client_id": client_id, "profile_id": profile_id, "job_id": str(job.id)},
        headers=auth_headers,
    )
    assert app_resp.status_code == 201

    db_session.add(
        KeywordAnalysis(
            profile_id=uuid.UUID(profile_id),
            target_role_id=uuid.UUID(target_role_id),
            extracted_keywords=["python"],
            missing_keywords=[],
            ats_score=80,
            recruiter_attention_score=80,
        )
    )
    await db_session.commit()

    delete_resp = await client.delete(f"{API}/clients/{client_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"{API}/clients/{client_id}", headers=auth_headers)
    assert get_resp.status_code == 404

    assert (await db_session.exec(select(Profile).where(Profile.id == uuid.UUID(profile_id)))).first() is None
    assert (
        await db_session.exec(select(TargetRole).where(TargetRole.id == uuid.UUID(target_role_id)))
    ).first() is None
    assert (
        await db_session.exec(select(Application).where(Application.client_id == uuid.UUID(client_id)))
    ).first() is None
    assert (
        await db_session.exec(select(KeywordAnalysis).where(KeywordAnalysis.profile_id == uuid.UUID(profile_id)))
    ).first() is None


async def test_client_delete_nulls_cross_client_comparison_winner(client, auth_headers, db_session):
    resp_a = await client.post(
        f"{API}/clients", json={"full_name": "Candidate A", "email": "cand-a@example.com"}, headers=auth_headers
    )
    client_a_id = resp_a.json()["id"]
    resp_b = await client.post(
        f"{API}/clients", json={"full_name": "Candidate B", "email": "cand-b@example.com"}, headers=auth_headers
    )
    client_b_id = resp_b.json()["id"]

    profile_a = (
        await client.post(
            f"{API}/profiles",
            json={"client_id": client_a_id, "type": "resume", "variant_label": "A"},
            headers=auth_headers,
        )
    ).json()
    profile_b = (
        await client.post(
            f"{API}/profiles",
            json={"client_id": client_b_id, "type": "resume", "variant_label": "A"},
            headers=auth_headers,
        )
    ).json()

    run = ComparisonRun(
        client_id=None,
        profile_ids=[profile_a["id"], profile_b["id"]],
        status=AnalysisStatus.complete,
        result_summary="A wins",
        winner_profile_id=uuid.UUID(profile_a["id"]),
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    delete_resp = await client.delete(f"{API}/clients/{client_a_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    await db_session.refresh(run)
    assert run.winner_profile_id is None
    assert run.profile_ids == [profile_a["id"], profile_b["id"]]

    # Candidate B's own data is untouched by A's deletion.
    b_check = await client.get(f"{API}/clients/{client_b_id}", headers=auth_headers)
    assert b_check.status_code == 200


async def test_client_delete_cross_bd_404(client, auth_headers):
    resp = await client.post(
        f"{API}/clients", json={"full_name": "Owned", "email": "owned@example.com"}, headers=auth_headers
    )
    client_id = resp.json()["id"]

    await client.post(
        f"{API}/auth/register",
        json={"email": "other-delete@example.com", "password": "testpass123", "full_name": "Other"},
    )
    login = await client.post(
        f"{API}/auth/login", json={"email": "other-delete@example.com", "password": "testpass123"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.delete(f"{API}/clients/{client_id}", headers=other_headers)
    assert resp.status_code == 404
