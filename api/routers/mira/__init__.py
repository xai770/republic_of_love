"""
Mira router — AI companion chat for yogis.

Split into sub-modules:
- models.py     — Pydantic request/response models
- language.py   — Language detection, formality, conversational patterns
- context.py    — Yogi context building, LLM helpers
- greeting.py   — /greeting endpoint
- tour.py       — /tour endpoint
- proactive.py  — /context, /proactive, /consent-prompt, /consent-submit endpoints
- chat.py       — /chat endpoint
"""
from fastapi import APIRouter

from api.routers.mira.greeting import router as greeting_router
from api.routers.mira.tour import router as tour_router
from api.routers.mira.proactive import router as proactive_router
from api.routers.mira.chat import router as chat_router

router = APIRouter(prefix="/mira", tags=["mira"])

router.include_router(greeting_router)
router.include_router(tour_router)
router.include_router(proactive_router)
router.include_router(chat_router)

# Re-export for any external code that imports from api.routers.mira directly
from api.routers.mira.models import *  # noqa: F401, F403
from api.routers.mira.language import *  # noqa: F401, F403
from api.routers.mira.context import build_yogi_context, format_yogi_context_for_prompt, ask_llm, log_unanswered  # noqa: F401
