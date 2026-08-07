import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessedContent:
    """Standardized representation of processed file payload."""
    raw_bytes: bytes
    mime_type: str
    base64_data: Optional[str] = None
    text_content: Optional[str] = None
    source_filename: str = ""
    is_text: bool = False
    converted_to_pdf: bool = False


class BaseDataHandler(ABC):
    """
    Abstract Base Class contract for all unstructured document and media handlers.
    """

    def convert_to_pdf(self, file_bytes: bytes, filename: str) -> bytes:
        """
        Optional contract method: Converts input file bytes into standard PDF bytes.
        """
        return file_bytes

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        """
        Default implementation: Converts to PDF and base64 encodes.
        """
        pdf_bytes = self.convert_to_pdf(file_bytes, filename)
        base64_str = base64.b64encode(pdf_bytes).decode("utf-8")
        return ProcessedContent(
            raw_bytes=pdf_bytes,
            mime_type="application/pdf",
            base64_data=base64_str,
            source_filename=filename,
            is_text=False,
            converted_to_pdf=True
        )
