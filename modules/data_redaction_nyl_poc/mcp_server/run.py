import os
import uvicorn
from starlette.routing import Route
from starlette.responses import PlainTextResponse
from main import mcp

app = mcp.sse_app()

async def healthcheck(request):
    return PlainTextResponse("OK")

app.router.routes.append(Route("/", endpoint=healthcheck))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
