"""
Health check endpoint.

Returns 200 when all dependencies are healthy, 503 otherwise.
Checks: database, Ollama LLM server.
"""
import os
import requests as http_requests
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from api.deps import get_db

router = APIRouter(tags=["health"])

OLLAMA_BASE_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')


@router.get("/health")
def health_check(conn=Depends(get_db)):
    """
    Health check. Returns 200 if all dependencies are reachable, 503 otherwise.
    Suitable for load balancers and uptime monitors.
    """
    checks = {}
    healthy = True

    # ── Database
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {e}"
        healthy = False

    # ── Ollama LLM server
    try:
        resp = http_requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m.get('name', '?') for m in resp.json().get('models', [])]
            checks["ollama"] = f"ok ({len(models)} models)"
        else:
            checks["ollama"] = f"error: HTTP {resp.status_code}"
            healthy = False
    except Exception as e:
        checks["ollama"] = f"unreachable: {e}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if healthy else "unhealthy", **checks}
    )
