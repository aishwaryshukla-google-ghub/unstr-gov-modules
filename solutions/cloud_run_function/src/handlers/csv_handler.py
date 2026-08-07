from .base import BaseDataHandler, ProcessedContent


class CSVHandler(BaseDataHandler):
    """
    Handler for CSV and TSV files.
    Passes raw tabular delimited text directly to the LLM for instantaneous, lossless parsing.
    """

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        text_content = file_bytes.decode("utf-8", errors="replace")
        
        formatted_text = (
            f"--- START OF CSV FILE ({filename}) ---\n"
            f"{text_content}\n"
            f"--- END OF CSV FILE ({filename}) ---"
        )

        return ProcessedContent(
            raw_bytes=file_bytes,
            mime_type="text/csv",
            text_content=formatted_text,
            source_filename=filename,
            is_text=True,
            converted_to_pdf=False
        )
