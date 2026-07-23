import logging
import uuid

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.schemas.client import ClientCreate, ClientUpdate
from db.models import (
    Application,
    BDRole,
    BusinessDeveloper,
    Client,
    ClientDocument,
    ComparisonRun,
    JobMatchRun,
    KeywordAnalysis,
    LocationAnalysis,
    Profile,
    TargetRole,
)
from services import s3_service

logger = logging.getLogger("applytics")


async def create_client(session: AsyncSession, bd: BusinessDeveloper, payload: ClientCreate) -> Client:
    client = Client(bd_id=bd.id, **payload.model_dump())
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def list_clients(session: AsyncSession, bd: BusinessDeveloper) -> list[Client]:
    statement = select(Client)
    if bd.role != BDRole.admin:
        statement = statement.where(Client.bd_id == bd.id)
    result = await session.exec(statement)
    return list(result.all())


async def get_client_scoped(session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if bd.role != BDRole.admin and client.bd_id != bd.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


async def update_client(
    session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID, payload: ClientUpdate
) -> Client:
    client = await get_client_scoped(session, bd, client_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def delete_client(session: AsyncSession, bd: BusinessDeveloper, client_id: uuid.UUID) -> None:
    """Deleting a client cascades through everything that belongs to them — unlike job
    deletion elsewhere in this app (which blocks if referenced, since a scraped job is
    shared data), a client's profiles/target roles/applications/analyses are entirely
    theirs, so a BD removing a candidate expects it all to go. Each phase is flushed
    before the next so statement order is explicit rather than relying on the ORM's
    automatic FK dependency sort across many unrelated mapped classes."""
    client = await get_client_scoped(session, bd, client_id)

    profiles = list((await session.exec(select(Profile).where(Profile.client_id == client.id))).all())
    profile_ids = [p.id for p in profiles]

    if profile_ids:
        # Cross-client comparison runs (client_id is None) may crown one of this
        # client's profiles the winner — null that FK rather than deleting the run,
        # since the run still involves another client's data too.
        cross_client_runs = (
            await session.exec(select(ComparisonRun).where(ComparisonRun.winner_profile_id.in_(profile_ids)))
        ).all()
        for run in cross_client_runs:
            run.winner_profile_id = None
            session.add(run)
        await session.flush()

    same_client_runs = (await session.exec(select(ComparisonRun).where(ComparisonRun.client_id == client.id))).all()
    for run in same_client_runs:
        await session.delete(run)
    await session.flush()

    job_match_runs = (await session.exec(select(JobMatchRun).where(JobMatchRun.client_id == client.id))).all()
    for run in job_match_runs:
        await session.delete(run)
    await session.flush()

    if profile_ids:
        keyword_analyses = (
            await session.exec(select(KeywordAnalysis).where(KeywordAnalysis.profile_id.in_(profile_ids)))
        ).all()
        for analysis in keyword_analyses:
            await session.delete(analysis)
        await session.flush()

    location_analyses = (
        await session.exec(select(LocationAnalysis).where(LocationAnalysis.client_id == client.id))
    ).all()
    for analysis in location_analyses:
        await session.delete(analysis)
    await session.flush()

    applications = (await session.exec(select(Application).where(Application.client_id == client.id))).all()
    for application in applications:
        await session.delete(application)
    await session.flush()

    documents = (await session.exec(select(ClientDocument).where(ClientDocument.client_id == client.id))).all()
    for document in documents:
        try:
            s3_service.delete_file(document.s3_key)
        except Exception:
            # Best-effort — an orphaned S3 object is a cheap cleanup problem, but
            # failing the whole client deletion over it is not an acceptable trade-off.
            logger.exception("Failed to delete S3 object %s for client %s", document.s3_key, client.id)
        await session.delete(document)
    await session.flush()

    for profile in profiles:
        await session.delete(profile)
    await session.flush()

    target_roles = (await session.exec(select(TargetRole).where(TargetRole.client_id == client.id))).all()
    for target_role in target_roles:
        await session.delete(target_role)
    await session.flush()

    await session.delete(client)
    await session.commit()
