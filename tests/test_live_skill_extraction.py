"""
LIVE integration test — calls real OpenAI API.

Run this manually only (not in CI), as it:
  - Costs API credits
  - Requires OPENAI_API_KEY in .env

Usage:
    conda run -n career-tours python -m pytest tests/test_live_skill_extraction.py -v -s

What this tests:
  1. Parses the real PDF resume (Manoj_Tungala_CV.pdf)
  2. Sends the real resume text to the real OpenAI API (gpt-5)
  3. Prints and asserts on the actual extracted skills
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from services.resume.parser import ResumeParser
from services.llm.openai_service import OpenAIService

load_dotenv()

PDF_PATH = Path(__file__).parent / "Manoj_Tungala_CV.pdf"

# Skip the entire module if no API key is configured
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping live LLM tests",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_skills(label: str, skills: list) -> None:
    print(f"\n{'='*60}")
    print(f"  {label} ({len(skills)} skills)")
    print(f"{'='*60}")
    for s in skills:
        bar = "█" * int(s.confidence * 10)
        print(
            f"  {s.skill_name:<30} "
            f"proficiency={s.proficiency:>2}/10  "
            f"confidence={s.confidence:.2f} [{bar:<10}]  "
            f"source={s.source}"
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def resume_text():
    """Parse the real PDF once and share across all tests in this module."""
    assert PDF_PATH.exists(), f"PDF not found: {PDF_PATH}"
    text = ResumeParser.extract_text(str(PDF_PATH))
    assert len(text) > 100, "PDF extraction returned too little text"
    return text


@pytest.fixture(scope="module")
def student_profile(resume_text):
    """
    Call the real OpenAI API once and share the result across tests.
    This is the expensive fixture — it actually calls gpt-5.
    """
    print(f"\n[INFO] Sending {len(resume_text)} chars of resume text to OpenAI...")
    llm = OpenAIService()
    profile = llm.extract_skills(resume_text, questionnaire_answers=None)
    print("[INFO] OpenAI responded successfully.")
    return profile


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLiveSkillExtraction:

    def test_profile_has_summary(self, student_profile):
        """LLM produces a non-empty summary of the candidate."""
        print(f"\n\n{'='*60}")
        print("  CANDIDATE SUMMARY")
        print(f"{'='*60}")
        print(f"  {student_profile.summary}")
        assert isinstance(student_profile.summary, str)
        assert len(student_profile.summary.strip()) > 20

    def test_technical_skills_extracted(self, student_profile):
        """LLM identifies at least 3 technical skills."""
        _print_skills("TECHNICAL SKILLS", student_profile.technical_skills)
        assert len(student_profile.technical_skills) >= 3, (
            "Expected at least 3 technical skills from the resume"
        )

    def test_soft_skills_extracted(self, student_profile):
        """LLM identifies at least 1 soft skill."""
        _print_skills("SOFT SKILLS", student_profile.soft_skills)
        assert len(student_profile.soft_skills) >= 1

    def test_domain_skills_extracted(self, student_profile):
        """LLM identifies at least 1 domain skill."""
        _print_skills("DOMAIN SKILLS", student_profile.domain_skills)
        assert len(student_profile.domain_skills) >= 1

    def test_all_skills_have_valid_confidence(self, student_profile):
        """All skills have confidence scores between 0 and 1."""
        all_skills = (
            student_profile.technical_skills
            + student_profile.soft_skills
            + student_profile.domain_skills
        )
        for skill in all_skills:
            assert 0.0 <= skill.confidence <= 1.0, (
                f"Invalid confidence {skill.confidence} for skill: {skill.skill_name}"
            )

    def test_all_skills_have_valid_proficiency(self, student_profile):
        """All skills have proficiency ratings between 1 and 10."""
        all_skills = (
            student_profile.technical_skills
            + student_profile.soft_skills
            + student_profile.domain_skills
        )
        for skill in all_skills:
            assert 1 <= skill.proficiency <= 10, (
                f"Invalid proficiency {skill.proficiency} for skill: {skill.skill_name}"
            )

    def test_all_skills_have_names(self, student_profile):
        """No skill should have a blank name."""
        all_skills = (
            student_profile.technical_skills
            + student_profile.soft_skills
            + student_profile.domain_skills
        )
        for skill in all_skills:
            assert skill.skill_name and skill.skill_name.strip(), (
                "Found a skill with an empty name"
            )

    def test_print_full_skill_report(self, student_profile):
        """Prints a complete skill extraction report for manual review."""
        all_skills = (
            student_profile.technical_skills
            + student_profile.soft_skills
            + student_profile.domain_skills
        )

        print(f"\n\n{'='*60}")
        print("  FULL SKILL EXTRACTION REPORT")
        print(f"{'='*60}")
        print(f"  Total skills extracted: {len(all_skills)}")
        print(f"    Technical : {len(student_profile.technical_skills)}")
        print(f"    Soft      : {len(student_profile.soft_skills)}")
        print(f"    Domain    : {len(student_profile.domain_skills)}")

        _print_skills("TECHNICAL SKILLS", student_profile.technical_skills)
        _print_skills("SOFT SKILLS",      student_profile.soft_skills)
        _print_skills("DOMAIN SKILLS",    student_profile.domain_skills)

        print(f"\n{'='*60}")
        print("  SUMMARY")
        print(f"{'='*60}")
        print(f"  {student_profile.summary}")
        print(f"{'='*60}\n")

        # Always passes — this is a reporting test
        assert True
