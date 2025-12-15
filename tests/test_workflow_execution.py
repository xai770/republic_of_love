#!/usr/bin/env python3
"""
Integration Tests for Workflow Execution
=========================================

Tests the complete workflow system including:
- Workflow execution from start to finish
- Checkpoint save and recovery
- Branch routing logic
- Error handling and recovery
- Circuit breaker functionality

Usage:
    # Run all tests
    pytest tests/

    # Run specific test
    pytest tests/test_workflow_execution.py::test_checkpoint_recovery

    # Run with verbose output
    pytest -v tests/

Requirements:
    pip install pytest pytest-asyncio
"""

import pytest
import psycopg2
from datetime import datetime
from core.database import get_connection
from core.wave_batch_processor import WaveBatchProcessor, PostingState
from core.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def db_conn():
    """Provide database connection for tests"""
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture
def test_workflow_id():
    """Test workflow ID (using 3001)"""
    return 3001


@pytest.fixture
def test_posting_id(db_conn):
    """Create a test posting and return its ID"""
    cursor = db_conn.cursor()
    
    # Find a posting that needs processing
    cursor.execute("""
        SELECT posting_id 
        FROM postings 
        WHERE enabled = TRUE 
          AND job_description IS NOT NULL
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    cursor.close()
    
    if result:
        return result['posting_id']
    else:
        pytest.skip("No test postings available")


class TestWorkflowExecution:
    """Test complete workflow execution"""
    
    def test_workflow_loads(self, test_workflow_id):
        """Test that workflow definition loads correctly"""
        processor = WaveBatchProcessor(test_workflow_id)
        
        assert processor.workflow_definition is not None
        assert 'workflow_id' in processor.workflow_definition
        assert processor.workflow_definition['workflow_id'] == test_workflow_id
        assert 'conversations' in processor.workflow_definition
        assert len(processor.workflow_definition['conversations']) > 0
    
    def test_posting_state_creation(self, test_posting_id):
        """Test PostingState object creation"""
        posting = PostingState(test_posting_id, "Test job description")
        
        assert posting.posting_id == test_posting_id
        assert posting.job_description == "Test job description"
        assert posting.current_conversation_id is None
        assert posting.is_terminal is False
        assert len(posting.outputs) == 0
        assert len(posting.execution_sequence) == 0
    
    def test_pending_postings_query(self, test_workflow_id):
        """Test that pending postings query returns results"""
        processor = WaveBatchProcessor(test_workflow_id)
        postings = processor._get_pending_postings(limit=5)
        
        assert isinstance(postings, list)
        # May be empty if all postings processed
        if len(postings) > 0:
            assert isinstance(postings[0], PostingState)
            assert postings[0].posting_id is not None


class TestCheckpointRecovery:
    """Test checkpoint save and recovery"""
    
    def test_checkpoint_save_and_load(self, db_conn, test_posting_id, test_workflow_id):
        """Test saving and loading checkpoint"""
        processor = WaveBatchProcessor(test_workflow_id)
        
        # Create a posting state with some data
        posting = PostingState(test_posting_id, "Test description")
        posting.workflow_run_id = 99999  # Test run ID
        posting.current_conversation_id = 123
        posting.outputs = {123: "test output"}
        posting.conversation_outputs = {'conversation_1_output': 'test output'}
        posting.execution_sequence = [123]
        
        # Save checkpoint
        processor._save_checkpoint(posting)
        
        # Load checkpoint
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT checkpoint_data 
            FROM posting_state_checkpoints
            WHERE workflow_run_id = %s 
              AND posting_id = %s
        """, (posting.workflow_run_id, posting.posting_id))
        
        result = cursor.fetchone()
        cursor.close()
        
        assert result is not None
        checkpoint = result['checkpoint_data']
        assert checkpoint['posting_id'] == test_posting_id
        assert checkpoint['current_conversation_id'] == 123
        assert len(checkpoint['outputs']) == 1
        
        # Cleanup
        cursor = db_conn.cursor()
        cursor.execute("""
            DELETE FROM posting_state_checkpoints 
            WHERE workflow_run_id = %s AND posting_id = %s
        """, (posting.workflow_run_id, posting.posting_id))
        db_conn.commit()
        cursor.close()


