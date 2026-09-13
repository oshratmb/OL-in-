import base64
import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]
# Supabase's HS256 JWT Signing Key was imported as a Base64-encoded secret,
# so it actually signs tokens with the *decoded* bytes — not the literal
# SUPABASE_JWT_SECRET string. Verifying Supabase-issued access tokens (below)
# must use the same decoded bytes; oauth_state.py's own self-signed/verified
# state token is unrelated to Supabase and keeps using the raw string.
SUPABASE_JWT_SIGNING_KEY = base64.b64decode(SUPABASE_JWT_SECRET)
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8000")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"

# Optional: only needed for the Gmail integration (Phase 3). Left unset,
# /gmail/* endpoints fail clearly at the point of use rather than the whole
# service refusing to boot for people who haven't set up Gmail yet.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
