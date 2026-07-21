import uuid

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.application import ApplicationCreate, ApplicationRead, ApplicationUpdate
from core.db import get_session
from core.deps import get_current_bd
from db.models import BusinessDeveloper
from services import application_service

router = APIRouter(prefix="/applications")


@router.post("", response_model=ApplicationRead, status_code=201)
async def create_application(
    payload: ApplicationCreate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    application = await application_service.create_application(session, bd, payload)
    return ApplicationRead.model_validate(application, from_attributes=True)


@router.get("", response_model=list[ApplicationRead])
async def list_applications(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ApplicationRead]:
    applications = await application_service.list_applications(session, bd, client_id)
    return [ApplicationRead.model_validate(a, from_attributes=True) for a in applications]


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    application = await application_service.get_application_scoped(session, bd, application_id)
    return ApplicationRead.model_validate(application, from_attributes=True)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    application = await application_service.update_application(session, bd, application_id, payload)
    return ApplicationRead.model_validate(application, from_attributes=True)
