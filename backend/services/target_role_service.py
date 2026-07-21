import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.target_role import TargetRoleCreate
from db.models import BusinessDeveloper, Client, TargetRole
from services.client_service import get_client_scoped


async def create_target_role(
    session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID, payload: TargetRoleCreate
) -> TargetRole:
    client: Client = await get_client_scoped(session, bd, client_id)
    target_role = TargetRole(client_id=client.id, **payload.model_dump())
    session.add(target_role)
    await session.commit()
    await session.refresh(target_role)
    return target_role


async def list_target_roles(session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID) -> list[TargetRole]:
    client: Client = await get_client_scoped(session, bd, client_id)
    result = await session.exec(select(TargetRole).where(TargetRole.client_id == client.id))
    return list(result.all())
