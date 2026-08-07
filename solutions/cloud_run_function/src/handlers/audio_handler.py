import base64
from .base import BaseDataHandler, ProcessedContent


class AudioHandler(BaseDataHandler):
    """
    Handler for audio files (MP3, WAV, M4A, AAC, OGG, FLAC).
    Preserves native audio stream for multimodal acoustic processing.
    """

    MIME_MAP = {
        "mp3": "audio/mp3",
        "wav": "audio/wav",
        "m4a": "audio/m4a",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "flac": "audio/flac"
    }

    def convert_to_pdf(self, file_bytes: bytes, filename: str) -> bytes:
        raise NotImplementedError("Audio files cannot be converted to PDF; pass directly as audio stream.")

    def process(self, file_bytes: bytes, filename: str) -> ProcessedContent:
        ext = filename.split(".")[-1].lower() if "." in filename else "mp3"
        mime_type = self.MIME_MAP.get(ext, "audio/mp3")
        base64_str = base64.b64encode(file_bytes).decode("utf-8")

        return ProcessedContent(
            raw_bytes=file_bytes,
            mime_type=mime_type,
            base64_data=base64_str,
            source_filename=filename,
            converted_to_pdf=False
        )
