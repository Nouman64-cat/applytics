import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlmodel.ext.asyncio.session import AsyncSession

from agents.resume_extraction_agent import (
    extract_linkedin_profile_details,
    extract_linkedin_profile_from_url,
    extract_resume_details,
)
from api.schemas.client import (
    ClientCreate,
    ClientRead,
    ClientUpdate,
    LinkedInTextExtractionRequest,
    LinkedInUrlExtractionRequest,
    ResumeExtractionRead,
)
from api.schemas.client_document import ClientDocumentRead
from api.schemas.performance import ProfilePerformanceRead
from api.schemas.target_role import TargetRoleCreate, TargetRoleRead
from core.db import get_session
from core.deps import get_current_bd
from core.rate_limit import limiter
from db.models import BusinessDeveloper, ClientDocument
from services import client_document_service, client_service, performance_service, s3_service, target_role_service

router = APIRouter(prefix="/clients")


@router.post("", response_model=ClientRead, status_code=201)
async def create_client(
    payload: ClientCreate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    client = await client_service.create_client(session, bd, payload)
    return ClientRead.model_validate(client, from_attributes=True)


@router.post("/extract-resume", response_model=ResumeExtractionRead)
@limiter.limit("10/minute")
async def extract_resume(
    request: Request,
    file: UploadFile = File(...),
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ResumeExtractionRead:
    """OCR/extract candidate contact details from an uploaded resume (Gemini 2.5 Flash) to
    prefill the new-client form. Doesn't create or touch any Client record itself."""
    content = await file.read()
    try:
        result = await extract_resume_details(session, file.filename or "resume", content)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ResumeExtractionRead.model_validate(result, from_attributes=True)


@router.post("/extract-linkedin-text", response_model=ResumeExtractionRead)
@limiter.limit("10/minute")
async def extract_linkedin_text(
    request: Request,
    payload: LinkedInTextExtractionRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ResumeExtractionRead:
    """Extract candidate contact/location details (Gemini 2.5 Flash) from text the BD pasted
    from their own logged-in LinkedIn session — no scraping, so no block risk."""
    try:
        result = await extract_linkedin_profile_details(session, payload.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ResumeExtractionRead.model_validate(result, from_attributes=True)


@router.post("/extract-linkedin-url", response_model=ResumeExtractionRead)
@limiter.limit("5/minute")
async def extract_linkedin_url(
    request: Request,
    payload: LinkedInUrlExtractionRequest,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ResumeExtractionRead:
    """Fetch a public LinkedIn profile URL in guest mode and extract candidate details
    (Gemini 2.5 Flash). Individual profile pages run much more aggressive bot-detection
    than LinkedIn's job-search pages — this can fail or return sparse results; callers
    should treat that as an expected occasional outcome and offer the text-paste fallback."""
    try:
        result = await extract_linkedin_profile_from_url(session, payload.url)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ResumeExtractionRead.model_validate(result, from_attributes=True)


@router.get("", response_model=list[ClientRead])
async def list_clients(
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ClientRead]:
    clients = await client_service.list_clients(session, bd)
    return [ClientRead.model_validate(c, from_attributes=True) for c in clients]


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    client = await client_service.get_client_scoped(session, bd, client_id)
    return ClientRead.model_validate(client, from_attributes=True)


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    client = await client_service.update_client(session, bd, client_id, payload)
    return ClientRead.model_validate(client, from_attributes=True)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> None:
    await client_service.delete_client(session, bd, client_id)


@router.post("/{client_id}/target-roles", response_model=TargetRoleRead, status_code=201)
async def create_target_role(
    client_id: uuid.UUID,
    payload: TargetRoleCreate,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> TargetRoleRead:
    target_role = await target_role_service.create_target_role(session, bd, client_id, payload)
    return TargetRoleRead.model_validate(target_role, from_attributes=True)


@router.get("/{client_id}/target-roles", response_model=list[TargetRoleRead])
async def list_target_roles(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[TargetRoleRead]:
    target_roles = await target_role_service.list_target_roles(session, bd, client_id)
    return [TargetRoleRead.model_validate(t, from_attributes=True) for t in target_roles]


@router.get("/{client_id}/performance", response_model=list[ProfilePerformanceRead])
async def get_client_performance(
    client_id: uuid.UUID,
    target_role_id: uuid.UUID | None = None,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ProfilePerformanceRead]:
    return await performance_service.get_profile_performance(session, bd, client_id, target_role_id)


def _document_read(document: ClientDocument) -> ClientDocumentRead:
    return ClientDocumentRead(
        id=document.id,
        client_id=document.client_id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        preview_url=s3_service.generate_presigned_url(document.s3_key),
        uploaded_at=document.uploaded_at,
    )


@router.post("/{client_id}/documents", response_model=ClientDocumentRead, status_code=201)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    client_id: uuid.UUID,
    file: UploadFile = File(...),
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> ClientDocumentRead:
    content = await file.read()
    document = await client_document_service.upload_document(
        session,
        bd,
        client_id,
        file.filename or "document",
        content,
        file.content_type or "application/octet-stream",
    )
    return _document_read(document)


@router.get("/{client_id}/documents", response_model=list[ClientDocumentRead])
async def list_documents(
    client_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> list[ClientDocumentRead]:
    documents = await client_document_service.list_documents(session, bd, client_id)
    return [_document_read(d) for d in documents]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    bd: BusinessDeveloper = Depends(get_current_bd),
    session: AsyncSession = Depends(get_session),
) -> None:
    await client_document_service.delete_document(session, bd, document_id)
