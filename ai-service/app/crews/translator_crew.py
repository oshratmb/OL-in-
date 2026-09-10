"""PRD §2.8: on-demand translation/rewrite of an already-generated, already
Gatekeeper-verified resume + cover letter. No fact-checking needed here."""

import json

from crewai import Agent, Crew, Task

from .json_utils import parse_json_output
from .llm import default_llm
from .schema_hints import PROFILE_SCHEMA_HINT

_LANGUAGE_NAMES = {"he": "Hebrew", "en": "English"}


def run_translation(resume: dict, cover_letter: str, target_language: str) -> dict:
    language_name = _LANGUAGE_NAMES.get(target_language, target_language)
    agent = Agent(
        role="Professional Resume Translator",
        goal=f"Translate and naturally localize a resume and cover letter into {language_name}.",
        backstory=(
            "A bilingual professional translator specializing in resumes and cover letters, "
            "who adapts phrasing to read naturally in the target language rather than "
            "translating word-for-word."
        ),
        llm=default_llm(),
        verbose=False,
    )

    task = Task(
        description=(
            f"Translate the resume and cover letter below into {language_name}. Keep the same "
            "facts, structure, and meaning — only the language changes. Adapt idioms/phrasing to "
            "read naturally to a native speaker; do not translate literally word-for-word.\n\n"
            f"Resume (JSON):\n{json.dumps(resume, ensure_ascii=False)}\n\n"
            f"Cover letter:\n{cover_letter}\n\n"
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
