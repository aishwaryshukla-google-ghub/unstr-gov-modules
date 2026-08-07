import io
from .base import BaseDataHandler, ProcessedContent


class DocxHandler(BaseDataHandler):
    """
    Handler for Microsoft Word (.docx) documents.
    Extracts headings, paragraphs, and tables directly into structured Markdown text.
    Bypasses PDF layout overhead and ensures zero loss of textual context.
    """

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        try:
            import docx

            doc = docx.Document(io.BytesIO(file_bytes))
            md_lines = [f"--- START OF WORD DOCUMENT ({filename}) ---", ""]

            # 1. Extract Paragraphs
            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue

                if p.style and p.style.name.startswith("Heading 1"):
                    md_lines.append(f"# {text}")
                elif p.style and p.style.name.startswith("Heading 2"):
                    md_lines.append(f"## {text}")
                elif p.style and p.style.name.startswith("Heading 3"):
                    md_lines.append(f"### {text}")
                else:
                    md_lines.append(text)

            # 2. Extract Tables into Markdown Tables
            if doc.tables:
                md_lines.append("\n### Document Tables:\n")
                for t_idx, table in enumerate(doc.tables):
                    md_lines.append(f"#### Table {t_idx + 1}")
                    for r_idx, row in enumerate(table.rows):
                        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        md_lines.append("| " + " | ".join(cells) + " |")
                        if r_idx == 0:
                            md_lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
                    md_lines.append("")

            md_lines.append(f"--- END OF WORD DOCUMENT ({filename}) ---")
            combined_text = "\n".join(md_lines)

            return ProcessedContent(
                raw_bytes=file_bytes,
                mime_type="text/markdown",
                text_content=combined_text,
                source_filename=filename,
                is_text=True,
                converted_to_pdf=False
            )

        except Exception as e:
            return ProcessedContent(
                raw_bytes=file_bytes,
                mime_type="text/plain",
                text_content=f"Word document parse fallback ({filename}): {str(e)}",
                source_filename=filename,
                is_text=True,
                converted_to_pdf=False
            )
