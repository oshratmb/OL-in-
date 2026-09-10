"""Screen 9 — Gmail connect/disconnect, manual email paste, account pause.
Mirrors settings.html + web/src/settings.js."""

import streamlit as st

import api
import nav
import ui


def _gmail_card():
    with st.container(border=True):
        st.markdown("#### חיבור Gmail")

        flag = st.session_state.pop("settings_gmail_flag", None)
        if flag == "connected":
            st.success("Gmail חובר בהצלחה")
        elif flag == "error":
            st.error("חיבור ה-Gmail נכשל, נסו שוב")

        ok, status, _ = api.ai_fetch("GET", "/gmail/status")
        if not ok:
            st.error(status.get("detail", "לא ניתן לקרוא את סטטוס ה-Gmail"))
            return

        if status.get("needs_reconnect"):
            st.warning("נדרש חיבור מחדש של חשבון ה-Gmail")

        if status.get("connected"):
            st.write(f"מחובר כ-{status.get('google_email', '')}")
            if status.get("last_synced_at"):
                st.caption(
                    "סנכרון אחרון: "
                    + status["last_synced_at"][:19].replace("T", " ")
                )
            if st.button("נתק את Gmail"):
                api.ai_fetch("POST", "/gmail/disconnect")
                st.rerun()
        else:
            st.write("Gmail אינו מחובר")
            if st.button("חבר את Gmail"):
                ok2, data, _ = api.ai_fetch("POST", "/gmail/connect/start")
                if ok2 and data.get("authorize_url"):
                    st.session_state.gmail_authorize_url = data["authorize_url"]
                else:
                    st.error(data.get("detail", "לא ניתן להתחיל חיבור Gmail"))
            if st.session_state.get("gmail_authorize_url"):
                st.link_button(
                    "המשך לאישור בחלון Google", st.session_state.gmail_authorize_url
                )


def _manual_email_card():
    with st.container(border=True):
        st.markdown("#### הדבקת אימייל ידנית")
        st.caption("למי שאין חיבור Gmail — הדביקו אימייל שקיבלתם וה-AI יסווג וישייך אותו.")
        sender = st.text_input("כתובת השולח", key="m_sender")
        subject = st.text_input("נושא", key="m_subject")
        body = st.text_area("תוכן המייל", key="m_body", height=170)
        if st.button("נתח ושייך אימייל"):
            if not sender.strip() or not body.strip():
                st.error("יש למלא לפחות שולח ותוכן מייל")
                return
            with st.spinner("מנתח..."):
                ok, data, _ = api.ai_fetch(
                    "POST",
                    "/emails/manual",
                    {
                        "sender": sender.strip(),
                        "subject": subject.strip(),
                        "body_content": body.strip(),
                    },
                )
            if ok:
                st.success("האימייל נותח בהצלחה")
            else:
                st.error(data.get("detail", "הניתוח נכשל"))


def _pause_card():
    with st.container(border=True):
        st.markdown("#### מצב חשבון")
        ok, rows, _ = api.supabase_fetch(
            "GET",
            f"/rest/v1/profiles?id=eq.{api.current_user_id()}&select=is_paused&limit=1",
        )
        is_paused = bool(ok and rows and rows[0].get("is_paused"))
        st.write(
            "החשבון מושהה. כלי ה-AI וסנכרון ה-Gmail מושבתים עד להפעלה מחדש."
            if is_paused
            else "החשבון פעיל."
        )
        label = "הפעל חשבון מחדש" if is_paused else "השהה חשבון"
        if st.button(label, type="primary" if is_paused else "secondary"):
            api.ai_fetch("POST", "/account/resume" if is_paused else "/account/pause")
            st.rerun()


def render():
    ui.header("הגדרות")
    _gmail_card()
    _manual_email_card()
    _pause_card()
    st.divider()
    if st.button("חזרה ללוח"):
        for key in ("m_sender", "m_subject", "m_body", "gmail_authorize_url"):
            st.session_state.pop(key, None)
        nav.go(nav.DASHBOARD)
