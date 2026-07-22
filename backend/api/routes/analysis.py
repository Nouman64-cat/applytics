import uuid

from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.analysis import (
    ComparisonRead,
    ComparisonRequest,
    CrossClientComparisonRequest,
    KeywordAnalysisRead,
    KeywordAnalysisRequest,
    LocationAnalysisRead,
    LocationAnalysisRequest,
)
from core.config import get_settings
from core.db import get_session
from core.deps import get_current_bd, require_admin
from core.rate_limit import limiter
from db.models import BusinessDeveloper
from services import analysis_service, feedback_loop_service

router = APIRouter(prefix="/analysis")


@router.post("/keywords", response_model=KeywordAnalysisRead, status_code=201)
@limiter.limit("20/minute")
async def analyze_keywords(
    request: Request,
    payload: KeywordAnalysisRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> KeywordAnalysisRead:
    record = await analysis_service.run_keyword_analysis(session, bd, payload.profile_id, payload.target_role_id)
    return KeywordAnalysisRead.model_validate(record, from_attributes=True)


@router.post("/location", response_model=LocationAnalysisRead, status_code=201)
@limiter.limit("20/minute")
async def analyze_location(
    request: Request,
    payload: LocationAnalysisRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> LocationAnalysisRead:
    record = await analysis_service.run_location_analysis(session, bd, payload.client_id, payload.target_role_id)
    return LocationAnalysisRead.model_validate(record, from_attributes=True)


@router.post("/compare", response_model=ComparisonRead, status_code=201)
@limiter.limit("10/minute")
async def compare_profiles(
    request: Request,
    payload: ComparisonRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ComparisonRead:
    run = await analysis_service.run_comparison(
        session, bd, payload.client_id, payload.profile_ids, payload.target_role_id
    )
    return ComparisonRead.model_validate(run, from_attributes=True)


@router.post("/compare-clients", response_model=ComparisonRead, status_code=201)
@limiter.limit("10/minute")
async def compare_clients(
    request: Request,
    payload: CrossClientComparisonRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ComparisonRead:
    """Compare resume profiles across different clients (e.g. two different candidates).
    Unlike /compare, profiles don't need to share a client — each is checked for BD
    ownership individually, and the role context is freeform title/keywords rather than
    a persisted TargetRole (which would belong to only one of the clients)."""
    run = await analysis_service.run_cross_client_comparison(
        session, bd, payload.profile_ids, payload.role_title, payload.role_keywords
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


@router.post("/refresh-stale", response_model=list[ComparisonRead])
async def refresh_stale_comparisons(
    bd: BusinessDeveloper = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[ComparisonRead]:
    """Manually trigger the same feedback-loop refresh the scheduler runs periodically.
    Admin-only since it operates system-wide, across all BDs' clients."""
    settings = get_settings()
    runs = await feedback_loop_service.refresh_stale_comparisons(
        session, min_new_applications=settings.feedback_loop_min_applications
    )
    return [ComparisonRead.model_validate(r, from_attributes=True) for r in runs]
