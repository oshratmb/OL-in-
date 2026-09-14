"""Screen 1 — sign up / sign in, then resume upload + AI parse.
Mirrors index.html + web/src/onboarding.js + web/src/auth.js."""

import re
import time

import streamlit as st

import api
import nav
import ui


def _validate_password(pw: str):
    problems = []
    if len(pw) < 8:
        problems.append("לפחות 8 תווים")
    if not re.search(r"[a-z]", pw):
        problems.append("אות קטנה")
    if not re.search(r"[A-Z]", pw):
        problems.append("אות גדולה")
    if not re.search(r"[0-9]", pw):
        problems.append("ספרה")
    if not re.search(r"[^A-Za-z0-9]", pw):
        problems.append("תו מיוחד")
    return problems


# --------------------------------------------------------------------------- #
# stage: auth
# --------------------------------------------------------------------------- #
def _auth_stage():
    ui.landing_hero()
    ui.how_it_works()

    st.markdown(
        """
        <div style="text-align:center;max-width:640px;margin:0 auto .5rem;">
          <div class="section-title">הצטרפו לפלטפורמה החכמה</div>
          <div class="section-sub">התחילו את מסע חיפוש העבודה המדויק והמקצועי ביותר שלכם</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.pop("onb_auth_error", None):
        st.error("ההתחברות באמצעות Google נכשלה, נסו שוב")

    _, card_col, _ = st.columns([1, 2, 1])
    with card_col, st.container(border=True):
        mode = st.segmented_control("איך תרצו להתחיל?", ["הרשמה", "התחברות"], default="הרשמה")
        signup = mode != "התחברות"

        with st.form("auth_form"):
            email = st.text_input("אימייל")
            password = st.text_input("סיסמה", type="password")
            name = st.text_input("שם מלא") if signup else ""
            if signup:
                st.caption("הסיסמה חייבת לכלול: לפחות 8 תווים, אות קטנה, אות גדולה, ספרה ותו מיוחד")
            submitted = st.form_submit_button(
                "יצירת חשבון חינם" if signup else "התחברות למערכת",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            try:
                if signup:
                    problems = _validate_password(password)
                    if problems:
                        st.error("הסיסמה חסרה: " + ", ".join(problems))
                        st.stop()
                    api.sign_up(email.strip(), password, name.strip())
                    st.session_state.onb_stage = "upload"
                    st.rerun()
                else:
                    result = api.log_in(email.strip(), password)
                    if result["status"] == "ok":
                        if api.has_completed_onboarding():
                            nav.go(nav.DASHBOARD)
                        st.session_state.onb_stage = "upload"
                        st.rerun()
                    else:
                        nav.go(
                            nav.MFA,
                            mode="enroll" if result["status"] == "mfa_enrollment_required" else "challenge",
                            temp_access_token=result["temp_access_token"],
                            factor_id=result.get("factor_id"),
                        )
            except api.ApiError as exc:
                st.error(str(exc))

        st.divider()
        st.link_button(
            "התחברות באמצעות Google", api.google_start_url(), use_container_width=True
        )
        st.caption(
            "בלחיצה על הרשמה הנכם מסכימים לתנאי השימוש ולמדיניות הפרטיות"
        )


# --------------------------------------------------------------------------- #
# stage: resume upload
# --------------------------------------------------------------------------- #
def _upload_stage():
    ui.header("העלאת קורות חיים", "קובץ PDF או Word (.docx). ה-AI יחלץ ממנו את הפרטים לאישורכם.")
    ui.progress(50)

    uploaded = st.file_uploader("גררו לכאן קובץ, או בחרו קובץ", type=["pdf", "docx"])

    if uploaded is not None and st.button("נתח את קורות החיים", type="primary"):
        try:
            with st.status("מעלה קובץ...", expanded=True) as status:
                storage_path = _upload_resume(uploaded)
                status.update(label="מנתח את קורות החיים...")
                parsed = _parse_resume(storage_path)
                status.update(label="הניתוח הושלם", state="complete")
            st.session_state.pending_profile = {
                "storage_path": storage_path,
                "parsed_data": parsed,
            }
            nav.go(nav.PROFILE)
        except api.ApiError as exc:
            st.error(str(exc))

    st.divider()
    if st.button("התנתקות"):
        api.log_out()
        for key in list(st.session_state.keys()):
            if key != "http_session":
                st.session_state.pop(key, None)
        st.rerun()


def _upload_resume(file) -> str:
    user_id = api.current_user_id()
    safe_name = re.sub(r"[^\w.\-]", "_", file.name)
    path = f"{user_id}/{int(time.time() * 1000)}_{safe_name}"
    ok, _, _ = api.supabase_fetch(
        "POST",
        f"/storage/v1/object/resumes/{path}",
        data=file.getvalue(),
        headers={
            "Content-Type": file.type or "application/octet-stream",
            "x-upsert": "true",
        },
    )
    if not ok:
        raise api.ApiError("העלאת הקובץ נכשלה")
    return path


def _parse_resume(storage_path: str):
    ok, data, _ = api.ai_fetch(
        "POST", "/parse-resume", {"storage_path": storage_path}
    )
    if not ok:
        raise api.ApiError(data.get("detail", "ניתוח קורות החיים נכשל"))
    return data["parsed_data"]


def render():
    authed = bool(api.get_token())
    stage = st.session_state.get("onb_stage") or ("upload" if authed else "auth")
    if stage == "upload" and authed:
        _upload_stage()
    else:
        _auth_stage()
