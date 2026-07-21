import uuid

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.profile import ProfileCreate
from db.models import BusinessDeveloper, Profile
from services.client_service import get_client_scoped


async def create_profile(session: AsyncSession, bd: BusinessDeveloper, payload: ProfileCreate) -> Profile:
    await get_client_scoped(session, bd, payload.client_id)
    profile = Profile(**payload.model_dump())
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def list_profiles(session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID) -> list[Profile]:
    await get_client_scoped(session, bd, client_id)
    result = await session.exec(select(Profile).where(Profile.client_id == client_id))
    return list(result.all())


async def get_profile_scoped(session: AsyncSession, bd: BusinessDeveloper, profile_id: uuid.UUID) -> Profile:
    profile = await session.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    await get_client_scoped(session, bd, profile.client_id)
    return profile
