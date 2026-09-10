"""Screen 11 — Super Admin TOTP 2FA: first-login enrollment (QR + secret) or the
code-only challenge on subsequent logins.
Mirrors mfa.html + web/src/mfa.js."""

import streamlit as st

import api
import nav
import ui


def _finish(session_data):
    api.set_token(session_data["access_token"])
    for key in list(st.session_state.keys()):
        if key.startswith("mfa_"):
            st.session_state.pop(key)
    nav.go(nav.DASHBOARD if api.has_completed_onboarding() else nav.ONBOARDING)


def render():
    p = nav.params()
    mode = p.get("mode") or st.session_state.get("mfa_mode")
    temp = p.get("temp_access_token") or st.session_state.get("mfa_temp")
    factor_id = p.get("factor_id") or st.session_state.get("mfa_factor")

    if not temp:
        nav.go(nav.ONBOARDING)

    st.session_state.mfa_mode = mode
    st.session_state.mfa_temp = temp
    st.session_state.mfa_factor = factor_id
    api.set_token(temp)

    if mode == "enroll":
        ui.header(
            "הפעילו אימות דו-שלבי",
            "כמנהל/ת על נדרש אימות דו-שלבי. סרקו את הקוד באפליקציית Authenticator "
            "(כגון Google Authenticator).",
        )
        if not st.session_state.get("mfa_enroll_data"):
            ok, data, _ = api.ai_fetch("POST", "/auth/mfa/enroll")
            if not ok:
                st.error(data.get("detail", "שגיאה בהפעלת האימות הדו-שלבי"))
                return
            st.session_state.mfa_enroll_data = data
            st.session_state.mfa_factor = data["factor_id"]
            factor_id = data["factor_id"]

        enroll = st.session_state.mfa_enroll_data
        if enroll.get("qr_code"):
            st.markdown(
                f'<img src="{enroll["qr_code"]}" width="200" alt="QR" />',
                unsafe_allow_html=True,
            )
        st.caption("או הזינו ידנית את המפתח:")
        st.code(enroll.get("secret", ""))
    else:
        ui.header("אימות דו-שלבי", "הזינו את הקוד מאפליקציית ה-Authenticator שלכם.")

    code = st.text_input("קוד בן 6 ספרות", max_chars=6)
    if st.button("אישור", type="primary"):
        if not code.strip() or not factor_id:
            st.error("יש להזין קוד בן 6 ספרות")
            return

        if mode == "enroll":
            ok, data, _ = api.ai_fetch(
                "POST",
                "/auth/mfa/verify-enroll",
                {"factor_id": factor_id, "code": code.strip()},
            )
        else:
            ok_c, challenge, _ = api.ai_fetch(
                "POST", "/auth/mfa/challenge", {"factor_id": factor_id}
            )
            if not ok_c:
                st.error(challenge.get("detail", "שגיאה ביצירת אתגר האימות"))
                return
            ok, data, _ = api.ai_fetch(
                "POST",
                "/auth/mfa/verify",
                {
                    "factor_id": factor_id,
                    "challenge_id": challenge["challenge_id"],
                    "code": code.strip(),
                },
            )

        if ok:
            _finish(data)
        else:
            st.error(data.get("detail", "הקוד שגוי, נסו שוב"))
