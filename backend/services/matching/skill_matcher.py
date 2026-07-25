from typing import Any, Dict, List, Optional, cast

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SkillMatcher:
    _model: Optional[SentenceTransformer] = None
    _embedding_cache: Dict[str, Any] = {}

    @classmethod
    def _get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")

        return cls._model

    @classmethod
    def _embed(cls, skills: List[str]) -> Dict[str, Any]:
        """Return embeddings for each skill name, keyed by name.

        Uncached names are encoded in a single batched ``model.encode`` call
        and stored in a process-wide cache, so any given skill string is only
        ever encoded once (student skills are reused across every occupation).
        """
        missing = [skill for skill in dict.fromkeys(skills) if skill not in cls._embedding_cache]

        if missing:
            model = cls._get_model()
            embeddings = model.encode(missing, convert_to_tensor=False, batch_size=64)

            for skill, embedding in zip(missing, embeddings):
                cls._embedding_cache[skill] = embedding

        return {skill: cls._embedding_cache[skill] for skill in skills}

    @classmethod
    def calculate_score(cls, student_skills, occupation_skills):
        occupation_names = [occupation_skill["skill_name"] for occupation_skill in occupation_skills]

        if not occupation_names or not student_skills:
            return {"score": 0.0, "skill_breakdown": []}

        embeddings = cls._embed(list(student_skills) + occupation_names)

        student_matrix = np.array([embeddings[skill] for skill in student_skills])
        occupation_matrix = np.array([embeddings[name] for name in occupation_names])

        # One vectorized pass: (num_occupation_skills x num_student_skills)
        # similarity matrix, then best-matching student skill per occupation skill.
        similarity_matrix = cosine_similarity(cast(Any, occupation_matrix), cast(Any, student_matrix))
        best_scores = similarity_matrix.max(axis=1)

        weighted_sum = 0.0
        total_weight = 0.0
        skill_breakdown = []

        for occupation_skill, best_score in zip(occupation_skills, best_scores):
            similarity = float(best_score)
            weight = float(occupation_skill["weight"])

            contribution = weight * similarity

            weighted_sum += contribution
            total_weight += weight

            skill_breakdown.append(
                {
                    "skill_name": occupation_skill["skill_name"],
                    "weight": weight,
                    "similarity": round(similarity, 4),
                    "contribution": round(contribution, 2),
                }
            )

        score = 0.0

        if total_weight > 0:
            score = round((weighted_sum / total_weight) * 100, 2)

        return {"score": score, "skill_breakdown": skill_breakdown}

    @classmethod
    def match_occupation(cls, student_skills, occupation, occupation_skills):
        result = cls.calculate_score(student_skills, occupation_skills)

        return {
            "occupation_id": occupation["occupation_id"],
            "occupation_name": occupation["occupation_name"],
            "score": result["score"],
            "skill_breakdown": result["skill_breakdown"],
        }
