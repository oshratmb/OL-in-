"""Thin wrapper over the Gmail API — just enough to list new messages and
read their subject/sender/plain-text body."""

import base64
import re

import httpx

_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def list_new_message_ids(access_token: str, after_ts: int) -> list[str]:
    resp = httpx.get(
        f"{_API_BASE}/messages",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"q": f"after:{after_ts}", "maxResults": 50},
    )
    resp.raise_for_status()
    return [m["id"] for m in resp.json().get("messages", [])]


def get_message(access_token: str, message_id: str) -> dict:
    """Returns {subject, sender, body_text}."""
    resp = httpx.get(
        f"{_API_BASE}/messages/{message_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"format": "full"},
    )
    resp.raise_for_status()
    payload = resp.json().get("payload", {})

    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    return {
        "subject": headers.get("subject", ""),
        "sender": headers.get("from", ""),
        "body_text": _extract_body_text(payload),
    }


def _extract_body_text(payload: dict) -> str:
    plain = _find_part(payload, "text/plain")
    if plain:
        return _decode_base64url(plain)
    html = _find_part(payload, "text/html")
    if html:
        return _strip_html(_decode_base64url(html))
    return ""


def _find_part(payload: dict, mime_type: str) -> str | None:
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return payload["body"]["data"]
    for part in payload.get("parts", []):
        found = _find_part(part, mime_type)
        if found:
            return found
    return None


def _decode_base64url(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()
