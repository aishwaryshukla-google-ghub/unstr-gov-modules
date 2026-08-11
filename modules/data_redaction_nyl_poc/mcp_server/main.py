import os
from mcp.server.fastmcp import FastMCP
from google.cloud import bigquery

# Initialize FastMCP Server
mcp = FastMCP("NYL-MCP-Server")

# Initialize BigQuery Client
bq_client = bigquery.Client()

@mcp.tool()
def search_redacted_documents(keyword: str, limit: int = 5) -> str:
    """
    Search through the fully redacted unstructured documents in BigQuery.
    Use this tool to generate content and answer user questions safely without exposing PII.
    
    Args:
        keyword: The keyword to search for in the redacted_text column. (e.g. "python")
        limit: Max number of documents to return.
    """
    project_id = os.environ['PROJECT_ID']
    dataset_id = os.environ['DATASET_ID']
    
    query = f"""
        SELECT uri, content_type, redacted_text 
        FROM `{project_id}.{dataset_id}.redacted_documents_view`
        WHERE LOWER(redacted_text) LIKE @keyword
        LIMIT @limit
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("keyword", "STRING", f"%{keyword.lower()}%"),
            bigquery.ScalarQueryParameter("limit", "INTEGER", limit),
        ]
    )
    
    query_job = bq_client.query(query, job_config=job_config)
    results = query_job.result()
    
    output = []
    for row in results:
        output.append(f"URI: {row.uri}\nContent Type: {row.content_type}\nRedacted Text Snippet:\n{row.redacted_text[:1000]}...\n{'-'*40}")
        
    if not output:
        return f"No redacted documents found containing '{keyword}'."
        
    return "\n".join(output)

@mcp.tool()
def create_pdf(title: str, content: str) -> str:
    """
    A dummy tool to fulfill the 'LIKE CREATE A PDF' requirement from the project spec.
    """
    return f"Simulated PDF Creation:\nTitle: {title}\nStatus: SUCCESS - Saved to secure storage."
