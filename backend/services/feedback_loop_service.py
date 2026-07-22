import logging

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import Application, Client, ComparisonRun, Profile, TargetRole
from db.models.enums import AnalysisStatus
from services.analysis_service import _role_context_from_target_role, execute_comparison

logger = logging.getLogger(__name__)


async def _last_comparison_completed_at(session: AsyncSession, client_id, target_role_id):
    statement = (
        select(ComparisonRun)
        .where(
            ComparisonRun.client_id == client_id,
            ComparisonRun.target_role_id == target_role_id,
            ComparisonRun.status == AnalysisStatus.complete,
        )
        .order_by(ComparisonRun.completed_at.desc())
        .limit(1)
    )
    result = await session.exec(statement)
    run = result.first()
    return run.completed_at if run else None


async def refresh_stale_comparisons(session: AsyncSession, min_new_applications: int) -> list[ComparisonRun]:
    """Re-run the comparison agent for client/target-role groups that have accumulated
    enough new application outcomes since their last comparison, so the AI's recommendation
    is informed by real interview/offer results instead of staying frozen at profile-creation
    time. Intended to run on a schedule (see core/scheduler.py) — has no BD context, so it
    operates system-wide across all clients rather than being scoped to one BD's data.
    """
    triggered: list[ComparisonRun] = []

    pairs_statement = (
        select(Profile.client_id, Profile.target_role_id)
        .where(Profile.target_role_id.is_not(None), Profile.is_active == True)  # noqa: E712
        .distinct()
    )
    pairs = (await session.execute(pairs_statement)).all()

    for client_id, target_role_id in pairs:
        profiles_result = await session.exec(
            select(Profile).where(
                Profile.client_id == client_id,
                Profile.target_role_id == target_role_id,
                Profile.is_active == True,  # noqa: E712
            )
        )
        profiles = list(profiles_result.all())
        if len(profiles) < 2:
            continue

        last_run_at = await _last_comparison_completed_at(session, client_id, target_role_id)

        count_statement = select(func.count()).select_from(Application).where(
            Application.profile_id.in_([p.id for p in profiles])
        )
        if last_run_at is not None:
            count_statement = count_statement.where(Application.applied_at > last_run_at)
        new_app_count = (await session.execute(count_statement)).scalar_one()

        if new_app_count < min_new_applications:
            continue

        client = await session.get(Client, client_id)
        target_role = await session.get(TargetRole, target_role_id)

        role_context = _role_context_from_target_role(target_role)
        run = await execute_comparison(
            session, client, profiles, role_context, target_role_id=target_role.id if target_role else None
        )
        triggered.append(run)
        logger.info(
            "Feedback loop: refreshed comparison for client=%s target_role=%s run=%s (%d new applications)",
            client_id,
            target_role_id,
            run.id,
            new_app_count,
        )

    return triggered
