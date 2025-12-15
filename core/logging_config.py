#!/usr/bin/env python3
"""
Structured Logging Configuration
=================================

Provides JSON-formatted structured logging for the entire application.
Replaces print() statements with proper logging for:
- Log aggregation and analysis
- Searchable structured data
- Consistent formatting
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Contextual metadata

Benefits:
- Parse logs with jq, grep, or log aggregators
- Track request IDs across operations
- Measure performance with structured timing data
- Debug issues with rich context

Usage:
    from core.logging_config import get_logger
    
    logger = get_logger(__name__)
    
    # Simple message
    logger.info("Processing started")
    
    # With context
    logger.info("Actor executed", extra={
        'actor_id': 123,
        'posting_id': 456,
        'latency_ms': 250
    })
    
    # Error with exception
    try:
        risky_operation()
    except Exception as e:
        logger.error("Operation failed", exc_info=True, extra={
            'operation': 'risky_operation',
            'user_id': 789
        })

Output format (JSON):
    {
        "timestamp": "2025-11-13T16:45:23.123Z",
        "level": "INFO",
        "logger": "core.wave_batch_processor",
        "message": "Actor executed",
        "actor_id": 123,
        "posting_id": 456,
        "latency_ms": 250,
        "hostname": "production-1",
        "pid": 12345
    }
"""

import os
import sys
import json
import logging
import socket
from datetime import datetime
from typing import Dict, Any


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs each log record as a single JSON line for easy parsing.
    """
    
    def __init__(self):
        super().__init__()
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        # Base log data
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'hostname': self.hostname,
            'pid': self.pid,
            'thread': record.thread,
            'thread_name': record.threadName
        }
        
        # Add file/line info for DEBUG level
        if record.levelno == logging.DEBUG:
            log_data['file'] = record.pathname
            log_data['line'] = record.lineno
            log_data['function'] = record.funcName
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add custom fields from extra={}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
            ]:
                log_data[key] = value
        
        return json.dumps(log_data)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for console output (not JSON).
    
    Used when LOG_FORMAT=human (development mode).
    """
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human reading"""
        
        # Color by level
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Build message
        parts = [
            f"{color}{timestamp}",
            f"[{record.levelname:8s}]",
            f"{record.name}:{reset}",
            record.getMessage()
        ]
        
        # Add custom fields
        extra_fields = []
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info'
            ]:
                extra_fields.append(f"{key}={value}")
        
        if extra_fields:
            parts.append(f"({', '.join(extra_fields)})")
        
        message = ' '.join(parts)
        
        # Add exception if present
        if record.exc_info:
            message += '\n' + self.formatException(record.exc_info)
        
        return message


def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger for a module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        _configure_logger(logger)
    
    return logger


def _configure_logger(logger: logging.Logger):
    """Configure logger with appropriate handler and formatter"""
    
    # Get log level from environment (default: INFO)
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Create handler (console)
    handler = logging.StreamHandler(sys.stdout)
    
    # Choose formatter based on environment
    log_format = os.getenv('LOG_FORMAT', 'json').lower()
    
    if log_format == 'human':
        formatter = HumanReadableFormatter()
    else:
        formatter = StructuredFormatter()
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Don't propagate to root logger (prevents duplicate logs)
    logger.propagate = False


# Convenience function for quick logging without getting logger
def log_info(message: str, **kwargs):
    """Quick info log"""
    logger = get_logger('base_yoga')
    logger.info(message, extra=kwargs)


def log_error(message: str, **kwargs):
    """Quick error log"""
    logger = get_logger('base_yoga')
    logger.error(message, extra=kwargs)


def log_warning(message: str, **kwargs):
    """Quick warning log"""
    logger = get_logger('base_yoga')
    logger.warning(message, extra=kwargs)
