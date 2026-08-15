"""Score a student's skills against every occupation.

Three properties this scorer is built to have, each of which the previous one
lacked:

* **A career is scored on what it requires.** ESCO marks 5,150 of its 8,114
  career/skill pairs optional, and they average weight 31, so they carried 44%
  of every career's total weight. Scoring them alongside the essential ones
  meant a career's rank was driven mostly by skills nobody needs to have.
* **Weight is used as a preference, not a tiebreak.** The weights are bunched
  (a career's strongest and weakest skill are rarely more than 3x apart), so a
  linear weighting is nearly a flat average. Squaring spreads them back out.
* **Zero means "no overlap".** The per-occupation-skill score is a max over the
  student's skills, and a max over more draws is systematically bigger — 40
  unrelated padding skills lifted every career from 30% to 50% without changing
  anything about the student's actual fit. Subtracting a per-student floor, and
  rescaling what is left, is what makes a score comparable between two students
  who listed different numbers of skills.
"""

import os
from typing import Any, Dict, List, Optional, Sequence, cast

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
    def similarities(cls, names: Sequence[str], other_names: Sequence[str]) -> np.ndarray:
        """Cosine similarity of every ``names`` entry against every other one.

        ``(len(names) x len(other_names))``. The general form of what scoring
        uses internally, exposed because course selection has to ask the same
        question about a different pair of lists.
        """
        if not names or not other_names:
            return np.zeros((len(names), len(other_names)), dtype="float32")

        embeddings = cls._embed(list(names) + list(other_names))

        matrix = np.array([embeddings[name] for name in names])
        other_matrix = np.array([embeddings[name] for name in other_names])

        return _cosine_similarity(cast(Any, matrix), cast(Any, other_matrix))

    @staticmethod
    def _scoring_weight(occupation_skill: Dict) -> float:
        """How much an occupation skill counts toward the score.

        ``(weight / 100) ** 2``, or zero for a skill ESCO marks optional.

        Squaring is the whole of the weighting change. ESCO's weights sit in a
        narrow band, so dividing by their sum turns a linear weighting into
        something very close to an unweighted mean — a career's defining skill
        and its incidental one land within a few points of each other. Squaring
        restores the ordering the weights were meant to express without needing
        a hand-tuned curve.

        A NULL ``relation_type`` counts as essential. The 32 occupations that
        predate the ESCO import have no marking to read, and treating an
        unmarked skill as optional would score those careers on nothing at all.
        """
        if (occupation_skill.get("relation_type") or "essential") != "essential":
            return 0.0

        weight = float(occupation_skill["weight"]) / 100.0

        return weight * weight

    @classmethod
    def _floor(cls, best_by_name: Dict[str, float]) -> float:
        """The similarity this student would get from an unrelated skill.

        ``best_by_name`` is the student's best cosine against *every* skill any
        occupation asks for — some thousands of them, of which only a handful
        relate to this student. Its mean is therefore a direct measurement of
        the student's background similarity: what the max-over-student-skills
        returns when there is nothing genuinely matching to find.

        It has to be measured per student rather than fixed, because it is a
        function of how many skills they listed, not of how good they are.
        """
        if not best_by_name:
            return 0.0

        return float(np.mean(list(best_by_name.values())))

    @classmethod
    def match_all(
        cls,
        student_skills: Sequence[str],
        occupation_skills_by_id: Dict[Any, List[Dict]],
    ) -> Dict[Any, Dict]:
        """Score every occupation at once, keyed by ``occupation_id``.

        Deliberately not a per-occupation call in a loop: the floor is defined
        over the union of all occupation skills, so a single occupation cannot
        be scored on its own scale. Embedding and comparing in one pass is also
        what keeps this to one similarity matrix instead of 267 of them.
        """
        occupation_names = sorted(
            {
                occupation_skill["skill_name"]
                for occupation_skills in occupation_skills_by_id.values()
                for occupation_skill in occupation_skills
            }
        )

        student_names = list(dict.fromkeys(student_skills))

        if not occupation_names or not student_names:
            return {
                occupation_id: {"score": 0.0, "skill_breakdown": []}
                for occupation_id in occupation_skills_by_id
            }

        embeddings = cls._embed(student_names + occupation_names)

        student_matrix = np.array([embeddings[name] for name in student_names])
        occupation_matrix = np.array([embeddings[name] for name in occupation_names])

        # One vectorized pass over the whole catalog: (num_distinct_occupation_skills
        # x num_student_skills), then the best-matching student skill per occupation
        # skill. Every occupation below reads its rows out of this.
        similarity_matrix = _cosine_similarity(cast(Any, occupation_matrix), cast(Any, student_matrix))
        best_by_name = {
            name: float(best)
            for name, best in zip(occupation_names, similarity_matrix.max(axis=1))
        }

        floor = cls._floor(best_by_name)
        headroom = max(1.0 - floor, 1e-6)

        return {
            occupation_id: cls._score_occupation(occupation_skills, best_by_name, floor, headroom)
            for occupation_id, occupation_skills in occupation_skills_by_id.items()
        }

    @classmethod
    def _score_occupation(
        cls,
        occupation_skills: List[Dict],
        best_by_name: Dict[str, float],
        floor: float,
        headroom: float,
    ) -> Dict:
        weighted_sum = 0.0
        total_weight = 0.0
        skill_breakdown = []

        for occupation_skill in occupation_skills:
            similarity = best_by_name.get(occupation_skill["skill_name"], 0.0)

            # What is left of the similarity once the student's background level
            # is removed, on a 0-1 scale. Clamped at zero: a skill the student
            # matches *worse* than they match an arbitrary skill is no evidence
            # against them, it is just noise.
            adjusted = max(0.0, (similarity - floor) / headroom)

            weight = cls._scoring_weight(occupation_skill)
            contribution = weight * adjusted

            weighted_sum += contribution
            total_weight += weight

            skill_breakdown.append(
                {
                    "skill_name": occupation_skill["skill_name"],
                    "relation_type": occupation_skill.get("relation_type") or "essential",
                    "weight": float(occupation_skill["weight"]),
                    # Raw cosine, not the adjusted value. Gap analysis compares
                    # it against a threshold calibrated on raw cosine, and the
                    # floor is a property of the student rather than of this
                    # pairing.
                    "similarity": round(similarity, 4),
                    "adjusted_similarity": round(adjusted, 4),
                    "scoring_weight": round(weight, 4),
                    "contribution": round(contribution, 4),
                }
            )

        score = 0.0

        # total_weight is zero only when every one of the occupation's skills is
        # optional, which the ESCO import cannot produce (its thinnest career has
        # 3 essential skills) but a hand-edited row could.
        if total_weight > 0:
            score = round((weighted_sum / total_weight) * 100, 2)

        return {"score": score, "skill_breakdown": skill_breakdown}
