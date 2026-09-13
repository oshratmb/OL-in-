"""AI Job Search Platform — Streamlit UI.

A full re-implementation of the ``/web`` frontend (Phases 1–5) as a single
Streamlit app. It talks to the same two backends: the FastAPI ``ai-service``
(auth proxy + AI endpoints) and Supabase REST/Storage (RLS-scoped).

Run:  ``streamlit run streamlit-app/app.py``
Config: ``AI_SERVICE_URL`` / ``SUPABASE_URL`` / ``SUPABASE_ANON_KEY``
        (env, ``.env`` next to where you run it, or ``.streamlit/secrets.toml``).
"""

import streamlit as st

import api
import nav
import ui
import screens_admin
import screens_dashboard
import screens_document_preview
import screens_feedback
import screens_interview
import screens_job_intake
import screens_mfa
import screens_onboarding
import screens_profile
import screens_qna
import screens_settings

ui.setup_page()

RENDERERS = {
    nav.ONBOARDING: screens_onboarding.render,
    nav.PROFILE: screens_profile.render,
    nav.DASHBOARD: screens_dashboard.render,
    nav.JOB_INTAKE: screens_job_intake.render,
    nav.QNA: screens_qna.render,
    nav.DOC_PREVIEW: screens_document_preview.render,
    nav.INTERVIEW: screens_interview.render,
    nav.FEEDBACK: screens_feedback.render,
    nav.SETTINGS: screens_settings.render,
    nav.ADMIN: screens_admin.render,
    nav.MFA: screens_mfa.render,
}


def _handle_oauth_return():
    """ai-service redirects OAuth round-trips back to ``FRONTEND_URL`` with query
    params. Capture the ones we can act on, then clear the URL."""
    qp = st.query_params
    touched = False

    if "auth_error" in qp:
        st.session_state.onb_auth_error = True
        touched = True

    if "google_login_code" in qp:
        if api.redeem_google_login(qp["google_login_code"]):
            st.session_state.screen = (
                nav.DASHBOARD if api.has_completed_onboarding() else nav.ONBOARDING
            )
            st.session_state.screen_params = {}
            if st.session_state.screen == nav.ONBOARDING:
                st.session_state.onb_stage = "upload"
        else:
            st.session_state.onb_auth_error = True
        touched = True

    if qp.get("gmail") == "connected" or "gmail_error" in qp:
        st.session_state.settings_gmail_flag = (
            "connected" if qp.get("gmail") == "connected" else "error"
        )
        st.session_state.screen = nav.SETTINGS
        st.session_state.screen_params = {}
        touched = True

    if touched:
        st.query_params.clear()


def _bootstrap():
    """First load of this browser session: try a silent refresh (the requests
    session may hold ``sb_refresh_token`` from a prior tab), then route like
    onboarding.js does."""
    st.session_state.screen = nav.ONBOARDING
    st.session_state.screen_params = {}
    if api.restore_session():
        if api.has_completed_onboarding():
            st.session_state.screen = nav.DASHBOARD
        else:
            st.session_state.onb_stage = "upload"


_handle_oauth_return()

if "screen" not in st.session_state:
    _bootstrap()

screen = st.session_state.screen

if screen in nav.GATED and not api.get_token() and not api.restore_session():
    screen = st.session_state.screen = nav.ONBOARDING

RENDERERS.get(screen, screens_onboarding.render)()
