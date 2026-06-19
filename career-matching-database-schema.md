# Career Matching Platform - Database Schema

## Overview

The database is centered around four core entities:

```text
Student
   ↓
Skills
   ↓
Occupations
   ↓
Courses
```

The matching engine operates using relationships between:

```text
Student ↔ Skills
Occupation ↔ Skills
Course ↔ Skills
```

---

# 1. students

Stores student profile information.

```sql
CREATE TABLE students (
    student_id UUID PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20),
    college_name VARCHAR(255),
    degree_name VARCHAR(255),
    graduation_year INT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

# 2. resumes

Stores uploaded resumes.

```sql
CREATE TABLE resumes (
    resume_id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    file_url TEXT,
    raw_text TEXT,
    parsed_at TIMESTAMP,
    created_at TIMESTAMP
);
```

---

# 3. skills

Master skill catalog.

Every skill should exist only once.

```sql
CREATE TABLE skills (
    skill_id UUID PRIMARY KEY,
    skill_name VARCHAR(255) UNIQUE,
    skill_category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP
);
```

Examples:

```text
Python
Machine Learning
React
Leadership
Communication
```

---

# 4. skill_aliases

Used for normalization.

```sql
CREATE TABLE skill_aliases (
    alias_id UUID PRIMARY KEY,
    skill_id UUID REFERENCES skills(skill_id),
    alias_name VARCHAR(255)
);
```

Examples:

```text
Py → Python

JS → JavaScript

ML → Machine Learning
```

---

# 5. student_skills

Skills extracted from resume and questionnaire.

```sql
CREATE TABLE student_skills (
    student_skill_id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    skill_id UUID REFERENCES skills(skill_id),
    proficiency_level INT,
    confidence_score DECIMAL(5,2),
    source VARCHAR(100),
    created_at TIMESTAMP
);
```

Examples:

```text
Python
Confidence = 0.96

Source = Resume
```

```text
Leadership

Source = Questionnaire
```

---

# 6. occupations

Master occupation catalog.

```sql
CREATE TABLE occupations (
    occupation_id UUID PRIMARY KEY,
    occupation_name VARCHAR(255),
    description TEXT,
    average_salary DECIMAL(12,2),
    growth_outlook VARCHAR(100),
    created_at TIMESTAMP
);
```

Examples:

```text
Data Scientist

Software Engineer

Machine Learning Engineer

Business Analyst
```

---

# 7. occupation_skills

Most important table in the system.

Maps occupations to skills.

```sql
CREATE TABLE occupation_skills (
    occupation_skill_id UUID PRIMARY KEY,
    occupation_id UUID REFERENCES occupations(occupation_id),
    skill_id UUID REFERENCES skills(skill_id),
    weight DECIMAL(5,2)
);
```

Example:

```text
Data Scientist

Python = 30
Machine Learning = 35
Statistics = 25
SQL = 10
```

Total:

```text
100
```

---

# 8. questionnaires

Stores assessment questions.

```sql
CREATE TABLE questionnaires (
    question_id UUID PRIMARY KEY,
    question_text TEXT,
    question_type VARCHAR(50),
    is_active BOOLEAN
);
```

---

# 9. questionnaire_responses

Student answers.

```sql
CREATE TABLE questionnaire_responses (
    response_id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    question_id UUID REFERENCES questionnaires(question_id),
    answer_text TEXT,
    created_at TIMESTAMP
);
```

---

# 10. courses

LMS courses.

```sql
CREATE TABLE courses (
    course_id UUID PRIMARY KEY,
    course_name VARCHAR(255),
    description TEXT,
    duration_hours INT,
    level VARCHAR(50),
    is_active BOOLEAN,
    created_at TIMESTAMP
);
```

---

# 11. course_skills

Maps LMS courses to skills.

```sql
CREATE TABLE course_skills (
    course_skill_id UUID PRIMARY KEY,
    course_id UUID REFERENCES courses(course_id),
    skill_id UUID REFERENCES skills(skill_id),
    coverage_weight DECIMAL(5,2)
);
```

Example:

```text
Machine Learning Bootcamp

Machine Learning = 40

Statistics = 30

Deep Learning = 30
```

---

# 12. student_career_matches

Stores generated recommendations.

```sql
CREATE TABLE student_career_matches (
    match_id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    occupation_id UUID REFERENCES occupations(occupation_id),
    match_percentage DECIMAL(5,2),
    rank_position INT,
    generated_at TIMESTAMP
);
```

Example:

```text
Data Scientist
89%
Rank 1
```

---

# 13. career_skill_gaps

Stores missing skills.

```sql
CREATE TABLE career_skill_gaps (
    gap_id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    occupation_id UUID REFERENCES occupations(occupation_id),
    skill_id UUID REFERENCES skills(skill_id),
    gap_percentage DECIMAL(5,2),
    created_at TIMESTAMP
);
```

Example:

```text
Student

Missing:
- Statistics
- Deep Learning
```

---

# 14. course_recommendations

Stores recommended courses.

```sql
CREATE TABLE course_recommendations (
    recommendation_id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    occupation_id UUID REFERENCES occupations(occupation_id),
    course_id UUID REFERENCES courses(course_id),
    coverage_percentage DECIMAL(5,2),
    recommendation_rank INT,
    created_at TIMESTAMP
);
```

Example:

```text
Advanced ML Course

Coverage = 100%

Rank = 1
```

---

# 15. llm_summaries

Stores generated summaries.

```sql
CREATE TABLE llm_summaries (
    summary_id UUID PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    occupation_id UUID REFERENCES occupations(occupation_id),
    summary_type VARCHAR(100),
    summary_text TEXT,
    created_at TIMESTAMP
);
```

Examples:

```text
Career Summary

Course Summary

Learning Path Summary
```

---

# Relationship Diagram

```text
students
    |
    ├── resumes
    |
    ├── student_skills
    |
    ├── questionnaire_responses
    |
    ├── student_career_matches
    |
    ├── career_skill_gaps
    |
    └── course_recommendations


skills
    |
    ├── skill_aliases
    |
    ├── student_skills
    |
    ├── occupation_skills
    |
    └── course_skills


occupations
    |
    ├── occupation_skills
    |
    ├── student_career_matches
    |
    ├── career_skill_gaps
    |
    └── course_recommendations


courses
    |
    ├── course_skills
    |
    └── course_recommendations
```

---

# Core Matching Query Logic

```text
Student Skills
       ↓
Compare Against
       ↓
Occupation Skills
       ↓
Calculate Match %
       ↓
Identify Missing Skills
       ↓
Find Courses Covering Missing Skills
       ↓
Generate LLM Summary
```

This schema supports:

* Top 5 career recommendations
* Skill-gap analysis
* LMS course recommendations
* Resume parsing
* Skill normalization
* Explainable match percentages
* Future AI enhancements without schema changes
