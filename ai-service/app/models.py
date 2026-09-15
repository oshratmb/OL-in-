from typing import Literal

from pydantic import BaseModel


class ParseResumeRequest(BaseModel):
    storage_path: str


class WorkExperienceEntry(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = []


class EducationEntry(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    year: str = ""


class ProjectEntry(BaseModel):
    name: str = ""
    description: str = ""


class PersonalInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""


class ParsedProfile(BaseModel):
    personal_info: PersonalInfo
    professional_summary: str = ""
    work_experience: list[WorkExperienceEntry] = []
    education: list[EducationEntry] = []
    skills: list[str] = []
    projects: list[ProjectEntry] = []
    languages: list[str] = []


class ParseResumeResponse(BaseModel):
    parsed_data: ParsedProfile


# --- Phase 2: job analysis, tailoring, gatekeeper, translation ---


class GapQuestion(BaseModel):
    id: str
    question: str


class RequirementMatch(BaseModel):
    requirement: str
    present: bool
    note: str = ""


class JobAnalyzeRequest(BaseModel):
    description_text: str


class JobAnalyzeResponse(BaseModel):
    detected_title: str = ""
    detected_company_name: str = ""
    requirements: list[RequirementMatch] = []
    match_percentage: int = 0
    gap_questions: list[GapQuestion] = []


class QnaAnswer(BaseModel):
    question_id: str
    question: str
    answer: str = ""  # empty string means the user skipped this question


class JobInput(BaseModel):
    title: str
    company_name: str
    description_text: str


ToneOption = Literal["professional", "enthusiastic", "concise"]
LanguageOption = Literal["he", "en"]


class GenerateDocumentsRequest(BaseModel):
    job: JobInput
    qna_answers: list[QnaAnswer] = []
    tone: ToneOption = "professional"
    # Set on a tone-switch re-generation (document-preview.html) so we update
    # the existing application in place instead of creating a duplicate one.
    application_id: str | None = None


GatekeeperStatus = Literal["PASS", "TRUST_WARNING"]


class GenerateDocumentsResponse(BaseModel):
    application_id: str
    resume: ParsedProfile
    tailored_resume_url: str
    cover_letter_text: str
    gatekeeper_status: GatekeeperStatus
    violations: list[str] = []


class TranslateRequest(BaseModel):
    application_id: str
    resume: ParsedProfile
    cover_letter_text: str
    target_language: LanguageOption


class TranslateResponse(BaseModel):
    resume: ParsedProfile
    tailored_resume_url: str
    cover_letter_text: str


class TailoringResult(BaseModel):
    resume: ParsedProfile
    cover_letter: str


class GatekeeperResult(BaseModel):
    status: Literal["PASS", "FAIL"]
    violations: list[str] = []


# --- Phase 3: Kanban, Gmail integration, Email Parser ---


class CandidateApplication(BaseModel):
    application_id: str
    job_title: str
    company_name: str
    status: str
    applied_at: str


class MatchingApplication(BaseModel):
    application_id: str
    confidence_score: float


RecommendedAction = Literal["AUTO_LINK", "MANUAL_LINK_PROMPT", "NO_MATCH"]


class EmailParserResult(BaseModel):
    company_name: str = ""
    classified_status: str = ""
    matching_applications: list[MatchingApplication] = []
    recommended_action: RecommendedAction = "NO_MATCH"


class ManualEmailRequest(BaseModel):
    subject: str
    sender: str
    body_content: str


class EmailLinkRequest(BaseModel):
    application_id: str


class GmailConnectStartResponse(BaseModel):
    authorize_url: str


class GmailStatusResponse(BaseModel):
    connected: bool
    google_email: str | None = None
    last_synced_at: str | None = None
    needs_reconnect: bool = False


class UnlinkedEmailCandidate(BaseModel):
    application_id: str
    job_title: str
    company_name: str


class UnlinkedEmailItem(BaseModel):
    id: str
    subject: str
    sender: str
    received_at: str
    candidates: list[UnlinkedEmailCandidate] = []


# --- Phase 4: Interview Simulator ---


class StartSimulationRequest(BaseModel):
    application_id: str


class StartSimulationResponse(BaseModel):
    simulation_id: str
    persona_role_title: str
    question: str


class SubmitAnswerRequest(BaseModel):
    answer: str


class SubmitAnswerResponse(BaseModel):
    done: bool
    question: str | None = None
    transcript: str | None = None


class ChatMessage(BaseModel):
    role: Literal["assistant", "user"]
    content: str


class PerQuestionFeedback(BaseModel):
    question: str
    answer: str
    feedback: str
    suggested_answer: str


class FeedbackReport(BaseModel):
    overall_score: int
    summary: str
    strengths: list[str] = []
    improvements: list[str] = []
    per_question: list[PerQuestionFeedback] = []


class SimulationDetail(BaseModel):
    id: str
    application_id: str
    persona_role_title: str
    chat_history: list[ChatMessage]
    feedback_report: FeedbackReport | None = None


# --- Phase 5: Admin portal ---


class AdminStats(BaseModel):
    total_users: int
    total_document_generations: int
    total_completed_simulations: int
    gmail_sync_errors_24h: int


class AdminUser(BaseModel):
    id: str
    name: str | None = None
    email: str | None = None
    role: str
    created_at: str
    is_paused: bool


class PauseUserRequest(BaseModel):
    paused: bool


class ErrorLogEntry(BaseModel):
    id: str
    source: str
    message: str
    created_at: str
