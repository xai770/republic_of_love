"""
/api/devlog/stream  — Server-Sent Events tail of logs/app.log.
Restricted to admin users only (is_admin flag or OWL admin_console privilege).
"""
import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.deps import get_db, require_user, user_has_owl_privilege

router = APIRouter(prefix="/devlog", tags=["devlog"])

LOG_PATH = Path(__file__).parent.parent.parent / "logs" / "app.log"
POLL_INTERVAL = 0.4   # seconds between file checks
MAX_BACKLOG   = 80    # lines to replay on connect


@router.get("/stream")
async def stream_log(
    user: dict = Depends(require_user),
    conn = Depends(get_db),
):
    """SSE stream of app.log. Admin-only."""
    is_admin = user.get('is_admin') or user_has_owl_privilege(conn, user['user_id'], 'admin_console')
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    async def generator():
        # --- send buffered header ---
        yield "retry: 2000\n\n"

        # --- replay recent lines so the panel isn't empty on connect ---
        try:
            with open(LOG_PATH, "r", errors="replace") as fh:
                lines = fh.readlines()
            for line in lines[-MAX_BACKLOG:]:
                text = line.rstrip("\n").replace("\n", " ")
                yield f"data: {text}\n\n"
            pos = os.path.getsize(LOG_PATH)
        except FileNotFoundError:
            yield "data: (log file not found)\n\n"
            return

        # --- follow new content ---
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            try:
                size = os.path.getsize(LOG_PATH)
                if size > pos:
                    with open(LOG_PATH, "r", errors="replace") as fh:
                        fh.seek(pos)
                        new = fh.read(size - pos)
                    pos = size
                    for line in new.splitlines():
                        text = line.strip()
                        if text:
                            yield f"data: {text}\n\n"
                elif size < pos:
                    # file was rotated / truncated
                    pos = size
            except Exception as exc:
                yield f"data: [stream error: {exc}]\n\n"
                break

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )
