import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlmodel import and_, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import (
    Application,
    BusinessDeveloper,
    Client,
    ComparisonRun,
    Job,
    JobSource,
    KeywordAnalysis,
    Profile,
    ScrapeRun,
    TargetRole,
)
from db.models.enums import AnalysisStatus, BDRole, ProfileType

TOP_TITLES_LIMIT = 20
TOP_COUNTRIES_LIMIT = 10
TREND_WINDOW_DAYS = 30
SCRAPE_HEALTH_WINDOW_DAYS = 30
CANDIDATE_PERFORMANCE_LIMIT = 60
MISSING_KEYWORDS_PREVIEW_LIMIT = 8
INTERVIEW_OR_BETTER_STATUSES = {"interview", "offer"}
COMPARISON_RUN_SCAN_LIMIT = 100
COMPARISON_RUN_RESULT_LIMIT = 15


def _window_filter(start: datetime, end: datetime):
    # Several sources (Indeed/Glassdoor/Jobright) don't reliably expose a real posted
    # date — same fallback used by job_service._filtered_statement, so jobs without a
    # posted_at are judged by when they were found instead of silently excluded.
    return or_(
        and_(Job.posted_at >= start, Job.posted_at < end),
        and_(Job.posted_at.is_(None), Job.scraped_at >= start, Job.scraped_at < end),
    )


def _scope_to_bd(statement, bd: BusinessDeveloper):
    if bd.role != BDRole.admin:
        statement = statement.where(Client.bd_id == bd.id)
    return statement


async def _counts_by_source_in_window(session: AsyncSession, start: datetime, end: datetime) -> dict[str, int]:
    statement = (
        select(JobSource.name, func.count(Job.id))
        .join(Job, Job.job_source_id == JobSource.id)
        .where(_window_filter(start, end))
        .group_by(JobSource.name)
    )
    result = await session.execute(statement)
    return {name: count for name, count in result.all()}


async def _top_titles(session: AsyncSession) -> list[dict]:
    normalized_title = func.lower(func.trim(Job.title)).label("normalized_title")
    statement = (
        select(normalized_title, func.count(Job.id))
        .group_by(normalized_title)
        .order_by(func.count(Job.id).desc())
        .limit(TOP_TITLES_LIMIT)
    )
    result = await session.execute(statement)
    return [{"title": title, "count": count} for title, count in result.all()]


async def _counts_by_remote_type(session: AsyncSession) -> dict[str, int]:
    statement = select(Job.remote_type, func.count(Job.id)).group_by(Job.remote_type)
    result = await session.execute(statement)
    return {remote_type.value: count for remote_type, count in result.all()}


async def _top_countries(session: AsyncSession) -> dict[str, int]:
    statement = (
        select(Job.country, func.count(Job.id))
        .where(Job.country.is_not(None))
        .group_by(Job.country)
        .order_by(func.count(Job.id).desc())
        .limit(TOP_COUNTRIES_LIMIT)
    )
    result = await session.execute(statement)
    return {country: count for country, count in result.all()}


async def _applications_by_source(session: AsyncSession, bd: BusinessDeveloper) -> dict[str, int]:
    statement = (
        select(JobSource.name, func.count(Application.id))
        .join(Job, Application.job_id == Job.id)
        .join(JobSource, Job.job_source_id == JobSource.id)
        .join(Client, Application.client_id == Client.id)
        .group_by(JobSource.name)
    )
    statement = _scope_to_bd(statement, bd)
    result = await session.execute(statement)
    return {name: count for name, count in result.all()}


async def _applications_by_target_role(session: AsyncSession, bd: BusinessDeveloper) -> dict[str, int]:
    statement = (
        select(TargetRole.title, func.count(Application.id))
        .join(Profile, Application.profile_id == Profile.id)
        .join(TargetRole, Profile.target_role_id == TargetRole.id)
        .join(Client, Application.client_id == Client.id)
        .group_by(TargetRole.title)
    )
    statement = _scope_to_bd(statement, bd)
    result = await session.execute(statement)
    return {title: count for title, count in result.all()}


