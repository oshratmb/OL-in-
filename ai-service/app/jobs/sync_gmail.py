"""Cron entrypoint (Railway Cron Job: `python -m app.jobs.sync_gmail`, twice
daily) — not an HTTP route. Also reused by POST /gmail/sync-now for a single
user's on-demand sync.
"""

import sys
import time
from datetime import datetime, timezone

import httpx

from .. import google_oauth, supabase_client
from ..email_processing import process_incoming_email
from ..gmail_client import get_message, list_new_message_ids

_FIRST_SYNC_LOOKBACK_SECONDS = 86400  # fallback only; connect always seeds last_synced_at


def sync_one_connection(connection: dict) -> None:
    user_id = connection["user_id"]
    last_synced_at = connection.get("last_synced_at")
    after_ts = (
        _to_unix_ts(last_synced_at)
        if last_synced_at
        else int(time.time()) - _FIRST_SYNC_LOOKBACK_SECONDS
    )

    try:
        access_token = google_oauth.get_gmail_access_token(connection["refresh_token"])
    except httpx.HTTPStatusError:
        # Refresh token rejected — almost certainly revoked/expired, not a
        # transient error. Flag for reconnect rather than retrying forever.
        supabase_client.mark_gmail_needs_reconnect(user_id)
        supabase_client.log_error("sync_gmail", f"user {user_id}: refresh failed, marked needs_reconnect")
        print(f"[sync_gmail] user {user_id}: refresh failed, marked needs_reconnect", file=sys.stderr)
        return

    for message_id in list_new_message_ids(access_token, after_ts):
        try:
            message = get_message(access_token, message_id)
            process_incoming_email(
                user_id=user_id,
                subject=message["subject"],
                sender=message["sender"],
                body_text=message["body_text"],
                gmail_message_id=message_id,
            )
        except Exception as exc:  # one bad message shouldn't stop the rest
            supabase_client.log_error("sync_gmail", f"user {user_id}: message {message_id} failed: {exc}")
            print(f"[sync_gmail] user {user_id}: message {message_id} failed: {exc}", file=sys.stderr)

    supabase_client.update_gmail_sync_time(user_id, datetime.now(timezone.utc).isoformat())


def sync_user_by_id(user_id: str) -> None:
    """Used by POST /gmail/sync-now — syncs just one already-connected user."""
    connection = supabase_client.get_gmail_connection(user_id)
    if connection is None:
        raise ValueError("Gmail is not connected for this user")
    sync_one_connection(connection)


def run_all() -> None:
    for connection in supabase_client.list_all_gmail_connections():
        try:
            sync_one_connection(connection)
        except Exception as exc:  # one user's failure must not abort the batch
            supabase_client.log_error("sync_gmail", f"user {connection.get('user_id')}: sync failed: {exc}")
            print(f"[sync_gmail] user {connection.get('user_id')}: sync failed: {exc}", file=sys.stderr)


def _to_unix_ts(iso_string: str) -> int:
    return int(datetime.fromisoformat(iso_string.replace("Z", "+00:00")).timestamp())


if __name__ == "__main__":
    run_all()
