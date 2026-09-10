from unittest.mock import patch

from app.crews.orchestration import run_tailoring_with_gatekeeper

CORE_PROFILE = {"personal_info": {"name": "Jane Doe"}}
JOB = {"title": "Engineer", "company_name": "Acme", "description_text": "Build things"}
DRAFT = {"resume": {"personal_info": {"name": "Jane Doe"}}, "cover_letter": "Dear team..."}
EDITED = {"resume": {"personal_info": {"name": "Jane Doe"}}, "cover_letter": "Dear hiring team..."}
DESIGNED = {
    "resume": {"personal_info": {"name": "Jane Doe"}},
    "cover_letter": "Dear hiring team...",
    "template_id": "modern",
    "design_notes": "modern hierarchy",
    "docx_bytes": b"PK-fake-docx",
}


def _patch_pipeline():
    return (
        patch("app.crews.orchestration.run_gatekeeper"),
        patch("app.crews.orchestration.run_design", return_value=DESIGNED),
        patch("app.crews.orchestration.run_text_editor", return_value=EDITED),
        patch("app.crews.orchestration.run_tailoring", return_value=DRAFT),
        patch("app.crews.orchestration.generate_resume_docx", return_value=b"PK-regen"),
    )


def test_returns_immediately_on_first_pass():
    gk, design, editor, tailoring, _regen = _patch_pipeline()
    with gk as mock_gatekeeper, design as mock_design, editor as mock_editor, tailoring as mock_tailoring:
        mock_gatekeeper.return_value = {"status": "PASS", "violations": [], "route_to": None}

        result = run_tailoring_with_gatekeeper(CORE_PROFILE, JOB, [], "professional")

        assert result.gatekeeper_status == "PASS"
        assert result.resume == DESIGNED["resume"]
        assert result.cover_letter == DESIGNED["cover_letter"]
        assert result.docx_bytes == b"PK-fake-docx"
        assert result.template_id == "modern"
        assert result.violations == []
        assert mock_tailoring.call_count == 1
        assert mock_editor.call_count == 1
        assert mock_design.call_count == 1
        assert mock_gatekeeper.call_count == 1


def test_gives_up_after_three_rounds_with_trust_warning():
    gk, design, editor, tailoring, _regen = _patch_pipeline()
    with gk as mock_gatekeeper, design, editor, tailoring as mock_tailoring:
        mock_gatekeeper.return_value = {
            "status": "FAIL",
            "violations": ["invented a job title"],
            "route_to": "tailoring",
        }

        result = run_tailoring_with_gatekeeper(CORE_PROFILE, JOB, [], "professional")

        assert result.gatekeeper_status == "TRUST_WARNING"
        assert result.violations == ["invented a job title"]
        assert mock_tailoring.call_count == 3
        assert mock_gatekeeper.call_count == 3


def test_recovers_on_second_round_via_tailoring_route():
    gk, design, editor, tailoring, _regen = _patch_pipeline()
    with gk as mock_gatekeeper, design, editor, tailoring as mock_tailoring:
        mock_gatekeeper.side_effect = [
            {"status": "FAIL", "violations": ["invented a skill"], "route_to": "tailoring"},
            {"status": "PASS", "violations": [], "route_to": None},
        ]

        result = run_tailoring_with_gatekeeper(CORE_PROFILE, JOB, [], "professional")

        assert result.gatekeeper_status == "PASS"
        assert mock_tailoring.call_count == 2
        assert mock_gatekeeper.call_count == 2
        second_call = mock_tailoring.call_args_list[1]
        assert second_call.args[4] == ["invented a skill"]


def test_editor_route_skips_tailoring_and_redesigns():
    gk, design, editor, tailoring, _regen = _patch_pipeline()
    with gk as mock_gatekeeper, design as mock_design, editor as mock_editor, tailoring as mock_tailoring:
        mock_gatekeeper.side_effect = [
            {"status": "FAIL", "violations": ["awkward phrasing in summary"], "route_to": "editor"},
            {"status": "PASS", "violations": [], "route_to": None},
        ]

        result = run_tailoring_with_gatekeeper(CORE_PROFILE, JOB, [], "professional")

        assert result.gatekeeper_status == "PASS"
        # Round 1: tailor + edit + design. Round 2 (editor): edit + design only.
        assert mock_tailoring.call_count == 1
        assert mock_editor.call_count == 2
        assert mock_design.call_count == 2
        editor_retry = mock_editor.call_args_list[1]
        assert editor_retry.args[1] == ["awkward phrasing in summary"]


def test_designer_route_bounces_design_and_editor_only():
    gk, design, editor, tailoring, regen = _patch_pipeline()
    with (
        gk as mock_gatekeeper,
        design as mock_design,
        editor as mock_editor,
        tailoring as mock_tailoring,
        regen as mock_regen,
    ):
        mock_gatekeeper.side_effect = [
            {"status": "FAIL", "violations": ["template too dense"], "route_to": "designer"},
            {"status": "PASS", "violations": [], "route_to": None},
        ]

        result = run_tailoring_with_gatekeeper(CORE_PROFILE, JOB, [], "professional")

        assert result.gatekeeper_status == "PASS"
        assert mock_tailoring.call_count == 1
        # Round 1: 1 edit. Round 2 designer path: design → edit → regen docx.
        assert mock_editor.call_count == 2
        assert mock_design.call_count == 2
        assert mock_regen.call_count == 1
        design_retry = mock_design.call_args_list[1]
        assert design_retry.args[2] == ["template too dense"]
