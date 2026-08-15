# Career Matching Engine - Product Logic

## Goal

Build a system that:

1. Accepts a student's resume.
2. Asks additional career-related questions.
3. Extracts skills from the student's profile.
4. Matches the student against all available occupations.
5. Returns the Top 5 career recommendations.
6. Explains why each career was recommended.
7. Identifies skill gaps.
8. Recommends LMS courses to close those gaps.

---

# Core Principle

Use a hybrid approach:

* LLM for extraction and explanation.
* Deterministic scoring for matching.
* LMS skill mappings for recommendations.

The LLM should never directly decide career rankings.

The LLM should:

* Extract skills.
* Infer hidden skills.
* Generate summaries.
* Explain recommendations.

The scoring engine should calculate career matches mathematically.

---

# System Flow

```text
Resume Upload
       ↓
Questionnaire Answers
       ↓
LLM Skill Extraction
       ↓
Skill Normalization
       ↓
Occupation Matching Engine
       ↓
Top 5 Careers
       ↓
Skill Gap Analysis
       ↓
Course Recommendations
       ↓
LLM Career Summary
```

---

# Step 1: Skill Extraction

## Inputs

### Resume

Examples:

* Education
* Projects
* Certifications
* Experience
* Technical Skills

### Questionnaire

Examples:

* Preferred domains
* Career interests
* Preferred work style
* Target industries

---

## LLM Output

Use structured output with Pydantic.

```python
class Skill(BaseModel):
    skill_name: str
    confidence: float
    proficiency: int
    source: str

class StudentProfile(BaseModel):
    technical_skills: list[Skill]
    soft_skills: list[Skill]
    domain_skills: list[Skill]
```

---

## Explicit Skills

Resume contains:

```text
Python
SQL
Machine Learning
```

Extract directly.

---

## Inferred Skills

Resume says:

```text
Built a customer churn prediction model.
```

Infer:

```text
Python
Machine Learning
Data Cleaning
Feature Engineering
Model Evaluation
```

This is where the LLM provides the most value.

---

# Step 2: Skill Normalization

Students often use different names for the same skill.

Examples:

```text
Py
Python Programming
Python Dev
```

Normalize all to:

```text
Python
```

Maintain a master skill catalog.

Example:

```json
{
  "Py":"Python",
  "Python Programming":"Python",
  "JS":"JavaScript"
}
```

---

# Step 3: Occupation Skill Mapping

Every occupation contains required skills.

Example:

```json
{
  "occupation":"Data Scientist",
  "skills":{
    "Python":30,
    "Machine Learning":35,
    "Statistics":25,
    "SQL":10
  }
}
```

Weights indicate importance.

Total weight should equal 100.

---

# Step 4: Occupation Matching

## Basic Match Formula

```text
Score =
Matched Skill Weight
/
Total Skill Weight
```

Example:

Occupation:

```text
Python = 30
Machine Learning = 35
Statistics = 25
SQL = 10
```

Student:

```text
Python
Machine Learning
SQL
```

Matched Weight:

```text
30 + 35 + 10 = 75
```

Total Weight:

```text
100
```

Result:

```text
75%
```

---

# Step 5: Embedding Similarity

Some skills are related but not identical.

Example:

Student:

```text
Scikit Learn
Pandas
NumPy
```

Occupation:

```text
Machine Learning
```

Traditional matching misses these relationships.

---

## Solution

Generate embeddings for:

* Skills
* Occupations
* Course descriptions

Calculate:

```text
Cosine Similarity
```

Example:

```text
Scikit Learn
↔
Machine Learning

Similarity = 0.92
```

Treat as a strong partial match.

---

# Step 6: Final Career Score

Combine multiple signals.

```text
Final Score =
0.7 × Weighted Skill Score
+
0.2 × Embedding Similarity
+
0.1 × Interest Alignment
```

Example:

```text
Skill Score = 80
Embedding Score = 90
Interest Score = 70
```

Calculation:

```text
80 × 0.7 = 56
90 × 0.2 = 18
70 × 0.1 = 7
```

Final:

```text
81%
```

---

# Step 7: Top 5 Career Ranking

Rank every occupation.

Example:

```text
Data Scientist       89%
ML Engineer          86%
Data Analyst         82%
BI Analyst           77%
Software Engineer    74%
```

Return only the top 5.

---

# Step 8: Skill Gap Analysis

Compare:

```text
Occupation Skills
-
Student Skills
```

Example:

Occupation:

```text
Python
ML
Statistics
Deep Learning
```

Student:

```text
Python
ML
```

Missing:

```text
Statistics
Deep Learning
```

Store these as skill gaps.

---

# Step 9: Course Recommendation

Existing LMS Data:

```text
Course → Skills
Occupation → Skills
```

Example:

Course A:

```text
Statistics
Probability
Hypothesis Testing
```

Missing Skills:

```text
Statistics
Deep Learning
```

Coverage:

```text
1 / 2 = 50%
```

---

Course B:

```text
Statistics
Deep Learning
Neural Networks
```

Coverage:

```text
2 / 2 = 100%
```

Recommend highest coverage first.

---

# Course Coverage Formula

```text
Coverage % =
Matched Missing Skills
/
Total Missing Skills
× 100
```

---

# Step 10: LLM Summary Generation

After scoring is completed, send the result to the LLM.

Input:

```json
{
  "occupation":"Data Scientist",
  "score":89,
  "matched_skills":[
    "Python",
    "SQL",
    "Machine Learning"
  ],
  "missing_skills":[
    "Statistics",
    "Deep Learning"
  ]
}
```

