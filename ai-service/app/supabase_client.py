"""Service-role access to Supabase Storage/REST (bypasses RLS — server-only).

Every function here takes an already-JWT-verified `user_id` from the caller
(never a client-supplied one) and scopes storage paths / row ownership to it
explicitly, so bypassing RLS doesn't become a cross-user data leak.
"""

from datetime import datetime, timedelta, timezone

import httpx

from . import config

_REST_URL = f"{config.SUPABASE_URL}/rest/v1"
_STORAGE_URL = f"{config.SUPABASE_URL}/storage/v1"


def _service_headers(extra: dict | None = None) -> dict:
    return {
        "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
        **(extra or {}),
    }


def download_resume(storage_path: str) -> bytes:
    resp = httpx.get(f"{_STORAGE_URL}/object/resumes/{storage_path}", headers=_service_headers())
    if resp.status_code == 404:
        raise FileNotFoundError(storage_path)
    resp.raise_for_status()
    return resp.content


def upload_tailored_document(storage_path: str, docx_bytes: bytes) -> None:
    resp = httpx.post(
        f"{_STORAGE_URL}/object/tailored-documents/{storage_path}",
        headers=_service_headers(
            {
                "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "x-upsert": "true",
            }
        ),
        content=docx_bytes,
    )
    resp.raise_for_status()


def create_signed_document_url(storage_path: str, expires_in: int = 3600) -> str:
    resp = httpx.post(
        f"{_STORAGE_URL}/object/sign/tailored-documents/{storage_path}",
        headers=_service_headers({"Content-Type": "application/json"}),
        json={"expiresIn": expires_in},
    )
    resp.raise_for_status()
    return f"{config.SUPABASE_URL}/storage/v1{resp.json()['signedURL']}"


def get_core_profile(user_id: str) -> dict | None:
    resp = httpx.get(
        f"{_REST_URL}/core_profiles",
        headers=_service_headers(),
        params={"user_id": f"eq.{user_id}", "select": "parsed_data", "limit": 1},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0]["parsed_data"] if rows else None


