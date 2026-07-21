from sqlmodel.ext.asyncio.session import AsyncSession

from agents.llm import run_structured
from agents.schemas import LocationAnalysisOutput
from db.models import Client, TargetRole


def _location_summary(client: Client) -> str:
    parts = [client.current_city, client.current_state, client.current_country]
    location = ", ".join(p for p in parts if p)
    return location or "unknown"


def _build_prompt(client: Client, target_role: TargetRole | None) -> str:
    role_line = f"Target role: {target_role.title}" if target_role else "Target role: unspecified"
    return (
        "You are advising a Business Developer who places candidates in 100%-remote, US-based roles. "
        "Assess whether the candidate's current physical location is likely to hurt their odds with "
        "employers hiring for fully remote US positions (e.g. timezone overlap, US work authorization "
        "assumptions, employer bias against non-US-based remote workers).\n\n"
        f"{role_line}\n"
        f"Candidate's current location: {_location_summary(client)}\n"
        f"Candidate's timezone: {client.timezone or 'unspecified'}"
    )


async def analyze_location(
    session: AsyncSession, client: Client, target_role: TargetRole | None
) -> LocationAnalysisOutput:
    return await run_structured(
        session,
        agent_type="location",
        related_entity_type="client",
        related_entity_id=client.id,
        prompt=_build_prompt(client, target_role),
        output_model=LocationAnalysisOutput,
    )
