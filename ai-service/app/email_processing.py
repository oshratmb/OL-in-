"""Shared by the Gmail sync job (app/jobs/sync_gmail.py) and the manual-paste
endpoint (POST /emails/manual) — one code path classifies and links an email
regardless of where it came from.
"""

from datetime import datetime, timezone

from . import supabase_client
from .crews.email_parser_crew import run_email_parser

# Must match supabase/migrations/0001_init.sql's application_status enum.
VALID_APPLICATION_STATUSES = {
    "applied",
    "phone_screen",
    "homework",
    "tech_interview",
    "offer",
    "rejected",
    "on_hold",
}


def process_incoming_email(
    user_id: str,
    subject: str,
    sender: str,
    body_text: str,
    received_at: str | None = None,
    gmail_message_id: str | None = None,
) -> dict | None:
    """Classifies and links an incoming email to the right application.

    Returns {email_id, application_id, recommended_action}, or None if the
    email was irrelevant (NO_MATCH — nothing stored) or a duplicate
    (gmail_message_id already processed).
    """
    received_at = received_at or datetime.now(timezone.utc).isoformat()

    candidates = supabase_client.list_candidate_applications(user_id)
    result = run_email_parser(subject, sender, body_text, candidates)

    if result["recommended_action"] == "NO_MATCH":
        return None

    application_id = None
    if result["recommended_action"] == "AUTO_LINK" and result["matching_applications"]:
        application_id = result["matching_applications"][0]["application_id"]

    classified_status = result.get("classified_status") or ""

    email_id = supabase_client.insert_email(
        user_id=user_id,
        subject=subject,
        sender=sender,
        body_content=body_text,
        status_classified=classified_status,
        received_at=received_at,
        application_id=application_id,
        gmail_message_id=gmail_message_id,
    )
    if email_id is None:
        return None  # duplicate gmail_message_id — already processed

    if application_id and classified_status in VALID_APPLICATION_STATUSES:
        supabase_client.update_application_status(application_id, classified_status)

    return {
        "email_id": email_id,
        "application_id": application_id,
        "recommended_action": result["recommended_action"],
    }
