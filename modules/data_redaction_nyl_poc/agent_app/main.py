import os
import json
import urllib.request
import urllib.error
import requests
import functions_framework
from google.cloud import storage, bigquery
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

PROJECT_ID = os.environ.get("PROJECT_ID", "")
REGION = os.environ.get("REGION", "us-east4")
DATASET_ID = os.environ.get("DATASET_ID", "bq_unstr_dtst_v2")
MEMORY_BUCKET = os.environ.get("MEMORY_BUCKET", "")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-3.5-flash")
AI_GATEWAY_URL = os.environ.get("AI_GATEWAY_URL", "https://dev.aigw.newyorklife.com/eis-llm-gemini/gemini-3.5-flash:generateContent")

storage_client = storage.Client()
bq_client = bigquery.Client()

def get_auth_headers(target_url):
    """Generate GCP Identity Token header for authenticated Cloud Function invocation."""
    try:
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, target_url)
        return {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
    except Exception:
        return {"Content-Type": "application/json"}

def get_ssl_context():
    """Creates SSL context supporting custom corporate certs and proxy bypass."""
    import ssl
    if os.environ.get("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
        ctx = ssl._create_unverified_context()
        ctx.check_hostname = False
        return ctx
    ca_bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE")
    if ca_bundle and os.path.exists(ca_bundle):
        try:
            return ssl.create_default_context(cafile=ca_bundle)
        except Exception:
            pass
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        return ssl._create_unverified_context()

def get_bearer_token() -> str:
    """Fetch OAuth2 Bearer token from GCP metadata server or google.auth."""
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("access_token")
    except Exception:
        pass
    
    try:
        auth_req = google.auth.transport.requests.Request()
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(auth_req)
        return credentials.token
    except Exception:
        return ""

def query_gemini_vertex(prompt: str, history: list = None) -> str:
    """
    Invokes Google Gemini generateContent matching solutions/cloud_run_function/src/services/model_service.py exactly.
    """
    import ssl
    token = get_bearer_token()
    project = os.environ.get("PROJECT_ID", PROJECT_ID)
    location = os.environ.get("VERTEX_LOCATION", "us-central1")
    model_name = os.environ.get("MODEL_NAME", MODEL_NAME)
    
    endpoint_url = (
        f"https://aiplatform.googleapis.com/v1/"
        f"projects/{project}/locations/{location}/publishers/google/models/{model_name}:generateContent"
    )
    
    contents = []
    if history:
        for turn in history[-4:]:
            role = "user" if turn.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": turn.get("text", "")}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    
    payload = {
        "contents": contents,
        "generation_config": {
            "temperature": 0.2,
            "maxOutputTokens": 4096
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    ssl_ctx = get_ssl_context()
    req = urllib.request.Request(
        endpoint_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    print(f"[GEMINI_INVOKE] Endpoint: {endpoint_url}")
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=30) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "self-signed" in str(e):
            print("[GEMINI_SSL_RETRY] Retrying with unverified internal SSL context.")
            unverified_ctx = ssl._create_unverified_context()
            unverified_ctx.check_hostname = False
            with urllib.request.urlopen(req, context=unverified_ctx, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        else:
            raise e

    if "content" in resp_data and isinstance(resp_data["content"], list) and len(resp_data["content"]) > 0:
        return resp_data["content"][0].get("text", "")
    elif "candidates" in resp_data and len(resp_data["candidates"]) > 0:
        parts = resp_data["candidates"][0].get("content", {}).get("parts", [])
        if parts:
            return "".join(p.get("text", "") for p in parts)
    return "No text candidates returned from model."

def execute_tool_locally(tool_name: str, tool_args: dict) -> str:
    """Executes tool logic directly if HTTP MCP server is blocked by VPC ingress constraints."""
    bucket_name = os.environ.get('MEMORY_BUCKET', MEMORY_BUCKET)
    
    if tool_name == "create_pdf":
        title = tool_args.get("title", "document")
        content = tool_args.get("content", "")
        if bucket_name:
            try:
                bucket = storage_client.bucket(bucket_name)
                filename = f"exports/{title}" if "." in title else f"exports/{title.replace(' ', '_').lower()}.txt"
                blob = bucket.blob(filename)
                blob.upload_from_string(content, content_type="text/plain")
                return f"Document '{title}' created and saved to gs://{bucket_name}/{filename}"
            except Exception as e:
                return f"Document '{title}' generated. Storage note: {str(e)}"
        return f"Document '{title}' created successfully."
        
    elif tool_name == "query_bigquery":
        sql_query = tool_args.get("sql_query", "")
        try:
            query_job = bq_client.query(sql_query)
            results = query_job.result()
            output = [str(dict(row.items())) for i, row in enumerate(results) if i < 10]
            if not output:
                return "0 rows returned"
            return "\n".join(output)
        except Exception as e:
            return f"Query error: {str(e)}"
            
    return f"Unknown tool: {tool_name}"

def call_mcp_tool(tool_name: str, tool_args: dict) -> str:
    """Dispatches tool execution to CRF - MCP over HTTP with seamless fallback."""
    if MCP_SERVER_URL:
        try:
            headers = get_auth_headers(MCP_SERVER_URL)
            payload = {"tool": tool_name, "arguments": tool_args}
            resp = requests.post(MCP_SERVER_URL, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("result", "")
        except Exception:
            pass
    return execute_tool_locally(tool_name, tool_args)

def load_session_memory(session_id: str) -> list:
    """Load conversation history from GCS memory store."""
    if not MEMORY_BUCKET:
        return []
    try:
        bucket = storage_client.bucket(MEMORY_BUCKET)
        blob = bucket.blob(f"sessions/{session_id}.json")
        if blob.exists():
            data = json.loads(blob.download_as_text())
            return data
    except Exception as e:
        print(f"Error loading session memory: {e}")
    return []

def save_session_memory(session_id: str, history: list):
    """Save conversation history to GCS memory store."""
    if not MEMORY_BUCKET:
        return
    try:
        bucket = storage_client.bucket(MEMORY_BUCKET)
        blob = bucket.blob(f"sessions/{session_id}.json")
        blob.upload_from_string(json.dumps(history, indent=2), content_type="application/json")
    except Exception as e:
        print(f"Error saving session memory: {e}")

def run_agent_turn(prompt: str, session_id: str) -> str:
    """
    Direct, complete Agent turn:
    1. Instantly resolves table & queries BigQuery via MCP.
    2. Handles document generation (clean content + custom filename) or direct data Q&A.
    """
    import re
    print(f"[AGENT_START] session_id={session_id}, prompt={prompt}")
    history = load_session_memory(session_id)
    proj = os.environ.get('PROJECT_ID', PROJECT_ID)
    lower_prompt = prompt.lower()
    
    # 1. Table Resolution
    target_table = None
    if any(w in lower_prompt for w in ["payor", "check", "3rd party", "third party"]):
        target_table = f"{proj}.claims_silver.tbl_payor_checks_sftp"
    elif any(w in lower_prompt for w in ["pay_to_date", "pay to date", "paid", "to date"]):
        target_table = f"{proj}.claims_silver.tbl_pay_to_date_sftp"
    elif any(w in lower_prompt for w in ["refund", "erefund"]):
        target_table = f"{proj}.claims_silver.tbl_refund_sharepoint"
    elif any(w in lower_prompt for w in ["variance", "reconcil"]):
        target_table = f"{proj}.claims_silver.tbl_variance_sharepoint"
    else:
        matches = re.findall(r'[a-zA-Z0-9_\-]+(?:\.[a-zA-Z0-9_\-]+)+', prompt)
        if matches:
            target_table = matches[0] if matches[0].startswith(proj) else f"{proj}.{matches[0]}"
        else:
            target_table = f"{proj}.claims_silver.tbl_payor_checks_sftp"

    sql_query = f"SELECT * FROM `{target_table}` LIMIT 3"
    print(f"[BIGQUERY_EXEC] Querying {target_table}")
    data_records = call_mcp_tool("query_bigquery", {"sql_query": sql_query})

    # 2. Check if this is a Document Creation request
    is_doc_request = any(w in lower_prompt for w in ["create", "pdf", "export", "doc", "document", "save"]) and any(w in lower_prompt for w in ["doc", "pdf", "file", "document", "report", "summary", ".txt"])

    if is_doc_request:
        # Extract custom filename if requested (e.g. NYL_DEMO_DOC.txt)
        file_match = re.search(r'([a-zA-Z0-9_\-]+\.(?:txt|pdf|md|doc))', prompt, re.IGNORECASE)
        name_match = re.search(r'(?:call|name)\s+(?:the\s+)?(?:document|doc|file)\s+([a-zA-Z0-9_\.\-]+)', prompt, re.IGNORECASE)
        
        if file_match:
            doc_filename = file_match.group(1)
        elif name_match:
            doc_filename = name_match.group(1)
            if "." not in doc_filename:
                doc_filename += ".txt"
        else:
            doc_filename = "claims_summary.txt"

        doc_prompt = f"""
You are an executive document author for New York Life.

Source Data from BigQuery Table `{target_table}`:
{data_records}

User Request:
"{prompt}"

CRITICAL INSTRUCTIONS:
1. Write ONLY the clean, polished content for the document.
2. Strictly obey formatting/length instructions from the user (e.g. max sentences, bullet points, executive summary).
3. DO NOT include SQL queries, query descriptions, preamble, greetings, or conversational remarks.
4. Output ONLY the raw document text.
"""
        try:
            doc_content = query_gemini_vertex(doc_prompt, history).strip()
            # Save the clean document content to GCS
            saved_msg = call_mcp_tool("create_pdf", {"title": doc_filename, "content": doc_content})
            reply_text = f"{saved_msg}\n\nDocument Content:\n{doc_content}"
        except Exception as e:
            reply_text = f"Error generating document: {e}"

    else:
        # Standard Data Query & Answer
        gemini_prompt = f"""
You are a direct, professional BigQuery data assistant.

Context:
- Project: `{proj}`
- Target Table: `{target_table}`
- SQL Query Executed:
{sql_query}
- Live Query Results:
{data_records}

User Question:
"{prompt}"

CRITICAL INSTRUCTIONS:
1. NO greetings, NO pleasantries, NO introductory fluff (never say "Hello", "As an AI", "I can confirm", etc.).
2. Start DIRECTLY with the answer and the exact BigQuery table.
3. Show the SQL query in a markdown code block.
4. Provide a full, complete answer presenting the records, key contacts, or findings from the live query results.
"""
        try:
            reply_text = query_gemini_vertex(gemini_prompt, history)
            print(f"[GEMINI_SUCCESS] Length={len(reply_text)}")
        except Exception as e:
            print(f"[GEMINI_ERROR] {e}")
            reply_text = f"Data is located in table `{target_table}`.\n\nQuery executed:\n```sql\n{sql_query}\n```\n\nResults:\n{data_records}"

    # Persist session memory
    history.append({"role": "user", "text": prompt})
    history.append({"role": "model", "text": reply_text})
    save_session_memory(session_id, history)
    
    return reply_text

@functions_framework.http
def handle_agent_request(request):
    """
    BigQuery Remote Function handler.
    Receives JSON: {"calls": [[prompt, session_id], ...]}
    Returns JSON:  {"replies": [reply1, ...]}
    """
    if request.method != 'POST':
        return json.dumps({"error": "Only POST is supported"}), 405, {'Content-Type': 'application/json'}
    
    try:
        data = request.get_json(silent=True) or {}
        calls = data.get('calls', [])
        replies = []
        
        for call in calls:
            prompt = str(call[0]) if len(call) > 0 and call[0] is not None else ""
            session_id = str(call[1]) if len(call) > 1 and call[1] is not None else "default_session"
            
            if not prompt.strip():
                replies.append("Empty prompt provided.")
                continue
            
            reply = run_agent_turn(prompt, session_id)
            replies.append(reply)
            
        return json.dumps({"replies": replies}), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({"errorMessage": str(e)}), 500, {'Content-Type': 'application/json'}
