"""Text Editing Agent: polishes tailored resume + cover-letter copy.

Pipeline position: Tailoring → Text Editor → Design → Gatekeeper.

Definition
----------
Role: Senior Resume Copy Editor
Goal: Improve grammar, clarity, density, ATS phrasing, length, and tone
      consistency of an already-tailored resume and cover letter — without
      inventing, exaggerating, or dropping any factual claim.
Backstory: A professional editor who has polished thousands of ATS-facing
      resumes. Obsessive about verbs, scannability, and measurable wording,
      but never invents employers, titles, dates, skills, or achievements.
Inputs: draft {resume, cover_letter}, optional Gatekeeper phrasing violations
Outputs: same JSON shape as Tailoring ({resume, cover_letter}), facts unchanged
Constraints: zero new facts (same bar as Gatekeeper); rewording/reordering only
"""

import json

from crewai import Agent, Crew, Task

from .json_utils import parse_json_output
from .llm import default_llm
from .schema_hints import PROFILE_SCHEMA_HINT


def _agent() -> Agent:
    return Agent(
        role="Senior Resume Copy Editor",
        goal=(
            "Polish resume and cover-letter wording for grammar, clarity, ATS density, "
            "length, and tone — without adding or changing any facts."
        ),
        backstory=(
            "A senior copy editor specializing in resumes and cover letters for applicant "
            "tracking systems. Improves verbs, scannability, and measurable phrasing, but "
            "never invents or exaggerates employers, titles, dates, skills, or achievements."
        ),
        llm=default_llm(),
        verbose=False,
    )


def run_text_editor(
    draft: dict,
    violations: list[str] | None = None,
) -> dict:
    agent = _agent()
    revision_note = (
        (
            "\n\nA prior draft failed fact-checking / quality review for these phrasing "
            "issues — fix only the wording problems listed, without introducing new facts:\n"
            + "\n".join(f"- {v}" for v in violations)
        )
        if violations
        else ""
    )

    task = Task(
        description=(
            "Edit the tailored resume and cover letter below for textual quality.\n\n"
            f"Draft (JSON):\n{json.dumps(draft, ensure_ascii=False)}\n"
            f"{revision_note}\n\n"
            "Improve: grammar, spelling, clarity, concision, ATS keyword density where "
            "already supported by the draft, bullet scannability, parallel structure, and "
            "cover-letter flow/tone consistency. Shorten filler; strengthen weak verbs when "
            "the underlying fact already supports it.\n\n"
            "Hard rules: NEVER invent or remove an employer, title, date, skill, project, "
            "language, or achievement. NEVER add quantified metrics that are not already "
            "present. Rewording and light reordering of bullets/sections is allowed.\n\n"
            "Return ONLY a JSON object (no markdown, no commentary) with this exact shape:\n"
            "{\n"
            f'  "resume": {PROFILE_SCHEMA_HINT},\n'
            '  "cover_letter": str\n'
            "}"
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return parse_json_output(str(crew.kickoff()))
