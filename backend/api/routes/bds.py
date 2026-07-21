from fastapi import APIRouter, Depends

from api.schemas.bd import BDRead
from core.deps import get_current_bd
from db.models import BusinessDeveloper

router = APIRouter(prefix="/bds")


@router.get("/me", response_model=BDRead)
async def read_current_bd(bd: BusinessDeveloper = Depends(get_current_bd)) -> BDRead:
    return BDRead.model_validate(bd, from_attributes=True)
