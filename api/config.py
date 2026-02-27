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

# Upload limits
MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', '10'))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Rate limiting
RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '60/minute')
RATE_LIMIT_LLM = os.getenv('RATE_LIMIT_LLM', '5/minute')
RATE_LIMIT_AUTH = os.getenv('RATE_LIMIT_AUTH', '10/minute')

# App — DEBUG defaults to false for safety; set DEBUG=true in .env for development
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Email encryption (Fernet symmetric — AES-128-CBC + HMAC-SHA256)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# WARNING: losing this key = permanent loss of all stored email addresses
EMAIL_ENCRYPTION_KEY = os.getenv('EMAIL_ENCRYPTION_KEY', '')

# Security guard: refuse to start with default SECRET_KEY in production
if not DEBUG and SECRET_KEY == 'change-me-in-production-use-openssl-rand-hex-32':
    raise RuntimeError(
        "FATAL: SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
    )

if not DEBUG and not EMAIL_ENCRYPTION_KEY:
    raise RuntimeError(
        "FATAL: EMAIL_ENCRYPTION_KEY is not set. "
        "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )
