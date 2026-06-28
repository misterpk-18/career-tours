from typing import Optional
from uuid import UUID

from repositories.project_skill_repository import ProjectSkillRepository
from services.llm.openai_service import OpenAIService
from services.skills.normalizer import SkillNormalizer


class ResumeSkillExtractor:

    @staticmethod
    def extract_and_save(
        project_id: UUID,
        resume_text: str,
        questionnaire_answers: Optional[dict] = None,
    ) -> dict:
        llm = OpenAIService()

        profile = llm.extract_skills(
            resume_text,
            questionnaire_answers,
        )

        all_skills = (
            profile.technical_skills
            + profile.soft_skills
            + profile.domain_skills
        )

        normalized = SkillNormalizer.normalize_skill_list(
            all_skills
        )

        mapped = SkillNormalizer.map_to_skill_ids(
            normalized
        )

        if mapped:
            ProjectSkillRepository.bulk_create(
                project_id,
                mapped
            )

        saved_skills = ProjectSkillRepository.get_by_project_id(
            project_id
        )

        return {
            "summary": profile.summary,
            "skills_saved": len(mapped),
            "skills_skipped": len(normalized) - len(mapped),
            "skills": saved_skills,
        }