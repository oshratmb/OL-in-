"""Screen 8 — the rubric-based feedback report (score gauge, strengths,
improvements, per-question rewrite suggestions). Re-rendered from the DB, so it
survives a direct reload via its ``simulation_id``.
Mirrors simulation-feedback.html + web/src/simulation-feedback.js."""

import streamlit as st

import api
import nav
import ui


def render():
    sim_id = nav.params().get("simulation_id") or st.session_state.get("feedback_sim_id")
    if not sim_id:
        nav.go(nav.DASHBOARD)
    st.session_state.feedback_sim_id = sim_id

    ok, sim, _ = api.ai_fetch("GET", f"/simulations/{sim_id}")
    if not ok:
        st.error("לא נמצאה סימולציה")
        if st.button("חזרה ללוח"):
            nav.go(nav.DASHBOARD)
        return

    report = sim.get("feedback_report")
    if not report:
        st.warning("המשוב עדיין לא הופק עבור סימולציה זו.")
        if st.button("חזרה ללוח"):
            nav.go(nav.DASHBOARD)
        return

    ui.header("משוב על הראיון", f"מראיין/ת: {sim.get('persona_role_title', '')}")
    ui.score_gauge(report.get("overall_score", 0))
    st.write(report.get("summary", ""))

    tab_strengths, tab_improve, tab_rewrite = st.tabs(
        ["חוזקות", "נקודות לשיפור", "הצעות לניסוח"]
    )
    with tab_strengths:
        ui.bullet_list(report.get("strengths", []))
    with tab_improve:
        ui.bullet_list(report.get("improvements", []))
    with tab_rewrite:
        for q in report.get("per_question", []):
            with st.container(border=True):
                st.markdown(f"**שאלה:** {q.get('question', '')}")
                st.markdown(f"**התשובה שלך:** {q.get('answer', '')}")
                st.markdown(f"**משוב:** {q.get('feedback', '')}")
                st.markdown(f"**הצעה לניסוח חלופי:** {q.get('suggested_answer', '')}")

    st.divider()
    col_redo, col_back = st.columns(2)
    if col_redo.button("בצע סימולציה חוזרת", type="primary"):
        nav.go(nav.INTERVIEW, application_id=sim["application_id"])
    if col_back.button("חזרה ללוח"):
        st.session_state.pop("feedback_sim_id", None)
        nav.go(nav.DASHBOARD)
