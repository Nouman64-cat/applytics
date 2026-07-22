import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from agents.market_research_agent import answer_question
from db.models import BusinessDeveloper, ChatMessage, ChatSession
from services.market_snapshot_service import build_market_snapshot

TITLE_MAX_LENGTH = 60


async def list_sessions(session: AsyncSession, bd: BusinessDeveloper) -> list[ChatSession]:
    # Chats are private research notes, not client records — no admin bypass, unlike
    # client-scoped resources elsewhere in this app.
    statement = select(ChatSession).where(ChatSession.bd_id == bd.id).order_by(ChatSession.updated_at.desc())
    result = await session.exec(statement)
    return list(result.all())


async def get_session_scoped(session: AsyncSession, bd: BusinessDeveloper, session_id: uuid.UUID) -> ChatSession:
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None or chat_session.bd_id != bd.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return chat_session


async def list_messages(session: AsyncSession, bd: BusinessDeveloper, session_id: uuid.UUID) -> list[ChatMessage]:
    await get_session_scoped(session, bd, session_id)
    statement = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    result = await session.exec(statement)
    return list(result.all())


async def delete_session(session: AsyncSession, bd: BusinessDeveloper, session_id: uuid.UUID) -> None:
    chat_session = await get_session_scoped(session, bd, session_id)
    messages = await session.exec(select(ChatMessage).where(ChatMessage.session_id == session_id))
    for message in messages.all():
        await session.delete(message)
    await session.delete(chat_session)
    await session.commit()


def _derive_title(question: str) -> str:
    stripped = question.strip()
    if len(stripped) <= TITLE_MAX_LENGTH:
        return stripped
    return stripped[: TITLE_MAX_LENGTH - 1].rstrip() + "…"


async def ask(
    session: AsyncSession, bd: BusinessDeveloper, session_id: uuid.UUID | None, question: str
) -> tuple[ChatSession, ChatMessage]:
    if session_id is None:
        chat_session = ChatSession(bd_id=bd.id, title=_derive_title(question))
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)
        history: list[ChatMessage] = []
    else:
        chat_session = await get_session_scoped(session, bd, session_id)
        history = await list_messages(session, bd, chat_session.id)

    user_message = ChatMessage(session_id=chat_session.id, role="user", content=question)
    session.add(user_message)
    await session.commit()

    snapshot = await build_market_snapshot(session, bd)
    output = await answer_question(session, chat_session.id, question, snapshot, history)

    assistant_message = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content=output.answer,
        key_data_points=output.key_data_points,
        suggested_follow_ups=output.suggested_follow_ups,
    )
    session.add(assistant_message)

    chat_session.updated_at = datetime.now(timezone.utc)
    session.add(chat_session)
    await session.commit()
    await session.refresh(assistant_message)
    await session.refresh(chat_session)

    return chat_session, assistant_message
