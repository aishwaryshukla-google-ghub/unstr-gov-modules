import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from .auth_service import AuthService, get_ssl_context
from handlers.base import ProcessedContent

logger = logging.getLogger("model_service")


class ModelService:
    """
    Constructs payloads and invokes multimodal foundation models on Vertex AI
    (Anthropic Claude rawPredict or Google Gemini generateContent).
    """

    @classmethod
    def invoke_model(
        cls,
        processed: ProcessedContent,
        prompt: str,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        model_name: str = "claude-3-5-sonnet-v2@20241022",
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Executes raw HTTP POST to Vertex AI model publisher endpoint using Bearer token.
        """
        token, project = AuthService.get_bearer_token_and_project(project_id)
        
        # Decide publisher provider (anthropic vs google)
        is_anthropic = "claude" in model_name.lower() or "anthropic" in model_name.lower()

        if is_anthropic:
            return cls._call_anthropic_vertex(
                processed=processed,
                prompt=prompt,
                token=token,
                project=project,
                location=location,
                model_name=model_name,
                max_tokens=max_tokens
            )
        else:
            return cls._call_gemini_vertex(
                processed=processed,
                prompt=prompt,
                token=token,
                project=project,
                location=location,
                model_name=model_name,
                max_tokens=max_tokens
            )

    @classmethod
    def _call_anthropic_vertex(
        cls,
        processed: ProcessedContent,
        prompt: str,
        token: str,
        project: str,
        location: str,
        model_name: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Claude on Vertex AI Streaming Messages API:
        POST https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/anthropic/models/{model}:streamRawPredict
        """
        # Handle global vs regional endpoint hostname
        host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
        endpoint_url = (
            f"https://{host}/v1/"
            f"projects/{project}/locations/{location}/publishers/anthropic/models/{model_name}:streamRawPredict"
        )

        content_parts = []

        # 1. Add Multimodal File Part (text, image, or document)
        if processed.is_text:
            content_parts.append({
                "type": "text",
                "text": f"--- START OF DOCUMENT ({processed.source_filename}) ---\n{processed.text_content}\n--- END OF DOCUMENT ---"
            })
        elif processed.mime_type.startswith("image/"):
            content_parts.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": processed.mime_type,
                    "data": processed.base64_data
                }
            })
        elif processed.mime_type == "application/pdf":
            content_parts.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": processed.base64_data
                }
            })
        else:
            content_parts.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": processed.base64_data
                }
            })

        # 2. Add Prompt Text Part
        content_parts.append({
            "type": "text",
            "text": prompt
        })

        # 3. Payload structured exactly as in screenshot + stream: true
        payload = {
            "anthropic_version": "vertex-2023-10-16",
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": content_parts
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Invoking Claude on Vertex streamRawPredict endpoint: {endpoint_url}")
        req = urllib.request.Request(
            endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            ssl_ctx = get_ssl_context()
            with urllib.request.urlopen(req, context=ssl_ctx) as resp:
                raw_bytes = resp.read()
                raw_str = raw_bytes.decode("utf-8")

                extracted_text = []
                usage = {}
                events = []

                # Parse Server-Sent Events (SSE) stream or JSON array
                for line in raw_str.splitlines():
                    clean_line = line.strip()
                    if not clean_line:
                        continue

                    # SSE data prefix
                    if clean_line.startswith("data:"):
                        json_str = clean_line[5:].strip()
                    else:
                        json_str = clean_line

                    try:
                        event = json.loads(json_str)
                        events.append(event)

                        # Extract text delta from streaming events
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                extracted_text.append(delta.get("text", ""))

                        # Extract usage statistics
                        if "usage" in event:
                            usage.update(event["usage"])
                        if "message" in event and "usage" in event["message"]:
                            usage.update(event["message"]["usage"])

                        # Direct non-streaming content block fallback
                        if "content" in event:
                            for part in event.get("content", []):
                                if part.get("type") == "text":
                                    extracted_text.append(part.get("text", ""))

                    except json.JSONDecodeError:
                        continue

                final_text = "".join(extracted_text)

                return {
                    "success": True,
                    "model": model_name,
                    "endpoint": ":streamRawPredict",
                    "extracted_text": final_text,
                    "usage": usage,
                    "events_count": len(events)
                }

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Claude API error HTTP {e.code}: {err_body}")
            raise RuntimeError(f"Claude on Vertex streamRawPredict failed with HTTP {e.code}: {err_body}")

    @classmethod
    def _call_gemini_vertex(
        cls,
        processed: ProcessedContent,
        prompt: str,
        token: str,
        project: str,
        location: str,
        model_name: str,
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        Google Gemini generateContent fallback endpoint.
        """
        endpoint_url = (
            f"https://aiplatform.googleapis.com/v1/"
            f"projects/{project}/locations/{location}/publishers/google/models/{model_name}:generateContent"
        )

        gemini_parts = []
        if processed.is_text:
            gemini_parts.append({
                "text": f"--- START OF DOCUMENT ({processed.source_filename}) ---\n{processed.text_content}\n--- END OF DOCUMENT ---"
            })
        else:
            gemini_parts.append({
                "inline_data": {
                    "mime_type": processed.mime_type,
                    "data": processed.base64_data
                }
            })
        gemini_parts.append({"text": prompt})

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": gemini_parts
                }
            ],
            "generation_config": {
                "temperature": 0.2,
                "maxOutputTokens": max_tokens
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        logger.info(f"Invoking Gemini on Vertex endpoint: {endpoint_url}")
        req = urllib.request.Request(
            endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            ssl_ctx = get_ssl_context()
            with urllib.request.urlopen(req, context=ssl_ctx) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                candidates = resp_data.get("candidates", [])
                extracted_text = ""
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    extracted_text = "".join(p.get("text", "") for p in parts)

                return {
                    "success": True,
                    "model": model_name,
                    "extracted_text": extracted_text,
                    "usage": resp_data.get("usageMetadata", {}),
                    "raw_response": resp_data
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Gemini API error HTTP {e.code}: {err_body}")
            raise RuntimeError(f"Gemini on Vertex failed with HTTP {e.code}: {err_body}")
