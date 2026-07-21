from sqlmodel.ext.asyncio.session import AsyncSession

from agents.llm import run_structured
from agents.schemas import KeywordAnalysisOutput
from db.models import Profile, TargetRole


def _role_context(target_role: TargetRole | None) -> str:
    if target_role is None:
        return (
            "No specific target role provided — evaluate general keyword strength for a 100% remote "
            "job search targeting USA-based companies."
        )
    keywords = ", ".join(target_role.must_have_keywords) or "none specified"
    return f"Target role: {target_role.title} (seniority: {target_role.seniority or 'unspecified'})\nMust-have keywords: {keywords}"


def _build_prompt(profile: Profile, target_role: TargetRole | None) -> str:
    return (
        "You are an expert resume reviewer helping a Business Developer place candidates in 100% "
        "remote roles at USA-based companies. Every hiring manager, recruiter, and ATS (Applicant "
        "Tracking System) you are evaluating against is American — assume US hiring conventions, "
        "US-style resume formatting expectations, and US industry terminology throughout. Evaluate "
        "the following resume text for keyword strength against the target role.\n\n"
        f"{_role_context(target_role)}\n\n"
        f"Candidate resume text:\n{profile.raw_text or '(no text available)'}"
    )


async def analyze_keywords(
    session: AsyncSession, profile: Profile, target_role: TargetRole | None
) -> KeywordAnalysisOutput:
    return await run_structured(
        session,
        agent_type="keyword",
        related_entity_type="profile",
        related_entity_id=profile.id,
        prompt=_build_prompt(profile, target_role),
        output_model=KeywordAnalysisOutput,
    )
