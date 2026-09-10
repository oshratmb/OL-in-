import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8000")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"

# Optional: only needed for the Gmail integration (Phase 3). Left unset,
# /gmail/* endpoints fail clearly at the point of use rather than the whole
# service refusing to boot for people who haven't set up Gmail yet.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
