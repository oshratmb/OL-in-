"""Gatekeeper Agent: fact-checks the draft and routes failures to the right agent.

Pipeline position: Tailoring → Text Editor → Design → Gatekeeper.

On FAIL, returns route_to so orchestration can retry at the correct stage:
  - tailoring — substance / job-fit / invented or missing material facts
  - editor    — phrasing, grammar, clarity, tone, ATS wording
  - designer  — template choice, layout density, visual hierarchy
"""

import json

from crewai import Agent, Crew, Task

from .json_utils import parse_json_output
from .llm import default_llm

_VALID_ROUTES = {"tailoring", "editor", "designer"}


def run_gatekeeper(
    core_profile: dict,
    qna_answers: list[dict],
    draft: dict,
    design_meta: dict | None = None,
) -> dict:
    agent = Agent(
        role="QA Auditor & Fact-Checker",
        goal=(
            "Catch any claim in a tailored resume/cover letter that isn't backed by the "
            "candidate's actual source data, judge textual and design quality issues, and "
            "route each failure to the agent that should fix it."
        ),
        backstory=(
            "A meticulous compliance analyst whose job is verifying that every company, "
            "title, date, skill, and achievement traces back to a real source — and who "
            "also flags wording problems for the copy editor and layout problems for the "
            "document designer. Rewording and reordering are fine; new facts are not."
        ),
        llm=default_llm(),
        verbose=False,
    )

    answers_text = (
        "\n".join(f"- Q: {a['question']}\n  A: {a['answer'] or '(skipped)'}" for a in qna_answers)
        or "(none)"
    )
    design_meta = design_meta or {}
    design_block = (
        f"Design metadata:\n"
        f"- template_id: {design_meta.get('template_id', '(none)')}\n"
        f"- design_notes: {design_meta.get('design_notes', '')}\n\n"
    )

    task = Task(
        description=(
            "Verify the draft below against the candidate's source data. Every company, title, "
            "date, skill, and quantified achievement in the draft must be traceable to the source "
            "profile or the answered questions — sentence by sentence. Also review wording quality "
            "and whether the chosen resume design/template fits the content and role.\n\n"
            f"Source candidate profile (JSON):\n{json.dumps(core_profile, ensure_ascii=False)}\n\n"
            f"Candidate's answers to gap-filling questions:\n{answers_text}\n\n"
            f"Draft to verify (JSON):\n{json.dumps(draft, ensure_ascii=False)}\n\n"
            f"{design_block}"
            "Return ONLY a JSON object (no markdown, no commentary) with this exact shape:\n"
            "{\n"
            '  "status": "PASS" or "FAIL",\n'
            '  "violations": [str],\n'
            '  "route_to": "tailoring" | "editor" | "designer" | null\n'
            "}\n\n"
            "Routing rules when status is FAIL (pick the single best owner for the dominant issue):\n"
            '- "tailoring": substance problems — invented/unsupported facts, job-fit gaps, '
            "missing material experience that should have been surfaced, wrong emphasis vs the job.\n"
            '- "editor": phrasing-only problems — grammar, clarity, tone, awkward wording, '
            "ATS phrasing, length/density of prose (facts are fine).\n"
            '- "designer": layout/template problems — poor template choice, hierarchy, density, '
            "or design notes that do not fit the content/role (facts and wording are fine).\n"
            "If multiple categories appear, prefer tailoring over editor over designer.\n"
            "When status is PASS, set route_to to null and violations to [].\n"
            "Rewording, reordering, and reasonable inference of impact from stated facts are NOT "
            "violations — only factually new information, clear wording defects, or clear design "
            "misfits are."
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = parse_json_output(str(crew.kickoff()))

    status = result.get("status", "FAIL")
    violations = result.get("violations") or []
    route_to = result.get("route_to")

    if status == "PASS":
        return {"status": "PASS", "violations": [], "route_to": None}

    if route_to not in _VALID_ROUTES:
        # Infer a safe default from violation text if the model omitted route_to.
        joined = " ".join(violations).lower()
        if any(k in joined for k in ("template", "layout", "design", "spacing", "visual")):
            route_to = "designer"
        elif any(k in joined for k in ("grammar", "phrasing", "wording", "tone", "clarity", "typo")):
            route_to = "editor"
        else:
            route_to = "tailoring"

    return {"status": "FAIL", "violations": violations, "route_to": route_to}
