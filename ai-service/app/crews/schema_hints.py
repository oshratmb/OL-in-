# Shared JSON-shape hints embedded in agent prompts. Kept in one place so the
# resume parser and the tailoring agent never drift into incompatible shapes
# (the frontend renders both through the same profile fields).

PROFILE_SCHEMA_HINT = (
    "{\n"
    '  "personal_info": {"name": str, "email": str, "phone": str, "location": str},\n'
    '  "professional_summary": str,\n'
    '  "work_experience": [{"company": str, "title": str, "start_date": str, '
    '"end_date": str, "bullets": [str]}],\n'
    '  "education": [{"institution": str, "degree": str, "field": str, "year": str}],\n'
    '  "skills": [str],\n'
    '  "projects": [{"name": str, "description": str}],\n'
    '  "languages": [str]\n'
    "}"
)
