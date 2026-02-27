"""
Rate limiter — shared instance for use in main.py and routers.

Separated from main.py to avoid circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.config import RATE_LIMIT_DEFAULT

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_DEFAULT])
