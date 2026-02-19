"""
Turing Platform — Centralized Configuration

Single source of truth for all runtime settings.
Every module imports from here instead of calling os.getenv() directly.

Environment variables still override defaults (12-factor compatible).
To change a setting for a single run:
    EMBED_WORKERS=4 python3 core/turing_daemon.py

To change permanently, edit the defaults below and commit.
"""

import os

# ============================================================================
# Ollama
# ============================================================================
OLLAMA_BASE_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_GENERATE_URL = OLLAMA_BASE_URL + '/api/generate'
OLLAMA_CHAT_URL = OLLAMA_BASE_URL + '/api/chat'
OLLAMA_EMBED_URL = OLLAMA_BASE_URL + '/api/embeddings'
OLLAMA_TAGS_URL = OLLAMA_BASE_URL + '/api/tags'

# ============================================================================
# LLM Models
# ============================================================================
LLM_MODEL = os.getenv('LLM_MODEL', 'qwen2.5:7b')
BERUFENET_MODEL = os.getenv('BERUFENET_MODEL', 'qwen2.5:7b')
EMBED_MODEL = os.getenv('EMBED_MODEL', 'bge-m3:567m')
SUMMARY_MODEL = os.getenv('SUMMARY_MODEL', 'qwen2.5-coder:7b')

# ============================================================================
# Parallelism
# ============================================================================
EMBED_WORKERS = int(os.getenv('EMBED_WORKERS', '8'))
LLM_WORKERS = int(os.getenv('LLM_WORKERS', '4'))

# ============================================================================
# Signal Notifications
# ============================================================================
SIGNAL_CLI = os.getenv('SIGNAL_CLI', os.path.expanduser('~/.local/bin/signal-cli'))
SIGNAL_SENDER = os.getenv('SIGNAL_SENDER', '')
SIGNAL_RECIPIENT = os.getenv('SIGNAL_RECIPIENT', '+4915125098515')

# ============================================================================
# Security
# ============================================================================
TURING_HANDSHAKE = os.getenv('TURING_HANDSHAKE', '')

# ============================================================================
# Database (used by scripts that don't go through core.database)
# ============================================================================
DB_NAME = os.getenv('DB_NAME', 'turing')
DB_USER = os.getenv('DB_USER', 'base_admin')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
