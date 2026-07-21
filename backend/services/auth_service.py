from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from core.security import create_access_token, hash_password, verify_password
from db.models import BusinessDeveloper


async def register_bd(session: AsyncSession, email: str, password: str, full_name: str) -> BusinessDeveloper:
    existing = await session.exec(select(BusinessDeveloper).where(BusinessDeveloper.email == email))
    if existing.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    bd = BusinessDeveloper(email=email, hashed_password=hash_password(password), full_name=full_name)
    session.add(bd)
    await session.commit()
    await session.refresh(bd)
    return bd


async def authenticate_bd(session: AsyncSession, email: str, password: str) -> str:
    result = await session.exec(select(BusinessDeveloper).where(BusinessDeveloper.email == email))
    bd = result.first()

    if bd is None or not verify_password(password, bd.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return create_access_token(subject=str(bd.id))
