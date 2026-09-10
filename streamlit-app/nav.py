"""In-app router. One screen at a time, tracked in ``st.session_state.screen``,
navigated with :func:`go`. Params for a screen ride in ``screen_params``."""

import streamlit as st

ONBOARDING = "onboarding"       # auth + resume upload  (index.html)
PROFILE = "profile"             # verify parsed profile (profile.html)
DASHBOARD = "dashboard"         # 6-column Kanban       (dashboard.html)
JOB_INTAKE = "job_intake"       # paste JD + gap analysis (job-intake.html)
QNA = "qna_wizard"              # gap-filling wizard    (qna-wizard.html)
DOC_PREVIEW = "document_preview"  # tailored docs        (document-preview.html)
INTERVIEW = "interview_simulator"  # mock interview     (interview-simulator.html)
FEEDBACK = "simulation_feedback"   # rubric report      (simulation-feedback.html)
SETTINGS = "settings"          # Gmail / manual email / pause (settings.html)
ADMIN = "admin"                # KPI + users + errors  (admin.html)
MFA = "mfa"                    # TOTP enroll / challenge (mfa.html)

GATED = {PROFILE, DASHBOARD, JOB_INTAKE, QNA, DOC_PREVIEW, INTERVIEW, FEEDBACK, SETTINGS, ADMIN}


def go(screen, **params):
    """Switch screens and rerun. Entering the interview always starts fresh, so
    any leftover ``sim_*`` state from a previous run is dropped here."""
    if screen == INTERVIEW:
        for key in list(st.session_state.keys()):
            if key.startswith("sim_") or key == "interview_app_id":
                st.session_state.pop(key)
    st.session_state.screen = screen
    st.session_state.screen_params = params
    st.rerun()


def params() -> dict:
    return st.session_state.get("screen_params", {})
