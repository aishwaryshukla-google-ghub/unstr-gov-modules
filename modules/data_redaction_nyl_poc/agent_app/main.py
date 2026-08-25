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

def query_nyl_ai_gateway(prompt: str, history: list = None) -> str:
    """Invokes NYL Enterprise AI Gateway endpoint for Gemini 3.5 Flash using urllib and custom SSL context."""
    token = get_bearer_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
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
    
    ssl_ctx = get_ssl_context()
    req = urllib.request.Request(
        AI_GATEWAY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    with urllib.request.urlopen(req, context=ssl_ctx, timeout=25) as resp:
        resp_data = json.loads(resp.read().decode("utf-8"))
        if "content" in resp_data and isinstance(resp_data["content"], list) and len(resp_data["content"]) > 0:
            return resp_data["content"][0].get("text", "")
        elif "candidates" in resp_data and len(resp_data["candidates"]) > 0:
            parts = resp_data["candidates"][0].get("content", {}).get("parts", [])
            if parts:
                return "".join(p.get("text", "") for p in parts)
        return "No text candidates returned from AI Gateway."

def execute_tool_locally(tool_name: str, tool_args: dict) -> str:
    """Executes tool logic directly if HTTP MCP server is blocked by VPC ingress constraints."""
    bucket_name = os.environ.get('MEMORY_BUCKET', MEMORY_BUCKET)
    
    if tool_name == "create_pdf":
        title = tool_args.get("title", "document")
        content = tool_args.get("content", "")
        if bucket_name:
            try:
                bucket = storage_client.bucket(bucket_name)
                filename = f"exports/{title.replace(' ', '_').lower()}.txt"
                blob = bucket.blob(filename)
                blob.upload_from_string(f"TITLE: {title}\n\n{content}", content_type="text/plain")
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
    """Execute single turn of Agent reasoning loop with GCS Memory, NYL AI Gateway, and MCP Tools."""
    print(f"[AGENT_START] session_id={session_id}, prompt={prompt}")
    history = load_session_memory(session_id)
    reply_text = ""
    
    # 1. Primary: NYL Enterprise AI Gateway (gemini-3.5-flash)
    try:
        print(f"[AI_GATEWAY_TRY] Target URL: {AI_GATEWAY_URL}")
        reply_text = query_nyl_ai_gateway(prompt, history)
        print(f"[AI_GATEWAY_SUCCESS] Length={len(reply_text)}")
    except Exception as e:
        print(f"[AI_GATEWAY_ERROR] {str(e)}")
        
    # 2. Fallback to direct MCP tool execution if gateway is temporarily unreachable
    if not reply_text:
        lower_prompt = prompt.lower()
        if "create" in lower_prompt or "summary" in lower_prompt or "pdf" in lower_prompt or "export" in lower_prompt:
            tool_result = call_mcp_tool("create_pdf", {"title": "policy_summary", "content": prompt})
            reply_text = f"[Agent Response via MCP Tool]: {tool_result}"
        else:
            proj = os.environ.get('PROJECT_ID', PROJECT_ID)
            dtst = os.environ.get('DATASET_ID', DATASET_ID)
            
            import re
            # 1. Check if an explicit table is mentioned
            matches = re.findall(r'[a-zA-Z0-9_\-]+(?:\.[a-zA-Z0-9_\-]+)+', prompt)
            target_table = None
            if matches:
                target_table = matches[0]
                if not target_table.startswith(proj):
                    target_table = f"{proj}.{target_table}"
            else:
                # 2. Extract key topical keywords (e.g. refund, claim, policy)
                words = [w.lower().strip("?,.!'\"") for w in prompt.split() if len(w) > 3 and w.lower() not in ["what", "about", "going", "know", "have", "with", "from", "this", "that", "these", "those", "does", "where", "when", "which", "could", "would", "tell", "show", "find", "there", "anything", "related"]]
                search_kw = words[0] if words else "refund"
                
                # Check tables in known datasets and region INFORMATION_SCHEMA
                disc_sql = f"SELECT table_name FROM `{proj}.claims_silver.INFORMATION_SCHEMA.TABLES` WHERE LOWER(table_name) LIKE '%{search_kw}%' OR LOWER(table_name) LIKE '%sharepoint%' LIMIT 3"
                disc_res = call_mcp_tool("query_bigquery", {"sql_query": disc_sql})
                
                if "0 rows" in disc_res or "error" in disc_res.lower():
                    # Check general claims_silver tables
                    disc_sql = f"SELECT table_name FROM `{proj}.claims_silver.INFORMATION_SCHEMA.TABLES` LIMIT 3"
                    disc_res = call_mcp_tool("query_bigquery", {"sql_query": disc_sql})
                
                # If a table was discovered
                if "tbl_" in disc_res:
                    tbl_name_match = re.search(r"tbl_[a-zA-Z0-9_]+", disc_res)
                    tbl_name = tbl_name_match.group(0) if tbl_name_match else "tbl_refund_sharepoint"
                    target_table = f"{proj}.claims_silver.{tbl_name}"
            
            if target_table:
                query_sql = f"SELECT * FROM `{target_table}` LIMIT 3"
                print(f"[BIGQUERY_MCP_EXEC] Querying table: {query_sql}")
                tool_res = call_mcp_tool("query_bigquery", {"sql_query": query_sql})
                reply_text = f"[Agent Response via BigQuery MCP]: Relevant records found from `{target_table}`:\n{tool_res}"
            else:
                reply_text = f"[Agent Response via BigQuery MCP]: Processed request for '{prompt}'. No matching tables found in project `{proj}`."
    
    # Update and persist memory
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
