from typing import Any, Optional, cast
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SkillMatcher:

    _model: Optional[SentenceTransformer] = None

    @classmethod
    def _get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")

        return cls._model

    @classmethod
    def get_similarity(
        cls,
        occupation_skill,
        student_skill
    ):
        model = cls._get_model()

        occupation_embedding = model.encode(
            occupation_skill,
            convert_to_tensor=False
        )

        student_embedding = model.encode(
            student_skill,
            convert_to_tensor=False
        )

        similarity = cosine_similarity(
            cast(Any, [occupation_embedding]),
            cast(Any, [student_embedding])
        )[0][0]

        return float(similarity)

    @classmethod
    def best_similarity(
        cls,
        occupation_skill,
        student_skills
    ):
        best_score = 0.0

        for student_skill in student_skills:
            similarity = cls.get_similarity(
                occupation_skill,
                student_skill
            )

            if similarity > best_score:
                best_score = similarity

        # if best_score < cls.SIMILARITY_THRESHOLD:
        #     return 0.0

        return best_score

    @classmethod
    def calculate_score(
        cls,
        student_skills,
        occupation_skills
    ):
        weighted_sum = 0.0
        total_weight = 0.0

        skill_breakdown = []

        for occupation_skill in occupation_skills:

            similarity = cls.best_similarity(
                occupation_skill["skill_name"],
                student_skills
            )

            contribution = (
                occupation_skill["weight"]
                * similarity
            )

            weighted_sum += contribution
            total_weight += occupation_skill["weight"]

            skill_breakdown.append({
                "skill_name": occupation_skill["skill_name"],
                "weight": occupation_skill["weight"],
                "similarity": round(
                    similarity,
                    4
                ),
                "contribution": round(
                    contribution,
                    2
                )
            })

        score = 0.0

        if total_weight > 0:
            score = round(
                (weighted_sum / total_weight)
                * 100,
                2
            )

        return {
            "score": score,
            "skill_breakdown": skill_breakdown
        }

    @classmethod
    def match_occupation(
        cls,
        student_skills,
        occupation,
        occupation_skills
    ):
        result = cls.calculate_score(
            student_skills,
            occupation_skills
        )

        return {
            "occupation_id":
                occupation["occupation_id"],
            "occupation_name":
                occupation["occupation_name"],
            "score":
                result["score"],
            "skill_breakdown":
                result["skill_breakdown"]
        }