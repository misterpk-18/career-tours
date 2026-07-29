-- Align student_skills.source with project_skills.source (varchar(100)).
--
-- The LLM returns `source` as a free-text provenance note ("Resume: PwC & Amazon
-- work experience; Skills section"). project_skills allowed 100 characters but
-- student_skills allowed only 50, so extraction wrote the project rows, then failed
-- on the student rows with StringDataRightTruncation and returned a 500 -- leaving
-- the two tables inconsistent. The width difference was accidental; both hold the
-- same value from the same extraction.
--
-- The write paths now also truncate to the column width, so an over-long note
-- degrades to a clipped string instead of a failed request.

ALTER TABLE public.student_skills
    ALTER COLUMN source TYPE character varying(100);
