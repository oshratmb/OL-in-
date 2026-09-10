"""PRD §3.5 Tailoring Agent: gap analysis, resume/cover-letter tailoring, and
revision-on-violations, as three tasks under one agent persona.
"""

import json

from crewai import Agent, Crew, Task

from .json_utils import parse_json_output
from .llm import default_llm
from .schema_hints import PROFILE_SCHEMA_HINT

_TONE_GUIDANCE = {
    "professional": "formal, professional, and measured",
    "enthusiastic": "enthusiastic, energetic, and personable while staying credible",
    "concise": "short, direct, and to the point — no filler",
}


def _agent() -> Agent:
    return Agent(
        role="Senior Recruiter & ATS Resume Strategist",
        goal=(
            "Tailor a candidate's resume and cover letter to a specific job, maximizing "
            "relevance while using only facts the candidate has actually provided."
        ),
        backstory=(
            "A senior technical recruiter who has screened thousands of resumes against "
            "applicant-tracking systems, and knows exactly which real, existing experience "
            "to surface for a given job — without ever inventing or exaggerating anything."
        ),
        llm=default_llm(),
        verbose=False,
    )


def run_gap_analysis(core_profile: dict, job_description: str) -> dict:
    agent = _agent()
    task = Task(
        description=(
            "Compare the candidate's profile against the job description below.\n\n"
            f"Candidate profile (JSON):\n{json.dumps(core_profile, ensure_ascii=False)}\n\n"
            f"Job description:\n{job_description}\n\n"
            "Return ONLY a JSON object (no markdown, no commentary) with this exact shape:\n"
            "{\n"
            '  "detected_title": str (the job title, extracted from the text),\n'
            '  "detected_company_name": str (the hiring company\'s name, extracted from the text; '
            'empty string if genuinely not mentioned),\n'
            '  "requirements": [{"requirement": str, "present": bool, "note": str}],\n'
            '  "match_percentage": int (0-100, your honest confidence the candidate fits),\n'
            '  "gap_questions": [{"id": str, "question": str}]\n'
            "}\n\n"
            "Rules: \"requirements\" lists the key requirements you extracted from the job "
            "description, each marked present=true only if clearly supported by the candidate's "
            "profile. \"gap_questions\" contains at most 5 short, specific questions that could "
            "close real gaps (e.g. asking about unlisted experience) — skip this entirely if the "
            "match is already strong. Never invent facts about the candidate."
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return parse_json_output(str(crew.kickoff()))


def run_tailoring(
    core_profile: dict,
    job: dict,
    qna_answers: list[dict],
    tone: str,
    violations: list[str] | None = None,
) -> dict:
    agent = _agent()
    answers_text = (
        "\n".join(f"- Q: {a['question']}\n  A: {a['answer'] or '(skipped)'}" for a in qna_answers)
        or "(none)"
    )
    revision_note = (
        (
            "\n\nA prior draft failed fact-checking for these reasons — fix them, using only "
            f"the source data above, and nothing else:\n" + "\n".join(f"- {v}" for v in violations)
        )
        if violations
        else ""
    )

    task = Task(
        description=(
            "Produce a tailored resume and a cover letter for this candidate and job.\n\n"
            f"Candidate profile (JSON, the ONLY source of truth for facts):\n"
            f"{json.dumps(core_profile, ensure_ascii=False)}\n\n"
            f"Candidate's answers to gap-filling questions (also usable as facts):\n{answers_text}\n\n"
            f"Job title: {job['title']}\nCompany: {job['company_name']}\n"
            f"Job description:\n{job['description_text']}\n\n"
            f"Cover letter tone: {_TONE_GUIDANCE.get(tone, tone)}."
            f"{revision_note}\n\n"
            "Return ONLY a JSON object (no markdown, no commentary) with this exact shape:\n"
            "{\n"
            f'  "resume": {PROFILE_SCHEMA_HINT},\n'
            '  "cover_letter": str\n'
            "}\n\n"
            "Rules for the resume: reorder/reword to emphasize what's relevant to this job, "
            "weave in job-description keywords the candidate genuinely has, rewrite bullets to "
            "highlight measurable outcomes where the source supports it. NEVER invent an employer, "
            "title, date, skill, or achievement that isn't in the candidate profile or answers "
            "above. Rules for the cover letter: 250-400 words, references specific real "
            "experience, matches the requested tone, addressed to the hiring team at the company."
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return parse_json_output(str(crew.kickoff()))