---

Expected Output

```text
You have a strong fit for Data Science because your profile demonstrates practical experience with Python, SQL and Machine Learning.

Strengths:
- Python
- SQL
- Machine Learning

Skill Gaps:
- Statistics
- Deep Learning

Career Outlook:
...

Salary Range:
...

Typical Responsibilities:
...
```

---

# Final Career Report Structure

For every recommended occupation:

```json
{
  "occupation":"Data Scientist",
  "match_percentage":89,
  "matched_skills":[...],
  "missing_skills":[...],
  "recommended_courses":[...],
  "career_summary":"..."
}
```

---

# Recommended Architecture

## Use LLM For

* Resume parsing
* Skill extraction
* Skill inference
* Career summaries
* Course summaries
* Explanation generation

---

## Use Deterministic Logic For

* Skill normalization
* Occupation matching
* Ranking
* Skill gap analysis
* Course coverage calculation

---

# Why This Design

Benefits:

* Explainable percentages
* Easy debugging
* High trust from users
* Accurate ranking
* Uses LMS mappings efficiently
* Leverages LLM strengths without relying on LLM reasoning for scoring
* Scales easily as occupations, skills and courses grow

This approach combines deterministic scoring with LLM intelligence and should provide highly accurate career recommendations, skill-gap analysis and LMS course suggestions.

---

# Implementation Notes: What the Scorer Actually Does

The steps above are the product design. The sections below describe the code as
it stands, which departs from the design in the places the design turned out to
be wrong. `services/matching/` is the source of truth.

## The final score is not a blend

Step 6's `0.7 × skill + 0.2 × embedding + 0.1 × interest` was never built, and
is not planned. The embedding *is* the skill score — every skill comparison is a
cosine — so the first two terms measure the same thing twice, and there is no
interest signal in the data model to supply the third.

What runs is one number per occupation:

```text
score = 100 × Σ(w² × adjusted_similarity) / Σ(w²)
```

over the occupation's **essential** skills only, where `w = weight / 100` and

```text
adjusted_similarity = max(0, (similarity − floor) / (1 − floor))
similarity          = best cosine against any one of the student's skills
floor               = the student's mean similarity across every skill
                      any occupation asks for
```

## Why each piece is there

**Essential skills only.** ESCO marks 5,150 of its 8,114 career/skill pairs
optional. They average weight 31, so they carried 44% of every career's total
weight and the ranking largely followed skills nobody needs to have. Optional
skills still appear in the breakdown and still produce gaps — they just do not
move the score. A NULL `relation_type` counts as essential, which is what keeps
the 32 occupations predating the ESCO import scoring at all.

**Squared weights.** ESCO's weights are bunched closely enough that dividing by
their sum makes a linear weighting behave like an unweighted mean. Squaring
spreads them back out without a hand-tuned curve.

**The floor.** `similarity` is a max over the student's skills, and a max over
more draws is systematically larger — 40 unrelated padding skills used to lift
every career from ~30% to ~50% with the student's real fit unchanged. Measuring
the student's background similarity across the whole catalog and subtracting it
holds that drift to under half a point, and makes 0 mean "no overlap": a
six-nonsense-word control now scores 10-13 where real students score 52-95.

Because the floor is defined over the union of all occupation skills, an
occupation cannot be scored on its own. `SkillMatcher.match_all` scores all of
them in one pass, and `OccupationRepository.get_skills_by_occupation` fetches
the whole table in one statement to feed it.

## Gaps are decided by identity, not by cosine

Step 8's set subtraction is right; doing it with a distance threshold was not.
At the old 0.75 cutoff only 0-4 of a career's 10-35 skills ever matched, so
`missing_skills` was effectively the career's whole skill list — the same list
for every student, which is why a nurse and a nonsense control drew the same
course recommendations as a real developer.

`GapAnalyzer.is_same_skill` asks identity first: both names go through
`SkillTaxonomy.identity`, which resolves canonical names and aliases and strips
wrapper wording ("experience with Django" → `django`, "Python (computer
programming)" → `python`). Cosine at **0.60** is the fallback for what identity
cannot reach — the value the reference open-source ESCO extractor uses with this
same MiniLM model.

The trade-off is real and visible: at 0.60, "Business Intelligence" and "web
analytics" sit at 0.612 and count as the same skill. Raising the threshold does
not fix that without re-breaking everything identity now handles; adding the
missing alias to `skill_taxonomy.json` does.

## Course coverage uses the same rule

Step 9's `matched / total` counted missing skills equally and joined courses to
gaps on `skill_id`. Only 168 of the 1,231 skills occupations ask for are taught
by a course under that same catalog row, so the exact join answered a much
narrower question than the one being asked, and it went unnoticed only because
the gap list was a constant that always hit enough of the 168 to fill five
slots.

`RecommendationGenerator._rank_courses` compares gaps to the whole active
syllabus with `GapAnalyzer.is_same_skill` — deliberately the same predicate, so
a skill cannot be simultaneously missing from a career and untaught by the
course that teaches it. Each gap carries its scoring weight (optional gaps at
`OPTIONAL_GAP_WEIGHT`, currently 0.25), a course gets credit for a gap once from
whichever of its skills covers it best, and `coverage_percentage` is the share
of the career's total gap weight the course closes.

A well-matched student can now legitimately get fewer than five courses, or
none. That is the correct answer to "what should I study next" when there is
very little left, not a failure to find anything.
