from typing import List, Dict
from uuid import UUID

from repositories.occupation_repository import OccupationRepository
from repositories.project_skill_repository import ProjectSkillRepository
from services.llm.openai_service import OpenAIService
from services.matching.gap_analysis import GapAnalyzer
from services.matching.skill_matcher import SkillMatcher


class CareerRankingService:

    DEFAULT_TOP_N = 5

    @staticmethod
    def get_project_skill_names(project_id: UUID) -> List[str]:
        skills = ProjectSkillRepository.get_by_project_id(project_id)
        return [skill["skill_name"] for skill in skills]

    @staticmethod
    def recommend(
        project_id: UUID,
        top_n: int = DEFAULT_TOP_N,
        include_summary: bool = False,
    ) -> Dict:
        project_skills = CareerRankingService.get_project_skill_names(
            project_id
        )

        if not project_skills:
            raise ValueError("No skills found for project. Extract skills first.")

        occupations = OccupationRepository.get_all()
        matches: List[Dict] = []

        for occupation in occupations:
            occupation_skills = OccupationRepository.get_skills(
                occupation["occupation_id"]
            )

            if not occupation_skills:
                continue

            match = SkillMatcher.match_occupation(
                project_skills,
                occupation,
                occupation_skills,
            )

            gaps = GapAnalyzer.analyze(
                match["skill_breakdown"]
            )

            match["matched_skills"] = gaps["matched_skills"]
            match["missing_skills"] = gaps["missing_skills"]

            matches.append(match)

        matches.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        top_matches = matches[:top_n]

        for index, match in enumerate(
            top_matches,
            start=1
        ):
            match["rank"] = index

        if include_summary:
            llm = OpenAIService()

            for match in top_matches:
                match["summary"] = llm.generate_career_summary(
                    match["occupation_name"],
                    match["score"],
                    match["matched_skills"],
                    match["missing_skills"],
                )

        return {
            "project_id": project_id,
            "recommendations": top_matches,
        }