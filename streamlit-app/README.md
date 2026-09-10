# Streamlit UI — AI Job Search Platform

A complete re-implementation of the `/web` frontend (PRD Phases 1–5) using
Streamlit. It renders every screen from the spec and calls the **same two
backends** the original UI uses:

| Backend | Used for |
| --- | --- |
| `ai-service` (FastAPI) — `AI_SERVICE_URL` | auth proxy (`/auth/*`), resume parse, job analysis, document generation + Gatekeeper, translation, Gmail, email parser, interview simulator, admin, account pause |
| Supabase REST + Storage — `SUPABASE_URL`, `SUPABASE_ANON_KEY` | resume file upload, `core_profiles`, the Kanban `applications`/`jobs` read + status writes, `profiles.is_paused` read (all RLS-scoped) |

No changes to `ai-service`, `supabase`, or `/web` are required — this app is
purely an alternative front end.

## Screens

| Module | Spec screen | Original file |
| --- | --- | --- |
| `screens_onboarding.py` | sign up / sign in / Google + resume upload & AI parse | `index.html` |
| `screens_profile.py` | verify & edit parsed profile → save `core_profiles` | `profile.html` |
| `screens_dashboard.py` | 6-column Kanban, status dropdowns, unlinked-email banner, Gmail sync | `dashboard.html` |
| `screens_job_intake.py` | paste JD → gap analysis (match %, requirement list) | `job-intake.html` |
| `screens_qna.py` | skip-friendly gap-filling wizard → auto-generate docs | `qna-wizard.html` |
| `screens_document_preview.py` | tailored résumé + cover letter, trust warning, tone switch, He/En translate, `.docx` download | `document-preview.html` |
| `screens_interview.py` | mock interview chat (persona, 5 questions, timer) | `interview-simulator.html` |
| `screens_feedback.py` | rubric report — score gauge, strengths, improvements, per-question rewrites, redo | `simulation-feedback.html` |
| `screens_settings.py` | Gmail connect/disconnect, manual email paste, account pause | `settings.html` |
| `screens_admin.py` | KPI tiles, searchable user directory, pause controls, error grid (server-side RBAC) | `admin.html` |
| `screens_mfa.py` | Super Admin TOTP enrollment (QR + secret) / code challenge | `mfa.html` |

`app.py` is the router (`st.session_state.screen`); `api.py` is the HTTP layer;
`nav.py` / `ui.py` are shared helpers.

## Run

```bash
cd streamlit-app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in the 3 values
streamlit run app.py
```

Point `AI_SERVICE_URL` at a running `ai-service` (see the repo root README for
how to start it) and `SUPABASE_URL` / `SUPABASE_ANON_KEY` at the same Supabase
project. Then open http://localhost:8501.

## How auth works here

The browser can't hold the `sb_refresh_token` HttpOnly cookie for a separate
Streamlit origin, so instead **one `requests.Session` per Streamlit session**
captures and replays that cookie — the server-side equivalent of the browser's
`credentials: "include"`. The short-lived access token lives in
`st.session_state` (server side). A `401` triggers one silent `/auth/refresh`
and a single retry, exactly like `web/src/apiClient.js`.

## Known limitations vs. the HTML frontend

- **Google Sign-In**: the button is present, but the OAuth round-trip ends with
  a refresh cookie set on the *ai-service* domain and a redirect to
  `FRONTEND_URL`. That only completes if this Streamlit app is served from the
  same origin configured as `FRONTEND_URL` in `ai-service`. For local
  development, use email/password (fully functional, including the Super Admin
  MFA enrollment/challenge path).
- **Interview timer** updates on each message rather than ticking every second
  (Streamlit reruns on interaction only; no extra dependency added).
- **Cover-letter copy** is a select-and-copy text area rather than a one-click
  button.
- Résumé work-experience bullets are edited as a single ` | `-separated cell in
  the data grid (Streamlit `data_editor` cells are single-line).