async def _application_status_funnel(session: AsyncSession, bd: BusinessDeveloper) -> dict[str, int]:
    statement = (
        select(Application.status, func.count(Application.id))
        .join(Client, Application.client_id == Client.id)
        .group_by(Application.status)
    )
    statement = _scope_to_bd(statement, bd)
    result = await session.execute(statement)
    return {status.value: count for status, count in result.all()}


async def _scrape_health(session: AsyncSession, since: datetime) -> dict[str, dict[str, int]]:
    statement = (
        select(JobSource.name, ScrapeRun.status, func.count(ScrapeRun.id))
        .join(JobSource, ScrapeRun.job_source_id == JobSource.id)
        .where(ScrapeRun.created_at >= since)
        .group_by(JobSource.name, ScrapeRun.status)
    )
    result = await session.execute(statement)
    health: dict[str, dict[str, int]] = {}
    for name, status, count in result.all():
        health.setdefault(name, {})[status.value] = count
    return health


async def _bd_resume_profiles(session: AsyncSession, bd: BusinessDeveloper) -> dict[uuid.UUID, dict]:
    """profile_id -> {client_name, variant_label, target_role, is_active} for every resume
    profile belonging to this BD's clients (active or not — a ComparisonRun may reference
    an older variant that's since been deactivated). Shared by the two functions below so
    each candidate/profile is only resolved to a client name once."""
    client_statement = select(Client.id, Client.full_name)
    client_statement = _scope_to_bd(client_statement, bd)
    clients = (await session.execute(client_statement)).all()
    if not clients:
        return {}
    client_names = {client_id: full_name for client_id, full_name in clients}

    profile_statement = (
        select(Profile.id, Profile.client_id, Profile.variant_label, Profile.is_active, TargetRole.title)
        .join(TargetRole, Profile.target_role_id == TargetRole.id, isouter=True)
        .where(Profile.client_id.in_(client_names.keys()), Profile.type == ProfileType.resume)
    )
    rows = (await session.execute(profile_statement)).all()
    return {
        profile_id: {
            "client_name": client_names[client_id],
            "variant_label": variant_label,
            "target_role": target_role_title,
            "is_active": is_active,
        }
        for profile_id, client_id, variant_label, is_active, target_role_title in rows
    }


async def _candidate_resume_performance(
    session: AsyncSession, profile_info: dict[uuid.UUID, dict]
) -> list[dict]:
    """Per-resume application volume/interview-rate and (where available) the most
    recent ATS/keyword-fit score, for this BD's active resumes. Secondary signal only —
    many BDs don't log every application in this system, so 0 applications means 'no
    data logged here', not 'this resume has never been used'. The primary signal for
    'why is X's resume outperforming Y's' is the resume comparison history below."""
    active_profile_ids = [pid for pid, info in profile_info.items() if info["is_active"]]
    if not active_profile_ids:
        return []

    app_statement = (
        select(Application.profile_id, Application.status, func.count())
        .where(Application.profile_id.in_(active_profile_ids))
        .group_by(Application.profile_id, Application.status)
    )
    app_counts: dict[uuid.UUID, dict[str, int]] = {}
    for profile_id, app_status, count in (await session.execute(app_statement)).all():
        app_counts.setdefault(profile_id, {})[app_status.value] = count

    ka_statement = (
        select(KeywordAnalysis)
        .where(KeywordAnalysis.profile_id.in_(active_profile_ids))
        .order_by(KeywordAnalysis.created_at.desc())
    )
    latest_keyword_analysis: dict[uuid.UUID, KeywordAnalysis] = {}
    for analysis in (await session.exec(ka_statement)).all():
        latest_keyword_analysis.setdefault(analysis.profile_id, analysis)

    rows = []
    for profile_id in active_profile_ids:
        info = profile_info[profile_id]
        status_counts = app_counts.get(profile_id, {})
        total = sum(status_counts.values())
        interview_or_better = sum(status_counts.get(s, 0) for s in INTERVIEW_OR_BETTER_STATUSES)
        analysis = latest_keyword_analysis.get(profile_id)
        rows.append(
            {
                "client_name": info["client_name"],
                "resume_variant": info["variant_label"],
                "target_role": info["target_role"],
                "total_applications": total,
                "status_counts": status_counts,
                "interview_rate": round(interview_or_better / total, 2) if total else None,
                "ats_score": analysis.ats_score if analysis else None,
                "recruiter_attention_score": analysis.recruiter_attention_score if analysis else None,
                "missing_keywords": analysis.missing_keywords[:MISSING_KEYWORDS_PREVIEW_LIMIT] if analysis else [],
            }
        )

    rows.sort(key=lambda r: (r["target_role"] or "", r["client_name"] or ""))
    return rows[:CANDIDATE_PERFORMANCE_LIMIT]


