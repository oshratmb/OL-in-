"""Phase 1's single-agent crew. Seeds the pattern Phase 2 extends with the
Tailoring + Gatekeeper agents (multi-agent crew in the same `crews/` package).
"""

from crewai import Agent, Crew, Task

from .json_utils import parse_json_output
from .llm import default_llm
from .schema_hints import PROFILE_SCHEMA_HINT as _SCHEMA_HINT


def run_resume_parser(resume_text: str) -> dict:
    llm = default_llm()

    parser_agent = Agent(
        role="Resume Parser",
        goal="Extract a candidate's factual profile from raw resume text with zero invention.",
        backstory=(
            "A meticulous HR data analyst who converts unstructured resumes into clean, "
            "structured records without ever adding information that isn't in the source text."
        ),
        llm=llm,
        verbose=False,
    )

    extract_task = Task(
        description=(
            "Extract the candidate's profile from the resume text below and return ONLY a JSON "
            f"object (no markdown, no commentary) with this exact shape:\n{_SCHEMA_HINT}\n\n"
            "Rules: use only facts present in the text. Use an empty string/list for anything "
            "not present. Never invent employers, dates, or skills.\n\n"
            f"Resume text:\n{resume_text}"
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=parser_agent,
    )

    crew = Crew(agents=[parser_agent], tasks=[extract_task], verbose=False)
    result = crew.kickoff()
    return parse_json_output(str(result))
