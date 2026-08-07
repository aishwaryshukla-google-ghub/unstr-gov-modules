import io
import base64
from typing import Optional
from .base import BaseDataHandler, ProcessedContent


class ImageHandler(BaseDataHandler):
    """
    Handler for image files (PNG, JPEG, WEBP, GIF, HEIC, TIFF).
    Passes through native image MIME format directly for multimodal processing.
    """

    MIME_MAP = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "heic": "image/heic",
        "tiff": "image/tiff",
        "tif": "image/tiff"
    }

    def convert_to_pdf(self, file_bytes: bytes, filename: str) -> bytes:
        """
        Converts image to a single-page PDF if PDF format is explicitly demanded.
        """
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            out_pdf = io.BytesIO()
            img.save(out_pdf, format="PDF", resolution=100.0)
            return out_pdf.getvalue()
        except ImportError:
            raise NotImplementedError("PIL/Pillow required for image to PDF conversion.")

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        """
        Processes image directly in its native image format for the multimodal model.
        """
        ext = filename.split(".")[-1].lower() if "." in filename else "png"
        mime_type = self.MIME_MAP.get(ext, "image/png")
        base64_str = base64.b64encode(file_bytes).decode("utf-8")
        
        return ProcessedContent(
            raw_bytes=file_bytes,
            mime_type=mime_type,
            base64_data=base64_str,
            source_filename=filename,
            converted_to_pdf=False
        )
