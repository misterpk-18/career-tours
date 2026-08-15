-- Keep ESCO's essential/optional distinction instead of discarding it at import.
--
-- career_skills.csv marks every pair as essential or optional, and load_careers.py
-- dropped the column. That loses the single biggest signal in the file: 5,150 of
-- the 8,114 pairs are optional, and because they still average weight 31 they
-- carried 44% of every career's total weight. A career was therefore scored
-- mostly on skills it does not actually require, and the ranking followed.
--
-- Weight alone cannot stand in for this. 16% of optional skills sit above the
-- 25th percentile of essential ones, so any weight cutoff that removes most
-- optional pairs also removes genuinely essential ones.
--
-- Nullable on purpose. 32 of the 267 occupations are outside the ESCO import and
-- have no relation_type to backfill; the scorer reads NULL as essential, so they
-- keep scoring on all of their skills exactly as they do today rather than
-- silently dropping to a score of zero.
ALTER TABLE public.occupation_skills
    ADD COLUMN IF NOT EXISTS relation_type character varying(16);

ALTER TABLE public.occupation_skills
    DROP CONSTRAINT IF EXISTS occupation_skills_relation_type_check;

ALTER TABLE public.occupation_skills
    ADD CONSTRAINT occupation_skills_relation_type_check
    CHECK (relation_type IS NULL OR relation_type IN ('essential', 'optional'));

-- The scorer filters by relation_type on every occupation it reads, and the
-- ranking endpoint reads all 267 of them per request.
CREATE INDEX IF NOT EXISTS occupation_skills_occupation_relation_idx
    ON public.occupation_skills (occupation_id, relation_type);
