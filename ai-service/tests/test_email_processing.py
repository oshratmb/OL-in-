from unittest.mock import patch

from app.email_processing import process_incoming_email

CANDIDATES = [
    {
        "application_id": "app-1",
        "job_title": "Backend Engineer",
        "company_name": "Acme",
        "status": "applied",
        "applied_at": "2026-01-01T00:00:00Z",
    }
]


@patch("app.email_processing.supabase_client.update_application_status")
@patch("app.email_processing.supabase_client.insert_email")
@patch("app.email_processing.supabase_client.list_candidate_applications")
@patch("app.email_processing.run_email_parser")
def test_auto_link_sets_application_id_and_updates_status(
    mock_parser, mock_candidates, mock_insert, mock_update_status
):
    mock_candidates.return_value = CANDIDATES
    mock_parser.return_value = {
        "company_name": "Acme",
        "classified_status": "phone_screen",
        "matching_applications": [{"application_id": "app-1", "confidence_score": 0.95}],
        "recommended_action": "AUTO_LINK",
    }
    mock_insert.return_value = "email-1"

    result = process_incoming_email("user-1", "Interview?", "hr@acme.com", "Let's schedule a call")

    assert result == {"email_id": "email-1", "application_id": "app-1", "recommended_action": "AUTO_LINK"}
    mock_insert.assert_called_once()
    assert mock_insert.call_args.kwargs["application_id"] == "app-1"
    mock_update_status.assert_called_once_with("app-1", "phone_screen")


@patch("app.email_processing.supabase_client.update_application_status")
@patch("app.email_processing.supabase_client.insert_email")
@patch("app.email_processing.supabase_client.list_candidate_applications")
@patch("app.email_processing.run_email_parser")
def test_manual_link_prompt_leaves_application_unlinked(
    mock_parser, mock_candidates, mock_insert, mock_update_status
):
    mock_candidates.return_value = CANDIDATES
    mock_parser.return_value = {
        "company_name": "Acme",
        "classified_status": "",
        "matching_applications": [{"application_id": "app-1", "confidence_score": 0.4}],
        "recommended_action": "MANUAL_LINK_PROMPT",
    }
    mock_insert.return_value = "email-2"

    result = process_incoming_email("user-1", "Update", "hr@acme.com", "Some ambiguous update")

    assert result["application_id"] is None
    assert mock_insert.call_args.kwargs["application_id"] is None
    mock_update_status.assert_not_called()


@patch("app.email_processing.supabase_client.update_application_status")
@patch("app.email_processing.supabase_client.insert_email")
@patch("app.email_processing.supabase_client.list_candidate_applications")
@patch("app.email_processing.run_email_parser")
def test_no_match_stores_nothing(mock_parser, mock_candidates, mock_insert, mock_update_status):
    mock_candidates.return_value = CANDIDATES
    mock_parser.return_value = {
        "company_name": "",
        "classified_status": "",
        "matching_applications": [],
        "recommended_action": "NO_MATCH",
    }

    result = process_incoming_email("user-1", "Weekly newsletter", "news@example.com", "...")

    assert result is None
    mock_insert.assert_not_called()
    mock_update_status.assert_not_called()


@patch("app.email_processing.supabase_client.update_application_status")
@patch("app.email_processing.supabase_client.insert_email")
@patch("app.email_processing.supabase_client.list_candidate_applications")
@patch("app.email_processing.run_email_parser")
def test_duplicate_gmail_message_is_skipped(mock_parser, mock_candidates, mock_insert, mock_update_status):
    mock_candidates.return_value = CANDIDATES
    mock_parser.return_value = {
        "company_name": "Acme",
        "classified_status": "rejected",
        "matching_applications": [{"application_id": "app-1", "confidence_score": 0.9}],
        "recommended_action": "AUTO_LINK",
    }
    mock_insert.return_value = None  # insert_email signals a duplicate this way

    result = process_incoming_email(
        "user-1", "Update", "hr@acme.com", "...", gmail_message_id="msg-123"
    )

    assert result is None
    mock_update_status.assert_not_called()
