"""Screen 7 — the mock interview. Persona chosen server-side from the job title,
exactly 5 questions one at a time, then a feedback report. Candidates can answer
by typing or by recording their voice — a recording is transcribed server-side
(ai-service's ``/simulations/{id}/answer-audio``, via Whisper) and from there on
is treated exactly like a typed answer.
Mirrors interview-simulator.html + web/src/interview-simulator.js."""

import re
import time

import requests
import streamlit as st

import api
import nav
import ui

# A flat, illustrated interviewer avatar (not a literal photo — none exists for
# an AI persona — but deliberately not Streamlit's default robot icon either).
# Passed as a raw SVG string: st.chat_message's avatar handling base64-encodes
# any string starting with "<svg" into a data URI on its own.
_INTERVIEWER_AVATAR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
  <defs>
    <linearGradient id="ia" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0052cc"/>
    </linearGradient>
  </defs>
  <circle cx="40" cy="40" r="40" fill="url(#ia)"/>
  <circle cx="40" cy="32" r="13" fill="#fff" fill-opacity="0.95"/>
  <path d="M13 75c0-17 12-28 27-28s27 11 27 28" fill="#fff" fill-opacity="0.95"/>
</svg>"""

_ANSWER_MODES = ["✍️ הקלדה", "🎙️ הקלטה קולית"]


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


def _guess_company_domain(company_name):
    slug = re.sub(r"[^a-z0-9]", "", (company_name or "").lower())
    return f"{slug}.com" if slug else None


@st.cache_data(ttl=86400, show_spinner=False)
def _resolve_logo_url(domain: str) -> str | None:
    """Streamlit's markdown sanitizer strips inline ``onerror`` handlers, so a
    client-side broken-image fallback doesn't work here — the logo is verified
    server-side instead, once per domain (cached), before ever being rendered."""
    url = f"https://logo.clearbit.com/{domain}?size=88"
    try:
        resp = requests.get(url, timeout=2.5)
    except requests.RequestException:
        return None
    if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
        return url
    return None


def _company_badge(company_name):
    """Best-effort company logo (guessed .com domain via Clearbit's public logo
    API) with a graceful initials-badge fallback — there's no reliable way to
    resolve an exact domain from a free-text company name, so this is what the
    system can consistently show rather than nothing."""
    domain = _guess_company_domain(company_name)
    logo_url = _resolve_logo_url(domain) if domain else None
    initial = (company_name or "?").strip()[:1].upper() or "?"

    if logo_url:
        badge_html = (
            f'<img src="{logo_url}" style="width:44px;height:44px;border-radius:12px;'
            f'object-fit:contain;background:#fff;border:1px solid {ui.BORDER};padding:5px;" />'
        )
    else:
        badge_html = (
            f'<div style="width:44px;height:44px;border-radius:12px;background:{ui.GRADIENT};'
            "color:#fff;display:flex;align-items:center;justify-content:center;"
            f'font-weight:800;font-size:1.15rem;">{initial}</div>'
        )

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:.65rem;margin-bottom:.3rem;">
          {badge_html}
          <div style="font-weight:700;color:{ui.ON_SURFACE_VARIANT};">{company_name or ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_answer_result(data):
    if data.get("done"):
        st.session_state.sim_done = True
    else:
        st.session_state.sim_chat.append({"role": "assistant", "content": data["question"]})
    st.rerun()


def _submit_text_answer(answer_text):
    with st.spinner("שולח תשובה..."):
        ok, data, _ = api.ai_fetch(
            "POST", f"/simulations/{st.session_state.sim_id}/answer", {"answer": answer_text}
        )
    if not ok:
        st.error(data.get("detail", "שליחת התשובה נכשלה"))
        return
    st.session_state.sim_chat.append({"role": "user", "content": answer_text})
    _apply_answer_result(data)


def _submit_audio_answer(audio_value):
    with st.spinner("מתמלל ושולח את התשובה..."):
        ok, data, _ = api.ai_upload(
            f"/simulations/{st.session_state.sim_id}/answer-audio",
            files={"audio": (audio_value.name, audio_value.getvalue(), audio_value.type)},
        )
    if not ok:
        st.error(data.get("detail", "שליחת ההקלטה נכשלה, נסו שוב"))
        return
    st.session_state.sim_chat.append({"role": "user", "content": data.get("transcript") or ""})
    _apply_answer_result(data)


def _clear_sim_state():
    for key in list(st.session_state.keys()):
        if key.startswith(("sim_", "typed_answer_", "answer_audio_")) or key in (
            "last_audio_id",
            "answer_mode",
            "interview_app_id",
        ):
            st.session_state.pop(key, None)


def _finish_interview():
    with st.spinner("מכין משוב..."):
        ok, data, _ = api.ai_fetch("POST", f"/simulations/{st.session_state.sim_id}/feedback")
    if not ok:
        st.error(data.get("detail", "הפקת המשוב נכשלה"))
        return
    sim_id = st.session_state.sim_id
    _clear_sim_state()
    nav.go(nav.FEEDBACK, simulation_id=sim_id)


def render():
    app_id = nav.params().get("application_id") or st.session_state.get("interview_app_id")
    if not app_id:
        nav.go(nav.DASHBOARD)
    st.session_state.interview_app_id = app_id

    if st.button("← חזרה ללוח", key="interview_back_top"):
        _clear_sim_state()
        nav.go(nav.DASHBOARD)

    if not st.session_state.get("sim_started"):
        with st.spinner("מתחילים סימולציית ראיון..."):
            ok, data, _ = api.ai_fetch(
                "POST", "/simulations/start", {"application_id": app_id}
            )
        if not ok:
            st.error(data.get("detail", "התחלת הסימולציה נכשלה"))
            return
        st.session_state.sim_id = data["simulation_id"]
        st.session_state.sim_persona = data["persona_role_title"]
        st.session_state.sim_chat = [{"role": "assistant", "content": data["question"]}]
        st.session_state.sim_done = False
        st.session_state.sim_started = True
        st.session_state.sim_start_ts = time.time()

    job = _job_info(app_id)
    history = st.session_state.sim_chat
    q_num = min(sum(1 for m in history if m["role"] == "assistant"), 5)

    head_col, exit_col = st.columns([5, 1])
    with head_col:
        _company_badge(job.get("company_name"))
        st.markdown(f"### 🎤 הכנה לראיון — {job.get('title', '')}")
        st.caption(
            f"מראיין/ת: {st.session_state.sim_persona}  ·  ⏱️ {_elapsed(st.session_state.sim_start_ts)}"
            f"  ·  שאלה {q_num} מתוך 5"
        )
    with exit_col:
        st.write("")
        st.write("")
        if st.button("🚪 סיום ומשוב", key="finish_top", use_container_width=True):
            _finish_interview()

    st.progress(q_num / 5)
    st.divider()

    # earlier turns, collapsed — keeps the screen focused on the live question
    # instead of a growing scroll of past ones
    earlier = history[:-1] if (history and history[-1]["role"] == "assistant") else history
    if earlier:
        with st.expander(f"📜 תמליל השיחה ({len(earlier)} הודעות)", expanded=st.session_state.sim_done):
            for msg in earlier:
                avatar = _INTERVIEWER_AVATAR if msg["role"] == "assistant" else None
                with st.chat_message(msg["role"], avatar=avatar):
                    st.write(msg["content"])

    if st.session_state.sim_done:
        st.success("🎉 הראיון הסתיים — לחצו על 'סיום ומשוב' למעלה כדי לקבל את המשוב שלכם.")
        return

    # the live question, and the answer input directly below it
    with st.container(border=True):
        with st.chat_message("assistant", avatar=_INTERVIEWER_AVATAR):
            st.write(history[-1]["content"])

        mode = st.segmented_control(
            "איך תרצו לענות?", _ANSWER_MODES, default=_ANSWER_MODES[0], key="answer_mode"
        )

        if mode == _ANSWER_MODES[1]:
            audio_value = st.audio_input("🎙️ הקליטו את תשובתכם", key=f"answer_audio_{len(history)}")
            if audio_value is not None and audio_value.file_id != st.session_state.get("last_audio_id"):
                st.session_state.last_audio_id = audio_value.file_id
                _submit_audio_answer(audio_value)
        else:
            answer = st.text_area(
                "התשובה שלך",
                key=f"typed_answer_{len(history)}",
                label_visibility="collapsed",
                placeholder="הקלידו את תשובתכם כאן...",
                height=120,
            )
            if st.button("שליחת התשובה ➤", type="primary"):
                if answer.strip():
                    _submit_text_answer(answer.strip())
                else:
                    st.warning("כתבו תשובה לפני השליחה")
