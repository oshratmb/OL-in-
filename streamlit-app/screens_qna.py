"""Screen 5 — the gap-filling Q&A wizard (skip-friendly). One question at a time;
after the last one the tailored documents are generated automatically.
Mirrors qna-wizard.html + web/src/qna-wizard.js."""

import streamlit as st

import api
import nav
import ui


def _generate(pending):
    with st.spinner("יוצרים עבורכם קורות חיים ומכתב מקדים מותאמים... זה עשוי לקחת עד דקה."):
        ok, data, _ = api.ai_fetch(
            "POST",
            "/documents/generate",
            {
                "job": pending["job"],
                "qna_answers": st.session_state.get("qna_answers", []),
                "tone": "professional",
            },
        )
    if not ok:
        st.error(data.get("detail", "יצירת המסמכים נכשלה"))
        if st.button("נסו שוב"):
            st.rerun()
        return

    st.session_state.document_result = {
        **data,
        "job": pending["job"],
        "qna_answers": st.session_state.get("qna_answers", []),
    }
    for key in ("pending_job", "qna_idx", "qna_answers", "qna_show_tip"):
        st.session_state.pop(key, None)
    nav.go(nav.DOC_PREVIEW)


def render():
    pending = st.session_state.get("pending_job")
    if not pending:
        nav.go(nav.JOB_INTAKE)

    questions = pending.get("gap_questions", [])
    st.session_state.setdefault("qna_idx", 0)
    st.session_state.setdefault("qna_answers", [])

    idx = st.session_state.qna_idx
    if not questions or idx >= len(questions):
        _generate(pending)
        return

    ui.header("השלמת פערים", "כמה שאלות קצרות שיעזרו ל-AI להתאים את קורות החיים למשרה. אפשר לדלג על כל שאלה.")
    ui.progress(idx / len(questions) * 100)

    if st.session_state.pop("qna_show_tip", False):
        st.info("אין בעיה — דילוג על שאלה לא פוגע בתהליך. ממשיכים הלאה 💪")

    question = questions[idx]
    st.markdown(f"**שאלה {idx + 1} מתוך {len(questions)}**")
    st.markdown(question["question"])
    answer = st.text_area("התשובה שלך", key=f"qna_ans_{idx}", height=140)

    col_next, col_skip = st.columns(2)
    if col_next.button("המשך", type="primary"):
        st.session_state.qna_answers.append(
            {"question_id": question["id"], "question": question["question"], "answer": answer.strip()}
        )
        st.session_state.qna_idx += 1
        st.rerun()
    if col_skip.button("דלג על השאלה"):
        st.session_state.qna_answers.append(
            {"question_id": question["id"], "question": question["question"], "answer": ""}
        )
        st.session_state.qna_idx += 1
        st.session_state.qna_show_tip = True
        st.rerun()
