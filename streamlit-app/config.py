"""Runtime configuration.

Values are read from (in order): OS environment, a local ``.env`` file, or
Streamlit ``secrets.toml``. The Streamlit UI talks to exactly two backends,
the same two the ``/web`` frontend uses:

* ``AI_SERVICE_URL``  – the FastAPI ``ai-service`` (auth proxy + AI endpoints)
* ``SUPABASE_URL`` / ``SUPABASE_ANON_KEY`` – Supabase REST + Storage (RLS-scoped)
"""

import os

from dotenv import load_dotenv

load_dotenv()

try:  # pragma: no cover - depends on how the app is launched
    import streamlit as st

    def _secret(key):
        try:
            return st.secrets.get(key)
        except Exception:
            return None

except Exception:  # streamlit not importable (e.g. plain unit test)

    def _secret(key):
        return None


def _val(key, default=""):
    return os.environ.get(key) or _secret(key) or default


AI_SERVICE_URL = _val("AI_SERVICE_URL", "http://localhost:8000").rstrip("/")
SUPABASE_URL = _val("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = _val("SUPABASE_ANON_KEY", "")
