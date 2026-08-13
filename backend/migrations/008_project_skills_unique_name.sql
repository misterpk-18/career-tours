-- One row per skill name per project, and delete the duplicates that accumulated
-- because there was never a constraint saying so.
--
-- ProjectSkillRepository.bulk_create has always ended with `ON CONFLICT DO
-- NOTHING`, but project_skills had no unique constraint other than its primary
-- key on a generated project_skill_id — which can never collide. So the clause
-- was decorative and every extraction appended a complete duplicate set. On the
-- one project with skills that meant 57 rows describing 30 distinct skills.
--
-- The visible symptom was not an error. `deduplicateSkills` in the frontend
-- (frontend/src/lib/format.js) exists to hide this, so the UI looked right while
-- the table grew on every re-extraction, and student_skills — which career
-- matching actually reads — was being re-upserted from a list containing the
-- same skill several times.
--
-- The index is on lower(skill_name), not skill_name. SkillNormalizer.normalize
-- (services/skills/normalizer.py:20-28) only canonicalises a name when it
-- matches an entry in SKILL_ALIASES; anything else keeps whatever casing the LLM
-- produced. So "Flask" and "flask" can both arrive, and an exact-name index
-- would happily store both, which is the same bug with extra steps. The current
-- data has no case-only variants, so this is strictly a superset of what an
-- exact index would remove.

-- Deduplicate first: an index cannot be created while violations exist.
--
-- Which row survives, in order: a catalog-matched row (skill_id IS NOT NULL)
-- beats an unmatched one, because student_skills and all career matching key on
-- skill_id and an unmatched row is dead weight there. Then the higher
-- confidence_score, then the most recent. COALESCE on the sort keys keeps NULLs
-- from winning by accident.
DELETE FROM public.project_skills ps
WHERE ps.project_skill_id NOT IN (
    SELECT DISTINCT ON (project_id, lower(skill_name)) project_skill_id
    FROM public.project_skills
    WHERE skill_name IS NOT NULL
    ORDER BY
        project_id,
        lower(skill_name),
        (skill_id IS NOT NULL) DESC,
        COALESCE(confidence_score, 0) DESC,
        COALESCE(created_at, '-infinity'::timestamp) DESC
)
AND ps.skill_name IS NOT NULL;

-- Partial, because a NULL skill_name carries no identity to deduplicate on and
-- Postgres would not treat two NULLs as equal anyway. There are none today; the
-- column is nullable, so the index should not pretend otherwise.
CREATE UNIQUE INDEX IF NOT EXISTS project_skills_project_id_name_key
    ON public.project_skills (project_id, lower(skill_name))
    WHERE skill_name IS NOT NULL;
