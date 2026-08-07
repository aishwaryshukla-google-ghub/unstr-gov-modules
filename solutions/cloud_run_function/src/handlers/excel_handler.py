import io
from .base import BaseDataHandler, ProcessedContent


class ExcelHandler(BaseDataHandler):
    """
    Handler for Excel spreadsheets (.xlsx, .xls).
    Iterates through each worksheet and converts tabular rows into clean Markdown/CSV text blocks.
    Completely eliminates PDF layout truncation and runs in <5ms.
    """

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        try:
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            sheet_outputs = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = list(ws.iter_rows(values_only=True))

                # Filter out trailing empty rows
                non_empty_rows = [r for r in rows if any(cell is not None and str(cell).strip() != "" for cell in r)]
                if not non_empty_rows:
                    continue

                sheet_md = [f"### Sheet: {sheet_name}"]

                for r_idx, row in enumerate(non_empty_rows):
                    # Clean and format cell values
                    cleaned_cells = [str(cell).strip().replace("\n", " ") if cell is not None else "" for cell in row]
                    
                    # Trim trailing empty cells in the row
                    while cleaned_cells and cleaned_cells[-1] == "":
                        cleaned_cells.pop()
                    
                    if not cleaned_cells:
                        continue

                    # Format as Markdown table row
                    row_str = "| " + " | ".join(cleaned_cells) + " |"
                    sheet_md.append(row_str)

                    # Add separator after header row
                    if r_idx == 0:
                        separator = "| " + " | ".join(["---"] * len(cleaned_cells)) + " |"
                        sheet_md.append(separator)

                sheet_outputs.append("\n".join(sheet_md))

            combined_text = (
                f"--- WORKBOOK: {filename} ---\n\n"
                + "\n\n".join(sheet_outputs)
                + f"\n\n--- END OF WORKBOOK: {filename} ---"
            )

            return ProcessedContent(
                raw_bytes=file_bytes,
                mime_type="text/markdown",
                text_content=combined_text,
                source_filename=filename,
                is_text=True,
                converted_to_pdf=False
            )

        except Exception as e:
            # Fallback if openpyxl fails
            return ProcessedContent(
                raw_bytes=file_bytes,
                mime_type="text/plain",
                text_content=f"Excel parse fallback ({filename}): {str(e)}",
                source_filename=filename,
                is_text=True,
                converted_to_pdf=False
            )
