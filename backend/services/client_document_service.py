import uuid

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import BusinessDeveloper, ClientDocument
from services import s3_service
from services.client_service import get_client_scoped

MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024


def _s3_key(client_id: uuid.UUID, document_id: uuid.UUID, filename: str) -> str:
    return f"clients/{client_id}/documents/{document_id}-{filename}"


async def upload_document(
    session: AsyncSession,
    bd: BusinessDeveloper,
    client_id: uuid.UUID,
    filename: str,
    content: bytes,
    content_type: str,
) -> ClientDocument:
    await get_client_scoped(session, bd, client_id)

    if len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)}MB limit",
        )

    document = ClientDocument(
        client_id=client_id,
        filename=filename,
        s3_key="",
        content_type=content_type or "application/octet-stream",
        size_bytes=len(content),
    )
    document.s3_key = _s3_key(client_id, document.id, filename)

    s3_service.upload_file(document.s3_key, content, document.content_type)

    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def list_documents(session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID) -> list[ClientDocument]:
    await get_client_scoped(session, bd, client_id)
    result = await session.exec(select(ClientDocument).where(ClientDocument.client_id == client_id))
    return list(result.all())


async def get_document_scoped(
    session: AsyncSession, bd: BusinessDeveloper, document_id: uuid.UUID
) -> ClientDocument:
    document = await session.get(ClientDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await get_client_scoped(session, bd, document.client_id)
    return document


async def delete_document(session: AsyncSession, bd: BusinessDeveloper, document_id: uuid.UUID) -> None:
    document = await get_document_scoped(session, bd, document_id)
    s3_service.delete_file(document.s3_key)
    await session.delete(document)
    await session.commit()
