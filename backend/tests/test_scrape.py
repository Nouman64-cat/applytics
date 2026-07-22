from sqlmodel import select

from db.models import Job, JobSource
from db.models.enums import RemoteType
from services.scraper import registry
from services.scraper.base import JobFilters, JobScraper, ScrapedJob
from tests.conftest import API


async def _make_job(db_session, external_id: str) -> Job:
    source = (await db_session.exec(select(JobSource).where(JobSource.name == "adzuna"))).first()
    job = Job(job_source_id=source.id, external_id=external_id, title="Test Job")
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


class FakeScraper(JobScraper):
    source_name = "adzuna"

    def __init__(self, jobs: list[ScrapedJob]):
        self._jobs = jobs

    async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
        return self._jobs


async def test_scrape_upserts_without_duplicating(client, auth_headers, monkeypatch):
    fake_job = ScrapedJob(
        external_id="fake-1",
        title="Fake Backend Job",
        remote_type=RemoteType.fully_remote,
        apply_url="https://example.com/1",
    )
    monkeypatch.setitem(registry._SCRAPERS, "adzuna", FakeScraper([fake_job]))

    resp1 = await client.post(f"{API}/scrape/runs", json={"source": "adzuna", "keywords": "test"}, headers=auth_headers)
    assert resp1.status_code == 201
    assert resp1.json()["status"] == "success"
    assert resp1.json()["jobs_found_count"] == 1

    resp2 = await client.post(f"{API}/scrape/runs", json={"source": "adzuna", "keywords": "test"}, headers=auth_headers)
    assert resp2.json()["jobs_found_count"] == 1

    jobs_resp = await client.get(f"{API}/jobs", params={"source": "adzuna"}, headers=auth_headers)
    matching = [j for j in jobs_resp.json() if j["external_id"] == "fake-1"]
    assert len(matching) == 1


async def test_scrape_disabled_source_returns_400(client, auth_headers):
    resp = await client.post(f"{API}/scrape/runs", json={"source": "linkedin"}, headers=auth_headers)
    assert resp.status_code == 400


async def test_scrape_unknown_source_returns_404(client, auth_headers):
    resp = await client.post(f"{API}/scrape/runs", json={"source": "does-not-exist"}, headers=auth_headers)
    assert resp.status_code == 404


async def test_scrape_failure_is_recorded_not_raised(client, auth_headers, monkeypatch):
    class BrokenScraper(JobScraper):
        source_name = "adzuna"

        async def fetch(self, filters: JobFilters) -> list[ScrapedJob]:
            raise RuntimeError("simulated upstream failure")

    monkeypatch.setitem(registry._SCRAPERS, "adzuna", BrokenScraper())

    resp = await client.post(f"{API}/scrape/runs", json={"source": "adzuna"}, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"
    assert "simulated upstream failure" in body["error_message"]


async def test_delete_job(client, auth_headers, db_session):
    job = await _make_job(db_session, "delete-me-1")

    resp = await client.delete(f"{API}/jobs/{job.id}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"{API}/jobs/{job.id}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_delete_job_referenced_by_application_is_blocked(client, auth_headers, db_session):
    job = await _make_job(db_session, "delete-me-referenced")
    client_resp = await client.post(
        f"{API}/clients", json={"full_name": "Ref", "email": "ref@example.com"}, headers=auth_headers
    )
    client_id = client_resp.json()["id"]
    profile_resp = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "type": "resume", "variant_label": "A"},
        headers=auth_headers,
    )
    profile_id = profile_resp.json()["id"]
    await client.post(
        f"{API}/applications",
        json={"client_id": client_id, "profile_id": profile_id, "job_id": str(job.id)},
        headers=auth_headers,
    )

    resp = await client.delete(f"{API}/jobs/{job.id}", headers=auth_headers)
    assert resp.status_code == 409

    get_resp = await client.get(f"{API}/jobs/{job.id}", headers=auth_headers)
    assert get_resp.status_code == 200


async def test_delete_nonexistent_job_returns_404(client, auth_headers):
    resp = await client.delete(f"{API}/jobs/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404


async def test_bulk_delete_jobs_skips_referenced_ones(client, auth_headers, db_session):
    deletable = await _make_job(db_session, "bulk-delete-a")
    referenced = await _make_job(db_session, "bulk-delete-b")

    client_resp = await client.post(
        f"{API}/clients", json={"full_name": "Bulk", "email": "bulk@example.com"}, headers=auth_headers
    )
    client_id = client_resp.json()["id"]
    profile_resp = await client.post(
        f"{API}/profiles",
        json={"client_id": client_id, "type": "resume", "variant_label": "A"},
        headers=auth_headers,
    )
    profile_id = profile_resp.json()["id"]
    await client.post(
        f"{API}/applications",
        json={"client_id": client_id, "profile_id": profile_id, "job_id": str(referenced.id)},
        headers=auth_headers,
    )

    resp = await client.post(
        f"{API}/jobs/bulk-delete",
        json={"job_ids": [str(deletable.id), str(referenced.id)]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 1, "skipped": 1}

    assert (await client.get(f"{API}/jobs/{deletable.id}", headers=auth_headers)).status_code == 404
    assert (await client.get(f"{API}/jobs/{referenced.id}", headers=auth_headers)).status_code == 200
