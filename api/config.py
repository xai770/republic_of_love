"""
API Configuration — loads from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Database - match core/database.py pattern
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'turing')
DB_USER = os.getenv('DB_USER', 'base_admin')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'https://talent.yoga/auth/callback')

# Session
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production-use-openssl-rand-hex-32')
SESSION_EXPIRE_HOURS = int(os.getenv('SESSION_EXPIRE_HOURS', '24'))

# CORS
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8000')

# App
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

# Security guard: refuse to start with default SECRET_KEY in production
if not DEBUG and SECRET_KEY == 'change-me-in-production-use-openssl-rand-hex-32':
    raise RuntimeError(
        "FATAL: SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
    )
