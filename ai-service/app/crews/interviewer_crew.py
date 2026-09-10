"""PRD §3.5 Interviewer Agent: persona-driven mock interview + rubric feedback."""

from crewai import Agent, Crew, Task

from .json_utils import parse_json_output
from .llm import default_llm

_TECHNICAL_KEYWORDS = (
    "developer",
    "engineer",
    "programmer",
    "devops",
    "מפתח",
    "מהנדס",
    "תוכנה",
    "backend",
    "frontend",
    "fullstack",
    "data",
)
_PRODUCT_KEYWORDS = ("product", "מוצר")


def build_persona(job_title: str) -> dict:
    """Deterministic keyword heuristic — a 3-way classification doesn't need
    an LLM call, and this keeps interview start latency to one LLM call."""
    lowered = job_title.lower()
    if any(k in lowered for k in _PRODUCT_KEYWORDS):
        return {
            "role_title": "מנהל/ת מוצר בכיר/ה",
            "persona_prompt": "a senior product manager who cares about user impact, prioritization, and cross-functional collaboration",
        }
    if any(k in lowered for k in _TECHNICAL_KEYWORDS):
        return {
            "role_title": "מנהל/ת פיתוח טכנולוגי",
            "persona_prompt": "a technical engineering manager who probes for real hands-on depth, architecture judgment, and problem-solving",
        }
    return {
        "role_title": "מנהל/ת גיוס (HR)",
        "persona_prompt": "an HR hiring manager who focuses on motivation, culture fit, and behavioral (STAR-style) evidence",
    }


def _agent(persona: dict) -> Agent:
    return Agent(
        role=persona["role_title"],
        goal="Conduct a realistic, focused mock interview for this specific job and candidate.",
        backstory=f"You are {persona['persona_prompt']}, interviewing a candidate for a real open role.",
        llm=default_llm(),
        verbose=False,
    )


def run_next_question(persona: dict, job: dict, profile: dict, chat_history: list[dict]) -> str:
    agent = _agent(persona)
    history_text = (
        "\n".join(f"{m['role'].upper()}: {m['content']}" for m in chat_history) or "(interview just started)"
    )

    task = Task(
        description=(
            f"You are interviewing a candidate for {job['title']} at {job['company_name']}.\n"
            f"Job description:\n{job['description']}\n\n"
            f"Candidate's background (JSON):\n{profile}\n\n"
            f"Conversation so far:\n{history_text}\n\n"
            "Ask exactly ONE next interview question. If there was a previous answer, open with a "
            "brief one-sentence acknowledgement of it (do not score or critique it — feedback comes "
            "later) before asking the new question. Mix behavioral questions (that invite a STAR-"
            "style answer) with questions specific to this role and candidate's background. "
            "Return ONLY the question text (with the brief acknowledgement folded in if applicable) "
            "— no labels, no markdown, no commentary."
        ),
        expected_output="The interviewer's next line of dialogue, nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return str(crew.kickoff()).strip()


def run_feedback(job: dict, chat_history: list[dict]) -> dict:
    agent = Agent(
        role="Interview Coach",
        goal="Give the candidate a constructive, specific rubric-based evaluation of their mock interview.",
        backstory=(
            "A seasoned interview coach who evaluates transcripts against four criteria: "
            "communication clarity, technical/professional accuracy, fit for the specific role, "
            "and use of the STAR method — and always offers a concrete better phrasing, not just criticism."
        ),
        llm=default_llm(),
        verbose=False,
    )

    history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in chat_history)

    task = Task(
        description=(
            f"Evaluate this mock interview transcript for a {job['title']} role at {job['company_name']}.\n\n"
            f"Transcript:\n{history_text}\n\n"
            "Return ONLY a JSON object (no markdown, no commentary) with this exact shape:\n"
            "{\n"
            '  "overall_score": int (0-100),\n'
            '  "summary": str (2-3 sentences),\n'
            '  "strengths": [str],\n'
            '  "improvements": [str],\n'
            '  "per_question": [{"question": str, "answer": str, "feedback": str, '
            '"suggested_answer": str}]\n'
            "}\n\n"
            "Score against: communication clarity, technical/professional accuracy, fit for this "
            "specific role, and use of the STAR method where the question invited it. "
            "\"per_question\" must cover every question/answer pair in the transcript, each with "
            "specific feedback and a concretely better suggested_answer (not just \"be more "
            "specific\" — write out an example)."
        ),
        expected_output="A single JSON object matching the schema above, and nothing else.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return parse_json_output(str(crew.kickoff()))
