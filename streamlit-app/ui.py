"""Shared chrome: RTL styling + small visual helpers that match
``web/src/style.css`` (same palette, cards, progress bar, match/score gauges).

The landing-page look (hero, feature grid, "how it works", auth card) mirrors
a design generated in Google Stitch against this project's own design
system ("Professional Pipeline") — see streamlit-app/README.md.
"""

import json

import streamlit as st
import streamlit.components.v1 as components

PRIMARY = "#0d6efd"
PRIMARY_HOVER = "#0b5ed7"
PRIMARY_DARK = "#0052cc"
SUCCESS = "#1c8a4b"
WARNING = "#e0a52c"
DANGER = "#d64545"
BORDER = "#e0e2ed"
SURFACE = "#faf8ff"
SURFACE_LOW = "#f2f3ff"
ON_SURFACE = "#1b1b21"
ON_SURFACE_VARIANT = "#45464f"

GRADIENT = f"linear-gradient(90deg, {PRIMARY} 0%, {PRIMARY} 60%, {PRIMARY_DARK} 100%)"

_CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
  @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');
  html, body, .stApp {{ font-family: 'Assistant', 'Plus Jakarta Sans', sans-serif; }}
  .stApp, .block-container {{ direction: rtl; }}
  .block-container {{ max-width: 1100px; padding-top: 2rem; }}
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
  .msi {{
    font-family: 'Material Symbols Outlined'; font-weight: normal; font-style: normal;
    font-size: 24px; line-height: 1; vertical-align: middle;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  }}

  /* Marketing landing page */
  .hero-badge {{
    display: inline-flex; align-items: center; gap: .4rem;
    background: rgba(13,110,253,0.1); color: {PRIMARY}; border: 1px solid rgba(13,110,253,0.2);
    border-radius: 999px; padding: .35rem .9rem; font-size: .78rem; font-weight: 700;
    margin-bottom: 1rem;
  }}
  .hero-badge .msi {{ font-size: 16px; }}
  .hero h1 {{
    font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2.6rem; font-weight: 800;
    line-height: 1.15; color: {ON_SURFACE} !important; margin: 0 0 1rem;
  }}
  .hero p.subhead {{
    font-size: 1.15rem; color: {ON_SURFACE_VARIANT} !important; line-height: 1.6; margin: 0 0 1.6rem;
  }}
  .trust-row {{
    display: flex; flex-wrap: wrap; gap: 1.4rem; margin-top: 1.6rem;
    padding-top: 1.4rem; border-top: 1px solid {BORDER};
    font-size: .82rem; color: {ON_SURFACE_VARIANT};
  }}
  .trust-row span {{ display: inline-flex; align-items: center; gap: .35rem; }}
  .trust-row .msi {{ font-size: 17px; color: {SUCCESS}; }}
  .hero-illustration {{ width: 100%; max-width: 420px; margin: 0 auto; display: block; }}
  .section-eyebrow {{
    font-size: .74rem; font-weight: 700; color: {PRIMARY}; letter-spacing: .08em;
    text-transform: uppercase; margin-bottom: .4rem;
  }}
  .section-title {{ font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.7rem; font-weight: 800; margin: 0 0 .5rem; }}
  .section-sub {{ color: {ON_SURFACE_VARIANT}; font-size: .95rem; margin: 0 0 1.6rem; }}
  .feature-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: .9rem;
    margin: 0 0 2.4rem;
  }}
  @media (max-width: 900px) {{ .feature-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  .feature-card {{
    background: #fff; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 1.2rem 1.1rem; text-align: right;
    box-shadow: 0 4px 20px -2px rgba(13,110,253,0.06), 0 2px 6px -1px rgba(0,0,0,0.04);
  }}
  .feature-card .icon-box {{
    width: 44px; height: 44px; border-radius: 10px; background: #eff6ff; color: {PRIMARY};
    display: flex; align-items: center; justify-content: center; margin-bottom: .9rem;
  }}
  .feature-card .title {{ font-weight: 700; font-size: .98rem; margin-bottom: .35rem; color: {ON_SURFACE}; }}
  .feature-card .desc {{ font-size: .82rem; color: {ON_SURFACE_VARIANT}; line-height: 1.5; }}
  .steps-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.6rem; margin: 0 0 2rem; }}
  @media (max-width: 900px) {{ .steps-row {{ grid-template-columns: 1fr; }} }}
  .step {{ text-align: center; }}
  .step .num {{
    width: 52px; height: 52px; border-radius: 999px; background: {PRIMARY}; color: #fff;
    font-weight: 800; font-size: 1.3rem; display: flex; align-items: center; justify-content: center;
    margin: 0 auto .9rem; box-shadow: 0 4px 12px -2px rgba(13,110,253,0.4);
  }}
  .step .title {{ font-weight: 700; font-size: 1.05rem; margin-bottom: .3rem; }}
  .step .desc {{ font-size: .85rem; color: {ON_SURFACE_VARIANT}; line-height: 1.5; max-width: 260px; margin: 0 auto; }}

  div[data-testid="stFormSubmitButton"] button,
  .stButton button[kind="primary"] {{
    background: {GRADIENT} !important; border: none !important;
    border-radius: 10px !important; font-weight: 700 !important;
  }}
  div[data-testid="stFormSubmitButton"] button:hover,
  .stButton button[kind="primary"]:hover {{ filter: brightness(1.06); }}
  [data-testid="stLinkButton"] a {{
    border-radius: 10px !important; font-weight: 600 !important;
  }}
