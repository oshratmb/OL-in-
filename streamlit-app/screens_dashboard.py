"""Screen 3 — the Kanban board (6 columns), unlinked-email banner, Gmail sync.
Mirrors dashboard.html + web/src/dashboard.js.

The board's look (colored columns, top-accent cards, drag handles) mirrors a
design generated in Google Stitch against this project's "Professional
Pipeline" design system — see streamlit-app/README.md. Dragging cards
between columns uses streamlit-sortables (SortableJS); since its items are
plain draggable strings, no widget can live *inside* a card, so a card's
exact status (e.g. picking "on_hold" vs "rejected" within the shared last
column) and the "start interview prep" action live in the compact list
below the board instead.
"""

import streamlit as st
from streamlit_sortables import sort_items

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

# label, css color key, the status a card dropped into this column gets,
# every status this column's header count should include
COLUMN_DEFS = [
    ("הוגש", "gray", "applied", ["applied"]),
    ("ראיון טלפוני", "blue", "phone_screen", ["phone_screen"]),
    ("משימת בית", "purple", "homework", ["homework"]),
    ("ראיון טכנולוגי", "indigo", "tech_interview", ["tech_interview"]),
    ("הצעת חוזה", "emerald", "offer", ["offer"]),
    ("דחייה / הוקפא", "rose", "rejected", ["rejected", "on_hold"]),
]

_COLORS = {
    "gray": {"bg": "#f4f5f7", "border": "#d8dae2", "accent": "#6c757d", "chip_bg": "#e9ebf0", "chip_fg": "#495057"},
    "blue": {"bg": "#eff6ff", "border": "#bfdbfe", "accent": "#0d6efd", "chip_bg": "#dbeafe", "chip_fg": "#0057cd"},
    "purple": {"bg": "#faf5ff", "border": "#e9d5ff", "accent": "#9333ea", "chip_bg": "#f3e8ff", "chip_fg": "#7e22ce"},
    "indigo": {"bg": "#eef2ff", "border": "#c7d2fe", "accent": "#4f46e5", "chip_bg": "#e0e7ff", "chip_fg": "#4338ca"},
    "emerald": {"bg": "#ecfdf5", "border": "#a7f3d0", "accent": "#10b981", "chip_bg": "#d1fae5", "chip_fg": "#065f46"},
    "rose": {"bg": "#fff1f2", "border": "#fecdd3", "accent": "#9ca3af", "chip_bg": "#f3f4f6", "chip_fg": "#6b7280"},
}


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
    if cols[0].button("➕ הוספת משרה חדשה", type="primary", use_container_width=True):
        nav.go(nav.JOB_INTAKE)
    if cols[1].button("⚙️ הגדרות", use_container_width=True):
        nav.go(nav.SETTINGS)
    if cols[2].button("🚪 יציאה", use_container_width=True):
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


def _item_text(app):
    job = app.get("jobs") or {}
    title = job.get("title") or "משרה"
    company = job.get("company_name") or ""
    date = (app.get("applied_at") or "")[:10]
    prep_hint = " 🎯" if app["status"] in ("phone_screen", "tech_interview") else ""
    return f"{_initials(company)} · {title}{prep_hint}\n{company}\n{date}"


def _board_custom_style():
    rules = [
        """
        .sortable-component { display: flex; flex-direction: row-reverse; gap: 14px;
          align-items: flex-start; overflow-x: auto; padding-bottom: 8px; }
        .sortable-container { flex: 1 1 0; min-width: 190px; border-radius: 14px;
          padding: 10px; }
        .sortable-container-header { font-weight: 800; font-size: .92rem; padding: 4px 6px 10px;
          font-family: 'Plus Jakarta Sans', sans-serif; }
        .sortable-container-body { display: flex; flex-direction: column; gap: 10px; min-height: 60px; }
        .sortable-item { background: #fff !important; color: #191b24 !important;
          border-radius: 10px; padding: 10px 12px 8px; cursor: grab;
          white-space: pre-line; font-size: .84rem; line-height: 1.45;
          box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04);
          border-top-width: 4px; border-top-style: solid; transition: box-shadow .15s, transform .15s; }
        .sortable-item:hover { box-shadow: 0 6px 16px rgba(0,0,0,0.12); transform: translateY(-1px); }
        .sortable-item:active { cursor: grabbing; }
        .sortable-item * { color: #191b24 !important; }
        """
    ]
    # nth-child is offset by one: the sortable component renders an extra,
    # non-".sortable-container" element as the first child of its wrapper.
    for i, (_, key, *_rest) in enumerate(COLUMN_DEFS, start=2):
        c = _COLORS[key]
        rules.append(
            f".sortable-container:nth-child({i}) {{ background: {c['bg']}; "
            f"border: 1px solid {c['border']}; }}"
        )
        rules.append(
            f".sortable-container:nth-child({i}) .sortable-item {{ border-top-color: {c['accent']}; }}"
        )
    return "\n".join(rules)


def _board(applications):
    # sort_items' items are plain draggable strings with no room for a hidden
    # id, so returned items are matched back to applications by their exact
    # label text — a pool per label, consumed in order. Two applications that
    # render identically (same company/title/date) are indistinguishable to
    # the user anyway, so an arbitrary pick between them is harmless.
    pool = {}
    groups = []
    for label, _key, primary_status, statuses in COLUMN_DEFS:
        col_apps = [a for a in applications if a.get("status") in statuses]
        items = []
        for app in col_apps:
            text = _item_text(app)
            pool.setdefault(text, []).append(app)
            items.append(text)
        groups.append({"header": f"{label}  ·  {len(items)}", "items": items})

    result = sort_items(
        groups,
        multi_containers=True,
        direction="vertical",
        custom_style=_board_custom_style(),
        key="kanban_board",
    )

    for (_, _key, primary_status, _statuses), group in zip(COLUMN_DEFS, result):
        for item_text in group["items"]:
            candidates = pool.get(item_text)
            if not candidates:
                continue
            app = candidates.pop(0)
            if app["status"] != primary_status:
                ok, _, _ = api.supabase_fetch(
                    "PATCH",
                    f"/rest/v1/applications?id=eq.{app['id']}",
                    json_body={"status": primary_status},
                )
                if ok:
                    st.rerun()
                else:
                    st.error("עדכון הסטטוס נכשל")


def _quick_actions(applications):
    actionable = [a for a in applications if a["status"] in ("phone_screen", "tech_interview")]
    with st.expander("🎯 הכנה לראיון / עדכון סטטוס מדויק (נדחה לעומת מוקפא)", expanded=False):
        if not applications:
            st.caption("אין משרות עדיין")
            return
        options = list(STATUS_LABELS.keys())
        for app in applications:
            job = app.get("jobs") or {}
            cols = st.columns([3, 2, 2])
            cols[0].markdown(f"**{job.get('title', '')}** · {job.get('company_name', '')}")
            current = app["status"] if app["status"] in options else options[0]
            prev_key = f"stprev_{app['id']}"
            new_status = cols[1].selectbox(
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
                if cols[2].button("התחל הכנה לראיון", key=f"prep_{app['id']}"):
                    nav.go(nav.INTERVIEW, application_id=app["id"])
        if not actionable:
            st.caption("אין כרגע משרות בשלב ראיון פעיל")


def render():
    ui.header("לוח המעקב שלי ✨", "כל המשרות שלכם, לפי שלב בתהליך")
    _top_bar()
    st.divider()
    _sync_and_unlinked()

    applications = _load_applications()
    _board(applications)
    _quick_actions(applications)
