import io
import csv
from .base import BaseDataHandler


class CSVHandler(BaseDataHandler):
    """
    Handler for CSV files.
    Converts tabular CSV rows and headers into a structured PDF table.
    """

    def convert_to_pdf(self, file_bytes: bytes, filename: str) -> bytes:
        text_content = file_bytes.decode("utf-8", errors="replace")
        csv_reader = csv.reader(io.StringIO(text_content))
        rows = list(csv_reader)

        if not rows:
            return b"%PDF-1.4\n% Empty CSV"

        try:
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            buffer = io.BytesIO()
            # Landscape orientation is better for wide tabular data
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(letter),
                rightMargin=20,
                leftMargin=20,
                topMargin=20,
                bottomMargin=20
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "TableTitle",
                parent=styles["Heading2"],
                fontSize=14,
                leading=16,
                textColor=colors.HexColor("#1a73e8"),
                spaceAfter=8
            )
            cell_style = ParagraphStyle(
                "TableCell",
                parent=styles["Normal"],
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#202124")
            )
            header_style = ParagraphStyle(
                "TableHeader",
                parent=styles["Normal"],
                fontSize=8,
                leading=10,
                fontName="Helvetica-Bold",
                textColor=colors.white
            )

            story = [Paragraph(f"Table Data: {filename}", title_style), Spacer(1, 6)]

            # Convert cells to Paragraph flowables for word wrapping
            table_data = []
            for r_idx, row in enumerate(rows[:200]):  # Cap at 200 rows to prevent memory explosion
                formatted_row = []
                for cell in row:
                    safe_cell = cell.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    p = Paragraph(safe_cell, header_style if r_idx == 0 else cell_style)
                    formatted_row.append(p)
                table_data.append(formatted_row)

            if table_data:
                t = Table(table_data, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dadce0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                ]))
                story.append(t)

            doc.build(story)
            return buffer.getvalue()

        except ImportError:
            # Fallback simple text-based rendering
            from .text_md_handler import TextMarkdownHandler
            return TextMarkdownHandler().convert_to_pdf(file_bytes, filename)
