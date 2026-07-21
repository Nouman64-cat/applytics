import uuid

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.client import ClientCreate, ClientUpdate
from db.models import BDRole, BusinessDeveloper, Client


async def create_client(session: AsyncSession, bd: BusinessDeveloper, payload: ClientCreate) -> Client:
    client = Client(bd_id=bd.id, **payload.model_dump())
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def list_clients(session: AsyncSession, bd: BusinessDeveloper) -> list[Client]:
    statement = select(Client)
    if bd.role != BDRole.admin:
        statement = statement.where(Client.bd_id == bd.id)
    result = await session.exec(statement)
    return list(result.all())


async def get_client_scoped(session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if bd.role != BDRole.admin and client.bd_id != bd.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


async def update_client(
    session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID, payload: ClientUpdate
) -> Client:
    client = await get_client_scoped(session, bd, client_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client
