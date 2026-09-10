"""Screen 2 — verify & edit the AI-parsed profile, then save to ``core_profiles``.
Mirrors profile.html + web/src/profile.js."""

import pandas as pd
import streamlit as st

import api
import nav
import ui

_BULLET_SEP = " | "


def _split_csv(value: str):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def _exp_frame(entries):
    rows = [
        {
            "חברה": e.get("company", ""),
            "תפקיד": e.get("title", ""),
            "מתאריך": e.get("start_date", ""),
            "עד תאריך": e.get("end_date", ""),
            "הישגים (מופרד ב- | )": _BULLET_SEP.join(e.get("bullets", []) or []),
        }
        for e in (entries or [])
    ]
    return pd.DataFrame(rows, columns=["חברה", "תפקיד", "מתאריך", "עד תאריך", "הישגים (מופרד ב- | )"])


def _edu_frame(entries):
    rows = [
        {
            "מוסד": e.get("institution", ""),
            "תואר": e.get("degree", ""),
            "תחום": e.get("field", ""),
            "שנה": e.get("year", ""),
        }
        for e in (entries or [])
    ]
    return pd.DataFrame(rows, columns=["מוסד", "תואר", "תחום", "שנה"])


def _proj_frame(entries):
    rows = [
        {"שם הפרויקט": e.get("name", ""), "תיאור": e.get("description", "")}
        for e in (entries or [])
    ]
    return pd.DataFrame(rows, columns=["שם הפרויקט", "תיאור"])


def _from_exp(df: pd.DataFrame):
    out = []
    for _, row in df.iterrows():
        company = str(row.get("חברה", "") or "").strip()
        title = str(row.get("תפקיד", "") or "").strip()
        if not company and not title:
            continue
        raw = str(row.get("הישגים (מופרד ב- | )", "") or "")
        bullets = [b.strip() for b in raw.replace("\n", "|").split("|") if b.strip()]
        out.append(
            {
                "company": company,
                "title": title,
                "start_date": str(row.get("מתאריך", "") or "").strip(),
                "end_date": str(row.get("עד תאריך", "") or "").strip(),
                "bullets": bullets,
            }
        )
    return out


def _from_edu(df: pd.DataFrame):
    out = []
    for _, row in df.iterrows():
        institution = str(row.get("מוסד", "") or "").strip()
        degree = str(row.get("תואר", "") or "").strip()
        if not institution and not degree:
            continue
        out.append(
            {
                "institution": institution,
                "degree": degree,
                "field": str(row.get("תחום", "") or "").strip(),
                "year": str(row.get("שנה", "") or "").strip(),
            }
        )
    return out


def _from_proj(df: pd.DataFrame):
    out = []
    for _, row in df.iterrows():
        name = str(row.get("שם הפרויקט", "") or "").strip()
        desc = str(row.get("תיאור", "") or "").strip()
        if not name and not desc:
            continue
        out.append({"name": name, "description": desc})
    return out


def render():
    pending = st.session_state.get("pending_profile")
    if not pending:
        nav.go(nav.ONBOARDING)

    parsed = pending["parsed_data"]
    personal = parsed.get("personal_info") or {}

    ui.header("אישור הפרופיל", "בדקו ותקנו את מה שה-AI חילץ מקורות החיים. זה יהיה הבסיס לכל התאמה עתידית.")
    ui.progress(100)

    tab_personal, tab_exp, tab_edu, tab_skills = st.tabs(
        ["פרטים אישיים", "ניסיון תעסוקתי", "השכלה", "כישורים ופרויקטים"]
    )

    with tab_personal:
        name = st.text_input("שם מלא", personal.get("name", ""))
        email = st.text_input("אימייל", personal.get("email", ""))
        phone = st.text_input("טלפון", personal.get("phone", ""))
        location = st.text_input("מיקום", personal.get("location", ""))
        summary = st.text_area(
            "תקציר מקצועי", parsed.get("professional_summary", ""), height=140
        )

    with tab_exp:
        st.caption("ניתן להוסיף/למחוק שורות. כל הישג בשורת החברה מופרד בתו | ")
        exp_df = st.data_editor(
            _exp_frame(parsed.get("work_experience", [])),
            num_rows="dynamic",
            key="exp_editor",
        )

    with tab_edu:
        edu_df = st.data_editor(
            _edu_frame(parsed.get("education", [])),
            num_rows="dynamic",
            key="edu_editor",
        )

    with tab_skills:
        skills = st.text_input(
            "כישורים (מופרדים בפסיק)", ", ".join(parsed.get("skills", []) or [])
        )
        languages = st.text_input(
            "שפות (מופרדים בפסיק)", ", ".join(parsed.get("languages", []) or [])
        )
        st.caption("פרויקטים")
        proj_df = st.data_editor(
            _proj_frame(parsed.get("projects", [])),
            num_rows="dynamic",
            key="proj_editor",
        )

    if st.button("שמירה והמשך", type="primary"):
        payload = {
            "user_id": api.current_user_id(),
            "original_resume_url": pending["storage_path"],
            "parsed_data": {
                "personal_info": {
                    "name": name.strip(),
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "location": location.strip(),
                },
                "professional_summary": summary.strip(),
                "work_experience": _from_exp(exp_df),
                "education": _from_edu(edu_df),
                "skills": _split_csv(skills),
                "languages": _split_csv(languages),
                "projects": _from_proj(proj_df),
            },
        }
        ok, data, _ = api.supabase_fetch(
            "POST",
            "/rest/v1/core_profiles?on_conflict=user_id",
            json_body=payload,
            headers={"Prefer": "resolution=merge-duplicates"},
        )
        if ok:
            st.session_state.pop("pending_profile", None)
            for key in ("exp_editor", "edu_editor", "proj_editor"):
                st.session_state.pop(key, None)
            nav.go(nav.DASHBOARD)
        else:
            st.error(data.get("detail") if isinstance(data, dict) else "שמירת הפרופיל נכשלה")
