"""Screen 3 — the Kanban board (4 columns), unlinked-email banner, Gmail sync.
Mirrors dashboard.html + web/src/dashboard.js, reworked from user feedback on
the first Stitch-based cut of this screen:

- Not every company's process has all of phone-screen/take-home/tech-interview
  as separate stages, and once a card left "applied" it was unclear whether an
  interview had already happened or when it was scheduled. Those three
  statuses are now one "בתהליך" (in process) column; the exact sub-stage and
  its date/note (``applications.next_step_at`` / ``next_step_note`` — see
  migration 0005) are set in the compact panel below the board, and shown as
  a line of text on the card itself.
- The rejected/on-hold column was rendering full-width *below* the other
  columns instead of beside them, and visually dominated the board in a way
  that felt discouraging. It's now a normal, deliberately narrow column in
  the same row as the others, last in RTL reading order.
- The column header counts didn't update after a drag: streamlit-sortables
  keeps its own client-side state once mounted and won't necessarily re-read
  new header text under an unchanged component key. The board's key is now
  derived from the applications themselves, so it only remounts (picking up
  fresh counts) when the underlying data actually changes.
"""

import datetime
import hashlib

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

IN_PROCESS_STATUSES = ["phone_screen", "homework", "tech_interview"]

# label, icon, css color key, flex weight, the status a card dropped into
# this column gets by default, every status this column covers
COLUMN_DEFS = [
    ("הוגש", "📥", "gray", 1, "applied", ["applied"]),
    ("בתהליך", "🚀", "indigo", 2, "phone_screen", IN_PROCESS_STATUSES),
    ("הצעת חוזה", "🏆", "emerald", 1, "offer", ["offer"]),
    ("נדחה / הוקפא", "🗂️", "rose", 1, "rejected", ["rejected", "on_hold"]),
]

_COLORS = {
    "gray": {"bg": "#f4f5f7", "border": "#d8dae2", "accent": "#6c757d"},
    "indigo": {"bg": "#eef2ff", "border": "#c7d2fe", "accent": "#4f46e5"},
    "emerald": {"bg": "#ecfdf5", "border": "#a7f3d0", "accent": "#10b981"},
    "rose": {"bg": "#f7f7f8", "border": "#e5e5e8", "accent": "#a1a1aa"},
}


def _initials(text):
    return (text or "?").strip()[:2].upper()


