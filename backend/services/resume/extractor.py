from typing import Optional
from uuid import UUID

from config.database import db
from repositories.project_skill_repository import ProjectSkillRepository
from repositories.student_skill_repository import StudentSkillRepository
from services.llm.openai_service import OpenAIService
from services.skills.normalizer import SkillNormalizer


class ResumeSkillExtractor:
    @staticmethod
    def existing_result(project_id: UUID, student_id: UUID) -> Optional[dict]:
        """Return the already-extracted skills for a project, or None.

        Extraction is an expensive, non-deterministic LLM call, so a second press of
        "Extract Skills" should hand back what is already stored rather than paying
        for it again (and risking a different answer, or an OpenAI quota error).

        It also reconciles the halves. student_skills used to be written in a second
        commit that could fail on its own, leaving a project with skills whose
        student rows were never created -- career matching reads student_skills, so
        those projects looked extracted but matched nothing. Re-upserting the
        catalog-matched rows here repairs that without another LLM call.
        """
        saved_skills = ProjectSkillRepository.get_by_project_id(project_id)

        if not saved_skills:
            return None

        matched = [skill for skill in saved_skills if skill["skill_id"] is not None]

        if matched:
            StudentSkillRepository.bulk_create(student_id, matched)
            db.session.commit()

        return {
            # The summary is a property of the LLM response, not of the stored rows,
            # so there is nothing to replay here.
            "summary": None,
            "skills_saved": len(matched),
            "additional_skills_saved": len(saved_skills) - len(matched),
            "skills": saved_skills,
            "reused": True,
        }

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

        # Both writes share one transaction: if the student_skills insert fails, the
        # project_skills rows must not survive on their own, or the two tables end up
        # describing different extractions.
        if mapped:
            ProjectSkillRepository.bulk_create(project_id, mapped)

        if matched:
            StudentSkillRepository.bulk_create(student_id, matched)

        if mapped or matched:
            db.session.commit()

        saved_skills = ProjectSkillRepository.get_by_project_id(project_id)

        return {
            "summary": profile.summary,
            "skills_saved": len(matched),
            "additional_skills_saved": len(mapped) - len(matched),
            "skills": saved_skills,
            "reused": False,
        }

