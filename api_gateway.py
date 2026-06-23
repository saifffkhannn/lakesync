import httpx
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_gateway")

app = FastAPI(title="LakeSync API Gateway")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

INGESTION_BACKEND = "https://lakesync-api.onrender.com"
ABAP_BACKEND = "https://lakesync-abap.onrender.com"

# Create a shared HTTP client
client = httpx.AsyncClient()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def route_request(request: Request, path: str):
    method = request.method
    headers = dict(request.headers)
    
    # Strip Host header so the target server handles it correctly
    if "host" in headers:
        headers.pop("host")
    
    # Determine routing destination
    if path.startswith("abap"):
        # Strip '/abap' prefix
        sub_path = path[4:]
        if sub_path.startswith("/"):
            sub_path = sub_path[1:]
        target_url = f"{ABAP_BACKEND}/{sub_path}"
        logger.info(f"[GATEWAY] Routing ABAP request {method} /{path} -> {target_url}")
    else:
        target_url = f"{INGESTION_BACKEND}/{path}"
        logger.info(f"[GATEWAY] Routing Ingestion request {method} /{path} -> {target_url}")

    # Forward query parameters
    query = request.url.query
    if query:
        target_url = f"{target_url}?{query}"

    # Read raw body
    body = await request.body()

    try:
        # Forward request to downstream service
        response = await client.request(
            method=method,
            url=target_url,
            headers=headers,
            content=body,
            timeout=60.0
        )
        
        # Print upstream headers to Render logs to diagnose compression issues
        print("UPSTREAM HEADERS:", dict(response.headers))

        # Copy non-structural headers we want to forward (like downloads/attachment)
        gateway_headers = {}
        for k, v in response.headers.items():
            if k.lower() in ["content-disposition", "content-length"]:
                gateway_headers[k] = v

        # Explicitly pass content-type and let FastAPI handle structural headers safely
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type"),
            headers=gateway_headers
        )
    except httpx.RequestError as exc:
        logger.error(f"[GATEWAY] Connection failed to {target_url}: {exc}")
        return Response(
            content=f"Gateway Error: Target server unreachable. Detail: {exc}",
            status_code=502
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
