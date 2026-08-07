from .base import BaseDataHandler, ProcessedContent


class TextMarkdownHandler(BaseDataHandler):
    """
    Handler for Plain Text (.txt), Markdown (.md), and formatted text files.
    Passes raw Markdown/text directly to LLMs for blazing-fast, token-efficient processing.
    """

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        text_content = file_bytes.decode("utf-8", errors="replace")
        return ProcessedContent(
            raw_bytes=file_bytes,
            mime_type="text/markdown" if filename.endswith(".md") else "text/plain",
            text_content=text_content,
            source_filename=filename,
            is_text=True,
            converted_to_pdf=False
        )