def create_job(title: str, company_name: str, description: str) -> str:
    resp = httpx.post(
        f"{_REST_URL}/jobs",
        headers=_service_headers({"Content-Type": "application/json", "Prefer": "return=representation"}),
        json={"title": title, "company_name": company_name, "description": description},
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def create_application(
    user_id: str, job_id: str, tailored_resume_url: str, cover_letter_text: str
) -> str:
    resp = httpx.post(
        f"{_REST_URL}/applications",
        headers=_service_headers({"Content-Type": "application/json", "Prefer": "return=representation"}),
        json={
            "user_id": user_id,
            "job_id": job_id,
            "tailored_resume_url": tailored_resume_url,
            "cover_letter_text": cover_letter_text,
        },
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def get_application(application_id: str, user_id: str) -> dict | None:
    """Returns the application only if it belongs to `user_id` — the ownership
    check `/documents/translate` relies on before touching another user's data."""
    resp = httpx.get(
        f"{_REST_URL}/applications",
        headers=_service_headers(),
        params={"id": f"eq.{application_id}", "user_id": f"eq.{user_id}", "limit": 1},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def update_application_documents(
    application_id: str, tailored_resume_url: str, cover_letter_text: str
) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/applications",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"id": f"eq.{application_id}"},
        json={"tailored_resume_url": tailored_resume_url, "cover_letter_text": cover_letter_text},
    )
    resp.raise_for_status()


# --- Phase 3: Gmail connections, email processing ---


def list_candidate_applications(user_id: str) -> list[dict]:
    """Open applications (not already rejected/offer) — the pool the Email
    Parser Agent is allowed to match an incoming email against."""
    resp = httpx.get(
        f"{_REST_URL}/applications",
        headers=_service_headers(),
        params={
            "user_id": f"eq.{user_id}",
            "status": "not.in.(rejected,offer)",
            "select": "id,status,applied_at,jobs(title,company_name)",
        },
    )
    resp.raise_for_status()
    return [
        {
            "application_id": row["id"],
            "job_title": row["jobs"]["title"],
            "company_name": row["jobs"]["company_name"],
            "status": row["status"],
            "applied_at": row["applied_at"],
        }
        for row in resp.json()
    ]


def update_application_status(application_id: str, status: str) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/applications",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"id": f"eq.{application_id}"},
        json={"status": status},
    )
    resp.raise_for_status()


def insert_email(
    user_id: str,
    subject: str,
    sender: str,
    body_content: str,
    status_classified: str,
    received_at: str,
    application_id: str | None = None,
    gmail_message_id: str | None = None,
) -> str | None:
    """Returns the new email's id, or None if it was a duplicate
    (gmail_message_id already processed) — inserts are idempotent."""
    resp = httpx.post(
        f"{_REST_URL}/emails",
        headers=_service_headers(
            {
                "Content-Type": "application/json",
                "Prefer": "return=representation,resolution=ignore-duplicates",
            }
        ),
        params={"on_conflict": "gmail_message_id"} if gmail_message_id else {},
        json={
            "user_id": user_id,
            "application_id": application_id,
            "gmail_message_id": gmail_message_id,
            "subject": subject,
            "sender": sender,
            "body_content": body_content,
            "status_classified": status_classified,
            "received_at": received_at,
        },
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0]["id"] if rows else None


def list_unlinked_emails(user_id: str) -> list[dict]:
    resp = httpx.get(
        f"{_REST_URL}/emails",
        headers=_service_headers(),
        params={
            "user_id": f"eq.{user_id}",
            "application_id": "is.null",
            "select": "id,subject,sender,received_at",
            "order": "received_at.desc",
        },
    )
    resp.raise_for_status()
    return resp.json()


def get_email(email_id: str, user_id: str) -> dict | None:
    resp = httpx.get(
        f"{_REST_URL}/emails",
        headers=_service_headers(),
        params={"id": f"eq.{email_id}", "user_id": f"eq.{user_id}", "limit": 1},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def link_email_to_application(email_id: str, application_id: str) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/emails",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"id": f"eq.{email_id}"},
        json={"application_id": application_id},
    )
    resp.raise_for_status()


def get_gmail_connection(user_id: str) -> dict | None:
    resp = httpx.get(
        f"{_REST_URL}/gmail_connections",
        headers=_service_headers(),
        params={"user_id": f"eq.{user_id}", "limit": 1},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def list_all_gmail_connections() -> list[dict]:
    # Excludes paused accounts (§2.9: pausing stops Gmail monitoring) via an
    # inner-joined, filtered embed rather than a second query per connection.
    resp = httpx.get(
        f"{_REST_URL}/gmail_connections",
        headers=_service_headers(),
        params={
            "needs_reconnect": "eq.false",
            "select": "*,profiles!inner(is_paused)",
            "profiles.is_paused": "eq.false",
        },
    )
    resp.raise_for_status()
    return resp.json()


def upsert_gmail_connection(user_id: str, refresh_token: str, google_email: str, connected_at: str) -> None:
    # last_synced_at is seeded to "now" (not left null) so the first sync only
    # looks at mail received from this moment on — PRD explicitly rules out
    # retroactively scanning the mailbox's history on connect.
    resp = httpx.post(
        f"{_REST_URL}/gmail_connections",
        headers=_service_headers(
            {"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
        ),
        params={"on_conflict": "user_id"},
        json={
            "user_id": user_id,
            "refresh_token": refresh_token,
            "google_email": google_email,
            "last_synced_at": connected_at,
            "needs_reconnect": False,
        },
    )
    resp.raise_for_status()


def delete_gmail_connection(user_id: str) -> None:
    resp = httpx.delete(
        f"{_REST_URL}/gmail_connections",
        headers=_service_headers(),
        params={"user_id": f"eq.{user_id}"},
    )
    resp.raise_for_status()


def update_gmail_sync_time(user_id: str, synced_at: str) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/gmail_connections",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"user_id": f"eq.{user_id}"},
        json={"last_synced_at": synced_at},
    )
    resp.raise_for_status()


def mark_gmail_needs_reconnect(user_id: str) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/gmail_connections",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"user_id": f"eq.{user_id}"},
        json={"needs_reconnect": True},
    )
    resp.raise_for_status()


# --- Phase 4: Interview simulator ---


def get_application_with_job(application_id: str, user_id: str) -> dict | None:
    resp = httpx.get(
        f"{_REST_URL}/applications",
        headers=_service_headers(),
        params={
            "id": f"eq.{application_id}",
            "user_id": f"eq.{user_id}",
            "select": "id,status,jobs(title,company_name,description)",
            "limit": 1,
        },
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def create_simulation(
    user_id: str, application_id: str, persona_details: dict, chat_history: list[dict]
) -> str:
    resp = httpx.post(
        f"{_REST_URL}/simulations",
        headers=_service_headers({"Content-Type": "application/json", "Prefer": "return=representation"}),
        json={
            "user_id": user_id,
            "application_id": application_id,
            "persona_details": persona_details,
            "chat_history": chat_history,
        },
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]


def get_simulation(simulation_id: str, user_id: str) -> dict | None:
    resp = httpx.get(
        f"{_REST_URL}/simulations",
        headers=_service_headers(),
        params={"id": f"eq.{simulation_id}", "user_id": f"eq.{user_id}", "limit": 1},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def update_simulation_chat(simulation_id: str, chat_history: list[dict]) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/simulations",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"id": f"eq.{simulation_id}"},
        json={"chat_history": chat_history},
    )
    resp.raise_for_status()


def update_simulation_feedback(simulation_id: str, feedback_report_json: str) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/simulations",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"id": f"eq.{simulation_id}"},
        json={"feedback_report": feedback_report_json},
    )
    resp.raise_for_status()


# --- Phase 5: RBAC, account pause, admin portal, error logging ---


def _count(table: str, params: dict | None = None) -> int:
    resp = httpx.head(
        f"{_REST_URL}/{table}", headers=_service_headers({"Prefer": "count=exact"}), params=params or {}
    )
    resp.raise_for_status()
    return int(resp.headers.get("content-range", "*/0").split("/")[-1])


def get_profile(user_id: str) -> dict | None:
    resp = httpx.get(
        f"{_REST_URL}/profiles",
        headers=_service_headers(),
        params={"id": f"eq.{user_id}", "select": "id,name,email,role,is_paused", "limit": 1},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def set_user_paused(user_id: str, paused: bool) -> None:
    resp = httpx.patch(
        f"{_REST_URL}/profiles",
        headers=_service_headers({"Content-Type": "application/json"}),
        params={"id": f"eq.{user_id}"},
        json={"is_paused": paused},
    )
    resp.raise_for_status()


def list_users(search: str | None = None) -> list[dict]:
    params = {
        "select": "id,name,email,role,created_at,is_paused",
        "order": "created_at.desc",
        "limit": 200,
    }
    if search:
        params["or"] = f"(name.ilike.*{search}*,email.ilike.*{search}*)"
    resp = httpx.get(f"{_REST_URL}/profiles", headers=_service_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def count_users() -> int:
    return _count("profiles")


def count_applications() -> int:
    return _count("applications")


def count_completed_simulations() -> int:
    return _count("simulations", {"feedback_report": "not.is.null"})


def log_error(source: str, message: str) -> None:
    # Best-effort: a logging failure must never mask the original error it's
    # trying to record, so this swallows its own exceptions.
    try:
        httpx.post(
            f"{_REST_URL}/error_logs",
            headers=_service_headers({"Content-Type": "application/json"}),
            json={"source": source, "message": message[:2000]},
            timeout=5,
        )
    except httpx.HTTPError:
        pass


def list_errors(limit: int = 100) -> list[dict]:
    resp = httpx.get(
        f"{_REST_URL}/error_logs",
        headers=_service_headers(),
        params={"order": "created_at.desc", "limit": limit},
    )
    resp.raise_for_status()
    return resp.json()


def count_recent_errors(source: str, hours: int = 24) -> int:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    return _count("error_logs", {"source": f"eq.{source}", "created_at": f"gte.{since}"})