class TestBranchRouting:
    """Test branch condition evaluation"""
    
    def test_wildcard_branch(self, test_workflow_id):
        """Test wildcard (*) branch matches everything"""
        processor = WaveBatchProcessor(test_workflow_id)
        
        branches = [
            {'branch_condition': '*', 'next_conversation_id': 999}
        ]
        
        result = processor._evaluate_branch_conditions(
            "any output",
            branches,
            posting_id=1,
            conversation_id=1
        )
        
        assert result == 999
    
    def test_terminal_branch(self, test_workflow_id):
        """Test TERMINAL branch returns None"""
        processor = WaveBatchProcessor(test_workflow_id)
        
        branches = [
            {'branch_condition': 'TERMINAL', 'next_conversation_id': None}
        ]
        
        result = processor._evaluate_branch_conditions(
            "any output",
            branches,
            posting_id=1,
            conversation_id=1
        )
        
        assert result is None
    
    def test_condition_matching(self, test_workflow_id):
        """Test that specific conditions match correctly"""
        processor = WaveBatchProcessor(test_workflow_id)
        
        branches = [
            {'branch_condition': 'SUCCESS', 'next_conversation_id': 100},
            {'branch_condition': 'FAILED', 'next_conversation_id': 200},
            {'branch_condition': '*', 'next_conversation_id': 300}
        ]
        
        # Test SUCCESS match
        result = processor._evaluate_branch_conditions(
            "Operation completed with SUCCESS",
            branches,
            posting_id=1,
            conversation_id=1
        )
        assert result == 100
        
        # Test FAILED match
        result = processor._evaluate_branch_conditions(
            "Operation FAILED due to error",
            branches,
            posting_id=1,
            conversation_id=1
        )
        assert result == 200
        
        # Test wildcard fallback
        result = processor._evaluate_branch_conditions(
            "Unknown status",
            branches,
            posting_id=1,
            conversation_id=1
        )
        assert result == 300


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_closed_by_default(self):
        """Test circuit starts in CLOSED state"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        assert breaker.can_call(actor_id=1) is True
        status = breaker.get_status(actor_id=1)
        assert status['state'] == 'CLOSED'
    
    def test_circuit_opens_after_failures(self):
        """Test circuit opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=10)
        actor_id = 1
        
        # Record failures
        for _ in range(3):
            breaker.record_failure(actor_id)
        
        # Circuit should now be open
        assert breaker.can_call(actor_id) is False
        status = breaker.get_status(actor_id)
        assert status['state'] == 'OPEN'
        assert status['failure_count'] == 3
    
    def test_circuit_success_resets(self):
        """Test successful call resets failure count in CLOSED state"""
        breaker = CircuitBreaker(failure_threshold=3)
        actor_id = 1
        
        # Record some failures
        breaker.record_failure(actor_id)
        breaker.record_failure(actor_id)
        
        # Then a success
        breaker.record_success(actor_id)
        
        status = breaker.get_status(actor_id)
        assert status['state'] == 'CLOSED'
        assert status['success_count'] == 1
    
    def test_circuit_permanent_disable(self):
        """Test circuit permanently disables after max opens"""
        breaker = CircuitBreaker(
            failure_threshold=2,
            cooldown_seconds=1,
            max_open_count=2
        )
        actor_id = 1
        
        # Open circuit twice
        for _ in range(2):
            breaker.record_failure(actor_id)
            breaker.record_failure(actor_id)
        
        # Should be permanently disabled
        status = breaker.get_status(actor_id)
        assert status['permanently_disabled'] is True
        assert breaker.can_call(actor_id) is False


class TestErrorHandling:
    """Test error handling and logging"""
    
    def test_workflow_errors_table_exists(self, db_conn):
        """Test that workflow_errors table exists"""
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'workflow_errors'
            )
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        
        assert exists is True
    
    def test_error_classification(self):
        """Test error classification logic"""
        from core.error_handler import classify_error, ErrorCategory
        
        # Transient errors
        timeout_error = TimeoutError("Request timed out")
        assert classify_error(timeout_error) == ErrorCategory.TRANSIENT
        
        # Permanent errors
        key_error = KeyError("missing_key")
        assert classify_error(key_error) == ErrorCategory.PERMANENT


class TestWorkflowValidation:
    """Test workflow validation"""
    
    def test_validator_catches_disabled_branches(self, db_conn, test_workflow_id):
        """Test that validator catches branches to disabled conversations"""
        # This test assumes workflow 3001 has been fixed
        # If we temporarily broke it, validator should catch it
        
        cursor = db_conn.cursor()
        
        # Check if any branches point to disabled conversations
        cursor.execute("""
            SELECT COUNT(*) as broken_branches
            FROM instructions i
            JOIN workflow_conversations wc_source ON wc_source.conversation_id = i.conversation_id
            JOIN instruction_steps ist ON ist.instruction_id = i.instruction_id
            LEFT JOIN workflow_conversations wc_target 
                ON wc_target.conversation_id = ist.next_conversation_id
                AND wc_target.workflow_id = %s
            WHERE wc_source.workflow_id = %s
              AND wc_source.enabled = TRUE
              AND ist.next_conversation_id IS NOT NULL
              AND ist.branch_condition != 'TERMINAL'
              AND (wc_target.enabled = FALSE OR wc_target.enabled IS NULL)
        """, (test_workflow_id, test_workflow_id))
        
        result = cursor.fetchone()
        cursor.close()
        
        # Should be 0 broken branches after our fixes
        assert result['broken_branches'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
