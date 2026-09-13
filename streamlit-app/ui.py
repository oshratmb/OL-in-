"""Shared chrome: RTL styling + small visual helpers that match
``web/src/style.css`` (same palette, cards, progress bar, match/score gauges)."""

import streamlit as st

PRIMARY = "#2f6fed"
SUCCESS = "#1c8a4b"
WARNING = "#e0a52c"
DANGER = "#d64545"
BORDER = "#e2e5ec"

GRADIENT = f"linear-gradient(135deg, {PRIMARY} 0%, #6a4cf0 100%)"

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

  /* Marketing landing page */
  .hero {{
    background: {GRADIENT}; color: #fff; border-radius: 20px;
    padding: 2.6rem 2.2rem; margin-bottom: 1.6rem;
    box-shadow: 0 12px 30px -12px rgba(47,111,237,0.55);
  }}
  .hero h1 {{ color: #fff !important; font-size: 2.1rem; margin: 0 0 .5rem; }}
  .hero p {{ color: rgba(255,255,255,0.92) !important; font-size: 1.05rem; margin: 0; }}
  .feature-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: .8rem;
    margin: 1.6rem 0 2rem;
  }}
  @media (max-width: 700px) {{ .feature-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  .feature-card {{
    background: #fff; border: 1px solid {BORDER}; border-radius: 14px;
    padding: 1rem .9rem; text-align: center;
  }}
  .feature-card .icon {{ font-size: 1.6rem; display: block; margin-bottom: .4rem; }}
  .feature-card .label {{ font-size: .82rem; font-weight: 600; color: #333; line-height: 1.3; }}
  div[data-testid="stFormSubmitButton"] button,
  .stButton button[kind="primary"] {{
    background: {GRADIENT} !important; border: none !important;
    border-radius: 10px !important; font-weight: 700 !important;
  }}
  div[data-testid="stFormSubmitButton"] button:hover,
  .stButton button[kind="primary"]:hover {{ filter: brightness(1.08); }}
  [data-testid="stLinkButton"] a {{
    border-radius: 10px !important; font-weight: 600 !important;
  }}
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


_FEATURES = [
    ("🤖", "ניתוח קורות חיים חכם"),
    ("🎯", "התאמת מסמכים AI לכל משרה"),
    ("📊", "לוח מעקב מועמדויות"),
    ("🎤", "סימולטור ראיונות עם משוב"),
]


def landing_hero():
    st.markdown(
        """
        <div class="hero">
          <h1>פלטפורמת חיפוש העבודה החכמה שלך</h1>
          <p>AI שמנתח את קורות החיים שלכם, מתאים אותם לכל משרה, ומכין אתכם
          לראיון — משלב החיפוש הראשון ועד קבלת ההצעה.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cards = "".join(
        f'<div class="feature-card"><span class="icon">{icon}</span>'
        f'<span class="label">{label}</span></div>'
        for icon, label in _FEATURES
    )
    st.markdown(f'<div class="feature-grid">{cards}</div>', unsafe_allow_html=True)


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
