from mcp.server.fastmcp import FastMCP
from google.cloud import bigquery

# Initialize FastMCP server
mcp = FastMCP("NYL-Redacted-Data-Server")

# Initialize BigQuery client
# This automatically uses Application Default Credentials (gcloud auth application-default login)
bq_client = bigquery.Client()

@mcp.tool()
def search_redacted_documents(keyword: str, project_id: str, dataset_id: str, limit: int = 3) -> str:
    """Search through the fully redacted unstructured documents in BigQuery to generate content."""
    
    query = f"""
    SELECT uri, redacted_text 
    FROM `{project_id}.{dataset_id}.redacted_documents_view`
    WHERE LOWER(redacted_text) LIKE LOWER('%{keyword}%')
    LIMIT {limit}
    """
    
    try:
        query_job = bq_client.query(query)
        results = query_job.result()
        
        output = []
        for row in results:
            output.append(f"Source Document: {row.uri}\nRedacted Content:\n{row.redacted_text}\n{'-'*40}")
            
        if not output:
            return f"No documents found containing the keyword: {keyword}"
            
        return "\n".join(output)
    except Exception as e:
        return f"Error querying BigQuery: {str(e)}"

if __name__ == "__main__":
    # Run the server using stdio (the protocol expected by MCP clients like Claude Desktop)
    mcp.run()
