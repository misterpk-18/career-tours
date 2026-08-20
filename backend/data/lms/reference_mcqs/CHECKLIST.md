# Tier A reference MCQ collection

Courses where multiple choice alone is a defensible assessment, because the
industry itself certifies the skill with a multiple-choice exam. For each one a
subagent gathers publicly available MCQs, filters to the ten best, and records
where every item came from.

**These are reference material, not corpus content.** They live here rather than
in `data/lms/questions/` deliberately: they are for calibrating what "hard"
should mean per course, and for checking our generated questions against how the
real certification exams pitch difficulty. Items sourced from third-party sites
carry their source URL and are marked verbatim or adapted. Nothing here should be
loaded into `course_section_questions` without a licensing decision first.

## Status

| # | Course | Code | Collected | Filtered to 10 | File | Notes |
|---|--------|------|-----------|----------------|------|-------|
| 1 | AWS Cloud | NT-C-026 | ☑ | ☑ | `NT-C-026.json` | 10 questions, 10 adapted / 0 verbatim, 9 sources — verified CLEAN |
| 2 | Azure Cloud | NT-C-027 | ☑ | ☑ | `NT-C-027.json` | 10 questions, 10 adapted / 0 verbatim, 9 sources — verified CLEAN |
| 3 | Cloud Computing | NT-C-028 | ☑ | ☑ | `NT-C-028.json` | 10 questions, 10 adapted / 0 verbatim, 10 sources — verified CLEAN |
| 4 | Hardware and Networking | NT-C-030 | ☑ | ☑ | `NT-C-030.json` | 10 questions, 10 adapted / 0 verbatim, 7 sources — verified CLEAN |
| 5 | CCNA | NT-C-031 | ☐ | ☐ | | collector hit the session limit before writing; needs a re-run |
| 6 | Cyber Security | NT-C-032 | ☑ | ☑ | `NT-C-032.json` | 10 questions, 10 adapted / 0 verbatim, 10 sources — verified CLEAN |
| 7 | SAP FICO | NT-C-039 | ☑ | ☑ | `NT-C-039.json` | 10 questions, 10 adapted / 0 verbatim, 10 sources — verified CLEAN |
| 8 | ServiceNow | NT-C-040 | ☑ | ☑ | `NT-C-040.json` | 10 questions, 10 adapted / 0 verbatim, 10 sources — verified CLEAN |

## Selection criteria given to each collector

1. **Grounded in this course.** The item must map to a skill in the course's own
   `data/lms/extracted/<code>.json` and to a module in
   `data/lms/modules/<code>.json`. A correct AWS question about a service this
   course never teaches is not useful.
2. **Hard, by the corpus definition.** Answerable only by someone who understands
   the mechanism — not by recognising a term. The banned glossary forms are the
   same ones the generator prohibits: "What is X?", "Which best describes X?",
   "What is the purpose of X?".
3. **Substantive distractors.** Each wrong option is a belief a half-learned
   candidate actually holds.
4. **Attributed.** Source name and URL on every item, and `verbatim` or `adapted`
   recorded honestly.
5. **Prefer adapted over verbatim.** Rewriting the scenario while keeping the
   concept avoids copying someone's expression and usually makes a better fit to
   the course anyway.

## Output shape

One file per course, `NT-C-0XX.json`:

```json
{
  "course_code": "NT-C-026",
  "course_name": "AWS Cloud",
  "sources": [{"name": "...", "url": "...", "note": "terms/licence observed"}],
  "questions": [
    {
      "question_number": 1,
      "stem": "string",
      "options": ["a", "b", "c", "d"],
      "correct_option": "A",
      "explanation": "why the key is right",
      "distractor_rationale": "why each wrong option tempts",
      "skills_covered": ["exact name from the course skill list"],
      "difficulty": "hard | medium",
      "source_name": "string",
      "source_url": "string",
      "provenance": "verbatim | adapted"
    }
  ]
}
```
