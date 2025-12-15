#!/usr/bin/env python3
"""
Unit Tests for WaveProcessor
=============================

Tests for the refactored wave processing logic to prevent regressions,
especially the critical indentation bug.

Created: November 19, 2025
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.wave_executor import WaveProcessor, RetryableError, PermanentError
from core.posting_state import PostingState


class MockLogger:
    """Mock logger for testing"""
    def __init__(self):
        self.logs = []
    
    def info(self, msg, **kwargs):
        self.logs.append(('INFO', msg, kwargs))
    
    def error(self, msg, **kwargs):
        self.logs.append(('ERROR', msg, kwargs))
    
    def warning(self, msg, **kwargs):
        self.logs.append(('WARNING', msg, kwargs))
    
    def debug(self, msg, **kwargs):
        self.logs.append(('DEBUG', msg, kwargs))


class MockCircuitBreaker:
    """Mock circuit breaker for testing"""
    def __init__(self, can_call_result=True):
        self.can_call_result = can_call_result
        self.success_calls = []
        self.failure_calls = []
    
    def can_call(self, actor_id):
        return self.can_call_result
    
    def record_success(self, actor_id):
        self.success_calls.append(actor_id)
    
    def record_failure(self, actor_id):
        self.failure_calls.append(actor_id)
    
    def get_status(self, actor_id):
        return {'state': 'OPEN', 'permanently_disabled': False}


class MockEventStore:
    """Mock event store for testing"""
    def __init__(self):
        self.events = []
    
    def append_event(self, event_type, aggregate_type, aggregate_id, event_data, metadata):
        self.events.append({
            'type': event_type,
            'aggregate_type': aggregate_type,
            'aggregate_id': aggregate_id,
            'event_data': event_data,
            'metadata': metadata
        })


class MockPromptRenderer:
    """Mock prompt renderer for testing"""
    def render(self, template, posting, execution_order):
        return f"Rendered: {template} for posting {posting.posting_id}"


def test_process_wave_success():
    """Test successful wave processing with multiple postings"""
    workflow_def = {
        'conversations': {
            1: {
                'conversation_id': 1,
                'canonical_name': 'test_conversation',
                'execution_order': 1,
                'actor_id': 74,
                'actor_name': 'test_actor',
                'workflow_step_id': 1,
                'instructions': [
                    {'prompt_template': 'Test: {job_description}', 'timeout_seconds': 30}
                ],
                'branches': []
            }
        }
    }
    
    logger = MockLogger()
    event_store = MockEventStore()
    circuit_breaker = MockCircuitBreaker(can_call_result=True)
    prompt_renderer = MockPromptRenderer()
    
    processor = WaveProcessor(
        workflow_definition=workflow_def,
        workflow_id=3001,
        circuit_breaker=circuit_breaker,
        event_store=event_store,
        prompt_renderer=prompt_renderer,
        logger=logger
    )
    
    # Create 3 test postings
    postings = [
        PostingState(posting_id=1, job_description="Test job 1"),
        PostingState(posting_id=2, job_description="Test job 2"),
        PostingState(posting_id=3, job_description="Test job 3")
    ]
    
    for p in postings:
        p.workflow_run_id = p.posting_id
    
    # Mock executor that always succeeds
    def mock_executor(actor_id, prompt, timeout):
        return {'status': 'SUCCESS', 'response': f'Success for {prompt}', 'latency_ms': 100}
    
    result = processor.process_wave(
        conversation_id=1,
        postings=postings,
        execute_actor_func=mock_executor
    )
    
    # Verify all 3 postings processed (THIS IS THE CRITICAL TEST - indentation bug would process only 1)
    assert result == 3, f"Expected 3 postings processed, got {result}"
    
    # Verify 3 events appended
    assert len(event_store.events) == 3, f"Expected 3 events, got {len(event_store.events)}"
    
    # Verify all events are for correct postings
    event_posting_ids = [int(e['aggregate_id']) for e in event_store.events]
    assert event_posting_ids == [1, 2, 3], f"Expected postings [1,2,3], got {event_posting_ids}"
    
    # Verify circuit breaker recorded 3 successes
    assert len(circuit_breaker.success_calls) == 3
    
    # Verify enhanced metadata is present
    first_event_metadata = event_store.events[0]['metadata']
    assert 'duration_ms' in first_event_metadata
    assert 'retry_count' in first_event_metadata
    assert 'correlation_id' in first_event_metadata
    assert first_event_metadata['correlation_id'] == 'workflow_3001_posting_1'
    
    print("✅ test_process_wave_success PASSED")


def test_process_wave_circuit_breaker_open():
    """Test wave processing when circuit breaker is open"""
    workflow_def = {
        'conversations': {
            1: {
                'conversation_id': 1,
                'canonical_name': 'test_conversation',
                'execution_order': 1,
                'actor_id': 74,
                'actor_name': 'test_actor',
                'workflow_step_id': 1,
                'instructions': [
                    {'prompt_template': 'Test: {job_description}', 'timeout_seconds': 30}
                ],
                'branches': []
            }
        }
    }
    
    logger = MockLogger()
    event_store = MockEventStore()
    circuit_breaker = MockCircuitBreaker(can_call_result=False)  # Circuit breaker CLOSED
    prompt_renderer = MockPromptRenderer()
    
    processor = WaveProcessor(
        workflow_definition=workflow_def,
        workflow_id=3001,
        circuit_breaker=circuit_breaker,
        event_store=event_store,
        prompt_renderer=prompt_renderer,
        logger=logger
    )
    
    postings = [PostingState(posting_id=1, job_description="Test job")]
    postings[0].workflow_run_id = 1
    
    def mock_executor(actor_id, prompt, timeout):
        return {'status': 'SUCCESS', 'output': 'Should not be called'}
    
    result = processor.process_wave(
        conversation_id=1,
        postings=postings,
        execute_actor_func=mock_executor
    )
    
    # No postings should be processed when circuit breaker is open
    assert result == 0, f"Expected 0 postings processed, got {result}"
    
    # No successes recorded (circuit breaker prevented execution)
    assert len(circuit_breaker.success_calls) == 0
    
    print("✅ test_process_wave_circuit_breaker_open PASSED")


def test_process_wave_actor_failure():
    """Test wave processing when actor execution fails"""
    workflow_def = {
        'conversations': {
            1: {
                'conversation_id': 1,
                'canonical_name': 'test_conversation',
                'execution_order': 1,
                'actor_id': 74,
                'actor_name': 'test_actor',
                'workflow_step_id': 1,
                'instructions': [
                    {'prompt_template': 'Test: {job_description}', 'timeout_seconds': 30}
                ],
                'branches': []
            }
        }
    }
    
    logger = MockLogger()
    event_store = MockEventStore()
    circuit_breaker = MockCircuitBreaker(can_call_result=True)
    prompt_renderer = MockPromptRenderer()
    
    processor = WaveProcessor(
        workflow_definition=workflow_def,
        workflow_id=3001,
        circuit_breaker=circuit_breaker,
        event_store=event_store,
        prompt_renderer=prompt_renderer,
        logger=logger
    )
    
    postings = [PostingState(posting_id=1, job_description="Test job")]
    postings[0].workflow_run_id = 1
    
    # Mock executor that fails
    def mock_executor(actor_id, prompt, timeout):
        return {'status': 'FAILURE', 'error': 'Test error', 'latency_ms': 50}
    
    result = processor.process_wave(
        conversation_id=1,
        postings=postings,
        execute_actor_func=mock_executor
    )
    
    # Posting should not be counted as "processed" on failure
    assert result == 0, f"Expected 0 successful postings, got {result}"
    
    # Circuit breaker should record failure
    assert len(circuit_breaker.failure_calls) == 1
    assert circuit_breaker.failure_calls[0] == 74
    
    # Failures are logged but don't create events in current implementation
    # (events are only created on success)
    
    print("✅ test_process_wave_actor_failure PASSED")


def test_indentation_bug_regression():
    """
    CRITICAL TEST: Verify the indentation bug is fixed.
    
    The original bug had try-except at the same level as the for loop,
    causing only the first posting in each chunk to be processed.
    
    This test processes 5 postings and verifies ALL 5 are processed,
    not just the first one.
    """
    workflow_def = {
        'conversations': {
            1: {
                'conversation_id': 1,
                'canonical_name': 'indentation_test',
                'execution_order': 1,
                'actor_id': 74,
                'actor_name': 'test_actor',
                'workflow_step_id': 1,
                'instructions': [
                    {'prompt_template': 'Test: {job_description}', 'timeout_seconds': 30}
                ],
                'branches': []
            }
        }
    }
    
    logger = MockLogger()
    event_store = MockEventStore()
    circuit_breaker = MockCircuitBreaker(can_call_result=True)
    prompt_renderer = MockPromptRenderer()
    
    processor = WaveProcessor(
        workflow_definition=workflow_def,
        workflow_id=3001,
        circuit_breaker=circuit_breaker,
        event_store=event_store,
        prompt_renderer=prompt_renderer,
        logger=logger
    )
    
    # Create 5 postings (simulates a small chunk)
    postings = [PostingState(posting_id=i, job_description=f"Job {i}") for i in range(1, 6)]
    for p in postings:
        p.workflow_run_id = p.posting_id
    
    execution_count = 0
    
    def counting_executor(actor_id, prompt, timeout):
        nonlocal execution_count
        execution_count += 1
        return {'status': 'SUCCESS', 'response': f'Result {execution_count}', 'latency_ms': 10}
    
    result = processor.process_wave(
        conversation_id=1,
        postings=postings,
        execute_actor_func=counting_executor
    )
    
    # CRITICAL ASSERTION: All 5 postings must be processed
    assert execution_count == 5, f"INDENTATION BUG REGRESSION! Only {execution_count}/5 postings executed"
    assert result == 5, f"Expected 5 postings processed, got {result}"
    assert len(event_store.events) == 5, f"Expected 5 events, got {len(event_store.events)}"
    
    print("✅ test_indentation_bug_regression PASSED - Bug is FIXED!")


if __name__ == '__main__':
    # Run tests
    print("\n" + "="*60)
    print("Running WaveProcessor Unit Tests")
    print("="*60 + "\n")
    
    test_process_wave_success()
    test_process_wave_circuit_breaker_open()
    test_process_wave_actor_failure()
    test_indentation_bug_regression()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60 + "\n")
    
    # Also run with pytest if available
    try:
        pytest.main([__file__, '-v'])
    except:
        print("pytest not available, manual test execution completed")
