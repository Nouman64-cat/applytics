import uuid

from sqlmodel import select

from db.models import Application, Job, JobSource
from services.feedback_loop_service import refresh_stale_comparisons
from tests.conftest import API


async def test_refresh_triggers_once_threshold_met(client, auth_headers, db_session, mock_llm):
    client_resp = await client.post(
        f"{API}/clients", json={"full_name": "FL", "email": "fl@example.com"}, headers=auth_headers
    )
    client_id = client_resp.json()["id"]

    role_resp = await client.post(
        f"{API}/clients/{client_id}/target-roles",
        json={"title": "Engineer", "must_have_keywords": []},
        headers=auth_headers,
    )
    role_id = role_resp.json()["id"]

    p1 = (
        await client.post(
            f"{API}/profiles",
            json={"client_id": client_id, "target_role_id": role_id, "type": "resume", "variant_label": "A"},
            headers=auth_headers,
        )
    ).json()
    await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "target_role_id": role_id, "type": "resume", "variant_label": "B"},
        headers=auth_headers,
    )

    source = (await db_session.exec(select(JobSource).where(JobSource.name == "adzuna"))).first()
    job = Job(job_source_id=source.id, external_id="fl-job-1", title="Job")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    for _ in range(3):
        db_session.add(Application(client_id=uuid.UUID(client_id), profile_id=uuid.UUID(p1["id"]), job_id=job.id))
    await db_session.commit()

    triggered = await refresh_stale_comparisons(db_session, min_new_applications=3)
    assert len(triggered) == 1
    assert triggered[0].status == "complete"


async def test_refresh_skips_when_below_threshold(client, auth_headers, db_session, mock_llm):
    client_resp = await client.post(
        f"{API}/clients", json={"full_name": "FL2", "email": "fl2@example.com"}, headers=auth_headers
    )
    client_id = client_resp.json()["id"]
    role_resp = await client.post(
        f"{API}/clients/{client_id}/target-roles",
        json={"title": "Engineer", "must_have_keywords": []},
        headers=auth_headers,
    )
    role_id = role_resp.json()["id"]

    p1 = (
        await client.post(
            f"{API}/profiles",
            json={"client_id": client_id, "target_role_id": role_id, "type": "resume", "variant_label": "A"},
            headers=auth_headers,
        )
    ).json()
    await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "target_role_id": role_id, "type": "resume", "variant_label": "B"},
        headers=auth_headers,
    )

    source = (await db_session.exec(select(JobSource).where(JobSource.name == "adzuna"))).first()
    job = Job(job_source_id=source.id, external_id="fl-job-2", title="Job")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    db_session.add(Application(client_id=uuid.UUID(client_id), profile_id=uuid.UUID(p1["id"]), job_id=job.id))
    await db_session.commit()

    triggered = await refresh_stale_comparisons(db_session, min_new_applications=3)
    assert triggered == []
