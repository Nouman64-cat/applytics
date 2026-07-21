from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from core.db import get_session

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
