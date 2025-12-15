# Tests Directory

This directory contains integration and unit tests for the workflow execution system.

## Running Tests

```bash
# Install pytest if needed
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_workflow_execution.py

# Run with verbose output
pytest -v tests/

# Run specific test
pytest tests/test_workflow_execution.py::TestCircuitBreaker::test_circuit_opens_after_failures
```

## Test Coverage

### test_workflow_execution.py
- **TestWorkflowExecution**: Complete workflow execution tests
  - Workflow definition loading
  - Posting state creation
  - Pending postings query

- **TestCheckpointRecovery**: Checkpoint save/load tests
  - Save checkpoint to database
  - Load checkpoint from database
  - Checkpoint data integrity

- **TestBranchRouting**: Branch condition evaluation
  - Wildcard (*) matching
  - TERMINAL branches
  - Condition-specific matching

- **TestCircuitBreaker**: Circuit breaker functionality
  - Default CLOSED state
  - Opens after failure threshold
  - Success resets in CLOSED state
  - Permanent disable after max opens

- **TestErrorHandling**: Error logging and classification
  - workflow_errors table exists
  - Error classification (transient vs permanent)

- **TestWorkflowValidation**: Configuration validation
  - Catches disabled conversation branches
  - Validates workflow integrity

## Test Database

Tests use the main `turing` database. Consider creating a test database for isolation:

```sql
CREATE DATABASE turing_test WITH TEMPLATE turing;
```

Then update tests to use `turing_test` for non-destructive testing.
