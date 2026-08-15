from repositories.career_match_repository import CareerMatchRepository
from repositories.career_skill_gap_repository import CareerSkillGapRepository
from repositories.course_recommendation_repository import CourseRecommendationRepository
from repositories.course_repository import CourseRepository
from repositories.course_skill_repository import CourseSkillRepository
from repositories.llm_summary_repository import LLMSummaryRepository
from repositories.project_repository import ProjectRepository
from repositories.skill_repository import SkillRepository
from services.jobs.progress import NULL_PROGRESS
from services.matching.gap_analysis import GapAnalyzer
from services.matching.ranking import CareerRankingService
from services.matching.skill_matcher import SkillMatcher


class RecommendationGenerator:
    TOP_CAREERS = 5
    TOP_COURSES = 5

    # How much an optional gap counts against an essential one of the same
    # weight when ranking courses. Optional skills are worth nothing to the
    # career *score* — that is the point of reading relation_type — but a course
    # that teaches one is still worth more than a course that teaches nothing.
    OPTIONAL_GAP_WEIGHT = 0.25

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

        # Fetched once for all five careers rather than once each: it is the same
        # 586 rows every time, and each fetch is a round trip to a cross-region
        # database.
        course_skills = CourseSkillRepository.get_all_active()

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
            RecommendationGenerator._save_course_recommendations(project, recommendation, course_skills)
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
    def _rank_courses(recommendation, course_skills):
        """Rank active courses by how much of this career's gap they close.

        Two things this does not do, both of which it used to.

        It does not join gaps to courses on ``skill_id``. Only 168 of the 1,231
        skills occupations ask for are taught by a course under the very same
        catalog row, so an exact join answers "does any course teach a skill
        spelled exactly like this gap", which is not the question. The gap and
        the syllabus are compared with the same identity-then-cosine rule that
        decided the gap was a gap in the first place.

        It does not treat every gap as equally worth closing. A course that
        teaches a career's defining requirement should outrank one that teaches
        a peripheral optional skill, so each gap carries the same weight the
        scorer gave it, and the resulting coverage is expressed as a share of
        the career's total gap — which is what ``coverage_percentage`` is
        stored and displayed as.
        """
        missing = set(recommendation["missing_skills"])

        gaps = [
            item
            for item in recommendation["skill_breakdown"]
            if item["skill_name"] in missing
        ]

        if not gaps or not course_skills:
            return []

        gap_names = [gap["skill_name"] for gap in gaps]
        taught_names = [course_skill["skill_name"] for course_skill in course_skills]

        similarity_matrix = SkillMatcher.similarities(gap_names, taught_names)

        # An optional gap still counts, just for less: scoring_weight is zero for
        # optional skills, so fall back to the raw weight scaled the same way.
        # Without this a career's optional gaps would rank courses at random.
        gap_weights = [
            gap["scoring_weight"] or (float(gap["weight"]) / 100.0) ** 2 * RecommendationGenerator.OPTIONAL_GAP_WEIGHT
            for gap in gaps
        ]

        total_gap_weight = sum(gap_weights)

        if total_gap_weight <= 0:
            return []

        # Best coverage per (course, gap): a course gets credit once for a gap,
        # from whichever of its skills covers it best, rather than accumulating
        # a point for every near-synonym on its syllabus.
        best_coverage: dict = {}

        for gap_index, gap in enumerate(gaps):
            for skill_index, course_skill in enumerate(course_skills):
                similarity = float(similarity_matrix[gap_index][skill_index])

                if not GapAnalyzer.is_same_skill(gap["skill_name"], course_skill["skill_name"], similarity):
                    continue

                key = (course_skill["course_id"], gap_index)
                coverage = float(course_skill["coverage_weight"]) / 100.0

                best_coverage[key] = max(best_coverage.get(key, 0.0), coverage)

        course_scores: dict = {}

        for (course_id, gap_index), coverage in best_coverage.items():
            course_scores[course_id] = course_scores.get(course_id, 0.0) + gap_weights[gap_index] * coverage

        return sorted(
            (
                (course_id, 100.0 * score / total_gap_weight)
                for course_id, score in course_scores.items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )

    @staticmethod
    def _save_course_recommendations(project, recommendation, course_skills):
        occupation_id = recommendation["occupation_id"]

        # Deferred for the same reason as in ResumeSkillExtractor: importing
        # openai and the langsmith wrapper costs ~1.3s on a Lambda cold start,
        # and no read endpoint needs it.
        from services.llm.openai_service import OpenAIService

        llm = OpenAIService()

        ranked_courses = RecommendationGenerator._rank_courses(recommendation, course_skills)

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
                # Already a percentage of the career's total gap weight; clamped
                # only against float drift at the top of the range.
                return {
                    "course_id": course_id,
                    "coverage_percentage": round(min(score, 100.0), 2),
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
