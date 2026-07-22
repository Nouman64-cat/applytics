import uuid

from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.market_research import AskRequest, ChatMessageRead, ChatSessionRead
from core.db import get_session
from core.deps import get_current_bd
from core.rate_limit import limiter
from db.models import BusinessDeveloper
from services import market_research_chat_service

router = APIRouter(prefix="/market-research")


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_sessions(
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ChatSessionRead]:
    sessions = await market_research_chat_service.list_sessions(session, bd)
    return [ChatSessionRead.model_validate(s, from_attributes=True) for s in sessions]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
async def list_messages(
    session_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ChatMessageRead]:
    messages = await market_research_chat_service.list_messages(session, bd, session_id)
    return [ChatMessageRead.model_validate(m, from_attributes=True) for m in messages]


@router.post("/ask", response_model=ChatMessageRead, status_code=201)
@limiter.limit("15/minute")
async def ask(
    request: Request,
    payload: AskRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ChatMessageRead:
    _chat_session, assistant_message = await market_research_chat_service.ask(
        session, bd, payload.session_id, payload.question
    )
    return ChatMessageRead.model_validate(assistant_message, from_attributes=True)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> None:
    await market_research_chat_service.delete_session(session, bd, session_id)