</style>
"""


def setup_page():
    st.set_page_config(
        page_title="פלטפורמת חיפוש עבודה חכמה",
        page_icon="💼",
        layout="wide",
    )
    st.markdown(_CSS, unsafe_allow_html=True)


def header(title, subtitle=None):
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)


# --------------------------------------------------------------------------- #
# "stay signed in" — bridges a persisted session into browser localStorage.
#
# Each Streamlit session lives only as long as its one browser tab's
# websocket connection: the HttpOnly refresh-token cookie ai-service sets
# is captured by that tab's own server-side ``requests.Session`` (see
# api.py's module docstring), never by the actual browser. A full-page
# navigation away and back (an OAuth redirect, a new tab, reopening the
# site tomorrow) starts a brand new session with none of that — so
# "remember me" needs a credential the real browser holds itself.
# --------------------------------------------------------------------------- #
_REMEMBER_KEY = "olin_remember_token"


def persist_remember_token(token: str):
    """Call right after a login/signup/Google-redeem that returned a
    ``remember_token`` — stores it in the browser's own localStorage."""
    if not token:
        return
    components.html(
        f"<script>try{{localStorage.setItem({json.dumps(_REMEMBER_KEY)},"
        f"{json.dumps(token)});}}catch(e){{}}</script>",
        height=0,
    )


def clear_remember_token():
    """Call on explicit logout, so a stale token doesn't silently sign the
    user back in on their next visit."""
    components.html(
        f"<script>try{{localStorage.removeItem({json.dumps(_REMEMBER_KEY)});}}"
        "catch(e){}</script>",
        height=0,
    )


def try_restore_remember_token():
    """Call once per unauthenticated page load. A fresh Streamlit session has
    no way to read the browser's localStorage directly (see module note
    above) — so if a token is there, this reloads the page once with it
    added to the URL, preserving whatever other query params are already on
    it (e.g. an OAuth-return ``gmail=connected``), for app.py's
    ``_handle_oauth_return`` to pick up on that next load.

    Streamlit's ``components.html`` iframe is sandboxed without
    ``allow-top-navigation``, so ``window.top.location = ...`` is silently
    blocked here — it does have ``allow-same-origin`` though, so instead this
    creates and clicks a real link *inside the top document itself*; that
    click, and the navigation it causes, runs in the top frame's own
    (unsandboxed) context rather than this iframe's."""
    components.html(
        f"""<script>
        try {{
          var t = localStorage.getItem({json.dumps(_REMEMBER_KEY)});
          if (t) {{
            var url = new URL(window.top.location.href);
            if (!url.searchParams.has('remember_token')) {{
              url.searchParams.set('remember_token', t);
              var a = window.top.document.createElement('a');
              a.href = url.toString();
              window.top.document.body.appendChild(a);
              a.click();
            }}
          }}
        }} catch (e) {{}}
        </script>""",
        height=0,
    )


_FEATURES = [
    ("document_scanner", "ניתוח קורות חיים חכם", "ה-AI סורק את קורות החיים שלכם ומחלץ את הפרטים אוטומטית"),
    ("tune", "התאמת מסמכים לכל משרה", "קורות חיים ומכתב מקדים מותאמים אישית, עם בדיקת עובדות"),
    ("view_kanban", "לוח מעקב מועמדויות", "מעקב ויזואלי אחר כל שלב בתהליך, מהגשה ועד הצעה"),
    ("forum", "סימולטור ראיונות", "תרגול ראיון עם דמות AI ומשוב מפורט בסוף"),
]

