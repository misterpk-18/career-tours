# O*NET Preview Spike

A throwaway sample, not a pipeline. It exists to answer one question:

> Is O*NET worth importing as the base for our career catalog, or is direct
> authoring cheaper?

See [NOTES.md](NOTES.md) for the answer.

## What's here

```
raw/                        slices of the O*NET 30.3 bulk download, 3 occupations only
  occupation_data.tsv       title + description
  skills.tsv                Essential + Transferable, IM scale, suppressed rows removed
  technology_skills.tsv     the Software Skills file (all 768 rows for these 3 occupations)
converted/                  the same data in the proposed role-family YAML format
  backend.software-developer.yaml
  frontend.web-developer.yaml
  data.data-scientist.yaml
NOTES.md                    findings and recommendation
```

## Occupations sampled

| SOC | Title |
|---|---|
| 15-1252.00 | Software Developers |
| 15-1254.00 | Web Developers |
| 15-2051.00 | Data Scientists |

## How the raw slices were produced

Downloaded `https://www.onetcenter.org/dl_files/database/db_30_3_text.zip`
(13 MB, no registration required), then:

- `Occupation Data.txt` — filtered to the three SOC codes.
- `Essential Skills.txt` + `Transferable Skills.txt` — filtered to the three SOC
  codes and `Scale ID = IM` (Importance), dropping rows flagged
  `Recommend Suppress = Y` or `Not Relevant = Y`. A `Source` column was prepended
  to record which of the two files each row came from.
- `Software Skills.txt` — filtered to the three SOC codes, unmodified otherwise.

Importance arrives on O*NET's 1–5 `IM` scale. The converted YAML rescales to
0–100 with `(value - 1) / 4 * 100`, matching both what O*NET OnLine displays and
our `occupation_skills.weight numeric(5,2)` column. Spot check: Critical Thinking
for Software Developers is `3.88` raw → `72`, which is what onetonline.org shows.

## Deliberately not done

- **No canonicalisation.** Skill names are verbatim O*NET. `skill_taxonomy.json`
  and `services/skills/taxonomy.py` were not read, imported or modified. How
  badly the raw names diverge from our vocabulary is one of the things this
  spike measures — see NOTES.md.
- **No database.** No migrations, no seeding, no schema changes.
- **No pipeline.** The conversion was done by hand. Nothing here is reusable
  code.

Nothing outside this folder was created or modified.

## Attribution

This folder contains data from the **O*NET 30.3 Database**, by the
**U.S. Department of Labor, Employment and Training Administration (USDOL/ETA)**.
Used under the [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) license.
O*NET® is a trademark of USDOL/ETA.

If any of this data reaches production, that attribution has to surface in the
app.
