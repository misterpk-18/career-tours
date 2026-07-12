-- Enforce that each student's mobile number is unique. Email already has a
-- unique constraint (students_email_key). phone is nullable, and Postgres
-- treats NULLs as distinct, so students without a phone do not collide --
-- only real duplicate numbers are rejected.

ALTER TABLE public.students
    ADD CONSTRAINT students_phone_key UNIQUE (phone);
