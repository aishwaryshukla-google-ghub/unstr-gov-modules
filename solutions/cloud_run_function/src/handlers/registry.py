from typing import Dict
from .base import BaseDataHandler
from .pdf_handler import PDFHandler
from .image_handler import ImageHandler
from .audio_handler import AudioHandler
from .text_md_handler import TextMarkdownHandler
from .csv_handler import CSVHandler
from .excel_handler import ExcelHandler
from .docx_handler import DocxHandler


class HandlerRegistry:
    """
    Central registry and dispatcher for file type handlers.
    """

    def __init__(self):
        self._handlers: Dict[str, BaseDataHandler] = {}
        self._setup_defaults()

    def register(self, extensions: list, handler: BaseDataHandler):
        for ext in extensions:
            clean_ext = ext.lower().lstrip(".")
            self._handlers[clean_ext] = handler

    def _setup_defaults(self):
        pdf_h = PDFHandler()
        img_h = ImageHandler()
        aud_h = AudioHandler()
        txt_h = TextMarkdownHandler()
        csv_h = CSVHandler()
        xls_h = ExcelHandler()
        doc_h = DocxHandler()

        # 1. Native PDF
        self.register(["pdf"], pdf_h)

        # 2. Images (native image multimodal payload)
        self.register(["png", "jpg", "jpeg", "webp", "gif", "heic", "tiff", "tif"], img_h)

        # 3. Audio (native audio multimodal payload)
        self.register(["mp3", "wav", "m4a", "aac", "ogg", "flac"], aud_h)

        # 4. Text & Markdown (converted to structured PDF)
        self.register(["txt", "md", "markdown", "log", "json", "yaml", "yml"], txt_h)

        # 5. Tabular CSV (converted to structured PDF table)
        self.register(["csv", "tsv"], csv_h)

        # 6. Spreadsheets (converted to structured PDF tables)
        self.register(["xlsx", "xls"], xls_h)

        # 7. Word Documents (converted to structured PDF pages)
        self.register(["docx", "doc"], doc_h)

    def get_handler(self, filename_or_ext: str) -> BaseDataHandler:
        if "." in filename_or_ext:
            ext = filename_or_ext.split("?")[0].split("#")[0].split(".")[-1].lower()
        else:
            ext = filename_or_ext.lower().lstrip(".")

        handler = self._handlers.get(ext)
        if not handler:
            # Fallback to TextMarkdown handler for arbitrary unknown text formats
            return self._handlers["txt"]
        return handler


# Global shared instance
registry = HandlerRegistry()
