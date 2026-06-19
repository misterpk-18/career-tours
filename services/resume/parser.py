from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader
)


class ResumeParser:

    @staticmethod
    def extract_pdf_text(file_path):
        loader = PyPDFLoader(file_path)

        documents = loader.load()

        return "\n".join(
            doc.page_content
            for doc in documents
        )

    @staticmethod
    def extract_docx_text(file_path):
        loader = Docx2txtLoader(file_path)

        documents = loader.load()

        return "\n".join(
            doc.page_content
            for doc in documents
        )

    @staticmethod
    def extract_text(file_path):
        extension = Path(file_path).suffix.lower()

        if extension == ".pdf":
            return ResumeParser.extract_pdf_text(
                file_path
            )

        if extension == ".docx":
            return ResumeParser.extract_docx_text(
                file_path
            )

        raise ValueError(
            f"Unsupported file type: {extension}"
        )