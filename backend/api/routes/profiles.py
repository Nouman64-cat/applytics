import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.profile import ProfileCreate, ProfileRead
from core.db import get_session
from core.deps import get_current_bd
from db.models import BusinessDeveloper, ProfileType
from services import profile_service
from services.profile_parsing import extract_text

router = APIRouter(prefix="/profiles")


@router.post("", response_model=ProfileRead, status_code=201)
async def create_profile(
    payload: ProfileCreate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ProfileRead:
    profile = await profile_service.create_profile(session, bd, payload)
    return ProfileRead.model_validate(profile, from_attributes=True)


@router.post("/upload", response_model=ProfileRead, status_code=201)
async def upload_profile(
    client_id: uuid.UUID = Form(...),
    variant_label: str = Form(...),
    target_role_id: uuid.UUID | None = Form(None),
    file: UploadFile = File(...),
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ProfileRead:
    content = await file.read()
    raw_text = extract_text(file.filename or "", content)
    payload = ProfileCreate(
        client_id=client_id,
        target_role_id=target_role_id,
        type=ProfileType.resume,
        variant_label=variant_label,
        raw_text=raw_text,
    )
    profile = await profile_service.create_profile(session, bd, payload)
    return ProfileRead.model_validate(profile, from_attributes=True)


@router.get("", response_model=list[ProfileRead])
async def list_profiles(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ProfileRead]:
    profiles = await profile_service.list_profiles(session, bd, client_id)
    return [ProfileRead.model_validate(p, from_attributes=True) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ProfileRead:
    profile = await profile_service.get_profile_scoped(session, bd, profile_id)
    return ProfileRead.model_validate(profile, from_attributes=True)
