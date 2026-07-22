from sqlmodel.ext.asyncio.session import AsyncSession

from agents.llm import run_structured
from agents.schemas import KeywordSuggestionOutput

# Each job board's search behaves differently — nudge phrasing style accordingly rather
# than suggesting the same generic query shape regardless of where it'll actually be typed.
_PLATFORM_NOTES = {
    "adzuna": "Adzuna's search matches loosely against title/description — short, common phrases work best.",
    "linkedin": "LinkedIn's search behaves like an exact-phrase title match — prefer precise, common job-title "
    "phrasing over long or unusual strings.",
    "indeed": "Indeed's search matches against title/description/company — short phrases and common synonyms "
    "work well.",
    "glassdoor": "Glassdoor's search matches fuzzily against title/description — short, common phrases work best.",
    "jobright": "Jobright's guest search has no real filtering behind it, so keep suggestions broad/common "
    "rather than narrow.",
    "jobwright": "Jobright's guest search has no real filtering behind it, so keep suggestions broad/common "
    "rather than narrow.",
}


def _build_prompt(seed: str, platform: str | None, remote_only: bool) -> str:
    role = seed.strip() or "a broadly useful remote tech/professional role (no specific idea was given)"

    platform_line = ""
    if platform:
        note = _PLATFORM_NOTES.get(platform.lower(), "")
        platform_line = f"Target job board: {platform}. {note}\n"

    remote_line = (
        'The candidate wants 100%-remote roles only — include "remote" in each suggestion where natural.\n'
        if remote_only
        else "The candidate is open to remote, hybrid, or onsite roles — do not force the word "
        '"remote" into every suggestion.\n'
    )

    return (
        "Context: a staffing agency's Business Developer is searching job boards (Adzuna, LinkedIn, Indeed, "
        "Glassdoor, Jobright) on behalf of one of their clients — a candidate looking for work at USA-based "
        "companies. This is background only; it does NOT mean the client is a Business Developer or is "
        "looking for business-development/sales work.\n\n"
        f"{platform_line}"
        f"{remote_line}\n"
        f'The candidate\'s target role is: "{role}"\n\n'
        f'Generate 6-10 search query strings for job boards, specifically for the target role "{role}" above '
        "— not for any other occupation. Include common title variants/synonyms for that same role, closely "
        "adjacent job titles within that same field, and a spread of seniority levels (junior/mid/senior) "
        "where relevant. Keep each suggestion short (2-5 words), phrased like a real query someone would "
        "type into a job board's search box, not a sentence."
    )


async def suggest_job_search_keywords(
    session: AsyncSession, seed: str, platform: str | None = None, remote_only: bool = True
) -> KeywordSuggestionOutput:
    return await run_structured(
        session,
        agent_type="keyword_suggestion",
        related_entity_type="job_search",
        related_entity_id=seed or "(blank)",
        prompt=_build_prompt(seed, platform, remote_only),
        output_model=KeywordSuggestionOutput,
    )
