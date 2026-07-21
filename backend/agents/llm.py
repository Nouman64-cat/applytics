import time
from typing import TypeVar

from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import get_settings
from db.models import AgentRun

T = TypeVar("T", bound=BaseModel)


def get_llm(temperature: float = 0.2) -> ChatOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured in .env")
    return ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key, temperature=temperature)


async def run_structured(
    session: AsyncSession,
    *,
    agent_type: str,
    related_entity_type: str,
    related_entity_id: object,
    prompt: str,
    output_model: type[T],
) -> T:
    settings = get_settings()
    llm = get_llm()
    structured_llm = llm.with_structured_output(output_model, include_raw=True)

    start = time.monotonic()
    status = "success"
    error: str | None = None
    parsed: T | None = None
    usage: dict = {}

    try:
        raw_result = await structured_llm.ainvoke(prompt)
        parsed = raw_result.get("parsed")
        parsing_error = raw_result.get("parsing_error")
        raw_message = raw_result.get("raw")
        if parsing_error is not None or parsed is None:
            raise ValueError(f"LLM did not return valid structured output: {parsing_error}")
        usage = getattr(raw_message, "usage_metadata", None) or {}
    except Exception as exc:
        status = "error"
        error = str(exc)
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        run = AgentRun(
            agent_type=agent_type,
            related_entity_type=related_entity_type,
            related_entity_id=str(related_entity_id),
            model_name=settings.llm_model,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            latency_ms=latency_ms,
            status=status,
            error_message=error,
        )
        session.add(run)
        await session.commit()

    return parsed
