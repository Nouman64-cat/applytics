import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from core.db import get_session
from core.security import decode_access_token
from db.models import BDRole, BusinessDeveloper

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_bd(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> BusinessDeveloper:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = decode_access_token(token)
    if subject is None:
        raise credentials_error

    try:
        bd_id = uuid.UUID(subject)
    except ValueError:
        raise credentials_error

    bd = await session.get(BusinessDeveloper, bd_id)
    if bd is None:
        raise credentials_error

    return bd


async def require_admin(bd: BusinessDeveloper = Depends(get_current_bd)) -> BusinessDeveloper:
    if bd.role != BDRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return bd
