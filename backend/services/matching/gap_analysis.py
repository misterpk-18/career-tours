"""Decide which of a career's skills the student already has.

This is a *classification*, not a score, and it was previously made entirely by
cosine distance at a 0.75 threshold. That is far above what this embedding
model produces for two spellings of the same skill, so almost nothing ever
matched: 0-4 of a career's 10-35 skills, which made ``missing_skills``
effectively the career's whole skill list and therefore the same list for every
student. Downstream that is the visible bug — course recommendations stop
depending on who the student is.

The fix is to stop asking the embedding a question that is not about
similarity. "Does this student have Django?" is a question about identity, and
the repo owns a vocabulary that answers it exactly. Cosine is kept only for
what identity cannot reach.
"""

from typing import Dict, List, Sequence

from services.skills.taxonomy import SkillTaxonomy


class GapAnalyzer:
    # Calibrated on raw cosine for all-MiniLM-L6-v2, which is also what the
    # reference open-source ESCO extractor uses with this same model, and where
    # published O*NET/ESCO mapping work settles. It is a fallback threshold: by
    # the time it is consulted, identity matching has already resolved the cases
    # it would get right anyway, so it only has to separate related-but-different
    # skills from unrelated ones.
    SIMILARITY_THRESHOLD = 0.60

    @staticmethod
    def is_same_skill(name: str, other: str, similarity: float) -> bool:
        """Whether two skill names refer to a skill the holder of one has.

        Identity first, cosine second, and the same rule wherever the question
        is asked — a career skill against a student's skills here, a course's
        syllabus against a career gap in the recommendation generator. Two
        places asking it two different ways is how a skill ends up simultaneously
        "missing" from a career and untaught by the course that teaches it.
        """
        identity = SkillTaxonomy.identity(name)
        other_identity = SkillTaxonomy.identity(other)

        # Both-None is not a match: it means neither name survived stripping,
        # not that they are the same skill.
        if identity is not None and identity == other_identity:
            return True

        return similarity >= GapAnalyzer.SIMILARITY_THRESHOLD

    @staticmethod
    def analyze(skill_breakdown: List[Dict], student_skills: Sequence[str]) -> Dict:
        """Split a career's skills into what the student has and what they lack.

        A career skill counts as held when it resolves to the same identity as
        one of the student's skills — same canonical taxonomy name, or the same
        name once wrapper wording is stripped — and otherwise when its cosine
        similarity clears the threshold.
        """
        student_identities = {
            identity
            for identity in (SkillTaxonomy.identity(skill) for skill in student_skills)
            if identity
        }

        matched_skills: List[str] = []
        missing_skills: List[str] = []

        for item in skill_breakdown:
            identity = SkillTaxonomy.identity(item["skill_name"])

            held = (identity is not None and identity in student_identities) or (
                item["similarity"] >= GapAnalyzer.SIMILARITY_THRESHOLD
            )

            (matched_skills if held else missing_skills).append(item["skill_name"])

        return {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
        }
