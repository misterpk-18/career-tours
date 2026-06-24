"""
Integration test: parse the real PDF resume and verify skill extraction.

Uses the actual PDF file at tests/Manoj_Tungala_CV.pdf.

- ResumeParser.extract_text() runs REAL (no mock) — verifies the PDF
  can actually be read and produces meaningful text.
- OpenAI LLM is MOCKED — we don't want to call the real API in tests,
  but we do verify that the structured output flows through correctly.
- DB / S3 calls are MOCKED.
"""

import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.resume.parser import ResumeParser
from services.llm.schemas.skill import Skill
from services.llm.schemas.student_profile import StudentProfile

# Path to the test fixture PDF
PDF_PATH = Path(__file__).parent / "Manoj_Tungala_CV.pdf"

# ---------------------------------------------------------------------------
# Section 1: Real PDF text extraction (no mocks)
# ---------------------------------------------------------------------------

class TestPdfTextExtraction:

    def test_pdf_exists(self):
        """Confirm the test fixture PDF is present."""
        assert PDF_PATH.exists(), f"PDF not found at: {PDF_PATH}"

    def test_pdf_extract_returns_nonempty_text(self):
        """ResumeParser produces non-empty text from the real PDF."""
        text = ResumeParser.extract_text(str(PDF_PATH))
        assert isinstance(text, str)
        assert len(text) > 100, "Expected substantial text from resume PDF"

    def test_pdf_text_contains_name(self):
        """Extracted text contains the candidate's name."""
        text = ResumeParser.extract_text(str(PDF_PATH))
        assert "Manoj" in text or "MANOJ" in text or "manoj" in text.lower()

    def test_pdf_text_contains_technical_keywords(self):
        """Extracted text contains at least some expected technical keywords."""
        text = ResumeParser.extract_text(str(PDF_PATH)).lower()
        # Check for at least 3 of these common resume keywords
        common_tech_terms = [
            "python", "sql", "java", "javascript", "react", "flask",
            "django", "machine learning", "deep learning", "tensorflow",
            "pytorch", "git", "docker", "aws", "api", "html", "css",
            "node", "kubernetes", "linux", "data", "software", "engineer",
        ]
        found = [t for t in common_tech_terms if t in text]
        print(f"\nTechnical keywords found in resume: {found}")
        assert len(found) >= 3, (
            f"Expected at least 3 tech keywords, only found: {found}"
        )

    def test_pdf_text_length_reasonable(self):
        """Resume text should be between 200 and 50,000 characters."""
        text = ResumeParser.extract_text(str(PDF_PATH))
        assert 200 <= len(text) <= 50_000, (
            f"Unexpected text length: {len(text)} chars"
        )

    def test_pdf_unsupported_extension_raises(self, tmp_path):
        """extract_text raises ValueError for unsupported file types."""
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("hello world")
        with pytest.raises(ValueError, match="Unsupported"):
            ResumeParser.extract_text(str(txt_file))


# ---------------------------------------------------------------------------
# Section 2: Mocked skill extraction pipeline on real PDF text
# ---------------------------------------------------------------------------

class TestSkillExtractionFromRealPdf:

    def _make_mock_profile(self, tech_skills: list[str]) -> StudentProfile:
        """Build a fake StudentProfile that mimics what OpenAI would return."""
        return StudentProfile(
            technical_skills=[
                Skill(
                    skill_name=name,
                    confidence=0.9,
                    proficiency=7,
                    source="resume",
                )
                for name in tech_skills
            ],
            soft_skills=[
                Skill(skill_name="Communication", confidence=0.8, proficiency=6, source="resume"),
                Skill(skill_name="Teamwork",      confidence=0.75, proficiency=6, source="resume"),
            ],
            domain_skills=[
                Skill(skill_name="Web Development", confidence=0.85, proficiency=7, source="resume"),
            ],
            summary="A skilled software developer with experience in Python and web technologies.",
        )

    def test_real_pdf_text_fed_to_extractor(self):
        """
        Verifies the real PDF text flows into the LLM extractor.

        1. Parses the real PDF → real raw_text
        2. Mocks OpenAI to return a structured StudentProfile
        3. Mocks DB saves
        4. Asserts the pipeline returns expected structure
        """
        real_text = ResumeParser.extract_text(str(PDF_PATH))
        assert len(real_text) > 100

        project_id = uuid.uuid4()
        mock_profile = self._make_mock_profile(["Python", "Flask", "SQL", "Git"])

        saved_skills = [
            {
                "student_skill_id": str(uuid.uuid4()),
                "student_id":       str(uuid.uuid4()),
                "skill_id":         str(uuid.uuid4()),
                "skill_name":       s.skill_name,
                "proficiency_level": "intermediate",
                "confidence_score":  s.confidence,
                "source":           s.source,
                "created_at":       datetime(2024, 6, 1, 12, 0),
            }
            for s in mock_profile.technical_skills
        ]

        with (
            patch("services.resume.extractor.OpenAIService") as mock_openai_cls,
            patch("services.resume.extractor.SkillNormalizer.normalize_skill_list") as mock_normalize,
            patch("services.resume.extractor.SkillNormalizer.map_to_skill_ids")    as mock_map,
            patch("services.resume.extractor.ProjectSkillRepository.bulk_create"),
            patch("services.resume.extractor.ProjectSkillRepository.get_by_project_id", return_value=saved_skills),
        ):
            # Configure the mock LLM to return our fake profile
            mock_llm = MagicMock()
            mock_llm.extract_skills.return_value = mock_profile
            mock_openai_cls.return_value = mock_llm

            # Normalizer passes skills through as-is for this test
            all_skills = (
                mock_profile.technical_skills
                + mock_profile.soft_skills
                + mock_profile.domain_skills
            )
            mock_normalize.return_value = all_skills
            mock_map.return_value = all_skills

            from services.resume.extractor import ResumeSkillExtractor
            result = ResumeSkillExtractor.extract_and_save(
                project_id,
                real_text,      # ← real text from the PDF
                questionnaire_answers=None,
            )

        # Verify the LLM was called with the real resume text
        mock_llm.extract_skills.assert_called_once_with(real_text, None)

        # Verify result structure
        assert "summary" in result
        assert "skills_saved" in result
        assert "skills" in result
        assert result["skills_saved"] > 0
        print(f"\nSkills extracted from real PDF (mocked LLM): {[s['skill_name'] for s in result['skills']]}")
        print(f"Summary: {result['summary']}")

    def test_real_pdf_text_is_passed_correctly(self):
        """
        Smoke test: confirms the raw PDF text isn't empty when passed
        into the skill extraction pipeline entry point.
        """
        real_text = ResumeParser.extract_text(str(PDF_PATH))
        # Should have meaningful content, not whitespace-only
        assert real_text.strip(), "PDF produced only whitespace"
        # Should contain at least a few words
        word_count = len(real_text.split())
        print(f"\nWord count in extracted resume text: {word_count}")
        assert word_count >= 50, f"Too few words extracted: {word_count}"
