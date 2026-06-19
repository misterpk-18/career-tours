from uuid import UUID

from repositories.student_skill_repository import StudentSkillRepository
from services.llm.openai_service import OpenAIService
from services.skills.normalizer import SkillNormalizer


class ResumeSkillExtractor:

    @staticmethod
    def extract_and_save(
        student_id: UUID,
        resume_text: str,
        questionnaire_answers: dict | None = None,
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

        normalized = SkillNormalizer.normalize_skill_list(all_skills)
        mapped = SkillNormalizer.map_to_skill_ids(normalized)

        if mapped:
            StudentSkillRepository.bulk_create(student_id, mapped)

        saved_skills = StudentSkillRepository.get_by_student_id(student_id)

        return {
            "summary": profile.summary,
            "skills_saved": len(mapped),
            "skills_skipped": len(normalized) - len(mapped),
            "skills": saved_skills,
        }
