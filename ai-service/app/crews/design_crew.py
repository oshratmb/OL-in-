"""Design Agent: picks a resume layout template and produces a downloadable .docx.

Pipeline position: Tailoring → Text Editor → Design → Gatekeeper.

Definition
----------
Role: Resume Document Designer
Goal: Choose the best available resume template (built-in styles or files in
      design_kb/) and map the edited resume content into a real Word (.docx)
      document for download — without inventing facts or writing application code.
Backstory: A document designer who layouts resumes for hiring pipelines. Works
      from a fixed library of designed samples (DOCX templates and PDF references)
      rather than inventing one-off layouts from scratch.
Inputs: edited draft {resume, cover_letter}, job context, optional design violations
Outputs: {resume, cover_letter, template_id, design_notes} + rendered docx bytes
Knowledge base: ai-service/app/crews/design_kb/ (.docx fillable / .pdf inspiration)
Constraints: content facts unchanged; cover letter stays plain text; PDF refs
      inspire choice but final deliverable is always .docx
"""

from __future__ import annotations

import json

from crewai import Agent, Crew, Task

from ..docx_generator import generate_resume_docx, list_design_templates
from .json_utils import parse_json_output
from .llm import default_llm
from .schema_hints import PROFILE_SCHEMA_HINT


def _agent() -> Agent:
    return Agent(
        role="Resume Document Designer",
        goal=(
            "Select the best resume template from the available design library and map "
            "edited candidate content into a polished Word document — without changing facts."
        ),
        backstory=(
            "A document designer specializing in resume layouts for competitive hiring "
            "pipelines. Chooses from a curated library of designed DOCX templates and PDF "
            "visual references, matching layout density and hierarchy to the role and "
            "content length — never inventing new biographical facts."
        ),
        llm=default_llm(),
        verbose=False,
    )


def _templates_prompt_block() -> str:
    lines = []
    for t in list_design_templates():
        lines.append(f'- id="{t["id"]}" kind={t["kind"]}: {t["description"]}')
    return "\n".join(lines) or '- id="classic" kind=builtin: default clean layout'


def run_design(
    draft: dict,
    job: dict,
    violations: list[str] | None = None,
) -> dict:
    """Returns resume/cover_letter (unchanged facts), template_id, design_notes, docx_bytes."""
    agent = _agent()
    revision_note = (
        (
            "\n\nA prior design failed review for these reasons — pick a better template "
            "and/or adjust section emphasis for layout only (no new facts):\n"
            + "\n".join(f"- {v}" for v in violations)
        )
        if violations
        else ""
    )

    task = Task(
        description=(
            "Design a Word resume document for this candidate and job by selecting one "
            "template from the library below and confirming the resume JSON that will be "
            "laid out into that template.\n\n"
            f"Available templates:\n{_templates_prompt_block()}\n\n"
            f"Edited draft (JSON):\n{json.dumps(draft, ensure_ascii=False)}\n\n"
            f"Job title: {job.get('title', '')}\nCompany: {job.get('company_name', '')}\n"
            f"Job description:\n{job.get('description_text', '')}\n"
            f"{revision_note}\n\n"
            "Rules: choose exactly one template_id from the list. Prefer a DOCX template "
            "when the role/seniority/content length clearly fits one; otherwise use a "
            "builtin (classic/modern/compact). PDF entries are visual references only — "
            "if you pick one, note that rendering will fall back to classic. You may lightly "
            "reorder sections or shorten line breaks for layout fit, but NEVER invent or "
            "alter employers, titles, dates, skills, or achievements. Leave cover_letter "
            "text unchanged unless a listed design violation explicitly requires a tiny "
            "wording tweak for layout (prefer leaving it as-is).\n\n"
            "Return ONLY a JSON object (no markdown, no commentary) with this exact shape:\n"
            "{\n"
            f'  "resume": {PROFILE_SCHEMA_HINT},\n'
            '  "cover_letter": str,\n'
            '  "template_id": str,\n'
            '  "design_notes": str\n'
            "}"
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = parse_json_output(str(crew.kickoff()))

    template_id = result.get("template_id") or "classic"
    # Ensure cover letter survives even if the model omits it.
    if not result.get("cover_letter"):
        result["cover_letter"] = draft.get("cover_letter", "")
    if not result.get("resume"):
        result["resume"] = draft.get("resume", {})

    result["docx_bytes"] = generate_resume_docx(result["resume"], template_id)
    result["template_id"] = template_id
    result.setdefault("design_notes", "")
    return result
