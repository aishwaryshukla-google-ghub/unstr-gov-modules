import os
import uvicorn
from main import mcp

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # mcp.sse_app() returns the Starlette ASGI application
    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=port)
