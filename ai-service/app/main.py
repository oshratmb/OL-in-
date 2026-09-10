from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, resume_extraction, supabase_client
from .auth_dependency import get_current_user
from .crews.resume_parser_crew import run_resume_parser
from .models import ParseResumeRequest, ParseResumeResponse
from .rbac import require_active_user
from .routers.account import router as account_router
from .routers.admin import router as admin_router
from .routers.auth import router as auth_router
from .routers.documents import router as documents_router
from .routers.emails import router as emails_router
from .routers.gmail import router as gmail_router
from .routers.simulations import router as simulations_router

app = FastAPI(title="AI Job Search Platform - AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(gmail_router)
app.include_router(emails_router)
app.include_router(simulations_router)
app.include_router(admin_router)
app.include_router(account_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse-resume", response_model=ParseResumeResponse)
async def parse_resume(
    body: ParseResumeRequest,
    user: dict = Depends(get_current_user),
    _active: dict = Depends(require_active_user),
):
    user_id = user["sub"]
    if not body.storage_path.startswith(f"{user_id}/"):
        raise HTTPException(403, "storage_path does not belong to the authenticated user")

    try:
        file_bytes = supabase_client.download_resume(body.storage_path)
    except FileNotFoundError as exc:
        raise HTTPException(404, "Resume file not found in storage") from exc

    try:
        text = resume_extraction.extract_text(file_bytes, body.storage_path)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    if not text:
        raise HTTPException(422, "Could not extract any text from the uploaded file")

    try:
        parsed = run_resume_parser(text)
    except ValueError as exc:
        supabase_client.log_error("parse_resume", str(exc))
        raise HTTPException(502, "AI parsing returned an unreadable result, please retry") from exc
    return {"parsed_data": parsed}
