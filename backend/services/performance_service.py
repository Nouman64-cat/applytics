import uuid

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.performance import ProfilePerformanceRead
from db.models import Application, BusinessDeveloper, Profile
from db.models.enums import ApplicationStatus
from services.client_service import get_client_scoped

INTERVIEW_OR_BETTER = {ApplicationStatus.interview, ApplicationStatus.offer}


async def get_profile_performance(
    session: AsyncSession,
    bd: BusinessDeveloper,
    client_id: uuid.UUID,
    target_role_id: uuid.UUID | None = None,
) -> list[ProfilePerformanceRead]:
    await get_client_scoped(session, bd, client_id)

    profile_statement = select(Profile).where(Profile.client_id == client_id)
    if target_role_id is not None:
        profile_statement = profile_statement.where(Profile.target_role_id == target_role_id)
    profiles = list((await session.exec(profile_statement)).all())
    if not profiles:
        return []

    profile_ids = [p.id for p in profiles]
    count_statement = (
        select(Application.profile_id, Application.status, func.count())
        .where(Application.profile_id.in_(profile_ids))
        .group_by(Application.profile_id, Application.status)
    )
    rows = (await session.execute(count_statement)).all()

    counts: dict[uuid.UUID, dict[ApplicationStatus, int]] = {p.id: {} for p in profiles}
    for profile_id, app_status, count in rows:
        counts[profile_id][app_status] = count

    results = []
    for profile in profiles:
        status_counts = counts[profile.id]
        total = sum(status_counts.values())
        interview_or_better = sum(status_counts.get(s, 0) for s in INTERVIEW_OR_BETTER)
        results.append(
            ProfilePerformanceRead(
                profile_id=profile.id,
                variant_label=profile.variant_label,
                total_applications=total,
                status_counts={s.value: status_counts.get(s, 0) for s in ApplicationStatus},
                interview_rate=(interview_or_better / total) if total else None,
            )
        )
    return results
