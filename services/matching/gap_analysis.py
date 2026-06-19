class GapAnalyzer:

    SIMILARITY_THRESHOLD = 0.75

    @staticmethod
    def analyze(skill_breakdown: list[dict]) -> dict:
        matched_skills: list[str] = []
        missing_skills: list[str] = []

        for item in skill_breakdown:
            if item["similarity"] >= GapAnalyzer.SIMILARITY_THRESHOLD:
                matched_skills.append(item["skill_name"])
            else:
                missing_skills.append(item["skill_name"])

        return {
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
        }
