from repositories.career_match_repository import CareerMatchRepository
from repositories.career_skill_gap_repository import CareerSkillGapRepository
from repositories.course_recommendation_repository import CourseRecommendationRepository
from repositories.course_repository import CourseRepository
from repositories.course_skill_repository import CourseSkillRepository
from repositories.llm_summary_repository import LLMSummaryRepository
from repositories.project_repository import ProjectRepository
from repositories.skill_repository import SkillRepository
from services.jobs.progress import NULL_PROGRESS
from services.llm.openai_service import OpenAIService
from services.matching.ranking import CareerRankingService


class RecommendationGenerator:
    TOP_CAREERS = 5
    TOP_COURSES = 5

    @staticmethod
    def generate(project_id, progress=NULL_PROGRESS):
        """Rebuild a project's recommendations from its extracted skills.

        `progress` is a ProgressReporter when this runs as a background job and
        a no-op otherwise, so the two paths execute identical code.

        Note that this is destructive before it is constructive: the four
        deletes below clear the project's existing recommendations before
        anything replaces them. An interrupted run therefore leaves the project
        with nothing, which is why every failure message says so.
        """
        project = ProjectRepository.get_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        ranking_result = CareerRankingService.recommend(
            project_id=project_id,
            top_n=RecommendationGenerator.TOP_CAREERS,
            include_summary=True,
            progress=progress,
        )
        recommendations = ranking_result["recommendations"]

        progress.stage("persisting", total=1)

        CareerMatchRepository.delete_by_project_id(project_id)
        CareerSkillGapRepository.delete_by_project_id(project_id)
        CourseRecommendationRepository.delete_by_project_id(project_id)
        LLMSummaryRepository.delete_by_project_id(project_id)

        CareerMatchRepository.bulk_create(
            student_id=project.student_id,
            project_id=project_id,
            recommendations=recommendations,
        )

        progress.advance()
        progress.stage("courses", total=len(recommendations))

        for recommendation in recommendations:
            if recommendation.get("summary"):
                LLMSummaryRepository.create(
                    student_id=project.student_id,
                    project_id=project.project_id,
                    occupation_id=recommendation["occupation_id"],
                    summary_type="career_summary",
                    summary_text=recommendation["summary"],
                )
            RecommendationGenerator._save_skill_gaps(project, recommendation)
            RecommendationGenerator._save_course_recommendations(project, recommendation)
            progress.advance(
                message=f"Courses for {recommendation['occupation_name']}"
            )

        return {
            "project_id": str(project_id),
            "careers_generated": len(recommendations),
        }

    @staticmethod
    def _save_skill_gaps(project, recommendation):
        occupation_id = recommendation["occupation_id"]
        missing_skill_names = recommendation["missing_skills"]
        gaps = []

        for skill_name in missing_skill_names:
            skill = SkillRepository.get_by_name(skill_name)
            if not skill:
                continue
            gaps.append(
                {
                    "skill_id": skill.skill_id,
                    "gap_percentage": 100,
                }
            )

        if gaps:
            CareerSkillGapRepository.bulk_create(
                student_id=project.student_id,
                project_id=project.project_id,
                occupation_id=occupation_id,
                skill_gaps=gaps,
            )

    @staticmethod
    def _save_course_recommendations(project, recommendation):
        occupation_id = recommendation["occupation_id"]
        missing_skill_names = recommendation["missing_skills"]
        course_scores = {}
        llm = OpenAIService()

        for skill_name in missing_skill_names:
            skill = SkillRepository.get_by_name(skill_name)
            if not skill:
                continue
            courses = CourseSkillRepository.get_by_skill_id(skill.skill_id)
            for course in courses:
                course_id = course["course_id"]
                score = float(course["coverage_weight"])
                course_scores[course_id] = course_scores.get(course_id, 0) + score

        ranked_courses = sorted(
            course_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        courses_to_process = []
        for rank, (course_id, score) in enumerate(
            ranked_courses[: RecommendationGenerator.TOP_COURSES],
            start=1,
        ):
            course = CourseRepository.get_by_id(course_id)
            if not course:
                continue

            course_skills = CourseSkillRepository.get_by_course_id(course_id)
            covered_skills = [s["skill_name"] for s in course_skills]
            courses_to_process.append((course_id, score, rank, course["course_name"], covered_skills))

        recommendations_to_save = []
        if courses_to_process:
            from concurrent.futures import ThreadPoolExecutor

            def _process_course(item):
                course_id, score, rank, course_name, covered_skills = item
                course_summary = llm.generate_course_summary(
                    course_name=course_name,
                    occupation_name=recommendation["occupation_name"],
                    covered_skills=covered_skills,
                ).model_dump_json()
                coverage_pct = min(score, 100.0)
                return {
                    "course_id": course_id,
                    "coverage_percentage": round(coverage_pct, 2),
                    "rank": rank,
                    "summary": course_summary,
                }

            with ThreadPoolExecutor(max_workers=5) as executor:
                recommendations_to_save = list(executor.map(_process_course, courses_to_process))

        if recommendations_to_save:
            CourseRecommendationRepository.bulk_create(
                student_id=project.student_id,
                project_id=project.project_id,
                occupation_id=occupation_id,
                recommendations=recommendations_to_save,
            )

            for rec in recommendations_to_save:
                LLMSummaryRepository.create(
                    student_id=project.student_id,
                    project_id=project.project_id,
                    occupation_id=occupation_id,
                    course_id=rec["course_id"],
                    summary_type="course_summary",
                    summary_text=rec["summary"],
                )
