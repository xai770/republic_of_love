"""
lib/crypto.py — Application-layer encryption for PII fields.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
The key is loaded from EMAIL_ENCRYPTION_KEY in the environment.

Key properties:
- DB admins see ciphertext only (gAAAAAB...) — useless without the key
- Application decrypts transparently on read
- Key loss = permanent data loss → back up the key as carefully as the DB

Usage:
    from lib.crypto import encrypt_email, decrypt_email

    # Write path (store in DB)
    row['email'] = encrypt_email(google_email)

    # Read path (return to caller)
    plaintext = decrypt_email(row['email'])
"""
import os
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Fernet token prefix — all encrypted values start with this when base64-decoded
_FERNET_MAGIC = b'gAAAAA'

def _get_fernet() -> Optional[Fernet]:
    """Return a Fernet instance using EMAIL_ENCRYPTION_KEY env var."""
    key = os.environ.get('EMAIL_ENCRYPTION_KEY', '')
    if not key:
        logger.warning("EMAIL_ENCRYPTION_KEY not set — email encryption disabled")
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        logger.error("Invalid EMAIL_ENCRYPTION_KEY: %s", e)
        return None


def is_encrypted(value: Optional[str]) -> bool:
    """
    Return True if the value looks like a Fernet ciphertext.
    Used during migration to avoid double-encrypting already-encrypted values.
    """
    if not value:
        return False
    # Fernet tokens are base64url-encoded and always start with 'gAAAAA'
    return value.startswith('gAAAAA')


def encrypt_email(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypt an email address for storage.

    Returns the Fernet ciphertext string, or the original value if:
    - plaintext is None/empty
    - EMAIL_ENCRYPTION_KEY is not configured (fail-open with a warning)
    - value is already encrypted (is_encrypted() check)
    """
    if not plaintext:
        return plaintext
    if is_encrypted(plaintext):
        return plaintext  # already encrypted, don't double-wrap
    f = _get_fernet()
    if f is None:
        return plaintext  # key not configured — store plaintext with warning
    try:
        return f.encrypt(plaintext.encode('utf-8')).decode('ascii')
    except Exception as e:
        logger.error("encrypt_email failed: %s", e)
        return plaintext  # fail-open: store plaintext rather than lose it


def decrypt_email(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypt a stored email address.

    Returns the plaintext, or the original value if:
    - ciphertext is None/empty
    - value is not encrypted (plaintext passthrough for backwards compatibility)
    - decryption fails (wrong key, corrupted data)
    """
    if not ciphertext:
        return ciphertext
    if not is_encrypted(ciphertext):
        return ciphertext  # plain text stored before encryption was enabled
    f = _get_fernet()
    if f is None:
        return None  # key not available — can't decrypt
    try:
        return f.decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except InvalidToken:
        logger.warning("decrypt_email: InvalidToken — wrong key or corrupted data")
        return None
    except Exception as e:
        logger.error("decrypt_email failed: %s", e)
        return None