_STEPS = [
    ("1", "העלו קורות חיים", "העלו את קובץ ה-PDF או ה-Word הקיים שלכם לניתוח מהיר ומיפוי חוזקות מקצועיות."),
    ("2", "הדביקו תיאור משרה", "הדביקו את תיאור המשרה הרצויה במערכת לניתוח פערים מותאם."),
    ("3", "קבלו מסמכים מותאמים", "קבלו מסמכים מותאמים ותתחילו להגיש מועמדות בביטחון."),
]

_HERO_SVG = """
<svg viewBox="0 0 600 500" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/><stop offset="100%" stop-color="#f2f3ff"/>
    </linearGradient>
    <linearGradient id="primaryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d6efd"/><stop offset="100%" stop-color="#0052cc"/>
    </linearGradient>
    <linearGradient id="accentGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.25"/><stop offset="100%" stop-color="#0d6efd" stop-opacity="0.05"/>
    </linearGradient>
    <filter id="softShadow" x="-10%" y="-10%" width="130%" height="130%">
      <feDropShadow dx="0" dy="16" stdDeviation="20" flood-color="#0d6efd" flood-opacity="0.12"/>
    </filter>
    <filter id="badgeShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000000" flood-opacity="0.08"/>
    </filter>
  </defs>
  <circle cx="300" cy="250" r="180" fill="url(#accentGlow)"/>
  <g transform="translate(180, 70) rotate(-6)" opacity="0.7">
    <rect width="260" height="340" rx="16" fill="#f8faff" stroke="#e0e7ff" stroke-width="1.5"/>
    <rect x="24" y="28" width="60" height="10" rx="5" fill="#c7d2fe"/>
    <rect x="24" y="52" width="180" height="8" rx="4" fill="#e2e8f0"/>
    <rect x="24" y="70" width="140" height="8" rx="4" fill="#e2e8f0"/>
    <rect x="24" y="88" width="160" height="8" rx="4" fill="#e2e8f0"/>
  </g>
  <g transform="translate(130, 80)" filter="url(#softShadow)">
    <rect width="320" height="360" rx="16" fill="url(#cardGrad)" stroke="#dbeafe" stroke-width="2"/>
    <rect x="24" y="24" width="48" height="48" rx="12" fill="#eff6ff"/>
    <path d="M40 48v-14h16v14M44 34h8M44 39h8" stroke="#0d6efd" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="84" y="28" width="120" height="14" rx="7" fill="#1e293b"/>
    <rect x="84" y="48" width="80" height="10" rx="5" fill="#64748b"/>
    <line x1="24" y1="92" x2="296" y2="92" stroke="#e2e8f0" stroke-width="1"/>
    <rect x="24" y="112" width="272" height="60" rx="10" fill="#f0fdf4" stroke="#bbf7d0" stroke-width="1"/>
    <circle cx="54" cy="142" r="18" fill="#22c55e"/>
    <path d="M48 142l4 4 8-8" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="86" y="136" font-family="system-ui, sans-serif" font-size="13" font-weight="bold" fill="#15803d">98% התאמה למשרת היעד</text>
    <text x="86" y="154" font-family="system-ui, sans-serif" font-size="11" fill="#166534">ניתוח דרישות הושלם בהצלחה</text>
    <g transform="translate(24, 192)">
      <rect x="0" y="0" width="70" height="24" rx="6" fill="#e0e7ff"/>
      <text x="35" y="16" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#4338ca" text-anchor="middle">Product</text>
      <rect x="78" y="0" width="80" height="24" rx="6" fill="#e0e7ff"/>
      <text x="118" y="16" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#4338ca" text-anchor="middle">Strategy</text>
      <rect x="166" y="0" width="74" height="24" rx="6" fill="#e0e7ff"/>
      <text x="203" y="16" font-family="system-ui, sans-serif" font-size="11" font-weight="600" fill="#4338ca" text-anchor="middle">AI Ops</text>
    </g>
    <rect x="24" y="238" width="260" height="8" rx="4" fill="#cbd5e1"/>
    <rect x="24" y="254" width="220" height="8" rx="4" fill="#e2e8f0"/>
    <rect x="24" y="270" width="240" height="8" rx="4" fill="#e2e8f0"/>
    <rect x="24" y="286" width="180" height="8" rx="4" fill="#e2e8f0"/>
    <rect x="24" y="312" width="130" height="28" rx="6" fill="url(#primaryGrad)"/>
    <text x="89" y="330" font-family="system-ui, sans-serif" font-size="11" font-weight="bold" fill="#ffffff" text-anchor="middle">קורות חיים מוכנים</text>
  </g>
  <g transform="translate(40, 220)" filter="url(#badgeShadow)">
    <rect width="170" height="66" rx="14" fill="#ffffff" stroke="#e2e8f0" stroke-width="1"/>
    <circle cx="34" cy="33" r="16" fill="#eff6ff"/>
    <path d="M28 29h12a2 2 0 012 2v6a2 2 0 01-2 2h-7l-4 3v-3a2 2 0 01-1-2v-6a2 2 0 012-2z" fill="#0d6efd"/>
    <text x="60" y="28" font-family="system-ui, sans-serif" font-size="11" font-weight="bold" fill="#0f172a">סימולציית ראיון</text>
    <text x="60" y="44" font-family="system-ui, sans-serif" font-size="10" fill="#64748b">"ספר לי על אתגר..."</text>
  </g>
  <g transform="translate(400, 310)" filter="url(#badgeShadow)">
    <rect width="165" height="64" rx="14" fill="#ffffff" stroke="#e2e8f0" stroke-width="1"/>
    <circle cx="32" cy="32" r="16" fill="#fef3c7"/>
    <text x="32" y="38" font-family="system-ui, sans-serif" font-size="16" text-anchor="middle">🎯</text>
    <text x="58" y="28" font-family="system-ui, sans-serif" font-size="11" font-weight="bold" fill="#0f172a">הזמנה לראיון סופי</text>
    <text x="58" y="44" font-family="system-ui, sans-serif" font-size="10" font-weight="600" fill="#059669">התקבלה הרגע!</text>
  </g>
  <circle cx="110" cy="110" r="4" fill="#38bdf8"/>
  <path d="M120 70l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" fill="#0d6efd"/>
  <path d="M470 160l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="#38bdf8"/>
  <circle cx="490" cy="200" r="3" fill="#818cf8"/>
</svg>
"""


