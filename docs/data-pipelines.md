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
└── extracted/NT-C-001.json               # one profile per course
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
