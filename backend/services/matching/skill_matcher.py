import os
from typing import Any, Dict, List, Optional, cast

import numpy as np
from huggingface_hub import InferenceClient

# Same model as the previous in-process sentence-transformers path, so the
# embeddings — and therefore every score — are unchanged. Calling it over the
# API keeps torch and its ~900MB of transitive dependencies out of the image.
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# The API accepts larger batches, but chunking bounds the payload size and keeps
# one oversized request from failing an entire recommendation run.
_BATCH_SIZE = 64


def _cosine_similarity(matrix_a: np.ndarray, matrix_b: np.ndarray) -> np.ndarray:
    """Row-wise cosine similarity, replacing ``sklearn.metrics.pairwise``.

    Kept local so scikit-learn (and the scipy it drags in) stay out of the
    dependency set; the result matches sklearn to within float32 noise.
    """
    norm_a = matrix_a / np.linalg.norm(matrix_a, axis=1, keepdims=True)
    norm_b = matrix_b / np.linalg.norm(matrix_b, axis=1, keepdims=True)

    return norm_a @ norm_b.T


class SkillMatcher:
    _client: Optional[InferenceClient] = None
    _embedding_cache: Dict[str, Any] = {}

    @classmethod
    def _get_client(cls) -> InferenceClient:
        if cls._client is None:
            cls._client = InferenceClient(api_key=os.getenv("HF_TOKEN"))

        return cls._client

    @classmethod
    def _embed(cls, skills: List[str]) -> Dict[str, Any]:
        """Return embeddings for each skill name, keyed by name.

        Uncached names are encoded in batched Hugging Face inference calls and
        stored in a process-wide cache, so any given skill string is only ever
        encoded once (student skills are reused across every occupation).
        """
        missing = [skill for skill in dict.fromkeys(skills) if skill not in cls._embedding_cache]

        if missing:
            client = cls._get_client()

            for start in range(0, len(missing), _BATCH_SIZE):
                batch = missing[start:start + _BATCH_SIZE]
                embeddings = client.feature_extraction(batch, model=_MODEL_NAME)

                for skill, embedding in zip(batch, np.asarray(embeddings, dtype="float32")):
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
        similarity_matrix = _cosine_similarity(cast(Any, occupation_matrix), cast(Any, student_matrix))
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