def _label_profile(profile_info: dict[uuid.UUID, dict], profile_id_str: str | None) -> str | None:
    if not profile_id_str:
        return None
    info = profile_info.get(uuid.UUID(profile_id_str))
    if info is None:
        return None
    return f"{info['client_name']} ({info['variant_label']})"


async def _recent_resume_comparisons(
    session: AsyncSession, profile_info: dict[uuid.UUID, dict]
) -> list[dict]:
    """Recent completed ComparisonRun records (from the Compare feature) touching any of
    this BD's resumes — the actual qualitative 'why is X's resume better than Y's'
    reasoning already produced by that feature, which this snapshot previously ignored
    entirely in favor of application counts most BDs don't actually log."""
    if not profile_info:
        return []
    owned_profile_id_strs = {str(pid) for pid in profile_info}

    statement = (
        select(ComparisonRun)
        .where(ComparisonRun.status == AnalysisStatus.complete)
        .order_by(ComparisonRun.created_at.desc())
        .limit(COMPARISON_RUN_SCAN_LIMIT)
    )
    runs = (await session.exec(statement)).all()

    results = []
    for run in runs:
        if not any(pid in owned_profile_id_strs for pid in run.profile_ids):
            continue
        candidates = [
            {"candidate": _label_profile(profile_info, score.get("profile_id")) or score.get("profile_id"), "score": score.get("score")}
            for score in run.result_detail.get("profile_scores", [])
        ]
        results.append(
            {
                "compared_at": run.created_at.isoformat(),
                "candidates": candidates,
                "winner": _label_profile(profile_info, str(run.winner_profile_id) if run.winner_profile_id else None),
                "summary": run.result_summary,
            }
        )
        if len(results) >= COMPARISON_RUN_RESULT_LIMIT:
            break
    return results


async def build_market_snapshot(session: AsyncSession, bd: BusinessDeveloper) -> dict:
    """Precomputed SQL aggregates handed to the market-research agent as grounding
    context each turn — never raw job/application rows, to keep prompt size and cost
    bounded (same cost-conscious approach as job_match_agent's candidate cap).

    Job/scrape data is platform-wide (matches the existing Jobs page, not BD-owned);
    application/target-role stats are scoped to the current BD's own clients (admins
    see all, same rule as client_service.list_clients).
    """
    now = datetime.now(timezone.utc)
    last_window_start = now - timedelta(days=TREND_WINDOW_DAYS)
    prior_window_start = now - timedelta(days=TREND_WINDOW_DAYS * 2)

    jobs_last_window = await _counts_by_source_in_window(session, last_window_start, now)
    jobs_prior_window = await _counts_by_source_in_window(session, prior_window_start, last_window_start)
    profile_info = await _bd_resume_profiles(session, bd)

    return {
        "generated_at": now.isoformat(),
        "trend_window_days": TREND_WINDOW_DAYS,
        "job_counts_by_source_last_window": jobs_last_window,
        "job_counts_by_source_prior_window": jobs_prior_window,
        "top_job_titles": await _top_titles(session),
        "job_counts_by_remote_type": await _counts_by_remote_type(session),
        "top_job_countries": await _top_countries(session),
        "applications_by_source": await _applications_by_source(session, bd),
        "applications_by_target_role": await _applications_by_target_role(session, bd),
        "application_status_funnel": await _application_status_funnel(session, bd),
        "scrape_health_by_source": await _scrape_health(session, now - timedelta(days=SCRAPE_HEALTH_WINDOW_DAYS)),
        "candidate_resume_performance": await _candidate_resume_performance(session, profile_info),
        "recent_resume_comparisons": await _recent_resume_comparisons(session, profile_info),
    }


