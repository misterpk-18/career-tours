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

**Vocabulary decides whether matching fires.** `occupation_skills` and
`course_skills` join to `skills` on `skill_id`, exactly — there is no fuzzy
match anywhere in the engine. A generated skill only ever matches a student if
it resolves to the same `skills` row that resume extraction produces, which is
why both loaders resolve names through `SkillTaxonomy.canonical` and then
`SkillNormalizer.normalize` before touching the catalog, and why the career
prompt picks from a closed vocabulary instead of naming skills freely.

The course pipeline predates that constraint being understood, and its skills
were extracted without a supplied vocabulary: 505 of its 591 `course_skills`
rows point at names no student profile produces. Re-running
`extract_course_profiles.py` with the taxonomy in the prompt would fix it.
