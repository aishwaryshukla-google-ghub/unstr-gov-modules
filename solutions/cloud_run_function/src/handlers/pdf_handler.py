import base64
from .base import BaseDataHandler, ProcessedContent


class PDFHandler(BaseDataHandler):
    """Handler for native PDF files."""

    def convert_to_pdf(self, file_bytes: bytes, filename: str) -> bytes:
        # Native PDF: no conversion needed, validate header
        if not file_bytes.startswith(b"%PDF"):
            raise ValueError(f"File '{filename}' is not a valid PDF file.")
        return file_bytes

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        pdf_bytes = self.convert_to_pdf(file_bytes, filename)
        base64_str = base64.b64encode(pdf_bytes).decode("utf-8")
        return ProcessedContent(
            raw_bytes=pdf_bytes,
            mime_type="application/pdf",
            base64_data=base64_str,
            source_filename=filename,
            converted_to_pdf=False
        )
