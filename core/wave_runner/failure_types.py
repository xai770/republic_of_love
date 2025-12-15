"""
Failure Classification for Turing Workflow System
Author: Sandy (GitHub Copilot)
Date: December 4, 2025

Failure types are classified at the moment of failure, not later.
This enables intelligent retry decisions inline with execution.

Failure Taxonomy:
├── Transient (retry will likely succeed)
│   ├── timeout      - Model/script took too long
│   ├── interrupted  - Runner was killed (SIGTERM)
│   ├── rate_limit   - API rate limit hit
│   └── connection   - Network/database blip
│
├── Deterministic (retry will fail the same way)
│   ├── invalid_input    - Bad data provided
│   ├── invalid_output   - LLM gave unparseable response
│   ├── script_error     - Script bug (non-zero exit)
│   └── not_found        - Resource doesn't exist
│
└── Resource (needs intervention)
    ├── oom          - Out of memory
    └── disk_full    - Storage exhausted
"""

from enum import Enum
from typing import Tuple
import re


class FailureType(Enum):
    """Failure classification enum."""
    # Transient - retry will likely succeed
    TIMEOUT = 'timeout'
    INTERRUPTED = 'interrupted'
    RATE_LIMIT = 'rate_limit'
    CONNECTION = 'connection'
    
    # Deterministic - retry will fail the same way
    INVALID_INPUT = 'invalid_input'
    INVALID_OUTPUT = 'invalid_output'
    SCRIPT_ERROR = 'script_error'
    NOT_FOUND = 'not_found'
    
    # Resource - needs intervention
    OOM = 'oom'
    DISK_FULL = 'disk_full'
    
    # Fallback
    UNKNOWN = 'unknown'


# Which failure types should be retried automatically
RETRIABLE_FAILURES = {
    FailureType.TIMEOUT,
    FailureType.INTERRUPTED,
    FailureType.RATE_LIMIT,
    FailureType.CONNECTION,
    FailureType.INVALID_OUTPUT,  # LLM might give valid output on retry
}


def classify_failure(error: Exception, error_message: str = None) -> Tuple[FailureType, bool]:
    """
    Classify a failure and determine if it's retriable.
    
    Called at the moment of failure with full context.
    
    Args:
        error: The exception that was raised
        error_message: Optional error message string for pattern matching
        
    Returns:
        Tuple of (FailureType, is_retriable)
    """
    msg = error_message or str(error)
    msg_lower = msg.lower()
    error_type = type(error).__name__
    
    # Timeout patterns
    if 'timeout' in msg_lower or 'timed out' in msg_lower:
        return FailureType.TIMEOUT, True
    
    if error_type == 'TimeoutExpired' or 'TimeoutExpired' in msg:
        return FailureType.TIMEOUT, True
    
    # Interrupted patterns (runner killed)
    if 'interrupt' in msg_lower or 'sigterm' in msg_lower or 'sigint' in msg_lower:
        return FailureType.INTERRUPTED, True
    
    # Rate limit patterns
    if 'rate limit' in msg_lower or '429' in msg or 'too many requests' in msg_lower:
        return FailureType.RATE_LIMIT, True
    
    # Connection patterns
    if any(p in msg_lower for p in ['connection', 'network', 'refused', 'reset', 'broken pipe']):
        return FailureType.CONNECTION, True
    
    # OOM patterns
    if 'out of memory' in msg_lower or 'oom' in msg_lower or 'memory' in msg_lower and 'alloc' in msg_lower:
        return FailureType.OOM, False
    
    # Disk patterns
    if 'disk' in msg_lower and ('full' in msg_lower or 'space' in msg_lower):
        return FailureType.DISK_FULL, False
    
    # Not found patterns
    if '404' in msg or 'not found' in msg_lower or 'does not exist' in msg_lower:
        return FailureType.NOT_FOUND, False
    
    # Invalid output patterns (LLM gave garbage)
    if any(p in msg_lower for p in ['json', 'parse', 'decode', 'invalid.*output', 'expected.*got']):
        return FailureType.INVALID_OUTPUT, True  # Retry once - LLM is non-deterministic
    
    # Script error patterns (usually deterministic)
    if 'exit code' in msg_lower or 'script failed' in msg_lower:
        # Check if it's a data issue (retriable) vs bug (not retriable)
        if 'no.*data' in msg_lower or 'missing.*data' in msg_lower:
            return FailureType.INVALID_INPUT, False
        return FailureType.SCRIPT_ERROR, False
    
    # Invalid input patterns
    if 'invalid' in msg_lower and 'input' in msg_lower:
        return FailureType.INVALID_INPUT, False
    
    # Default: unknown, but allow one retry
    return FailureType.UNKNOWN, True


def should_retry(failure_type: FailureType, retry_count: int, max_retries: int) -> bool:
    """
    Determine if an interaction should be retried.
    
    Args:
        failure_type: The classified failure type
        retry_count: Current retry count
        max_retries: Maximum retries allowed
        
    Returns:
        True if should retry, False if should fail permanently
    """
    if retry_count >= max_retries:
        return False
    
    return failure_type in RETRIABLE_FAILURES
