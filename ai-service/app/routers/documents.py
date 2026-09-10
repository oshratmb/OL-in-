import uuid

from fastapi import APIRouter, Depends, HTTPException

from .. import supabase_client
from ..auth_dependency import get_current_user
from ..crews.orchestration import run_tailoring_with_gatekeeper
from ..crews.tailoring_crew import run_gap_analysis
from ..crews.translator_crew import run_translation
from ..docx_generator import generate_resume_docx
from ..models import (
    GenerateDocumentsRequest,
    GenerateDocumentsResponse,
    JobAnalyzeRequest,
    JobAnalyzeResponse,
    TranslateRequest,
    TranslateResponse,
)
from ..rbac import require_active_user

router = APIRouter(tags=["documents"])


def _require_core_profile(user_id: str) -> dict:
    profile = supabase_client.get_core_profile(user_id)
    if profile is None:
        raise HTTPException(400, "Complete your profile (Onboarding) before using this feature")
    return profile


def _store_document(user_id: str, resume: dict, docx_bytes: bytes | None = None) -> str:
    payload = docx_bytes if docx_bytes else generate_resume_docx(resume)
    storage_path = f"{user_id}/{uuid.uuid4()}.docx"
    supabase_client.upload_tailored_document(storage_path, payload)
    return supabase_client.create_signed_document_url(storage_path)


@router.post("/jobs/analyze", response_model=JobAnalyzeResponse)
async def analyze_job(
    body: JobAnalyzeRequest,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    core_profile = _require_core_profile(user["sub"])
    try:
        result = run_gap_analysis(core_profile, body.description_text)
    except ValueError as exc:
        supabase_client.log_error("jobs_analyze", str(exc))
        raise HTTPException(502, "AI analysis returned an unreadable result, please retry") from exc
    return result


@router.post("/documents/generate", response_model=GenerateDocumentsResponse)
async def generate_documents(
    body: GenerateDocumentsRequest,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    user_id = user["sub"]
    core_profile = _require_core_profile(user_id)

    try:
        result = run_tailoring_with_gatekeeper(
            core_profile,
            body.job.model_dump(),
            [a.model_dump() for a in body.qna_answers],
            body.tone,
        )
    except ValueError as exc:
        supabase_client.log_error("documents_generate", str(exc))
        raise HTTPException(502, "AI generation returned an unreadable result, please retry") from exc

    tailored_resume_url = _store_document(user_id, result.resume, result.docx_bytes or None)

    if body.application_id:
        # Re-generation (e.g. tone switch on the preview screen) for a job
        # already saved — update in place, don't create a duplicate application.
        existing = supabase_client.get_application(body.application_id, user_id)
        if existing is None:
            raise HTTPException(404, "Application not found")
        application_id = body.application_id
        supabase_client.update_application_documents(application_id, tailored_resume_url, result.cover_letter)
    else:
        job_id = supabase_client.create_job(body.job.title, body.job.company_name, body.job.description_text)
        application_id = supabase_client.create_application(
            user_id, job_id, tailored_resume_url, result.cover_letter
        )

    return GenerateDocumentsResponse(
        application_id=application_id,
        resume=result.resume,
        tailored_resume_url=tailored_resume_url,
        cover_letter_text=result.cover_letter,
        gatekeeper_status=result.gatekeeper_status,
        violations=result.violations,
    )


@router.post("/documents/translate", response_model=TranslateResponse)
async def translate_documents(
    body: TranslateRequest,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    user_id = user["sub"]
    application = supabase_client.get_application(body.application_id, user_id)
    if application is None:
        raise HTTPException(404, "Application not found")

    try:
        translated = run_translation(body.resume.model_dump(), body.cover_letter_text, body.target_language)
    except ValueError as exc:
        supabase_client.log_error("documents_translate", str(exc))
        raise HTTPException(502, "AI translation returned an unreadable result, please retry") from exc

    tailored_resume_url = _store_document(user_id, translated["resume"])
    supabase_client.update_application_documents(
        body.application_id, tailored_resume_url, translated["cover_letter"]
    )

    return TranslateResponse(
        resume=translated["resume"],
        tailored_resume_url=tailored_resume_url,
        cover_letter_text=translated["cover_letter"],
    )
