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
