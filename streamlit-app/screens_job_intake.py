"""Screen 4 — paste a job description, run the AI gap analysis.
Mirrors job-intake.html + web/src/job-intake.js."""

import streamlit as st

import api
import nav
import ui


def render():
    if st.button("← חזרה ללוח"):
        st.session_state.pop("job_analysis", None)
        st.session_state.pop("job_desc_text", None)
        nav.go(nav.DASHBOARD)

    ui.header("הוספת משרה חדשה", "הדביקו את תיאור המשרה המלא. ה-AI ינתח את מידת ההתאמה שלכם ואת הפערים.")

    jd_text = st.text_area("תיאור המשרה", height=260, key="jd_text")

    if st.button("נתח משרה", type="primary"):
        if not jd_text.strip():
            st.error("יש להדביק תיאור משרה לפני הניתוח")
        else:
            with st.spinner("מנתח..."):
                ok, data, _ = api.ai_fetch(
                    "POST", "/jobs/analyze", {"description_text": jd_text.strip()}
                )
            if ok:
                st.session_state.job_analysis = data
                st.session_state.job_desc_text = jd_text.strip()
            else:
                st.error(data.get("detail", "הניתוח נכשל"))

    analysis = st.session_state.get("job_analysis")
    if not analysis:
        return

    st.divider()
    with st.container(border=True):
        title = st.text_input("שם המשרה", analysis.get("detected_title", ""))
        company = st.text_input("שם החברה", analysis.get("detected_company_name", ""))

        pct = max(0, min(100, analysis.get("match_percentage", 0)))
        ui.match_bar(pct)

        st.markdown("**דרישות המשרה**")
        for req in analysis.get("requirements", []):
            mark = "✅" if req.get("present") else "❌"
            note = f" — {req['note']}" if req.get("note") else ""
            st.markdown(f"{mark} {req.get('requirement', '')}{note}")

        if st.button("המשך לשאלון השלמת פערים", type="primary"):
            st.session_state.pending_job = {
                "job": {
                    "title": title.strip(),
                    "company_name": company.strip(),
                    "description_text": st.session_state.job_desc_text,
                },
                "gap_questions": analysis.get("gap_questions", []),
            }
            st.session_state.pop("job_analysis", None)
            nav.go(nav.QNA)
