"""Screen 3 — the Kanban board (6 columns), unlinked-email banner, Gmail sync.
Mirrors dashboard.html + web/src/dashboard.js."""

import streamlit as st

import api
import nav
import ui

STATUS_LABELS = {
    "applied": "הוגש",
    "phone_screen": "ראיון טלפוני",
    "homework": "משימת בית",
    "tech_interview": "ראיון טכנולוגי",
    "offer": "הצעת חוזה",
    "rejected": "נדחה",
    "on_hold": "מוקפא",
}

COLUMNS = [
    ("הוגש", ["applied"]),
    ("ראיון טלפוני", ["phone_screen"]),
    ("משימת בית", ["homework"]),
    ("ראיון טכנולוגי", ["tech_interview"]),
    ("הצעת חוזה", ["offer"]),
    ("דחייה / הוקפא", ["rejected", "on_hold"]),
]


def _initials(text):
    return (text or "?").strip()[:2].upper()


def _load_applications():
    ok, rows, _ = api.supabase_fetch(
        "GET",
        "/rest/v1/applications?select=id,status,applied_at,jobs(title,company_name)"
        "&order=applied_at.desc",
    )
    return rows if ok and isinstance(rows, list) else []


def _top_bar():
    cols = st.columns([2, 1, 1, 1])
    if cols[0].button("➕ הוספת משרה חדשה", type="primary"):
        nav.go(nav.JOB_INTAKE)
    if cols[1].button("⚙️ הגדרות"):
        nav.go(nav.SETTINGS)
    if cols[2].button("🛡️ ניהול"):
        nav.go(nav.ADMIN)
    if cols[3].button("🚪 יציאה"):
        api.log_out()
        for key in list(st.session_state.keys()):
            if key != "http_session":
                st.session_state.pop(key, None)
        nav.go(nav.ONBOARDING)


def _sync_and_unlinked():
    if st.button("🔄 סנכרן אימיילים עכשיו"):
        with st.spinner("מסנכרן..."):
            ok, data, _ = api.ai_fetch("POST", "/gmail/sync-now")
        if ok:
            st.success("הסנכרון הושלם")
            st.rerun()
        else:
            st.error(data.get("detail", "הסנכרון נכשל"))

    ok, emails, _ = api.ai_fetch("GET", "/emails/unlinked")
    if not (ok and emails):
        return

    with st.container(border=True):
        st.warning("התקבלו אימיילים שטרם שויכו למשרה — בחרו את המשרה המתאימה:")
        for email in emails:
            st.markdown(f"**{email['sender']}**: {email['subject']}")
            candidates = email.get("candidates", [])
            btn_cols = st.columns(max(len(candidates), 1))
            for cand, col in zip(candidates, btn_cols):
                label = f"{cand['job_title']} — {cand['company_name']}"
                if col.button(label, key=f"link_{email['id']}_{cand['application_id']}"):
                    api.ai_fetch(
                        "POST",
                        f"/emails/{email['id']}/link",
                        {"application_id": cand["application_id"]},
                    )
                    st.rerun()


def _card(app):
    job = app.get("jobs") or {}
    with st.container(border=True):
        st.markdown(f"**{_initials(job.get('company_name'))}** · **{job.get('title', '')}**")
        st.caption(f"{job.get('company_name', '')} · {(app.get('applied_at') or '')[:10]}")

        options = list(STATUS_LABELS.keys())
        current = app["status"] if app["status"] in options else options[0]
        prev_key = f"stprev_{app['id']}"
        new_status = st.selectbox(
            "סטטוס",
            options,
            index=options.index(current),
            format_func=lambda v: STATUS_LABELS[v],
            key=f"status_{app['id']}",
            label_visibility="collapsed",
        )
        if new_status != current and st.session_state.get(prev_key) != new_status:
            st.session_state[prev_key] = new_status
            ok, _, _ = api.supabase_fetch(
                "PATCH",
                f"/rest/v1/applications?id=eq.{app['id']}",
                json_body={"status": new_status},
            )
            if ok:
                st.rerun()
            else:
                st.error("עדכון הסטטוס נכשל")

        if app["status"] in ("phone_screen", "tech_interview"):
            if st.button("התחל הכנה לראיון", key=f"prep_{app['id']}"):
                nav.go(nav.INTERVIEW, application_id=app["id"])


def render():
    ui.header("לוח המעקב שלי", "כל המשרות שלכם, לפי שלב בתהליך")
    _top_bar()
    st.divider()
    _sync_and_unlinked()

    applications = _load_applications()
    board_cols = st.columns(len(COLUMNS))
    for (label, statuses), col in zip(COLUMNS, board_cols):
        with col:
            st.markdown(f"##### {label}")
            items = [a for a in applications if a.get("status") in statuses]
            if not items:
                st.caption("אין משרות")
            for app in items:
                _card(app)
