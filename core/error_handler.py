#!/usr/bin/env python3
"""
Global Error Handler
====================

Centralized exception handling for consistent error management across
all workflow components.

Features:
- Consistent error logging format
- Database error recording
- Error classification (transient vs permanent)
- Retry logic recommendations
- Stack trace capture

Usage:
    from core.error_handler import handle_error, ErrorSeverity
    
    try:
        risky_operation()
    except Exception as e:
        handle_error(
            e,
            context={
                'posting_id': 123,
                'task_type': 'gemma3_extract',
                'workflow_run_id': 456
            },
            severity=ErrorSeverity.ERROR,
            db_conn=conn
        )
"""

import traceback
import json
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "INFO"          # Informational, not a failure
    WARNING = "WARNING"    # Concerning but workflow continues
    ERROR = "ERROR"        # Failure but recoverable
    CRITICAL = "CRITICAL"  # System-level failure


class ErrorCategory(Enum):
    """Error categories for classification"""
    TRANSIENT = "TRANSIENT"      # Temporary (timeouts, rate limits) - retry
    PERMANENT = "PERMANENT"      # Code/config error - don't retry
    EXTERNAL = "EXTERNAL"        # Third-party service issue
    DATA = "DATA"                # Bad input data
    UNKNOWN = "UNKNOWN"          # Can't determine


def classify_error(error: Exception) -> ErrorCategory:
    """
    Classify error to determine if retry is appropriate.
    
    Args:
        error: Exception to classify
    
    Returns:
        ErrorCategory
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Transient errors (retry makes sense)
    transient_indicators = [
        'timeout', 'timed out', 'connection', 'network',
        'rate limit', 'too many requests', 'service unavailable',
        'temporarily unavailable', '503', '504', '429'
    ]
    if any(indicator in error_str for indicator in transient_indicators):
        return ErrorCategory.TRANSIENT
    
    # Permanent errors (don't retry)
    permanent_indicators = [
        'syntax error', 'type error', 'attribute error',
        'key error', 'index error', 'value error',
        'not found', '404', '403', 'forbidden',
        'unauthorized', '401', 'invalid', 'malformed'
    ]
    if any(indicator in error_str for indicator in permanent_indicators):
        return ErrorCategory.PERMANENT
    
    # External service errors
    if 'api' in error_str or 'http' in error_str.lower():
        return ErrorCategory.EXTERNAL
    
    # Database errors are often transient (locks, connections)
    if 'database' in error_str or 'postgres' in error_str:
        return ErrorCategory.TRANSIENT
    
    return ErrorCategory.UNKNOWN


def handle_error(
    error: Exception,
    context: Dict[str, Any],
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    db_conn: Optional[Any] = None,
    raise_after_handling: bool = False
) -> Dict[str, Any]:
    """
    Handle exception with consistent logging and recording.
    
    Args:
        error: Exception that occurred
        context: Context dict (posting_id, task_type, etc.)
        severity: Error severity level
        db_conn: Database connection for recording (optional)
        raise_after_handling: Whether to re-raise after handling
    
    Returns:
        Error details dict
    """
    # Classify error
    category = classify_error(error)
    
    # Build error details
    error_details = {
        'timestamp': datetime.utcnow().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'error_category': category.value,
        'severity': severity.value,
        'stack_trace': traceback.format_exc(),
        'context': context,
        'should_retry': category in [ErrorCategory.TRANSIENT, ErrorCategory.EXTERNAL]
    }
    
    # Log to database if connection provided
    if db_conn and 'posting_id' in context:
        try:
            cursor = db_conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_errors (
                    workflow_run_id,
                    posting_id,
                    task_type_id,
                    actor_id,
                    execution_order,
                    error_type,
                    error_message,
                    stack_trace,
                    context
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                context.get('workflow_run_id'),
                context.get('posting_id'),
                context.get('task_type_id'),
                context.get('actor_id'),
                context.get('execution_order'),
                error_details['error_type'],
                error_details['error_message'][:1000],
                error_details['stack_trace'][:5000],
                json.dumps(context)
            ))
            db_conn.commit()
            cursor.close()
        except Exception as db_error:
            # Don't fail the error handler if DB write fails
            print(f"Warning: Failed to log error to database: {db_error}")
            db_conn.rollback()
    
    # Print error (structured logging would be better)
    print(json.dumps(error_details, indent=2))
    
    # Re-raise if requested
    if raise_after_handling:
        raise error
    
    return error_details


def get_retry_delay(attempt: int, category: ErrorCategory) -> int:
    """
    Calculate retry delay with exponential backoff.
    
    Args:
        attempt: Retry attempt number (1, 2, 3, ...)
        category: Error category
    
    Returns:
        Delay in seconds before retry
    """
    if category == ErrorCategory.PERMANENT:
        return 0  # Don't retry
    
    if category == ErrorCategory.TRANSIENT:
        # Exponential backoff: 5s, 10s, 20s, 40s, 80s (max 2 min)
        return min(5 * (2 ** (attempt - 1)), 120)
    
    if category == ErrorCategory.EXTERNAL:
        # Longer delays for external services: 30s, 60s, 120s
        return min(30 * attempt, 120)
    
    # Unknown - conservative backoff
    return min(10 * attempt, 60)
