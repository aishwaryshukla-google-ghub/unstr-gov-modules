import os
import json
import logging
import subprocess
import urllib.request
import urllib.error
from typing import Tuple, Optional

logger = logging.getLogger("auth_service")


class AuthService:
    """
    Handles Bearer Token acquisition using GCP Metadata Server in Cloud Run Functions,
    with graceful fallbacks for local development (google.auth and gcloud CLI).
    """

    @staticmethod
    def get_token_from_metadata_server() -> Optional[str]:
        """
        Fetches an OAuth2 Access Token from the GCP Compute Engine / Cloud Run Metadata Server.
        """
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        req = urllib.request.Request(metadata_url, headers={"Metadata-Flavor": "Google"})
        try:
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("access_token")
        except Exception as e:
            logger.debug(f"GCP metadata server token unavailable: {e}")
        return None

    @staticmethod
    def get_project_from_metadata_server() -> Optional[str]:
        """
        Fetches current GCP Project ID from the Metadata Server.
        """
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
        req = urllib.request.Request(metadata_url, headers={"Metadata-Flavor": "Google"})
        try:
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8").strip()
        except Exception as e:
            logger.debug(f"GCP metadata server project unavailable: {e}")
        return None

    @classmethod
    def get_bearer_token_and_project(cls, override_project: Optional[str] = None) -> Tuple[str, str]:
        # 1. Primary: Metadata server (Cloud Run Function environment)
        token = cls.get_token_from_metadata_server()
        project = override_project or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID") or cls.get_project_from_metadata_server()

        if token and project:
            return token, project

        # 2. Fallback: google.auth
        try:
            import google.auth
            from google.auth.transport.requests import Request
            credentials, detected_proj = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())
            if credentials.token:
                return credentials.token, override_project or detected_proj or project or "databricks-playground-497321"
        except Exception:
            pass

        # 3. Fallback: gcloud CLI (Local testing)
        try:
            token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
            if not project:
                project = subprocess.check_output(["gcloud", "config", "get-value", "project"], text=True).strip()
            return token, project or "databricks-playground-497321"
        except Exception as e:
            logger.error(f"Failed to acquire bearer token: {e}")
            raise RuntimeError("Could not obtain GCP Bearer Token from Metadata Server or ADC.")
