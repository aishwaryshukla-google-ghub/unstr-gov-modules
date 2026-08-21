import os
import json
import functions_framework
from google.cloud import bigquery
from google.cloud import storage

bq_client = bigquery.Client()
storage_client = storage.Client()

def query_bigquery(sql_query: str) -> str:
    """Execute a read-only SQL query against BigQuery datasets."""
    try:
        query_job = bq_client.query(sql_query)
        results = query_job.result()
        output = []
        for i, row in enumerate(results):
            if i >= 10:
                output.append("... (truncated to 10 rows)")
                break
            output.append(str(dict(row.items())))
        if not output:
            return "Query executed successfully with 0 rows returned."
        return "\n".join(output)
    except Exception as e:
        return f"Query error: {str(e)}"

def create_pdf(title: str, content: str) -> str:
    """Create and save a document/artifact to GCS."""
    bucket_name = os.environ.get('MEMORY_BUCKET', '')
    if bucket_name:
        try:
            bucket = storage_client.bucket(bucket_name)
            filename = f"exports/{title.replace(' ', '_').lower()}.txt"
            blob = bucket.blob(filename)
            blob.upload_from_string(f"TITLE: {title}\n\n{content}", content_type="text/plain")
            return f"Document '{title}' created and saved to gs://{bucket_name}/{filename}"
        except Exception as e:
            return f"Simulated artifact created for '{title}'. Storage error: {str(e)}"
    return f"Simulated artifact created for '{title}'."

TOOLS = {
    "query_bigquery": query_bigquery,
    "create_pdf": create_pdf
}

@functions_framework.http
def handle_tool_request(request):
    """
    HTTP entrypoint for CRF - MCP.
    Expects POST: {"tool": "tool_name", "arguments": {...}}
    """
    if request.method != 'POST':
        return json.dumps({"error": "Only POST method is supported"}), 405, {'Content-Type': 'application/json'}
    
    try:
        data = request.get_json(silent=True) or {}
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})
        
        if tool_name not in TOOLS:
            return json.dumps({"error": f"Unknown tool: {tool_name}. Available: {list(TOOLS.keys())}"}), 400, {'Content-Type': 'application/json'}
        
        func = TOOLS[tool_name]
        result = func(**arguments)
        return json.dumps({"result": result}), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}
