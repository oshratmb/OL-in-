"""PRD §3.5 Email Parser Agent ("Correspondence Analyst"). Collapses the
PRD's staged subject-parsing -> body-analysis -> correlation-matrix pipeline
into one LLM call that weighs all the same signals (subject, body, sender,
and each candidate application's company/title/status/applied-date) together
and returns a confidence-scored match directly.
"""

import json

from crewai import Agent, Crew, Task

from .json_utils import parse_json_output
from .llm import default_llm

_AUTO_LINK_THRESHOLD = 0.75


def run_email_parser(subject: str, sender: str, body_text: str, candidates: list[dict]) -> dict:
    agent = Agent(
        role="Correspondence Analyst",
        goal="Classify a recruiting email and identify which job application it belongs to.",
        backstory=(
            "A meticulous analyst who reads recruiter emails and matches them to the right "
            "job application, using every signal available — company name, dates, tone, and "
            "explicit references — rather than just keyword matching."
        ),
        llm=default_llm(),
        verbose=False,
    )

    candidates_text = (
        "\n".join(
            f"- id={c['application_id']}: {c['job_title']} at {c['company_name']} "
            f"(status={c['status']}, applied={c['applied_at']})"
            for c in candidates
        )
        or "(the candidate has no open applications)"
    )

    task = Task(
        description=(
            "An email arrived. Classify it and decide which (if any) of the candidate's open "
            "job applications it relates to.\n\n"
            f"Email subject: {subject}\nEmail sender: {sender}\nEmail body:\n{body_text}\n\n"
            f"Candidate's open applications:\n{candidates_text}\n\n"
            "Return ONLY a JSON object (no markdown, no commentary) with this exact shape:\n"
            "{\n"
            '  "company_name": str (the hiring company this email is from, best guess),\n'
            '  "classified_status": one of "applied", "phone_screen", "homework", '
            '"tech_interview", "offer", "rejected", "on_hold", or "" if the email is not a '
            "status update at all (e.g. a newsletter),\n"
            '  "matching_applications": [{"application_id": str, "confidence_score": float 0-1}] '
            "(only applications you have some evidence for, ranked highest confidence first, at "
            "most 3),\n"
            '  "recommended_action": "AUTO_LINK" if you are highly confident about exactly one '
            'match, "MANUAL_LINK_PROMPT" if there are one or more plausible-but-uncertain '
            'matches, or "NO_MATCH" if this email has nothing to do with any of the candidate\'s '
            "applications\n"
            "}"
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = parse_json_output(str(crew.kickoff()))

    # Defense in depth: never trust the LLM's own action label over the score
    # it actually reported (a bare AUTO_LINK with no matches would set the
    # application_id to nothing downstream, or worse, act on a stale value).
    matches = result.get("matching_applications", [])
    if not matches:
        result["recommended_action"] = "NO_MATCH"
    elif matches[0]["confidence_score"] < _AUTO_LINK_THRESHOLD or len(matches) > 1:
        if result.get("recommended_action") == "AUTO_LINK":
            result["recommended_action"] = "MANUAL_LINK_PROMPT"
    return result
