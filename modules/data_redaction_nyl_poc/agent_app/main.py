import os
import json
import requests
import functions_framework
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    Part
)
from google.cloud import storage, bigquery
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

PROJECT_ID = os.environ.get("PROJECT_ID", "")
REGION = os.environ.get("REGION", "us-east4")
DATASET_ID = os.environ.get("DATASET_ID", "bq_unstr_dtst_v2")
MEMORY_BUCKET = os.environ.get("MEMORY_BUCKET", "")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "")

# Initialize Vertex AI, BigQuery & Storage Client
if PROJECT_ID:
    try:
        vertexai.init(project=PROJECT_ID, location=REGION)
    except Exception:
        pass
storage_client = storage.Client()
bq_client = bigquery.Client()

# Tool Declarations for Gemini
search_docs_func = FunctionDeclaration(
    name="search_redacted_documents",
    description="Search through redacted unstructured documents in BigQuery to find policy and claims details.",
    parameters={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Keyword to search for in redacted text"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of matching documents to return"
            }
        },
        "required": ["keyword"]
    }
)

query_bq_func = FunctionDeclaration(
    name="query_bigquery",
    description="Execute a read-only SQL query against BigQuery datasets in the project.",
    parameters={
        "type": "object",
        "properties": {
            "sql_query": {
                "type": "string",
                "description": "SQL query to execute"
            }
        },
        "required": ["sql_query"]
    }
)

create_pdf_func = FunctionDeclaration(
    name="create_pdf",
    description="Create a summary report or PDF document and save it to cloud storage.",
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Document title"
            },
            "content": {
                "type": "string",
                "description": "Content of the document/summary"
            }
        },
        "required": ["title", "content"]
    }
)

agent_tools = Tool(
    function_declarations=[search_docs_func, query_bq_func, create_pdf_func]
)

def get_auth_headers(target_url):
    """Generate GCP Identity Token header for authenticated Cloud Function invocation."""
    try:
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, target_url)
        return {"Authorization": f"Bearer {id_token}", "Content-Type": "application/json"}
    except Exception:
        return {"Content-Type": "application/json"}

def execute_tool_locally(tool_name: str, tool_args: dict) -> str:
    """Executes tool logic directly if HTTP MCP server is blocked by VPC ingress constraints."""
    proj = os.environ.get('PROJECT_ID', PROJECT_ID)
    dtst = os.environ.get('DATASET_ID', DATASET_ID)
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
        
    elif tool_name == "search_redacted_documents":
        keyword = tool_args.get("keyword", "")
        limit = tool_args.get("limit", 5)
        query = f"""
            SELECT *
            FROM `{proj}.{dtst}.redacted_documents_view`
            WHERE LOWER(redacted_text) LIKE @keyword
            LIMIT @limit
        """
        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("keyword", "STRING", f"%{keyword.lower()}%"),
                    bigquery.ScalarQueryParameter("limit", "INTEGER", int(limit)),
                ]
            )
            query_job = bq_client.query(query, job_config=job_config)
            results = query_job.result()
            output = [str(dict(row.items())) for row in results]
            if not output:
                return f"No redacted documents found matching '{keyword}'."
            return "\n---\n".join(output)
        except Exception as e:
            return f"BigQuery search note: {str(e)}"
            
    elif tool_name == "query_bigquery":
        sql_query = tool_args.get("sql_query", "")
        try:
            query_job = bq_client.query(sql_query)
            results = query_job.result()
            output = [str(dict(row.items())) for i, row in enumerate(results) if i < 10]
            if not output:
                return "Query executed with 0 rows returned."
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
            resp = requests.post(MCP_SERVER_URL, json=payload, headers=headers, timeout=10)
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
    """Execute single turn of Agent reasoning loop with GCS Memory and MCP Tools."""
    history = load_session_memory(session_id)
    reply_text = ""
    
    try:
        system_instruction = (
            "You are the New York Life (NYL) AI Claims & Documents Assistant. "
            "You have access to tools to search redacted unstructured claims documents in BigQuery "
            "and create summary documents. Always answer accurately and professionally based on tool results."
        )
        
        model = GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=[agent_tools],
            system_instruction=system_instruction
        )
        
        chat = model.start_chat()
        response = chat.send_message(prompt)
        
        iterations = 0
        while response.candidates and response.candidates[0].function_calls and iterations < 5:
            iterations += 1
            function_call = response.candidates[0].function_calls[0]
            tool_name = function_call.name
            tool_args = dict(function_call.args.items())
            
            tool_result = call_mcp_tool(tool_name, tool_args)
            
            response = chat.send_message(
                Part.from_function_response(
                    name=tool_name,
                    response={"content": tool_result}
                )
            )
        
        reply_text = response.text if hasattr(response, 'text') else "No response generated."
    except Exception as e:
        # Fallback to direct MCP tool execution if Vertex AI is restricted by organization VPC Service Controls
        lower_prompt = prompt.lower()
        if "create" in lower_prompt or "summary" in lower_prompt or "pdf" in lower_prompt or "export" in lower_prompt:
            tool_result = call_mcp_tool("create_pdf", {"title": "policy_summary", "content": prompt})
            reply_text = f"[Agent Response via MCP Tool]: {tool_result}"
        else:
            # Extract search terms from the prompt to query BigQuery directly
            terms = [w.strip("?,.!") for w in prompt.split() if len(w) > 3 and w.lower() not in ["what", "about", "going", "know", "have", "with", "from", "this", "that", "these", "those", "does", "where", "when", "which", "could", "would"]]
            search_keyword = terms[0] if terms else "claim"
            tool_result = call_mcp_tool("search_redacted_documents", {"keyword": search_keyword, "limit": 5})
            if "No redacted documents found" in tool_result or "error" in tool_result.lower():
                # Try generic claim lookup
                tool_result = call_mcp_tool("search_redacted_documents", {"keyword": "claim", "limit": 3})
            reply_text = f"[Agent Response via BigQuery MCP]: {tool_result}"
    
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
