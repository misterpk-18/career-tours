from typing import List, Dict
from uuid import UUID

from repositories.occupation_repository import OccupationRepository
from repositories.project_skill_repository import ProjectSkillRepository
from services.jobs.progress import NULL_PROGRESS
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
        progress=NULL_PROGRESS,
    ) -> Dict:
        project_skills = CareerRankingService.get_project_skill_names(project_id)

        if not project_skills:
            raise ValueError("No skills found for project. Extract skills first.")

        occupations = OccupationRepository.get_all()

        # Every occupation's skills in one statement, and every occupation
        # scored in one pass. The scorer subtracts a per-student floor measured
        # across the whole catalog, so occupations cannot be scored one at a
        # time and still land on a comparable scale.
        skills_by_occupation = OccupationRepository.get_skills_by_occupation()
        scores = SkillMatcher.match_all(project_skills, skills_by_occupation)

        matches: List[Dict] = []

        progress.stage("matching", total=len(occupations))

        for occupation in occupations:
            progress.advance()

            result = scores.get(occupation["occupation_id"])

            if not result or not result["skill_breakdown"]:
                continue

            gaps = GapAnalyzer.analyze(result["skill_breakdown"], project_skills)

            matches.append(
                {
                    "occupation_id": occupation["occupation_id"],
                    "occupation_name": occupation["occupation_name"],
                    "score": result["score"],
                    "skill_breakdown": result["skill_breakdown"],
                    "matched_skills": gaps["matched_skills"],
                    "missing_skills": gaps["missing_skills"],
                }
            )

        matches.sort(key=lambda item: item["score"], reverse=True)
        top_matches = matches[:top_n]

        for index, match in enumerate(top_matches, start=1):
            match["rank"] = index

        if include_summary:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from services.llm.openai_service import OpenAIService
            llm = OpenAIService()

            progress.stage("career_summaries", total=len(top_matches))

            def _gen_summary(match):
                # Stored as JSON in llm_summaries.summary_text; the API parses it back
                # out for the client.
                match["summary"] = llm.generate_career_summary(
                    match["occupation_name"],
                    match["score"],
                    match["matched_skills"],
                    match["missing_skills"],
                ).model_dump_json()

            # submit/as_completed rather than executor.map: map returns a lazy
            # iterator, and this one was never consumed, so an exception inside
            # _gen_summary was discarded silently and the career shipped with no
            # summary and no log line. as_completed also lets progress advance
            # as each summary lands instead of all at once at the end.
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_gen_summary, match) for match in top_matches]

                for future in as_completed(futures):
                    future.result()
                    progress.advance()

        return {
            "project_id": project_id,
            "recommendations": top_matches,
        }
