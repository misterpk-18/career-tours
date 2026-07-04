from typing import Optional
from uuid import UUID

from repositories.project_skill_repository import ProjectSkillRepository
from repositories.student_skill_repository import StudentSkillRepository
from services.llm.openai_service import OpenAIService
from services.skills.normalizer import SkillNormalizer


class ResumeSkillExtractor:
    @staticmethod
    def extract_and_save(
        project_id: UUID,
        student_id: UUID,
        resume_text: str,
        questionnaire_answers: Optional[dict] = None,
    ) -> dict:
        llm = OpenAIService()

        profile = llm.extract_skills(
            resume_text,
            questionnaire_answers,
        )

        all_skills = profile.technical_skills + profile.soft_skills + profile.domain_skills

        normalized = SkillNormalizer.normalize_skill_list(all_skills)

        mapped = SkillNormalizer.map_skills(normalized)

        # project_skills captures every extracted skill, including additional
        # ones not in the master catalog (stored with skill_id = NULL).
        # student_skills only holds catalog-matched skills, where skill_id is
        # required and must not be NULL.
        matched = [skill for skill in mapped if skill["skill_id"] is not None]

        if mapped:
            ProjectSkillRepository.bulk_create(project_id, mapped)

        if matched:
            StudentSkillRepository.bulk_create(student_id, matched)

        saved_skills = ProjectSkillRepository.get_by_project_id(project_id)

        return {
            "summary": profile.summary,
            "skills_saved": len(matched),
            "additional_skills_saved": len(mapped) - len(matched),
            "skills": saved_skills,
        }

