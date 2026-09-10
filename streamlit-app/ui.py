"""Shared chrome: RTL styling + small visual helpers that match
``web/src/style.css`` (same palette, cards, progress bar, match/score gauges)."""

import streamlit as st

PRIMARY = "#2f6fed"
SUCCESS = "#1c8a4b"
WARNING = "#e0a52c"
DANGER = "#d64545"
BORDER = "#e2e5ec"

_CSS = f"""
<style>
  .stApp, .block-container {{ direction: rtl; }}
  .block-container {{ max-width: 820px; padding-top: 2.2rem; }}
  .block-container h1, .block-container h2, .block-container h3,
  .block-container h4, .block-container h5,
  .block-container p, .block-container li, .block-container label,
  .block-container .stMarkdown {{ text-align: right; }}
  .stTextInput input, .stTextArea textarea, .stNumberInput input {{ text-align: right; }}
  [data-testid="stChatMessageContent"] {{ text-align: right; }}
  [data-testid="stMetric"] {{
    background: #fff; border: 1px solid {BORDER};
    border-radius: 12px; padding: 14px 16px;
  }}
  [data-testid="stMetricValue"] {{ direction: ltr; text-align: right; }}
  div[data-testid="stExpander"] details {{ border-radius: 10px; }}
</style>
"""


def setup_page():
    st.set_page_config(
        page_title="פלטפורמת חיפוש עבודה חכמה",
        page_icon="💼",
        layout="centered",
    )
    st.markdown(_CSS, unsafe_allow_html=True)


def header(title, subtitle=None):
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)


def progress(pct: float):
    st.progress(max(0, min(100, int(round(pct)))))


def _color_for(pct: int) -> str:
    return SUCCESS if pct >= 70 else WARNING if pct >= 40 else DANGER


def match_bar(pct: int):
    pct = max(0, min(100, int(pct)))
    color = _color_for(pct)
    st.markdown(
        f"""
        <div style="background:{BORDER};border-radius:6px;overflow:hidden;height:16px;">
          <div style="width:{pct}%;background:{color};height:100%;"></div>
        </div>
        <div style="text-align:center;margin-top:6px;font-weight:700;">{pct}% התאמה</div>
        """,
        unsafe_allow_html=True,
    )


def score_gauge(score: int):
    score = max(0, min(100, int(score)))
    color = _color_for(score)
    st.markdown(
        f"""
        <div style="display:flex;justify-content:center;margin:8px 0 18px;">
          <div style="width:150px;height:150px;border-radius:50%;
               background:conic-gradient({color} {score}%, {BORDER} 0);
               display:flex;align-items:center;justify-content:center;">
            <div style="width:112px;height:112px;border-radius:50%;background:#fff;
                 display:flex;align-items:center;justify-content:center;
                 font-size:2.2rem;font-weight:800;">{score}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bullet_list(items):
    items = list(items or [])
    if not items:
        st.caption("אין נתונים")
        return
    for item in items:
        st.markdown(f"- {item}")
