from fastapi import APIRouter, Depends, HTTPException

from .. import supabase_client
from ..auth_dependency import get_current_user
from ..email_processing import VALID_APPLICATION_STATUSES, process_incoming_email
from ..models import EmailLinkRequest, ManualEmailRequest, UnlinkedEmailCandidate, UnlinkedEmailItem
from ..rbac import require_active_user

router = APIRouter(prefix="/emails", tags=["emails"])

_MAX_CANDIDATES_SHOWN = 3


@router.post("/manual")
async def submit_manual_email(
    body: ManualEmailRequest,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    try:
        result = process_incoming_email(
            user_id=user["sub"], subject=body.subject, sender=body.sender, body_text=body.body_content
        )
    except ValueError as exc:
        supabase_client.log_error("emails_manual", str(exc))
        raise HTTPException(502, "AI classification returned an unreadable result, please retry") from exc
    return {"ok": True, "result": result}


@router.get("/unlinked", response_model=list[UnlinkedEmailItem])
async def list_unlinked(user: dict = Depends(get_current_user)):
    user_id = user["sub"]
    emails = supabase_client.list_unlinked_emails(user_id)
    if not emails:
        return []

    candidates = [
        UnlinkedEmailCandidate(
            application_id=c["application_id"], job_title=c["job_title"], company_name=c["company_name"]
        )
        for c in supabase_client.list_candidate_applications(user_id)[:_MAX_CANDIDATES_SHOWN]
    ]
    if not candidates:
        return []  # nothing to link to — don't bother the user about it

    return [
        UnlinkedEmailItem(
            id=e["id"],
            subject=e["subject"],
            sender=e["sender"],
            received_at=e["received_at"],
            candidates=candidates,
        )
        for e in emails
    ]


@router.post("/{email_id}/link")
async def link_email(email_id: str, body: EmailLinkRequest, user: dict = Depends(get_current_user)):
    user_id = user["sub"]
    email = supabase_client.get_email(email_id, user_id)
    if email is None:
        raise HTTPException(404, "Email not found")
    application = supabase_client.get_application(body.application_id, user_id)
    if application is None:
        raise HTTPException(404, "Application not found")

    supabase_client.link_email_to_application(email_id, body.application_id)
    status_classified = email.get("status_classified")
    if status_classified in VALID_APPLICATION_STATUSES:
        supabase_client.update_application_status(body.application_id, status_classified)

    return {"ok": True}