def _load_applications():
    ok, rows, _ = api.supabase_fetch(
        "GET",
        "/rest/v1/applications?select=id,status,applied_at,next_step_at,next_step_note,"
        "jobs(title,company_name)&order=applied_at.desc",
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


def _motivation_strip(applications):
    active = sum(1 for a in applications if a["status"] not in ("rejected", "on_hold"))
    offers = sum(1 for a in applications if a["status"] == "offer")
    if offers:
        st.success(f"🏆 {offers} הצעות חוזה על השולחן — כל הכבוד, אתם קרובים!")
    elif active:
        st.info(f"🔥 {active} משרות פעילות בתהליך. ממשיכים קדימה!")


def _gmail_connect_cta(needs_reconnect=False):
    """Shown in place of the sync button when Gmail isn't connected (or its
    connection expired) — sync-now would otherwise surface a raw English
    backend error ("Gmail is not connected for this user"), which isn't
    actionable for the user. A connect call-to-action is.

    The authorize URL is fetched eagerly (it's a cheap, side-effect-free call
    that just builds a Google URL) so the button itself is a real link
    straight to Google's consent screen — one click, not a click to fetch
    the link followed by a second click to use it."""
    with st.container(border=True):
        if needs_reconnect:
            st.markdown("#### 🔄 נדרש חיבור מחדש ל-Gmail")
            st.caption("החיבור לג'ימייל פג — חברו מחדש כדי להמשיך לקבל עדכונים אוטומטיים על המשרות שלכם.")
            btn_label = "🔗 חיבור מחדש ל-Gmail"
        else:
            st.markdown("#### 📧 חברו את הג'ימייל שלכם")
            st.caption(
                "חברו את הג'ימייל שלכם עכשיו ותוכלו להיות מעודכנים אוטומטית על כל "
                "תשובה מהמעסיקים — בלי לפספס אף מייל."
            )
            btn_label = "🔗 חיבור Gmail עכשיו"

        ok, data, _ = api.ai_fetch("POST", "/gmail/connect/start")
        if ok and data.get("authorize_url"):
            st.link_button(btn_label, data["authorize_url"], type="primary")
        else:
            st.error(data.get("detail", "לא ניתן להתחיל חיבור Gmail"))


def _sync_and_unlinked():
    ok_status, status, _ = api.ai_fetch("GET", "/gmail/status")
    connected = ok_status and status.get("connected") and not status.get("needs_reconnect")

    if connected:
        if st.button("🔄 סנכרן אימיילים עכשיו"):
            with st.spinner("מסנכרן..."):
                ok, data, _ = api.ai_fetch("POST", "/gmail/sync-now")
            if ok:
                st.success("הסנכרון הושלם")
                st.rerun()
            else:
                st.error(data.get("detail", "הסנכרון נכשל"))
    else:
        _gmail_connect_cta(needs_reconnect=bool(ok_status and status.get("needs_reconnect")))

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
    lines = [f"{_initials(company)} · {title}", company]
    if app["status"] in IN_PROCESS_STATUSES:
        stage_line = f"🚀 {STATUS_LABELS[app['status']]}"
        if app.get("next_step_at"):
            stage_line += f" · {app['next_step_at'][:10]}"
        lines.append(stage_line)
        if app.get("next_step_note"):
            lines.append(app["next_step_note"])
    else:
        lines.append((app.get("applied_at") or "")[:10])
    return "\n".join(lines)


def _board_signature(applications):
    key_bits = sorted(
        f"{a['id']}:{a['status']}:{a.get('next_step_at')}" for a in applications
    )
    return hashlib.md5("|".join(key_bits).encode()).hexdigest()[:10]


def _board_custom_style():
    rules = [
        """
        .sortable-component { display: flex; flex-direction: row-reverse; gap: 14px;
          align-items: flex-start; overflow-x: auto; padding-bottom: 8px; }
        .sortable-container { border-radius: 14px; padding: 10px; }
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
    # nth-child is offset by one: the component renders an extra, non-
    # ".sortable-container" element as the first child of its wrapper.
    for i, (_, _icon, key, weight, *_rest) in enumerate(COLUMN_DEFS, start=2):
        c = _COLORS[key]
        rules.append(
            f".sortable-container:nth-child({i}) {{ background: {c['bg']}; "
            f"border: 1px solid {c['border']}; flex: {weight} {weight} 0; min-width: "
            f"{'150px' if weight == 1 else '190px'}; }}"
        )
        rules.append(
            f".sortable-container:nth-child({i}) .sortable-item {{ border-top-color: {c['accent']}; }}"
        )
    return "\n".join(rules)


def _board(applications):
    pool = {}
    groups = []
    for label, icon, _key, _weight, _primary, statuses in COLUMN_DEFS:
        col_apps = [a for a in applications if a.get("status") in statuses]
        items = []
        for app in col_apps:
            text = _item_text(app)
            pool.setdefault(text, []).append(app)
            items.append(text)
        groups.append({"header": f"{icon} {label}  ·  {len(items)}", "items": items})

    result = sort_items(
        groups,
        multi_containers=True,
        direction="vertical",
        custom_style=_board_custom_style(),
        key=f"kanban_board_{_board_signature(applications)}",
    )

    for (_, _icon, _key, _weight, primary_status, statuses), group in zip(COLUMN_DEFS, result):
        for item_text in group["items"]:
            candidates = pool.get(item_text)
            if not candidates:
                continue
            app = candidates.pop(0)
            if app["status"] not in statuses:
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
    with st.expander("🎯 שלב מדויק, מועד לראיון והכנה", expanded=False):
        if not applications:
            st.caption("אין משרות עדיין")
            return
        options = list(STATUS_LABELS.keys())
        any_in_process = False
        for app in applications:
            job = app.get("jobs") or {}
            st.markdown(f"**{job.get('title', '')}** · {job.get('company_name', '')}")
            cols = st.columns([2, 2, 2, 1])

            current = app["status"] if app["status"] in options else options[0]
            prev_key = f"stprev_{app['id']}"
            new_status = cols[0].selectbox(
                "סטטוס",
                options,
                index=options.index(current),
                format_func=lambda v: STATUS_LABELS[v],
                key=f"status_{app['id']}",
                label_visibility="collapsed",
            )
            patch = {}
            if new_status != current and st.session_state.get(prev_key) != new_status:
                st.session_state[prev_key] = new_status
                patch["status"] = new_status

            if new_status in IN_PROCESS_STATUSES:
                any_in_process = True
                current_date = None
                if app.get("next_step_at"):
                    try:
                        current_date = datetime.date.fromisoformat(app["next_step_at"][:10])
                    except ValueError:
                        current_date = None
                new_date = cols[1].date_input(
                    "מועד",
                    value=current_date,
                    key=f"date_{app['id']}",
                    label_visibility="collapsed",
                )
                new_note = cols[2].text_input(
                    "הערה",
                    value=app.get("next_step_note") or "",
                    key=f"note_{app['id']}",
                    placeholder="הערה (למשל: Google Meet)",
                    label_visibility="collapsed",
                )
                current_next_step_date = (app.get("next_step_at") or "")[:10] or None
                new_at = new_date.isoformat() if new_date else None
                if new_at != current_next_step_date:
                    patch["next_step_at"] = new_at
                if new_note != (app.get("next_step_note") or ""):
                    patch["next_step_note"] = new_note or None

            if patch:
                ok, _, _ = api.supabase_fetch(
                    "PATCH", f"/rest/v1/applications?id=eq.{app['id']}", json_body=patch
                )
                if ok:
                    st.rerun()
                else:
                    st.error("העדכון נכשל")

            if new_status in ("phone_screen", "tech_interview"):
                if cols[3].button("🎯 הכנה", key=f"prep_{app['id']}"):
                    nav.go(nav.INTERVIEW, application_id=app["id"])
            st.divider()

        if not any_in_process:
            st.caption("אין כרגע משרות בשלב 'בתהליך'")


def render():
    ui.header("לוח המעקב שלי ✨", "כל המשרות שלכם, לפי שלב בתהליך")
    _top_bar()
    st.divider()

    applications = _load_applications()
    _motivation_strip(applications)
    _sync_and_unlinked()
    _board(applications)
    _quick_actions(applications)
