from sqlmodel import select

from db.models import Job, JobSource
from tests.conftest import API


async def _make_job(db_session, external_id: str) -> Job:
    source = (await db_session.exec(select(JobSource).where(JobSource.name == "adzuna"))).first()
    job = Job(job_source_id=source.id, external_id=external_id, title="Test Job")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_application_lifecycle_and_performance(client, auth_headers, db_session):
    client_resp = await client.post(
        f"{API}/clients", json={"full_name": "App", "email": "app@example.com"}, headers=auth_headers
    )
    client_id = client_resp.json()["id"]

    profile_resp = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "type": "resume", "variant_label": "A"},
        headers=auth_headers,
    )
    profile_id = profile_resp.json()["id"]

    job = await _make_job(db_session, "app-job-1")

    create_resp = await client.post(
        f"{API}/applications",
        json={"client_id": client_id, "profile_id": profile_id, "job_id": str(job.id)},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    application_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "applied"

    list_resp = await client.get(f"{API}/applications", params={"client_id": client_id}, headers=auth_headers)
    assert len(list_resp.json()) == 1

    patch_resp = await client.patch(
        f"{API}/applications/{application_id}", json={"status": "interview"}, headers=auth_headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "interview"

    perf_resp = await client.get(f"{API}/clients/{client_id}/performance", headers=auth_headers)
    assert perf_resp.status_code == 200
    entry = next(p for p in perf_resp.json() if p["profile_id"] == profile_id)
    assert entry["total_applications"] == 1
    assert entry["interview_rate"] == 1.0
    assert entry["status_counts"]["interview"] == 1


async def test_application_requires_matching_client(client, auth_headers, db_session):
    client_a = (
        await client.post(f"{API}/clients", json={"full_name": "A", "email": "aa@example.com"}, headers=auth_headers)
    ).json()["id"]
    client_b = (
        await client.post(f"{API}/clients", json={"full_name": "B", "email": "bb@example.com"}, headers=auth_headers)
    ).json()["id"]

    profile_b = (
        await client.post(
            f"{API}/profiles",
            json={"client_id": client_b, "type": "resume", "variant_label": "A"},
            headers=auth_headers,
        )
    ).json()

    job = await _make_job(db_session, "app-job-mismatch")

    resp = await client.post(
        f"{API}/applications",
        json={"client_id": client_a, "profile_id": profile_b["id"], "job_id": str(job.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 400
