import uuid

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.client import ClientCreate, ClientRead, ClientUpdate
from api.schemas.target_role import TargetRoleCreate, TargetRoleRead
from core.db import get_session
from core.deps import get_current_bd
from db.models import BusinessDeveloper
from services import client_service, target_role_service

router = APIRouter(prefix="/clients")


@router.post("", response_model=ClientRead, status_code=201)
async def create_client(
    payload: ClientCreate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    client = await client_service.create_client(session, bd, payload)
    return ClientRead.model_validate(client, from_attributes=True)


@router.get("", response_model=list[ClientRead])
async def list_clients(
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ClientRead]:
    clients = await client_service.list_clients(session, bd)
    return [ClientRead.model_validate(c, from_attributes=True) for c in clients]


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    client = await client_service.get_client_scoped(session, bd, client_id)
    return ClientRead.model_validate(client, from_attributes=True)


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    client = await client_service.update_client(session, bd, client_id, payload)
    return ClientRead.model_validate(client, from_attributes=True)


@router.post("/{client_id}/target-roles", response_model=TargetRoleRead, status_code=201)
async def create_target_role(
    client_id: uuid.UUID,
    payload: TargetRoleCreate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> TargetRoleRead:
    target_role = await target_role_service.create_target_role(session, bd, client_id, payload)
    return TargetRoleRead.model_validate(target_role, from_attributes=True)


@router.get("/{client_id}/target-roles", response_model=list[TargetRoleRead])
async def list_target_roles(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[TargetRoleRead]:
    target_roles = await target_role_service.list_target_roles(session, bd, client_id)
    return [TargetRoleRead.model_validate(t, from_attributes=True) for t in target_roles]
