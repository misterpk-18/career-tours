from pathlib import Path

import docx2txt
from pypdf import PdfReader


class ResumeParser:
    """Text extraction from resume files.

    This used langchain_community's PyPDFLoader and Docx2txtLoader, which are thin
    wrappers over pypdf and docx2txt — both of which are already direct
    dependencies. Calling them directly drops langchain_community, langchain_core
    and langchain_classic from the image: about 58MB, and more importantly a slow
    import chain that every Lambda cold start had to pay for before serving its
    first request.
    """

    @staticmethod
    def extract_pdf_text(file_path):
        reader = PdfReader(file_path)

        # One string per page joined by newline, which is what PyPDFLoader
        # produced: it emitted a Document per page and the caller joined them.
        #
        # The .strip() per page is not cosmetic — PyPDFParser strips each page
        # before yielding it, and without it a PDF whose text begins with layout
        # padding extracts differently. One of the two resumes tested came back
        # 42 characters longer and started with whitespace instead of the
        # candidate's name.
        #
        # extract_text() returns None for a page with nothing extractable (a
        # scanned image, usually), so it is coerced rather than skipped —
        # dropping it would silently shift the page boundaries.
        return "\n".join(
            (page.extract_text() or "").strip() for page in reader.pages
        )

    @staticmethod
    def extract_docx_text(file_path):
        # Docx2txtLoader wrapped exactly this call in a single Document.
        return docx2txt.process(file_path)

    @staticmethod
    def extract_text(file_path):
        extension = Path(file_path).suffix.lower()

        if extension == ".pdf":
            return ResumeParser.extract_pdf_text(file_path)

        if extension == ".docx":
            return ResumeParser.extract_docx_text(file_path)

        raise ValueError(f"Unsupported file type: {extension}")
