from unittest.mock import patch

from app.crews.interviewer_crew import build_persona
from app.simulation_service import MAX_QUESTIONS, submit_answer

APPLICATION = {"id": "app-1", "jobs": {"title": "Backend Engineer", "company_name": "Acme", "description": "..."}}


def _chat_history(assistant_count: int) -> list[dict]:
    history = []
    for i in range(assistant_count):
        history.append({"role": "assistant", "content": f"Question {i + 1}"})
        history.append({"role": "user", "content": f"Answer {i + 1}"})
    return history


def test_build_persona_technical_title():
    assert build_persona("Senior Backend Engineer")["role_title"] == "מנהל/ת פיתוח טכנולוגי"


def test_build_persona_product_title():
    assert build_persona("Product Manager")["role_title"] == "מנהל/ת מוצר בכיר/ה"


def test_build_persona_defaults_to_hr():
    assert build_persona("Office Coordinator")["role_title"] == "מנהל/ת גיוס (HR)"


@patch("app.simulation_service.supabase_client.update_simulation_chat")
@patch("app.simulation_service.supabase_client.get_application_with_job")
@patch("app.simulation_service.supabase_client.get_core_profile")
@patch("app.simulation_service.run_next_question")
@patch("app.simulation_service.supabase_client.get_simulation")
def test_submit_answer_returns_next_question_before_cap(
    mock_get_sim, mock_run_question, mock_profile, mock_get_app, mock_update_chat
):
    mock_get_sim.return_value = {
        "application_id": "app-1",
        "persona_details": {"role_title": "x", "persona_prompt": "y"},
        "chat_history": _chat_history(2),  # 2 of 5 questions asked so far
    }
    mock_get_app.return_value = APPLICATION
    mock_profile.return_value = {}
    mock_run_question.return_value = "Question 3"

    result = submit_answer("sim-1", "user-1", "my answer")

    assert result == {"done": False, "question": "Question 3"}
    mock_run_question.assert_called_once()
    mock_update_chat.assert_called_once()


@patch("app.simulation_service.supabase_client.update_simulation_chat")
@patch("app.simulation_service.supabase_client.get_application_with_job")
@patch("app.simulation_service.supabase_client.get_core_profile")
@patch("app.simulation_service.run_next_question")
@patch("app.simulation_service.supabase_client.get_simulation")
def test_submit_answer_stops_at_cap_without_asking_again(
    mock_get_sim, mock_run_question, mock_profile, mock_get_app, mock_update_chat
):
    mock_get_sim.return_value = {
        "application_id": "app-1",
        "persona_details": {"role_title": "x", "persona_prompt": "y"},
        "chat_history": _chat_history(MAX_QUESTIONS - 1) + [{"role": "assistant", "content": "Question 5"}],
    }

    result = submit_answer("sim-1", "user-1", "final answer")

    assert result == {"done": True, "question": None}
    mock_run_question.assert_not_called()
    mock_get_app.assert_not_called()  # no need to load job context if we're not asking anything
    mock_update_chat.assert_called_once()


@patch("app.simulation_service.supabase_client.update_simulation_chat")
@patch("app.simulation_service.supabase_client.get_application_with_job")
@patch("app.simulation_service.supabase_client.get_core_profile")
@patch("app.simulation_service.run_next_question")
@patch("app.simulation_service.supabase_client.get_simulation")
def test_submit_answer_stays_done_if_called_again_after_cap(
    mock_get_sim, mock_run_question, mock_profile, mock_get_app, mock_update_chat
):
    mock_get_sim.return_value = {
        "application_id": "app-1",
        "persona_details": {"role_title": "x", "persona_prompt": "y"},
        "chat_history": _chat_history(MAX_QUESTIONS),  # already fully answered
    }

    result = submit_answer("sim-1", "user-1", "an extra message after done")

    assert result == {"done": True, "question": None}
    mock_run_question.assert_not_called()
