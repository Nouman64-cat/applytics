from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from api.schemas.bd import BDRead
from core.db import get_session
from services.auth_service import authenticate_bd, register_bd

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=BDRead, status_code=201)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> BDRead:
    bd = await register_bd(session, payload.email, payload.password, payload.full_name)
    return BDRead.model_validate(bd, from_attributes=True)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    token = await authenticate_bd(session, payload.email, payload.password)
    return TokenResponse(access_token=token)
