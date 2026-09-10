"""Plain Python control flow for the document pipeline.

Happy path:
  Tailoring → Text Editor → Design → Gatekeeper

On Gatekeeper FAIL, route_to decides the retry entry point:
  - tailoring → full cycle again (Tailoring → Editor → Design → Gatekeeper)
  - editor    → Editor → Design → Gatekeeper
  - designer  → Design ↔ Editor only (Design → Editor → re-render → Gatekeeper)

Pass/fail branching and the round cap stay explicit product rules (not CrewAI retries).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .design_crew import run_design
from .gatekeeper_crew import run_gatekeeper
from .tailoring_crew import run_tailoring
from .text_editor_crew import run_text_editor
from ..docx_generator import generate_resume_docx

MAX_ROUNDS = 3

Route = str  # "tailoring" | "editor" | "designer"


@dataclass
class OrchestrationResult:
    resume: dict
    cover_letter: str
    gatekeeper_status: str  # "PASS" | "TRUST_WARNING"
    violations: list[str]
    docx_bytes: bytes = field(repr=False, default=b"")
    template_id: str = "classic"


def run_tailoring_with_gatekeeper(
    core_profile: dict, job: dict, qna_answers: list[dict], tone: str
) -> OrchestrationResult:
    violations: list[str] = []
    route_to: Route = "tailoring"
    draft: dict = {"resume": {}, "cover_letter": ""}
    template_id = "classic"
    docx_bytes = b""

    for _round in range(1, MAX_ROUNDS + 1):
        draft, template_id, docx_bytes = _run_from_route(
            route_to=route_to,
            core_profile=core_profile,
            job=job,
            qna_answers=qna_answers,
            tone=tone,
            draft=draft,
            violations=violations,
        )

        check = run_gatekeeper(
            core_profile,
            qna_answers,
            draft,
            design_meta={"template_id": template_id, "design_notes": draft.get("design_notes", "")},
        )

        if check["status"] == "PASS":
            return OrchestrationResult(
                resume=draft["resume"],
                cover_letter=draft["cover_letter"],
                gatekeeper_status="PASS",
                violations=[],
                docx_bytes=docx_bytes,
                template_id=template_id,
            )

        violations = check.get("violations", [])
        route_to = check.get("route_to") or "tailoring"

    return OrchestrationResult(
        resume=draft["resume"],
        cover_letter=draft["cover_letter"],
        gatekeeper_status="TRUST_WARNING",
        violations=violations,
        docx_bytes=docx_bytes or generate_resume_docx(draft.get("resume") or {}, template_id),
        template_id=template_id,
    )


def _run_from_route(
    *,
    route_to: Route,
    core_profile: dict,
    job: dict,
    qna_answers: list[dict],
    tone: str,
    draft: dict,
    violations: list[str],
) -> tuple[dict, str, bytes]:
    """Execute the pipeline segment starting at route_to. Returns draft, template_id, docx_bytes."""
    feedback = violations or None

    if route_to == "tailoring":
        draft = run_tailoring(core_profile, job, qna_answers, tone, feedback)
        draft = run_text_editor(draft, None)
        return _design_stage(draft, job, None)

    if route_to == "editor":
        draft = run_text_editor(
            {"resume": draft["resume"], "cover_letter": draft["cover_letter"]},
            feedback,
        )
        return _design_stage(draft, job, None)

    # designer: only bounce between Design and Text Editor (no Tailoring).
    designed = run_design(
        {"resume": draft["resume"], "cover_letter": draft["cover_letter"]},
        job,
        feedback,
    )
    edited = run_text_editor(
        {"resume": designed["resume"], "cover_letter": designed["cover_letter"]},
        None,
    )
    # Re-apply the chosen template so the .docx matches final edited text.
    template_id = designed.get("template_id") or "classic"
    docx_bytes = generate_resume_docx(edited["resume"], template_id)
    return (
        {
            "resume": edited["resume"],
            "cover_letter": edited["cover_letter"],
            "design_notes": designed.get("design_notes", ""),
        },
        template_id,
        docx_bytes,
    )


def _design_stage(draft: dict, job: dict, design_violations: list[str] | None) -> tuple[dict, str, bytes]:
    designed = run_design(draft, job, design_violations)
    return (
        {
            "resume": designed["resume"],
            "cover_letter": designed["cover_letter"],
            "design_notes": designed.get("design_notes", ""),
        },
        designed.get("template_id") or "classic",
        designed["docx_bytes"],
    )
