"""
Health check endpoint.
"""
from fastapi import APIRouter, Depends
from api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(conn=Depends(get_db)):
    """
    Basic health check. Verifies database connection.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
