-- Normalize blank-string profile fields to NULL.
--
-- The registration form posts every field it renders, so fields left empty arrived
-- as '' instead of being absent. `phone` has a UNIQUE constraint (002) and Postgres
-- treats '' as an ordinary value -- only NULLs are mutually distinct -- so the first
-- student who registered without a phone stored '', and every later blank-phone
-- signup then failed on students_phone_key.
--
-- StudentRepository._blank_to_none now coerces these on write; this backfills rows
-- created before that. Safe to re-run.

UPDATE students SET
    phone                  = nullif(trim(phone), ''),
    college_name           = nullif(trim(college_name), ''),
    degree_name            = nullif(trim(degree_name), ''),
    branch_name            = nullif(trim(branch_name), ''),
    preferred_job_location = nullif(trim(preferred_job_location), ''),
    target_role            = nullif(trim(target_role), ''),
    career_interest        = nullif(trim(career_interest), '')
WHERE trim(coalesce(phone, 'x')) = ''
   OR trim(coalesce(college_name, 'x')) = ''
   OR trim(coalesce(degree_name, 'x')) = ''
   OR trim(coalesce(branch_name, 'x')) = ''
   OR trim(coalesce(preferred_job_location, 'x')) = ''
   OR trim(coalesce(target_role, 'x')) = ''
   OR trim(coalesce(career_interest, 'x')) = '';
