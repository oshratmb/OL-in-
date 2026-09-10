"""Screen 7 — the mock interview. Persona chosen server-side from the job title,
exactly 5 questions one at a time, then a feedback report.
Mirrors interview-simulator.html + web/src/interview-simulator.js."""

import time

import streamlit as st

import api
import nav
import ui


def _job_info(application_id):
    ok, rows, _ = api.supabase_fetch(
        "GET",
        f"/rest/v1/applications?id=eq.{application_id}&select=jobs(title,company_name)&limit=1",
    )
    if ok and rows:
        return rows[0].get("jobs") or {}
    return {}


def _elapsed(start_ts):
    total = int(time.time() - start_ts)
    return f"{total // 60:02d}:{total % 60:02d}"


def render():
    app_id = nav.params().get("application_id") or st.session_state.get("interview_app_id")
    if not app_id:
        nav.go(nav.DASHBOARD)
    st.session_state.interview_app_id = app_id

    if not st.session_state.get("sim_started"):
        with st.spinner("מתחילים סימולציית ראיון..."):
            ok, data, _ = api.ai_fetch(
                "POST", "/simulations/start", {"application_id": app_id}
            )
        if not ok:
            st.error(data.get("detail", "התחלת הסימולציה נכשלה"))
            if st.button("חזרה ללוח"):
                nav.go(nav.DASHBOARD)
            return
        st.session_state.sim_id = data["simulation_id"]
        st.session_state.sim_persona = data["persona_role_title"]
        st.session_state.sim_chat = [{"role": "assistant", "content": data["question"]}]
        st.session_state.sim_done = False
        st.session_state.sim_started = True
        st.session_state.sim_start_ts = time.time()

    job = _job_info(app_id)
    ui.header(
        f"הכנה לראיון — {job.get('title', '')}",
        f"{job.get('company_name', '')} · מראיין/ת: {st.session_state.sim_persona} "
        f"· זמן: {_elapsed(st.session_state.sim_start_ts)}",
    )

    for msg in st.session_state.sim_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if st.session_state.sim_done:
        st.info("הראיון הסתיים — לחצו על 'סיום הראיון וקבלת משוב' כדי לראות את המשוב שלכם.")
    else:
        prompt = st.chat_input("הקלד/י את תשובתך...")
        if prompt:
            st.session_state.sim_chat.append({"role": "user", "content": prompt})
            ok, data, _ = api.ai_fetch(
                "POST", f"/simulations/{st.session_state.sim_id}/answer", {"answer": prompt}
            )
            if not ok:
                st.error(data.get("detail", "שליחת התשובה נכשלה"))
            elif data.get("done"):
                st.session_state.sim_done = True
            else:
                st.session_state.sim_chat.append(
                    {"role": "assistant", "content": data["question"]}
                )
            st.rerun()

    st.divider()
    if st.button("סיום הראיון וקבלת משוב", type="primary"):
        with st.spinner("מכין משוב..."):
            ok, data, _ = api.ai_fetch(
                "POST", f"/simulations/{st.session_state.sim_id}/feedback"
            )
        if ok:
            sim_id = st.session_state.sim_id
            for key in list(st.session_state.keys()):
                if key.startswith("sim_"):
                    st.session_state.pop(key)
            nav.go(nav.FEEDBACK, simulation_id=sim_id)
        else:
            st.error(data.get("detail", "הפקת המשוב נכשלה"))
