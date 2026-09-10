"""Mirrors email_processing.py's pattern: business logic separated from the
router, so it's unit-testable without mocking a full request/response cycle.
"""

import json

from . import supabase_client
from .crews.interviewer_crew import build_persona, run_feedback, run_next_question

MAX_QUESTIONS = 5


def start_simulation(user_id: str, application_id: str) -> dict:
    application = supabase_client.get_application_with_job(application_id, user_id)
    if application is None:
        raise ValueError("Application not found")

    job = application["jobs"]
    profile = supabase_client.get_core_profile(user_id) or {}
    persona = build_persona(job["title"])

    question = run_next_question(persona, job, profile, [])
    chat_history = [{"role": "assistant", "content": question}]

    simulation_id = supabase_client.create_simulation(user_id, application_id, persona, chat_history)
    return {
        "simulation_id": simulation_id,
        "persona_role_title": persona["role_title"],
        "question": question,
    }


def submit_answer(simulation_id: str, user_id: str, answer_text: str) -> dict:
    simulation = supabase_client.get_simulation(simulation_id, user_id)
    if simulation is None:
        raise ValueError("Simulation not found")

    chat_history = simulation["chat_history"] + [{"role": "user", "content": answer_text}]

    assistant_turns = sum(1 for m in chat_history if m["role"] == "assistant")
    if assistant_turns >= MAX_QUESTIONS:
        supabase_client.update_simulation_chat(simulation_id, chat_history)
        return {"done": True, "question": None}

    application = supabase_client.get_application_with_job(simulation["application_id"], user_id)
    job = application["jobs"]
    profile = supabase_client.get_core_profile(user_id) or {}

    question = run_next_question(simulation["persona_details"], job, profile, chat_history)
    chat_history.append({"role": "assistant", "content": question})
    supabase_client.update_simulation_chat(simulation_id, chat_history)

    return {"done": False, "question": question}


def generate_feedback(simulation_id: str, user_id: str) -> dict:
    simulation = supabase_client.get_simulation(simulation_id, user_id)
    if simulation is None:
        raise ValueError("Simulation not found")

    application = supabase_client.get_application_with_job(simulation["application_id"], user_id)
    job = application["jobs"]

    try:
        report = run_feedback(job, simulation["chat_history"])
    except json.JSONDecodeError as exc:
        # Distinct from the ValueError("...not found") above — a "not found"
        # and an unparseable-AI-output are different failures (404 vs 502)
        # and must not collide under one except clause in the router.
        raise RuntimeError(f"AI feedback returned unparseable output: {exc}") from exc

    supabase_client.update_simulation_feedback(simulation_id, json.dumps(report))
    return report
