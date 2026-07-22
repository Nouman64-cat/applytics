import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from agents.llm import run_structured
from agents.schemas import JobMatchOutput
from db.models import Job

_DESCRIPTION_LIMIT = 300


def _truncate(text: str | None) -> str:
    if not text:
        return "(no description available)"
    text = text.strip()
    return text if len(text) <= _DESCRIPTION_LIMIT else text[:_DESCRIPTION_LIMIT].rstrip() + "…"


def _job_line(job: Job) -> str:
    return (
        f"- id: {job.id} | title: {job.title} | company: {job.company or 'unknown'} | "
        f"location: {job.location_raw or 'unknown'} | remote: {job.remote_type.value} | "
        f"description: {_truncate(job.description)}"
    )


def _build_prompt(resume_text: str, jobs: list[Job]) -> str:
    jobs_block = "\n".join(_job_line(job) for job in jobs)
    return (
        "You are helping a Business Developer at a staffing agency figure out which of their already-scraped "
        "remote job listings (at USA-based companies) are genuinely the best fit for their candidate's resume "
        "below. Score suitability based on skills/experience alignment, seniority match, and role relevance — "
        "not generic job-posting quality. Reference the exact job `id` given for each listing, unchanged — do "
        "not invent or modify ids. Only include jobs that are a real, defensible fit — omit clearly irrelevant "
        "jobs entirely rather than including them with a low score. Rank matches best-fit first, and give a "
        "1-2 sentence rationale per job that references specific resume content.\n\n"
        f"Candidate resume:\n{resume_text or '(no resume text available)'}\n\n"
        f"Candidate jobs:\n{jobs_block}"
    )


async def match_jobs_to_resume(
    session: AsyncSession, profile_id: uuid.UUID, resume_text: str, jobs: list[Job]
) -> JobMatchOutput:
    return await run_structured(
        session,
        agent_type="job_match",
        related_entity_type="profile",
        related_entity_id=profile_id,
        prompt=_build_prompt(resume_text, jobs),
        output_model=JobMatchOutput,
    )
