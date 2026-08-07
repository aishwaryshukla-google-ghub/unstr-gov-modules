import os
import urllib.parse
import urllib.request
import urllib.error
from typing import Tuple
from .auth_service import AuthService


class GCSService:
    """
    Downloads file bytes from Google Cloud Storage (GCS) URIs (gs://bucket/object/path).
    Supports both direct GCS Client and REST API fallback using Metadata Server Bearer Token.
    """

    @staticmethod
    def parse_gcs_uri(gcs_uri: str) -> Tuple[str, str, str]:
        """
        Parses gs://bucket_name/path/to/file.ext into (bucket_name, blob_name, filename).
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"Invalid GCS URI: '{gcs_uri}'. Must start with 'gs://'.")

        path_part = gcs_uri[5:]
        parts = path_part.split("/", 1)
        if len(parts) < 2 or not parts[1]:
            raise ValueError(f"Invalid GCS URI '{gcs_uri}': missing object path.")

        bucket_name = parts[0]
        blob_name = parts[1]
        filename = os.path.basename(blob_name)
        return bucket_name, blob_name, filename

    @classmethod
    def download_file_bytes(cls, gcs_uri: str) -> Tuple[bytes, str]:
        """
        Downloads the target object bytes from GCS. Returns (file_bytes, filename).
        """
        # Local file bypass for testing
        if os.path.exists(gcs_uri):
            with open(gcs_uri, "rb") as f:
                return f.read(), os.path.basename(gcs_uri)

        bucket_name, blob_name, filename = cls.parse_gcs_uri(gcs_uri)

        # 1. Try google-cloud-storage if installed
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return blob.download_as_bytes(), filename
        except Exception:
            pass

        # 2. REST API fallback using Bearer Token
        token, _ = AuthService.get_bearer_token_and_project()
        encoded_blob = urllib.parse.quote(blob_name, safe="")
        download_url = f"https://storage.googleapis.com/download/storage/v1/b/{bucket_name}/o/{encoded_blob}?alt=media"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        req = urllib.request.Request(download_url, headers=headers)
        try:
            from .auth_service import get_ssl_context
            with urllib.request.urlopen(req, context=get_ssl_context()) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"GCS Download failed with HTTP {resp.status}")
                return resp.read(), filename
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"GCS Download failed for '{gcs_uri}': HTTP {e.code} - {e.read().decode('utf-8')}")
