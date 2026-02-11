"""
Tests for core/error_handler.py — error classification and retry logic.
"""
import pytest
from core.error_handler import (
    classify_error,
    get_retry_delay,
    ErrorCategory,
    ErrorSeverity,
)


# ── classify_error ───────────────────────────────────────────────────

class TestClassifyError:
    def test_timeout_is_transient(self):
        err = Exception("Connection timeout after 30s")
        assert classify_error(err) == ErrorCategory.TRANSIENT

    def test_rate_limit_is_transient(self):
        err = Exception("429 Too Many Requests")
        assert classify_error(err) == ErrorCategory.TRANSIENT

    def test_503_is_transient(self):
        err = Exception("503 Service Unavailable")
        assert classify_error(err) == ErrorCategory.TRANSIENT

    def test_syntax_error_is_permanent(self):
        err = Exception("syntax error at position 42")
        assert classify_error(err) == ErrorCategory.PERMANENT

    def test_404_is_permanent(self):
        err = Exception("404 not found")
        assert classify_error(err) == ErrorCategory.PERMANENT

    def test_unauthorized_is_permanent(self):
        err = Exception("401 unauthorized")
        assert classify_error(err) == ErrorCategory.PERMANENT

    def test_api_error_is_external(self):
        err = Exception("API returned unexpected response")
        assert classify_error(err) == ErrorCategory.EXTERNAL

    def test_database_is_transient(self):
        err = Exception("database connection lost")
        assert classify_error(err) == ErrorCategory.TRANSIENT

    def test_unknown(self):
        err = Exception("something weird happened")
        assert classify_error(err) == ErrorCategory.UNKNOWN


# ── get_retry_delay ──────────────────────────────────────────────────

class TestGetRetryDelay:
    def test_permanent_no_retry(self):
        assert get_retry_delay(1, ErrorCategory.PERMANENT) == 0
        assert get_retry_delay(5, ErrorCategory.PERMANENT) == 0

    def test_transient_exponential_backoff(self):
        assert get_retry_delay(1, ErrorCategory.TRANSIENT) == 5
        assert get_retry_delay(2, ErrorCategory.TRANSIENT) == 10
        assert get_retry_delay(3, ErrorCategory.TRANSIENT) == 20

    def test_transient_max_120(self):
        assert get_retry_delay(10, ErrorCategory.TRANSIENT) == 120

    def test_external_linear(self):
        assert get_retry_delay(1, ErrorCategory.EXTERNAL) == 30
        assert get_retry_delay(2, ErrorCategory.EXTERNAL) == 60
        assert get_retry_delay(3, ErrorCategory.EXTERNAL) == 90

    def test_external_max_120(self):
        assert get_retry_delay(10, ErrorCategory.EXTERNAL) == 120

    def test_unknown_conservative(self):
        assert get_retry_delay(1, ErrorCategory.UNKNOWN) == 10
        assert get_retry_delay(2, ErrorCategory.UNKNOWN) == 20


# ── ErrorSeverity / ErrorCategory enums ──────────────────────────────

class TestEnums:
    def test_severity_values(self):
        assert ErrorSeverity.INFO.value == "INFO"
        assert ErrorSeverity.CRITICAL.value == "CRITICAL"

    def test_category_values(self):
        assert ErrorCategory.TRANSIENT.value == "TRANSIENT"
        assert ErrorCategory.PERMANENT.value == "PERMANENT"
