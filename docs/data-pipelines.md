# Reference Data Pipelines

How `courses`, `course_skills`, `occupations`, `occupation_skills` and `skills`
get their contents. These are the catalog tables the matching engine reads;
none of them is populated by application traffic, and an empty one presents as
"no recommendations" rather than as an error.

Two independent pipelines feed them:

| Pipeline | Source | Fills |
|---|---|---|
| [Course corpus](#course-corpus) | Nipuna's approved knowledge-corpus PDF | `courses`, `course_skills` |
| [ESCO careers](#esco-careers) | ESCO occupation data + authored market titles | `occupations`, `occupation_skills` |

Both add rows to `skills`, which is the shared vocabulary that makes a student's
extracted skills joinable to an occupation's requirements and a course's
coverage.

Everything below runs from `backend/` as the working directory, because the
packages use bare imports.

---

## Course corpus

`backend/data/lms/` holds Nipuna's *Approved Knowledge Corpus v3.0*, split from
the single 413-page source PDF into one file per course:

```text
backend/data/lms/
├── info.pdf                              # front matter, pages 1-12
├── courses/NT-C-001_Python_Full_Stack.pdf  # 40 files, 10 pages each
│   ...  NT-C-040_ServiceNow.pdf
├── extracted/NT-C-001.json               # one profile per course
└── modules/NT-C-001.json                 # one module breakdown per course
```

Course boundaries were detected by scanning each page for its `NT-C-0NN` code
rather than assuming a fixed page count — the codes happened to fall exactly 10
pages apart, but nothing guarantees that for a future corpus version.

### Running it

```bash
python3 scripts/extract_course_profiles.py [--force] [--workers 8] [--only NT-C-001]
python3 scripts/load_course_profiles.py --dry-run
python3 scripts/load_course_profiles.py
```

Extraction is one `gpt-5` call per course (`OpenAIService.extract_course_profile`),
run 8-wide. A course that already has a JSON file is skipped, so a re-run costs
nothing and a failed run resumes where it stopped. The JSON is the reviewable
record: edit a file by hand and re-load, without paying OpenAI again.

The loader upserts on `courses.course_code` (added by migration
`009_courses_course_code.sql`), adopting an existing row that matches by name so
its `course_id` — and any `course_recommendations` pointing at it — survives.
Courses absent from the corpus are set `is_active = false` rather than deleted.
`course_skills` is emptied and rebuilt in full, because the corpus is the source
of truth for what a course teaches.

### Section and module breakdown

A second, independent pass fills `course_sections` and `course_modules` — the
four-sections, eight-modules-per-course syllabus that the profile extraction
reads past and discards.

```bash
python3 scripts/extract_course_modules.py [--force] [--only NT-C-001] [--dry-run]
python3 scripts/load_course_modules.py --dry-run
python3 scripts/load_course_modules.py
```

**This one uses no LLM.** The corpus PDFs are generated from a fixed template
and it holds across all 40: four `Deep Knowledge` sections, two modules each,
every module introduced by `Module N - <title>` / `Objective:` /
`Observable evidence:`. A regex finds all 320 with nothing left over, so the run
is free, takes about two seconds, and is byte-identical every time. A model
would have cost 40 full-document calls to re-derive text already in the file,
and bought the one failure this data cannot absorb — a module silently
renumbered, retitled or merged. The parser asserts eight modules per course and
fails loudly rather than writing a short course.

The `Objective:` line *is* the topic list ("Syntax, data types, control flow,
functions" is four topics), so `topics` is the split of it and `objective` keeps
the raw string — a bad split stays cosmetic instead of losing data. A module
belongs to the last section id appearing before it in the text.

The loader writes sections first (`course_modules.section_code` points at them),
upserting on `section_code` and `(course_id, module_number)`; the corpus names
its own sections and numbers its own modules, so a re-run updates the same 160
and 320 rows instead of appending a set. Unlike `course_skills` nothing is
deleted first, because every row in both tables came from this script and a
partial run must not empty the other 39 courses. A course code with no row in
`courses` is reported and skipped, not fatal — run `load_course_profiles.py`
first.

### What the corpus repeats, and what is therefore not stored or not served

Much of a course PDF is generated from templates, and it is worth knowing which
parts carry no information before building anything on them:

| Field | Measurement | Consequence |
|---|---|---|
| Concept table, "approved knowledge statement" | **1** distinct template across 1,009 rows | not extracted |
| Concept table, "application behaviour" | **1** distinct template across 1,167 rows | not extracted |
| Concept table, "evidence" column | repeats the module's `Observable evidence` | not extracted |
| Concept table, "concept" column | equals the objective's topic list | already `topics` |
| `sections.competency` | equals its two modules' objectives joined, **160/160** | stored, not served |
| `sections.completion_evidence` | equals its two modules' evidence joined, **160/160** | stored, not served |
| `sections.assessment` | identical across all 4 sections of a course, **40/40** | served, rendered once |
| `sections.weight_pct` | 20/25/25/30 in every course | served |
| `modules.objective` | the comma-joined form of `topics` | stored, not served |

The four-column concept table under each module is the largest thing here and
the least worth having: it would add roughly 1,280 rows of generated prose whose
only real column is already `topics`. `competency` and `completion_evidence` are
stored because the corpus states them at section level, but omitting them from
the API cut 29% off the course-list response with nothing lost.

---

## ESCO careers

`backend/data/imports/esco/` is a curated import with three published CSVs and a
`_staging/` directory of intermediate artifacts:

| File | Rows | Contents |
|---|---|---|
| `careers.csv` | 235 | one row per career; `selection` is the reliable filter |
| `skills.csv` | 1,120 | the curated skill vocabulary, with ESCO ids |
| `career_skills.csv` | 8,114 | `career_title` × `skill_id` × weight × relation |
| `validate.py` | — | the acceptance test for the three above |

### Reading `careers.csv`

`selection` is the column to filter on. `source` and `has_skill_data` are the
same fact restated and carry no extra information; `isco_group_name` is **not**
usable as a filter, because the market rows have no ISCO group and had authored
categories (`Backend Development`) written into that column instead.

| `selection` | Rows | What it is |
|---|---|---|
| `core_ict` | 121 | ESCO ICT occupations — `mobile application developer` |
| `adjacent_tech` | 22 | ESCO occupations touching tech — `3D printing technician` |
| `market_title` | 92 | authored modern roles ESCO has no code for — `LLM Engineer` |

### Running it

```bash
python3 scripts/author_career_skills.py [--force] [--workers 8] [--only "AI Engineer"]
python3 scripts/build_career_skills.py
python3 data/imports/esco/validate.py          # must exit 0
python3 scripts/load_careers.py --dry-run
python3 scripts/load_careers.py
```

`author_career_skills.py` fills the careers that have no weighted skills, listed
in `_staging/author_input_*.json`. It handles two groups differently, which is
the one non-obvious thing about this pipeline:

* **market titles** — nothing upstream exists, so the model picks skill ids from
  the whole of `skills.csv` and assigns relation types and weights.
* **ESCO careers** — `validate.py` rejects any pair marked `career_source=esco`
  that is not in the upstream ESCO relations, so their candidate list is exactly
  their own rows and the model only chooses weights.

`build_career_skills.py` then joins the staged weights to their relation types
and merges the authored output into `career_skills.csv`. `validate.py` is the
real gate: it enforces referential integrity, ESCO traceability, and a per-career
shape (≥5 skills, ≥3 essential, ≥4 distinct weights, ≤40% of weights above 80,
mean essential weight above mean optional). Those rules are restated in the
extraction prompt because the model otherwise produces a flat 80/85/90 spread
that fails them.

The loader upserts `occupations` on name, leaves occupations outside the import
untouched, and rebuilds `occupation_skills` **only for the occupations it
loads** — a full-table wipe would strip the skills off the untouched
occupations, leaving them visible to matching but unmatchable.

---

## Two things that will bite

**Always batch writes.** Postgres is on Neon in another region, so a statement
costs a network round trip whether it writes one row or eight thousand. A
row-at-a-time version of `load_careers.py` spent 16 minutes with the server
sitting in `ClientRead` — idle, waiting on the client — for work the database
does in seconds.

Note that `executemany` is **not** the fix: SQLAlchemy's `text()` with a list of
parameter dicts hands off to psycopg2's `executemany`, which loops and sends one
statement per row. The `bulk_insert` helper in `scripts/load_careers.py` builds
genuine multi-row `VALUES` statements at 1,000 rows each; that is what took the
run from 16 minutes to 11 seconds.

**Vocabulary decides whether *course recommendation* fires — not career
matching.** The two work differently, and it is easy to over-generalise from one
to the other:

* **Career match percentage ignores `skill_id` entirely.** `SkillMatcher` embeds
  skill *names* with all-MiniLM-L6-v2 and scores by cosine similarity, so
  "Django ORM" and "ORM" still contribute. Naming drift costs accuracy here, not
  correctness.
* **Course recommendation is an exact lookup.** `generator.py` takes each
  missing skill *name*, resolves it with `SkillRepository.get_by_name`
  (case-insensitive, exact), and joins `course_skills` on the `skill_id` it gets
  back. A course skill spelled differently from the occupation skill produces no
  recommendation at all, silently.

That is why both loaders resolve names through `SkillTaxonomy.canonical` and
then `SkillNormalizer.normalize`, and why both extraction prompts are handed a
vocabulary instead of naming skills freely.

The course pipeline originally ran without one, and the cost was measurable:
only 52 skills appeared in both `course_skills` and `occupation_skills`, leaving
94 of 267 occupations unable to reach any course. Re-extracting against the
shared vocabulary (`skills.csv` ∪ `skill_taxonomy.json`, 1,469 names) took that
to 168 shared skills and 19 unreachable occupations. Roughly 79% of extracted
course skills now come from the vocabulary; the remainder are genuine gaps in it
— ESCO does not name `Django REST Framework` or `Azure Key Vault` — which is why
the vocabulary is a strong preference in the prompt rather than a hard
constraint.


---

## Section question corpus

`backend/scripts/generate_section_questions.py` writes one JSON per course to
`backend/data/lms/questions/`, then `backend/scripts/load_section_questions.py`
loads them into `course_section_questions`.

Unlike the other pipelines here this is **not a parser** — the questions do not
exist in the source PDFs. What the corpus does supply is the shape: every section
already declares `assessment` as "10 concept MCQ (30 marks) + 4 code/design
scenarios (30) + 2 practical tasks (40)", and the generator makes that concrete.

### Running it

```bash
python scripts/generate_section_questions.py --dry-run
python scripts/generate_section_questions.py --workers 16          # all pending courses
python scripts/generate_section_questions.py --only NT-C-023       # one course
python scripts/generate_section_questions.py --sections NT-C-023-S01   # one section: a cheap probe
python scripts/load_section_questions.py --dry-run
python scripts/load_section_questions.py
```

**Measured:** ~4.75 gpt-5 calls per course including validation retries (4 nominal,
one per section), each returning 10–15k output tokens. 40 courses = 160 sections in
~50 minutes at `--workers 16`, with no rate limiting at any point (the ceiling is
500 RPM / 500K TPM). 16 workers did 4× the work of 8 for 11% more wall clock.

`--sections` writes `NT-C-023-S01.section.json`, **not** a course file. A course
JSON holding one of four sections looks complete to the loader and to anyone
reading it; the gap only surfaces when a learner reaches the missing section.

### Three things the model is not trusted with

- **The answer key.** Left alone, gpt-5 put the correct option at B for nine of ten
  MCQs in the first section generated — a student who always answers B scores
  27/30. Asking for a spread in the prompt invites the bias back in a new shape, so
  `balance_answer_key` deals positions from a balanced pool afterwards: ten
  questions draw from A/B/C/D cycled, giving exactly 3/3/2/2 per section by
  construction. Verified across all 160 section codes with worst-case all-B input.
- **The arithmetic.** `validate` re-checks counts, the 30/30/40 marks split, each
  rubric summing to its question's marks, and that no question cites a skill
  outside `skills_assessed`. A rubric that sums to 9 out of 8 marks is invisible
  until an assessor is halfway through marking with it.
- **The skill names.** gpt-5 once produced a whole section whose skills read
  `Tally Prime (course-level coverage 90/100, technical)` — it had copied the
  annotation the prompt puts beside each name. Every internal consistency check
  passed, because the corrupted names were used consistently. Only comparing
  against the course's real skill list catches that class of error, which is why
  `validate` takes a `vocabulary` argument and the loader re-checks against
  `skills` independently.

### Formatting is part of the contract

1,495 of 1,600 MCQs carry a code or data artefact, and the prompt requires every
one to be in a fenced block with a language tag. `check_formatting` fails a section
for an unclosed fence, an untagged fence, stray headings or pipe tables, or code
sitting outside any fence.

Unknown language tags are **normalised, not rejected**: gpt-5 reached for
` ```docker `, ` ```nginx ` and ` ```http ` on the first probe course and all three
were the right instinct — the whitelist was what was wrong. Rejection cost a full
regeneration (~150s, 15k tokens) for something cosmetic, and under the
all-or-nothing write the third failure discarded three good sections with it.
Aliases now resolve (`docker`→`dockerfile`, `PY`→`python`), anything unrecognised
degrades to `text`, and only unclosed fences still fail — guessing where a block
was meant to end would be inventing content.

Control characters are rejected outright. gpt-5 produced three NUL bytes, all in
questions *about* invisible characters, by corrupting its own `\u00A0` escapes into
`\x00A` while writing a Power BI text-normalisation stem. Postgres text cannot hold
`0x00` at all, so one of them aborted the entire 2,560-row load with a driver-level
error naming no field.

### The loader

- Validates every file with the generator's own `validate` before a single row
  moves. The generator validated what the model returned; this validates what is
  actually being loaded, and those are the same thing only if nothing touched the
  files in between.
- **Canonicalises skill-name case** against `skills.skill_name` and stores the
  canonical spelling — the extracted profiles and the skills table disagree on case
  for a handful of entries (`design systems` vs `Design systems`), which an exact
  join treats as two different skills. Names matching nothing at any casing are
  loaded as written and reported loudly rather than silently dropped.
- Upserts on `(section_code, question_type, question_number)`; one transaction, one
  commit. `--prune` (off by default) removes rows for sections no longer on disk.
