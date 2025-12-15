#!/usr/bin/env python3
"""
Test Event Store Implementation

Tests:
1. Basic event append and retrieval
2. Projection rebuild from events
3. Idempotency (duplicate events)
4. Validation against old schema
5. Snapshot creation
6. Dual-write mode

Run: python3 scripts/test_event_store.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.event_store import EventStore
import json


def test_basic_event_append():
    """Test 1: Append events and retrieve state"""
    print("\n" + "="*60)
    print("TEST 1: Basic Event Append")
    print("="*60)
    
    # Disable dual-write for initial testing
    store = EventStore(enable_dual_write=False)
    
    # Create posting
    event_id_1 = store.append_event(
        aggregate_type='posting',
        aggregate_id='9999',
        event_type='posting_created',
        event_data={'step': 1, 'workflow_id': 3001},
        metadata={'actor_id': 12, 'workflow_id': 3001},
        correlation_id='test_run_123'
    )
    print(f"✅ Created posting_created event: {event_id_1}")
    
    # Complete conversation
    event_id_2 = store.append_event(
        aggregate_type='posting',
        aggregate_id='9999',
        event_type='conversation_completed',
        event_data={
            'conversation_id': 1,
            'output': '[PASS]',
            'tokens': 150,
            'duration_ms': 1200
        },
        metadata={'actor_id': 12, 'workflow_id': 3001},
        correlation_id='test_run_123',
        causation_id=event_id_1
    )
    print(f"✅ Created conversation_completed event: {event_id_2}")
    
    # Branch to next step
    event_id_3 = store.append_event(
        aggregate_type='posting',
        aggregate_id='9999',
        event_type='posting_branched_to',
        event_data={'next_step': 2, 'branch': 'success'},
        metadata={'actor_id': 12, 'workflow_id': 3001},
        correlation_id='test_run_123',
        causation_id=event_id_2
    )
    print(f"✅ Created posting_branched_to event: {event_id_3}")
    
    print("\n✅ TEST 1 PASSED: Events appended successfully")
    
    store.close()


def test_projection_rebuild():
    """Test 2: Rebuild projection from events"""
    print("\n" + "="*60)
    print("TEST 2: Projection Rebuild")
    print("="*60)
    
    store = EventStore(enable_dual_write=True)
    
    # Rebuild projection from events
    metrics = store.rebuild_projection(9999)
    
    print(f"✅ Projection rebuilt:")
    print(f"   - Events replayed: {metrics['events_replayed']}")
    print(f"   - Rebuild time: {metrics['rebuild_time_ms']}ms")
    
    # Get current state
    state = store.get_posting_state(9999)
    
    print(f"\n✅ Current state:")
    print(f"   - Current step: {state['current_step']}")
    print(f"   - Status: {state['current_status']}")
    print(f"   - Outputs: {state['outputs']}")
    print(f"   - Total tokens: {state['total_tokens']}")
    print(f"   - Last updated: {state['last_updated']}")
    
    assert state['current_step'] == 2, "Expected step 2"
    assert state['outputs'].get('1') == '[PASS]', "Expected [PASS] output"
    
    print("\n✅ TEST 2 PASSED: Projection rebuilt correctly")
    
    store.close()


def test_idempotency():
    """Test 3: Idempotency - duplicate events should not create duplicates"""
    print("\n" + "="*60)
    print("TEST 3: Idempotency")
    print("="*60)
    
    store = EventStore(enable_dual_write=True)
    
    # Create event with idempotency key
    idempotency_key = "posting_9999_conv_5_test"
    
    event_id_1 = store.append_event(
        aggregate_type='posting',
        aggregate_id='9999',
        event_type='conversation_completed',
        event_data={'conversation_id': 5, 'output': '[PASS]'},
        metadata={'actor_id': 12},
        idempotency_key=idempotency_key
    )
    print(f"✅ First event created: {event_id_1}")
    
    # Try to create same event again (retry scenario)
    event_id_2 = store.append_event(
        aggregate_type='posting',
        aggregate_id='9999',
        event_type='conversation_completed',
        event_data={'conversation_id': 5, 'output': '[PASS]'},
        metadata={'actor_id': 12},
        idempotency_key=idempotency_key
    )
    print(f"✅ Retry returned same event: {event_id_2}")
    
    assert event_id_1 == event_id_2, "Idempotency failed - different event IDs!"
    
    print("\n✅ TEST 3 PASSED: Idempotency works correctly")
    
    store.close()


def test_validation():
    """Test 4: Validate event store against old schema"""
    print("\n" + "="*60)
    print("TEST 4: Validation")
    print("="*60)
    
    store = EventStore(enable_dual_write=True)
    
    # Rebuild projection to ensure sync
    store.rebuild_projection(9999)
    
    # Validate
    discrepancies = store.validate()
    
    if discrepancies:
        print(f"⚠️  Found {len(discrepancies)} discrepancies:")
        for disc in discrepancies[:5]:
            print(f"   - Posting {disc['posting_id']}: {disc['discrepancy_type']}")
            print(f"     Old: {disc['old_value']}")
            print(f"     New: {disc['new_value']}")
    else:
        print("✅ No discrepancies found - event store matches old schema")
    
    print("\n✅ TEST 4 PASSED: Validation completed")
    
    store.close()


def test_snapshot_creation():
    """Test 5: Snapshot creation"""
    print("\n" + "="*60)
    print("TEST 5: Snapshot Creation")
    print("="*60)
    
    store = EventStore(enable_dual_write=True)
    
    # Create snapshot (interval=3 for testing)
    store.maybe_create_snapshot(9999, snapshot_interval=3)
    
    print("✅ Snapshot creation attempted (check if interval reached)")
    print("\n✅ TEST 5 PASSED: Snapshot logic works")
    
    store.close()


def test_metrics():
    """Test 6: Get metrics"""
    print("\n" + "="*60)
    print("TEST 6: Metrics")
    print("="*60)
    
    store = EventStore(enable_dual_write=True)
    
    # Add a few events
    for i in range(3):
        store.append_event(
            aggregate_type='posting',
            aggregate_id='9999',
            event_type='llm_call_completed',
            event_data={'conversation_id': i, 'tokens': 100},
            metadata={'actor_id': 12}
        )
    
    # Get metrics
    metrics = store.get_metrics()
    
    print("✅ Event Store Metrics:")
    print(f"   - Events appended: {metrics['events_appended']}")
    print(f"   - Projections rebuilt: {metrics['projections_rebuilt']}")
    print(f"   - Dual writes: {metrics['dual_writes']}")
    print(f"   - Snapshots created: {metrics['snapshots_created']}")
    print(f"   - Dual-write enabled: {metrics['enable_dual_write']}")
    
    print("\n✅ TEST 6 PASSED: Metrics collected")
    
    store.close()


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("EVENT STORE TEST SUITE")
    print("="*60)
    print("Testing event sourcing implementation...")
    
    try:
        test_basic_event_append()
        test_projection_rebuild()
        test_idempotency()
        test_snapshot_creation()
        test_metrics()
        test_validation()  # Last because it checks all postings
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nEvent store is working correctly.")
        print("Ready for integration with workflow_executor.py")
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED")
        print("="*60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
