"""Screen 6 — tailored resume + cover letter, with the Gatekeeper trust warning,
tone switching and Hebrew/English translation.
Mirrors document-preview.html + web/src/document-preview.js."""

import streamlit as st

import api
import nav
import ui

TONE_LABELS = {"professional": "מקצועי", "enthusiastic": "נלהב", "concise": "תמציתי"}


def _render_resume(resume: dict):
    personal = resume.get("personal_info") or {}
    st.markdown(f"### {personal.get('name', '')}")
    contact = " | ".join(
        x for x in [personal.get("email"), personal.get("phone"), personal.get("location")] if x
    )
    if contact:
        st.caption(contact)
    if resume.get("professional_summary"):
        st.write(resume["professional_summary"])

    if resume.get("work_experience"):
        st.markdown("#### ניסיון תעסוקתי")
        for e in resume["work_experience"]:
            st.markdown(
                f"**{e.get('title', '')} — {e.get('company', '')}** "
                f"({e.get('start_date', '')} - {e.get('end_date', '')})"
            )
            for bullet in e.get("bullets", []) or []:
                st.markdown(f"- {bullet}")

    if resume.get("education"):
        st.markdown("#### השכלה")
        for e in resume["education"]:
            parts = [e.get("degree"), e.get("field"), e.get("institution"), e.get("year")]
            st.markdown("- " + " · ".join(p for p in parts if p))

    if resume.get("skills"):
        st.markdown("#### מיומנויות")
        st.write(", ".join(resume["skills"]))

    if resume.get("languages"):
        st.markdown("#### שפות")
        st.write(", ".join(resume["languages"]))


def render():
    data = st.session_state.get("document_result")
    if not data:
        nav.go(nav.DASHBOARD)

    ui.header("המסמכים המותאמים שלך", "קורות חיים ומכתב מקדים שנוצרו למשרה זו ואומתו ע\"י סוכן ה-Gatekeeper.")

    if data.get("gatekeeper_status") == "TRUST_WARNING":
        st.warning("**שימו לב** — נמצאו אי-התאמות שכדאי לבדוק לפני שליחה:")
        for violation in data.get("violations", []):
            st.markdown(f"- {violation}")

    tone = st.session_state.get("doc_tone", "professional")
    lang = st.session_state.get("doc_lang", "he")

    col_tone, col_lang = st.columns(2)
    with col_tone:
        new_tone = st.selectbox(
            "טון המכתב",
            list(TONE_LABELS.keys()),
            index=list(TONE_LABELS.keys()).index(tone),
            format_func=lambda t: TONE_LABELS[t],
        )
        if new_tone != tone:
            st.session_state.doc_tone = new_tone
            with st.spinner("מעדכן את הטון..."):
                ok, upd, _ = api.ai_fetch(
                    "POST",
                    "/documents/generate",
                    {
                        "job": data["job"],
                        "qna_answers": data["qna_answers"],
                        "tone": new_tone,
                        "application_id": data["application_id"],
                    },
                )
            if ok:
                st.session_state.document_result = {**data, **upd}
                st.rerun()
            else:
                st.error(upd.get("detail", "עדכון הטון נכשל"))

    with col_lang:
        st.write("")
        toggle_label = "תרגם לאנגלית" if lang == "he" else "תרגם לעברית"
        if st.button(toggle_label):
            target = "en" if lang == "he" else "he"
            with st.spinner("מתרגם..."):
                ok, upd, _ = api.ai_fetch(
                    "POST",
                    "/documents/translate",
                    {
                        "application_id": data["application_id"],
                        "resume": data["resume"],
                        "cover_letter_text": data["cover_letter_text"],
                        "target_language": target,
                    },
                )
            if ok:
                st.session_state.document_result = {**data, **upd}
                st.session_state.doc_lang = target
                st.rerun()
            else:
                st.error(upd.get("detail", "התרגום נכשל"))

    tab_resume, tab_letter = st.tabs(["קורות חיים מותאמים", "מכתב מקדים"])
    with tab_resume:
        _render_resume(data["resume"])
        st.divider()
        st.link_button("הורדת קובץ Word (.docx)", data["tailored_resume_url"])
    with tab_letter:
        st.text_area("מכתב מקדים", data["cover_letter_text"], height=380)
        st.caption("סמנו והעתיקו את הטקסט (Ctrl/Cmd+C)")

    st.divider()
    if st.button("חזרה ללוח"):
        for key in ("document_result", "doc_tone", "doc_lang"):
            st.session_state.pop(key, None)
        nav.go(nav.DASHBOARD)
