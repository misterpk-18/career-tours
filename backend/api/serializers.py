"""Row serializers shared by the route modules.

These live outside any one blueprint because the same row shape is returned from
more than one endpoint, and the client compares the payloads. A project skill,
for example, is returned by both `POST /resumes/<id>/extract-skills` and
`GET /projects/<id>/skills`; if the two drifted, the page would render different
fields depending on which call happened to populate it.
"""


def serialize_project_skill(skill: dict) -> dict:
    return {
        "project_skill_id": str(skill["project_skill_id"]),
        "project_id": str(skill["project_id"]),
        "skill_id": str(skill["skill_id"]) if skill["skill_id"] is not None else None,
        "skill_name": skill["skill_name"],
        "proficiency_level": skill["proficiency_level"],
        "confidence_score": float(skill["confidence_score"]),
        "source": skill["source"],
        "created_at": skill["created_at"].isoformat(),
    }
