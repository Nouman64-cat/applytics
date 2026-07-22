from sqlmodel.ext.asyncio.session import AsyncSession

from agents.llm import run_gemini_structured
from agents.schemas import MarketResearchAnswer
from core.config import get_settings
from db.models import ChatMessage
from services.market_snapshot_service import format_snapshot_for_prompt

HISTORY_MESSAGE_LIMIT = 15
HISTORY_ANSWER_CHAR_LIMIT = 1500

SYSTEM_INSTRUCTION = (
    "You are a market research assistant embedded in a recruiting/business-development platform. "
    "Business Developers ask you about job market trends, platform (job source) performance, position "
    "demand for their clients' remote US job search, and how specific named candidates' resumes are "
    "performing against each other. Answer ONLY using the DATA SNAPSHOT and conversation transcript "
    "provided in the prompt — never invent numbers or claim real-time/live knowledge beyond the "
    "snapshot's generated_at timestamp. Reason concretely: cite specific counts and comparisons from the "
    "snapshot (e.g. 'LinkedIn produced 40 jobs this window vs 100 last window, a 60% drop') rather than "
    "vague generalities. When asked to compare two named candidates (e.g. 'why is X's resume "
    "outperforming Y's'), look them up first in the recent resume comparison runs section (the actual "
    "LLM-judged strengths/weaknesses from the Compare feature — this is the real explanatory signal) and "
    "lean on the per-candidate resume performance section only for supplementary detail (interview_rate/"
    "ats_score) — never treat low or zero application counts as evidence a candidate is underperforming, "
    "since many BDs don't log every application in this system. If a name in the question doesn't exactly "
    "match an entry (misspellings, nicknames), use the closest reasonable match from the snapshot and say "
    "which candidate you matched it to. If multiple comparison runs between the same two candidates "
    "disagree on the winner, say so explicitly and describe them as closely matched rather than presenting "
    "one run as settled fact. If the data snapshot has nothing relevant to a question, say so plainly and "
    "redirect toward what you can answer instead of guessing."
)


def _format_history(history: list[ChatMessage]) -> str:
    if not history:
        return "(no prior messages in this conversation)"
    recent = history[-HISTORY_MESSAGE_LIMIT:]
    lines = []
    for message in recent:
        speaker = "BD" if message.role == "user" else "Assistant"
        content = message.content[:HISTORY_ANSWER_CHAR_LIMIT]
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


async def answer_question(
    session: AsyncSession,
    chat_session_id: object,
    question: str,
    snapshot: dict,
    history: list[ChatMessage],
) -> MarketResearchAnswer:
    settings = get_settings()

    prompt = (
        f"{format_snapshot_for_prompt(snapshot)}\n\n"
        f"CONVERSATION SO FAR:\n{_format_history(history)}\n\n"
        f"NEW QUESTION FROM THE BD: {question}"
    )

    return await run_gemini_structured(
        session,
        agent_type="market_research",
        related_entity_type="chat_session",
        related_entity_id=chat_session_id,
        contents=[prompt],
        output_model=MarketResearchAnswer,
        model_name=settings.gemini_market_research_model,
        system_instruction=SYSTEM_INSTRUCTION,
    )
