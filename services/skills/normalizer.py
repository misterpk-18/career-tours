from repositories.skill_repository import SkillRepository


class SkillNormalizer:

    SKILL_ALIASES = {
        "py": "Python",
        "python programming": "Python",
        "python developer": "Python",
        "ml": "Machine Learning",
        "machine learning engineer": "Machine Learning",
        "js": "JavaScript",
        "javascript developer": "JavaScript",
        "postgres": "PostgreSQL",
        "postgresql database": "PostgreSQL",
        "sql db": "SQL",
        "structured query language": "SQL"
    }

    @staticmethod
    def normalize(skill_name):
        if not skill_name:
            return None

        skill_name = skill_name.strip()

        normalized = SkillNormalizer.SKILL_ALIASES.get(
            skill_name.lower(),
            skill_name
        )

        return normalized

    @staticmethod
    def normalize_skill_list(skills):
        normalized_skills = []

        for skill in skills:
            normalized_name = SkillNormalizer.normalize(
                skill.skill_name
            )

            skill.skill_name = normalized_name

            normalized_skills.append(skill)

        return normalized_skills

    @staticmethod
    def get_skill_id(skill_name):
        normalized_name = SkillNormalizer.normalize(
            skill_name
        )

        skill = SkillRepository.get_by_name(
            normalized_name
        )

        if not skill:
            return None

        return skill.skill_id

    @staticmethod
    def map_to_skill_ids(skills):
        mapped_skills = []

        for skill in skills:
            skill_id = SkillNormalizer.get_skill_id(
                skill.skill_name
            )

            if skill_id:
                mapped_skills.append({
                    "skill_id": skill_id,
                    "proficiency_level": skill.proficiency,
                    "confidence_score": skill.confidence,
                    "source": skill.source
                })

        return mapped_skills