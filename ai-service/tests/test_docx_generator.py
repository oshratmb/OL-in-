from app.docx_generator import generate_resume_docx, list_design_templates, resolve_template

RESUME = {
    "personal_info": {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "123",
        "location": "Tel Aviv",
    },
    "professional_summary": "Engineer",
    "work_experience": [
        {
            "company": "Acme",
            "title": "Developer",
            "start_date": "2020",
            "end_date": "2024",
            "bullets": ["Built APIs"],
        }
    ],
    "education": [{"institution": "Uni", "degree": "BSc", "field": "CS", "year": "2019"}],
    "skills": ["Python"],
    "projects": [{"name": "Tool", "description": "Does things"}],
    "languages": ["Hebrew", "English"],
}


def test_list_design_templates_includes_builtins():
    ids = {t["id"] for t in list_design_templates()}
    assert {"classic", "modern", "compact"} <= ids


def test_resolve_unknown_template_falls_back_to_classic():
    assert resolve_template("does-not-exist")["id"] == "classic"


def test_generate_each_builtin_returns_docx_bytes():
    for template_id in ("classic", "modern", "compact"):
        data = generate_resume_docx(RESUME, template_id)
        assert data[:2] == b"PK"  # zip/docx signature