def landing_hero():
    text_col, illustration_col = st.columns([7, 5], gap="large")
    with text_col:
        st.markdown(
            f"""
            <div class="hero">
              <div class="hero-badge">
                <span class="msi">auto_awesome</span>
                <span>טכנולוגיית AI מהדור הבא למציאת עבודה</span>
              </div>
              <h1>פלטפורמת חיפוש העבודה החכמה שלך</h1>
              <p class="subhead">AI שמנתח את קורות החיים שלכם, מתאים אותם לכל משרה, ומכין
              אתכם לראיון — משלב החיפוש הראשון ועד קבלת ההצעה.</p>
              <div class="trust-row">
                <span><span class="msi">check_circle</span>ללא צורך בכרטיס אשראי</span>
                <span><span class="msi">check_circle</span>אבטחת מידע ופרטיות מלאה</span>
                <span><span class="msi">check_circle</span>התאמה מלאה לשוק הישראלי</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with illustration_col:
        st.markdown(f'<div class="hero-illustration">{_HERO_SVG}</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:center;max-width:640px;margin:3rem auto 1.6rem;">
          <div class="section-eyebrow">יתרונות מרכזיים</div>
          <div class="section-title">כל הכלים הדרושים כדי להתקבל לתפקיד הבא שלך</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cards = "".join(
        f'<div class="feature-card"><div class="icon-box"><span class="msi">{icon}</span></div>'
        f'<div class="title">{title}</div><div class="desc">{desc}</div></div>'
        for icon, title, desc in _FEATURES
    )
    st.markdown(f'<div class="feature-grid">{cards}</div>', unsafe_allow_html=True)


def how_it_works():
    st.markdown(
        """
        <div style="text-align:center;max-width:640px;margin:0 auto 1.8rem;">
          <div class="section-eyebrow">פשוט ומהיר</div>
          <div class="section-title">איך זה עובד?</div>
          <div class="section-sub">שלושה צעדים קלים בדרך למשרה הבאה שלכם</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    steps = "".join(
        f'<div class="step"><div class="num">{num}</div>'
        f'<div class="title">{title}</div><div class="desc">{desc}</div></div>'
        for num, title, desc in _STEPS
    )
    st.markdown(f'<div class="steps-row">{steps}</div>', unsafe_allow_html=True)


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
