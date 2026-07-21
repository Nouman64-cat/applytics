import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.application import ApplicationCreate, ApplicationUpdate
from db.models import Application, BusinessDeveloper, Job
from services.client_service import get_client_scoped
from services.profile_service import get_profile_scoped


async def create_application(
    session: AsyncSession, bd: BusinessDeveloper, payload: ApplicationCreate
) -> Application:
    client = await get_client_scoped(session, bd, payload.client_id)
    profile = await get_profile_scoped(session, bd, payload.profile_id)
    if profile.client_id != client.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile does not belong to this client"
        )

    job = await session.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    application = Application(
        client_id=client.id,
        profile_id=profile.id,
        job_id=job.id,
        notes=payload.notes,
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


async def list_applications(session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID) -> list[Application]:
    await get_client_scoped(session, bd, client_id)
    result = await session.exec(
        select(Application).where(Application.client_id == client_id).order_by(Application.applied_at.desc())
    )
    return list(result.all())


async def get_application_scoped(
    session: AsyncSession, bd: BusinessDeveloper, application_id: uuid.UUID
) -> Application:
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    await get_client_scoped(session, bd, application.client_id)
    return application


async def update_application(
    session: AsyncSession, bd: BusinessDeveloper, application_id: uuid.UUID, payload: ApplicationUpdate
) -> Application:
    application = await get_application_scoped(session, bd, application_id)

    if payload.status is not None:
        application.status = payload.status
        application.status_updated_at = datetime.now(timezone.utc)
    if payload.notes is not None:
        application.notes = payload.notes

    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application
