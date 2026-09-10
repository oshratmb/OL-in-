"""Screen 10 — admin portal. KPI tiles + searchable user directory for
support/super_admin; pause controls + error-monitoring grid for super_admin only.
Every gate is enforced server-side; the UI just reacts to 403s.
Mirrors admin.html + web/src/admin.js."""

from urllib.parse import quote

import streamlit as st

import api
import nav
import ui


def render():
    ui.header("פורטל ניהול")

    ok, stats, _ = api.ai_fetch("GET", "/admin/stats")
    if not ok:
        st.error("אין לך הרשאה לצפות בעמוד זה")
        if st.button("חזרה ללוח"):
            nav.go(nav.DASHBOARD)
        return

    tiles = st.columns(4)
    tiles[0].metric("סך משתמשים", stats.get("total_users", 0))
    tiles[1].metric("התאמות קו\"ח שבוצעו", stats.get("total_document_generations", 0))
    tiles[2].metric("סימולציות שהושלמו", stats.get("total_completed_simulations", 0))
    tiles[3].metric("שגיאות Gmail (24ש')", stats.get("gmail_sync_errors_24h", 0))

    # /admin/errors is super_admin-only — its success doubles as the role probe.
    errors_ok, errors, _ = api.ai_fetch("GET", "/admin/errors")
    is_super = errors_ok

    st.divider()
    st.markdown("#### משתמשים")
    search = st.text_input("חיפוש לפי שם או אימייל")
    query = f"?search={quote(search.strip())}" if search.strip() else ""
    users_ok, users, _ = api.ai_fetch("GET", f"/admin/users{query}")
    users = users if users_ok and isinstance(users, list) else []

    widths = [2, 3, 1.4, 1.4, 1, 1] if is_super else [2, 3, 1.4, 1.4, 1]
    headers = ["שם", "אימייל", "תפקיד", "נוצר", "סטטוס"] + (["פעולה"] if is_super else [])
    head_cols = st.columns(widths)
    for col, label in zip(head_cols, headers):
        col.markdown(f"**{label}**")

    for user in users:
        row = st.columns(widths)
        row[0].write(user.get("name") or "-")
        row[1].write(user.get("email") or "-")
        row[2].write(user.get("role", ""))
        row[3].write((user.get("created_at") or "")[:10])
        row[4].write("מושהה" if user.get("is_paused") else "פעיל")
        if is_super:
            btn_label = "הפעל" if user.get("is_paused") else "השהה"
            if row[5].button(btn_label, key=f"pause_{user['id']}"):
                api.ai_fetch(
                    "PATCH",
                    f"/admin/users/{user['id']}/pause",
                    {"paused": not user.get("is_paused")},
                )
                st.rerun()

    if is_super:
        st.divider()
        st.markdown("#### יומן שגיאות מערכת")
        err_head = st.columns([2, 4, 2])
        for col, label in zip(err_head, ["מקור", "הודעה", "זמן"]):
            col.markdown(f"**{label}**")
        for entry in errors or []:
            row = st.columns([2, 4, 2])
            row[0].write(entry.get("source", ""))
            row[1].write(entry.get("message", ""))
            row[2].write((entry.get("created_at") or "").replace("T", " ")[:19])
        if not errors:
            st.caption("אין שגיאות רשומות")

    st.divider()
    if st.button("חזרה ללוח"):
        nav.go(nav.DASHBOARD)
