import uuid

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.analysis import (
    ComparisonRead,
    ComparisonRequest,
    KeywordAnalysisRead,
    KeywordAnalysisRequest,
    LocationAnalysisRead,
    LocationAnalysisRequest,
)
from core.db import get_session
from core.deps import get_current_bd
from db.models import BusinessDeveloper
from services import analysis_service

router = APIRouter(prefix="/analysis")


@router.post("/keywords", response_model=KeywordAnalysisRead, status_code=201)
async def analyze_keywords(
    payload: KeywordAnalysisRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> KeywordAnalysisRead:
    record = await analysis_service.run_keyword_analysis(session, bd, payload.profile_id, payload.target_role_id)
    return KeywordAnalysisRead.model_validate(record, from_attributes=True)


@router.post("/location", response_model=LocationAnalysisRead, status_code=201)
async def analyze_location(
    payload: LocationAnalysisRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> LocationAnalysisRead:
    record = await analysis_service.run_location_analysis(session, bd, payload.client_id, payload.target_role_id)
    return LocationAnalysisRead.model_validate(record, from_attributes=True)


@router.post("/compare", response_model=ComparisonRead, status_code=201)
async def compare_profiles(
    payload: ComparisonRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ComparisonRead:
    run = await analysis_service.run_comparison(
        session, bd, payload.client_id, payload.profile_ids, payload.target_role_id
    )
    return ComparisonRead.model_validate(run, from_attributes=True)


@router.get("/comparisons/{run_id}", response_model=ComparisonRead)
async def get_comparison(
    run_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ComparisonRead:
    run = await analysis_service.get_comparison_run(session, bd, run_id)
    return ComparisonRead.model_validate(run, from_attributes=True)
