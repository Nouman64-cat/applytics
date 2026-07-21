import mimetypes
import time

from google import genai
from google.genai import types
from sqlmodel.ext.asyncio.session import AsyncSession

from agents.schemas import ResumeExtraction
from core.config import get_settings
from db.models import AgentRun
from services.linkedin_profile_fetcher import fetch_linkedin_profile_text
from services.profile_parsing import extract_text_from_docx

RESUME_PROMPT = (
    "You are extracting structured contact/location details from a candidate's resume for a "
    "recruiting platform. Read the document (use OCR if it is a scanned/image-based file) and "
    "return: the candidate's full name, email address, current city, current state/region, and "
    "current country as best you can determine them from the document. Also return the complete "
    "plain-text content of the resume. If a field cannot be determined, use null for it."
)

LINKEDIN_PROMPT = (
    "You are extracting structured contact/location details from text copy-pasted from a "
    "candidate's LinkedIn profile page for a recruiting platform. Return the candidate's full name, "
    "current city, current state/region, and current country as best you can determine them from "
    "the headline/About/location text. LinkedIn profiles rarely show a public email address — leave "
    "email null unless one is explicitly present in the text. Also return the complete plain-text "
    "content that was given to you as raw_text. If a field cannot be determined, use null for it."
)


def _mime_type_for(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


async def _run_gemini_extraction(
    session: AsyncSession, agent_type: str, related_entity_id: str, parts: list
) -> ResumeExtraction:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not configured in .env")

    client = genai.Client(api_key=settings.gemini_api_key)

    start = time.monotonic()
    status = "success"
    error: str | None = None
    result: ResumeExtraction | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=parts,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResumeExtraction,
            ),
        )
        result = ResumeExtraction.model_validate_json(response.text)
        usage = response.usage_metadata
        if usage is not None:
            prompt_tokens = usage.prompt_token_count
            completion_tokens = usage.candidates_token_count
    except Exception as exc:
        status = "error"
        error = str(exc)
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        session.add(
            AgentRun(
                agent_type=agent_type,
                related_entity_type="upload",
                related_entity_id=related_entity_id,
                model_name=settings.gemini_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                status=status,
                error_message=error,
            )
        )
        await session.commit()

    return result


async def extract_resume_details(session: AsyncSession, filename: str, content: bytes) -> ResumeExtraction:
    if filename.lower().endswith(".docx"):
        # DOCX already has machine-readable text — no OCR needed, skip straight to text extraction.
        parts = [extract_text_from_docx(content), RESUME_PROMPT]
    else:
        parts = [types.Part.from_bytes(data=content, mime_type=_mime_type_for(filename)), RESUME_PROMPT]

    return await _run_gemini_extraction(session, "resume_extraction", filename, parts)


async def extract_linkedin_profile_details(session: AsyncSession, text: str) -> ResumeExtraction:
    parts = [text, LINKEDIN_PROMPT]
    return await _run_gemini_extraction(session, "linkedin_extraction", "pasted-text", parts)


async def extract_linkedin_profile_from_url(session: AsyncSession, url: str) -> ResumeExtraction:
    text = await fetch_linkedin_profile_text(url)
    parts = [text, LINKEDIN_PROMPT]
    return await _run_gemini_extraction(session, "linkedin_url_extraction", url, parts)