def _format_candidate_row(row: dict) -> str:
    parts = [
        f"- {row['client_name']} (resume variant {row['resume_variant']}, target role: "
        f"{row['target_role'] or 'unspecified'}): {row['total_applications']} applications, "
        f"interview_rate={row['interview_rate']}, status_counts={row['status_counts']}"
    ]
    if row["ats_score"] is not None:
        parts.append(
            f"ATS score={row['ats_score']}, recruiter_attention_score={row['recruiter_attention_score']}, "
            f"missing_keywords={row['missing_keywords']}"
        )
    return "; ".join(parts)


def _format_comparison_row(row: dict) -> str:
    candidates_str = ", ".join(f"{c['candidate']}={c['score']}" for c in row["candidates"]) or "unavailable"
    winner = row["winner"] or "no clear winner / tie"
    return f"- Compared {row['compared_at']}: {candidates_str}. Winner: {winner}. Why: {row['summary']}"


def format_snapshot_for_prompt(snapshot: dict) -> str:
    candidate_rows = snapshot["candidate_resume_performance"]
    candidate_lines = (
        [_format_candidate_row(row) for row in candidate_rows]
        if candidate_rows
        else ["(no active candidate resumes found)"]
    )

    comparison_rows = snapshot["recent_resume_comparisons"]
    comparison_lines = (
        [_format_comparison_row(row) for row in comparison_rows]
        if comparison_rows
        else ["(no resume comparisons have been run between this BD's candidates yet)"]
    )

    lines = [
        f"DATA SNAPSHOT generated at {snapshot['generated_at']} "
        f"(trend windows are {snapshot['trend_window_days']}-day periods; job titles are grouped by raw "
        "lowercased/trimmed string, so near-duplicates like 'Sr.' vs 'Senior' are NOT merged — caveat "
        "any title-based precision accordingly):",
        "",
        f"Job counts by source, most recent {snapshot['trend_window_days']} days: "
        f"{snapshot['job_counts_by_source_last_window']}",
        f"Job counts by source, prior {snapshot['trend_window_days']} days (for trend/dip comparison): "
        f"{snapshot['job_counts_by_source_prior_window']}",
        f"Top scraped job titles (all-time, top {TOP_TITLES_LIMIT}): {snapshot['top_job_titles']}",
        f"Job counts by remote type: {snapshot['job_counts_by_remote_type']}",
        f"Top job countries: {snapshot['top_job_countries']}",
        f"Applications logged by job source (this BD's clients — NOTE: many BDs don't log every application "
        f"in this system, so low/zero counts here mean 'not logged here', NOT 'this candidate has no real "
        f"activity' — don't treat this as evidence of inactivity): {snapshot['applications_by_source']}",
        f"Applications logged by target role title (this BD's clients, same caveat as above): "
        f"{snapshot['applications_by_target_role']}",
        f"Application status funnel (this BD's clients, same caveat as above): {snapshot['application_status_funnel']}",
        f"Recent scrape run health by source (last {SCRAPE_HEALTH_WINDOW_DAYS} days, success/failed/pending "
        f"counts — a source with only failures may be blocked, not reflective of real market conditions): "
        f"{snapshot['scrape_health_by_source']}",
        "",
        "Recent resume comparison runs (this BD's candidates, from the Compare feature) — this is the "
        "PRIMARY signal for 'why is candidate X's resume outperforming candidate Y's' questions, since it "
        "contains actual LLM-judged strengths/weaknesses, not just usage counts. If the same two candidates "
        "have been compared more than once with different scores/winners, say so explicitly and describe "
        "them as closely matched rather than picking one run as the definitive verdict:",
        *comparison_lines,
        "",
        "Per-candidate resume performance (this BD's own clients, active resumes only — SECONDARY signal, "
        "supplementary detail only; missing_keywords/ats_score are only present if a keyword analysis has "
        "actually been run for that resume):",
        *candidate_lines,
    ]
    return "\n".join(lines)
