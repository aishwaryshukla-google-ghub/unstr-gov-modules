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
from google.cloud import storage
import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

PROJECT_ID = os.environ.get("PROJECT_ID", "")
REGION = os.environ.get("REGION", "us-east4")
MEMORY_BUCKET = os.environ.get("MEMORY_BUCKET", "")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "")

# Initialize Vertex AI & Storage Client
if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=REGION)
storage_client = storage.Client()

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

def call_mcp_tool(tool_name: str, tool_args: dict) -> str:
    """Dispatches tool execution to CRF - MCP over HTTP."""
    if not MCP_SERVER_URL:
        return f"Error: MCP_SERVER_URL is not configured."
    
    headers = get_auth_headers(MCP_SERVER_URL)
    payload = {"tool": tool_name, "arguments": tool_args}
    try:
        resp = requests.post(MCP_SERVER_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("result", "")
        return f"Tool execution failed with HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Exception executing tool '{tool_name}': {str(e)}"

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
    
    # Initialize chat session
    chat = model.start_chat()
    
    # Execute query
    response = chat.send_message(prompt)
    
    # Handle function calling loop (up to 5 iterations)
    iterations = 0
    while response.candidates and response.candidates[0].function_calls and iterations < 5:
        iterations += 1
        function_call = response.candidates[0].function_calls[0]
        tool_name = function_call.name
        tool_args = dict(function_call.args.items())
        
        # Execute tool via CRF - MCP
        tool_result = call_mcp_tool(tool_name, tool_args)
        
        # Send function response back to model
        response = chat.send_message(
            Part.from_function_response(
                name=tool_name,
                response={"content": tool_result}
            )
        )
    
    reply_text = response.text if hasattr(response, 'text') else "No response generated."
    
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
