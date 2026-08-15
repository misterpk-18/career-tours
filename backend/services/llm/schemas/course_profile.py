from typing import List, Literal

from pydantic import BaseModel


class CourseSkillCoverage(BaseModel):
    """One skill a course teaches, with how thoroughly it teaches it.

    ``category`` exists only for skills the master catalog has never seen: it is
    what ``skills.skill_category`` gets set to when the loader has to create the
    row. It is ignored for skills that already exist, whose category is whatever
    the catalog already says.
    """

    skill_name: str
    coverage_weight: float
    category: Literal["technical", "soft", "domain"]


class CourseProfile(BaseModel):
    """The parts of a Nipuna course knowledge profile that the DB stores.

    Mirrors the ``courses`` columns rather than the shape of the source PDF —
    the corpus carries far more (assessment splits, per-concept knowledge
    statements, remediation) than there is anywhere to put.
    """

    course_name: str
    description: str
    duration_hours: int
    level: str
    skills: List[CourseSkillCoverage]
