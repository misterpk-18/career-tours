# Findings

**Verdict: don't import O*NET as the weight source. Take its skill *lists* if you
want a checklist, author the weights yourself.**

The premise going in was that O*NET's numeric Importance ratings would drop
straight into `occupation_skills.weight` and remove most of the authoring work.
That premise is wrong, for three independent reasons.

---

## 1. The weighted skills are not the skills you match on

O*NET splits skills across two kinds of file, and the split is exactly backwards
for our purpose:

| | has numeric Importance | resume-matchable |
|---|---|---|
| `Essential Skills.txt` / `Transferable Skills.txt` | **yes** | mostly no |
| `Software Skills.txt` | **no** | yes |

The complete weighted skill list for **Software Developers** (15-1252.00), all 35
of them, rescaled to 0–100:

```
75 Programming            56 Operations Analysis      40 Negotiation
72 Critical Thinking      53 Speaking                 40 Troubleshooting
66 Judgment and Decision  53 Time Management          31 Mgmt of Personnel Res.
62 Reading Comprehension  50 Monitoring               28 Science
62 Active Learning        50 Coordination             28 Equipment Selection
62 Systems Analysis       47 Social Perceptiveness    25 Operation and Control
60 Active Listening       47 Instructing              22 Installation
60 Complex Problem Solv.  47 Service Orientation      19 Mgmt of Financial Res.
60 Technology Design      44 Mathematics              16 Mgmt of Material Res.
60 Systems Evaluation     44 Persuasion                6 Equipment Maintenance
56 Writing                44 Quality Control Analysis  3 Repairing
                          44 Operations Monitoring
```

Six of those are usable. `Programming` is the only technical one. The rest are
generic worker competencies — a student resume will never produce "Reading
Comprehension" or "Service Orientation", so these skills cannot discriminate
between careers. They would sit in `occupation_skills` adding weight that every
candidate matches identically, or nobody matches at all.

The tail is worse than useless. **Repairing 3, Equipment Maintenance 6,
Installation 22** for a software developer — non-zero importance for physical
maintenance work. For Web Developers the same two skills score 0 and 0. The same
survey, two adjacent occupations, and the values disagree. That is the noise
floor of the instrument, and it is visible in the published data.

Per occupation, what actually carried over:

| occupation | O*NET-weighted skills kept | authored | dropped |
|---|---|---|---|
| Software Developers | 6 | 6 | 29 |
| Web Developers | 6 | 6 | 29 |
| Data Scientists | **0** | 10 | — |

## 2. The technology skills are an unranked dump

`Software Skills.txt` has the content we actually want — Python, Docker, React,
Kafka. It has no importance value of any kind.

- Software Developers: **430** technology skills
- Web Developers: **251**
- Data Scientists: **87**

Unranked and unfiltered. The Software Developers list includes **Adobe Photoshop,
Adobe InDesign, Adobe After Effects**, and legacy entries like **COBOL, ALGOL,
BASIC and APL**. It reads as the union of every technology ever mentioned in a
posting for that occupation, which is roughly what it is.

The two available filters don't rescue it:

- `In Demand` — **empty for all three occupations**. Zero rows flagged.
- `Hot Technology` — a *global* property of the technology, not per-occupation.
  It cuts 430 → 152 and still leaves Photoshop and InDesign in a backend role.

So picking the 6–8 technologies that define a role is a hand judgement. That is
the same judgement as authoring the weights, so importing saves nothing at the
step that costs.

## 3. The modern occupations have no data at all

**Data Scientists (15-2051.00) has zero skill rows.** Not suppressed, not
low-confidence — absent from both `Essential Skills.txt` and `Transferable
Skills.txt`. The occupation exists with a title, a description and 87 technology
skills, and no weighted skill whatsoever.

It isn't isolated. Of the 38 occupations in SOC major group 15-xxxx:

```
31 have skills data
 7 do not:
     15-1255.00  Web and Digital Interface Designers
     15-1299.00  Computer Occupations, All Other
     15-1299.04  Penetration Testers
     15-1299.06  Digital Forensics Analysts
     15-1299.07  Blockchain Engineers
     15-2051.00  Data Scientists
     15-2099.00  Mathematical Science Occupations, All Other
```

The gaps are precisely the newer roles — data science, security, blockchain,
product design. Those map onto the domains we most wanted help with.

## 4. Coverage is much smaller than expected

I estimated ~100–120 relevant occupations earlier. The real number is **38** in
SOC 15-xxxx, of which 31 are usable. Against a target of 31 domains with a full
career ladder, O*NET supplies fewer distinct occupations than we have domains —
and no seniority dimension at all, since "Software Developers" is one occupation
spanning junior through principal.

## 5. Naming divergence (sizing only, not fixed here)

Canonicalisation was deferred, so names are verbatim. For the record: across the
three occupations there are **489 distinct technology names, 206 of them longer
than two words**, following an acronym-expansion convention:

```
Cascading style sheets CSS              Amazon Simple Storage Service S3
Hypertext markup language HTML          Amazon Elastic Compute Cloud EC2
Structured query language SQL           Amazon Web Services AWS software
Advanced business application programming ABAP
Beginner's all-purpose symbolic instruction code BASIC
```

Two specifics worth knowing. First, the convention is not applied consistently:
Data Scientists lists `Structured query language SQL` while Software Developers
has no plain SQL entry at all, only `Microsoft SQL Server` and
`Microsoft transact-structural query language T-SQL`. Second, none of these
would match our vocabulary without a mapping layer — this is a real, sizeable
job, roughly 200 hand-checked aliases for a full import, and it lands on top of
the weight authoring rather than instead of it.

---

## Recommendation

**Author the catalog directly. Use O*NET as a reference checklist, not an import.**

The work O*NET was supposed to remove — deciding which 8 skills define a role and
how much each matters — is exactly the work it doesn't do. What it does supply
(generic competency ratings) is data we'd discard, and the mapping layer needed
to consume any of it costs about as much as authoring from scratch.

Concretely:

- **Drop the import pipeline** (`fetch_onet.py`, `map_onet.py`,
  `onet_to_catalog.yaml`). That's most of Phase 2–3 of the earlier plan.
- **Keep the role-family + level-overlay model.** Nothing here undermines it;
  the converted files show the format works. It remains the thing that turns
  ~900 occupations into ~75 authored units.
- **Use `Software Skills.txt` as a coverage checklist** when authoring a family —
  "did I forget Terraform for a DevOps role?" It's a genuinely useful prompt, and
  it's free. But it informs authoring rather than replacing it.
- **Revisit ESCO separately.** Its essential/optional distinction is a different
  proposition from O*NET's numeric ratings and this spike says nothing about it.
  Worth its own preview before deciding — ESCO has 3,007 occupations against
  O*NET's 1,016 and explicitly models skill transferability, so the coverage
  problem in §3 and §4 may not repeat.

One thing that got cheaper, not more expensive: since we're authoring anyway, the
weights can be tuned directly against the ranking behaviour we want, rather than
inherited from a survey instrument whose noise floor puts Repairing at 3 for a
software developer.

## Attribution

Data from the O*NET 30.3 Database by USDOL/ETA, used under CC BY 4.0.
