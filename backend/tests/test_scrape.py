from db.models.enums import RemoteType
from services.scraper import registry
from services.scraper.base import JobFilters, JobScraper, ScrapedJob
from tests.conftest import API


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
