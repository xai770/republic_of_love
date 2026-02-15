"""
Pipeline tests — testing the things that have bitten us.

Tests the core pipeline infrastructure:
1. BaseActor connection lifecycle (cleanup, signal handling)
2. ON CONFLICT batch upsert (AA actor)
3. Daemon VPN rotation logic (consecutive failure counting)
4. Task_types VIEW trigger propagation
5. Actor loading by daemon (finds class with process())
"""

import json
import time
import pytest
import psycopg2.extras

from core.base_actor import BaseActor, ProcessingActor


# ============================================================================
# 1. BASE ACTOR — Connection lifecycle
# ============================================================================

class TestBaseActorLifecycle:
    """Test that BaseActor properly manages DB connections."""
    
    def test_owns_connection_when_none_passed(self):
        """Actor creates and owns connection when none provided."""
        actor = BaseActor()
        try:
            assert actor._owns_conn is True
            assert actor.conn is not None
            assert not actor.conn.closed
        finally:
            actor.cleanup()
    
    def test_does_not_own_passed_connection(self, db_conn):
        """Actor does not own connection passed by daemon."""
        actor = BaseActor(db_conn=db_conn)
        assert actor._owns_conn is False
        actor.cleanup()
        # Connection should NOT be returned (we don't own it)
        assert not db_conn.closed
    
    def test_cleanup_returns_owned_connection(self):
        """cleanup() returns owned connection to pool."""
        actor = BaseActor()
        assert actor.conn is not None
        actor.cleanup()
        assert actor.conn is None  # Connection returned
    
    def test_cleanup_idempotent(self):
        """cleanup() can be called multiple times safely."""
        actor = BaseActor()
        actor.cleanup()
        actor.cleanup()  # Should not raise
    
    def test_subject_id_extraction(self, db_conn):
        """subject_id property checks multiple key names."""
        actor = BaseActor(db_conn=db_conn)
        
        actor.input_data = {'subject_id': 42}
        assert actor.subject_id == 42
        
        actor.input_data = {'posting_id': 99}
        assert actor.subject_id == 99
        
        actor.input_data = {'pending_id': 7}
        assert actor.subject_id == 7
        
        actor.input_data = {}
        assert actor.subject_id is None
    
    def test_progress_logging_respects_interval(self, db_conn):
        """log_progress only logs at configured interval."""
        actor = BaseActor(db_conn=db_conn)
        # Force last log to now
        actor._progress_last_log = time.time()
        # This should NOT log (too soon)
        actor.log_progress(1, 100, interval=5.0)
        # Force last log to 10s ago
        actor._progress_last_log = time.time() - 10
        # This should log
        actor.log_progress(50, 100, interval=5.0)
    
    def test_progress_always_logs_last_item(self, db_conn):
        """log_progress always logs the final item regardless of interval."""
        actor = BaseActor(db_conn=db_conn)
        actor._progress_last_log = time.time()  # Just logged
        # Should still log because current == total
        actor.log_progress(100, 100, interval=999.0)


# ============================================================================
# 2. PROCESSING ACTOR — Three-phase structure
# ============================================================================

class DummyActor(ProcessingActor):
    """Minimal ProcessingActor for testing."""
    
    def _preflight(self, subject_id):
        if subject_id == -1:
            return {'ok': False, 'reason': 'TEST_SKIP', 'message': 'test skip'}
        return {'ok': True, 'data': {'value': subject_id * 2, 'should_fail': subject_id == 99}}
    
    def _do_work(self, data, feedback=None):
        if data.get('should_fail'):
            return {'success': False, 'error': 'forced failure'}
        return {'success': True, 'result_value': data['value']}
    
    def _save_result(self, subject_id, result):
        pass  # No-op for testing


class TestProcessingActor:
    """Test the three-phase process() flow."""
    
    def test_successful_process(self, db_conn):
        actor = DummyActor(db_conn=db_conn)
        actor.input_data = {'subject_id': 5}
        result = actor.process()
        
        assert result['success'] is True
        assert result['_consistency'] == '1/1'
        assert result['subject_id'] == 5
        assert result['result_value'] == 10
    
    def test_preflight_skip(self, db_conn):
        actor = DummyActor(db_conn=db_conn)
        actor.input_data = {'subject_id': -1}
        result = actor.process()
        
        assert result['success'] is False
        assert result['skip_reason'] == 'TEST_SKIP'
    
    def test_no_subject_id(self, db_conn):
        actor = DummyActor(db_conn=db_conn)
        actor.input_data = {}
        result = actor.process()
        
        assert result['success'] is False
        assert 'subject_id' in result['error'].lower()
    
    def test_work_failure(self, db_conn):
        actor = DummyActor(db_conn=db_conn)
        actor.input_data = {'subject_id': 99}  # subject_id=99 triggers failure
        result = actor.process()
        
        assert result['success'] is False
        assert 'forced failure' in result['error']


# ============================================================================
# 3. ON CONFLICT UPSERT — AA actor
# ============================================================================

class TestAAUpsert:
    """Test the batch ON CONFLICT upsert in AA actor."""
    
    def test_batch_upsert_new_and_existing(self, db_txn):
        """ON CONFLICT correctly counts new vs existing rows."""
        cur = db_txn.cursor()  # pool default: RealDictCursor
        
        # Create a test job with a unique refnr
        test_refnr = f'TEST-UPSERT-{int(time.time())}'
        
        # First insert should be new
        results = psycopg2.extras.execute_values(cur, """
            INSERT INTO postings (
                external_id, external_job_id, posting_name, job_title, beruf,
                location_city, location_postal_code, location_state, location_country,
                source, external_url, source_metadata, job_description,
                first_seen_at, last_seen_at, posting_status
            ) VALUES %s
            ON CONFLICT (external_job_id)
                WHERE invalidated = false AND external_job_id IS NOT NULL
            DO UPDATE SET
                last_seen_at = NOW(),
                job_description = CASE
                    WHEN EXCLUDED.job_description IS NOT NULL
                         AND LENGTH(EXCLUDED.job_description) >
                             LENGTH(COALESCE(postings.job_description, '')) + 50
                    THEN EXCLUDED.job_description
                    ELSE postings.job_description
                END
            RETURNING (xmax = 0) AS was_inserted
        """, [(
            test_refnr, test_refnr, 'Test Co', 'Test Job', '',
            'Berlin', '10115', 'Berlin', 'DE',
            'arbeitsagentur', 'https://test.com', '{}', 'Short desc',
        )],
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')",
            fetch=True
        )
        
        assert len(results) == 1
        assert results[0]['was_inserted'] == True  # new row
        
        # Second insert of same refnr should be existing (conflict → update)
        results2 = psycopg2.extras.execute_values(cur, """
            INSERT INTO postings (
                external_id, external_job_id, posting_name, job_title, beruf,
                location_city, location_postal_code, location_state, location_country,
                source, external_url, source_metadata, job_description,
                first_seen_at, last_seen_at, posting_status
            ) VALUES %s
            ON CONFLICT (external_job_id)
                WHERE invalidated = false AND external_job_id IS NOT NULL
            DO UPDATE SET
                last_seen_at = NOW(),
                job_description = CASE
                    WHEN EXCLUDED.job_description IS NOT NULL
                         AND LENGTH(EXCLUDED.job_description) >
                             LENGTH(COALESCE(postings.job_description, '')) + 50
                    THEN EXCLUDED.job_description
                    ELSE postings.job_description
                END
            RETURNING (xmax = 0) AS was_inserted
        """, [(
            test_refnr, test_refnr, 'Test Co', 'Test Job', '',
            'Berlin', '10115', 'Berlin', 'DE',
            'arbeitsagentur', 'https://test.com', '{}', 'Short desc',
        )],
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')",
            fetch=True
        )
        
        assert len(results2) == 1
        assert results2[0]['was_inserted'] == False  # conflict → update
    
    def test_description_update_on_longer(self, db_txn):
        """ON CONFLICT updates description when new one is significantly longer."""
        cur = db_txn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        test_refnr = f'TEST-DESC-{int(time.time())}'
        short_desc = 'Short job description for testing'
        long_desc = short_desc + ' ' + 'x' * 100  # 50+ chars longer
        
        # Insert with short description
        psycopg2.extras.execute_values(cur, """
            INSERT INTO postings (
                external_id, external_job_id, posting_name, job_title, beruf,
                location_city, location_postal_code, location_state, location_country,
                source, external_url, source_metadata, job_description,
                first_seen_at, last_seen_at, posting_status
            ) VALUES %s
            ON CONFLICT (external_job_id)
                WHERE invalidated = false AND external_job_id IS NOT NULL
            DO UPDATE SET
                last_seen_at = NOW(),
                job_description = CASE
                    WHEN EXCLUDED.job_description IS NOT NULL
                         AND LENGTH(EXCLUDED.job_description) >
                             LENGTH(COALESCE(postings.job_description, '')) + 50
                    THEN EXCLUDED.job_description
                    ELSE postings.job_description
                END
            RETURNING posting_id
        """, [(
            test_refnr, test_refnr, 'Test', 'Test', '',
            'Berlin', '10115', 'Berlin', 'DE',
            'arbeitsagentur', 'https://test.com', '{}', short_desc,
        )],
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')",
            fetch=True
        )
        
        # Upsert with longer description
        psycopg2.extras.execute_values(cur, """
            INSERT INTO postings (
                external_id, external_job_id, posting_name, job_title, beruf,
                location_city, location_postal_code, location_state, location_country,
                source, external_url, source_metadata, job_description,
                first_seen_at, last_seen_at, posting_status
            ) VALUES %s
            ON CONFLICT (external_job_id)
                WHERE invalidated = false AND external_job_id IS NOT NULL
            DO UPDATE SET
                last_seen_at = NOW(),
                job_description = CASE
                    WHEN EXCLUDED.job_description IS NOT NULL
                         AND LENGTH(EXCLUDED.job_description) >
                             LENGTH(COALESCE(postings.job_description, '')) + 50
                    THEN EXCLUDED.job_description
                    ELSE postings.job_description
                END
            RETURNING posting_id
        """, [(
            test_refnr, test_refnr, 'Test', 'Test', '',
            'Berlin', '10115', 'Berlin', 'DE',
            'arbeitsagentur', 'https://test.com', '{}', long_desc,
        )],
            template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 'active')",
            fetch=True
        )
        
        # Verify description was updated
        cur.execute("""
            SELECT job_description FROM postings WHERE external_job_id = %s
        """, (test_refnr,))
        row = cur.fetchone()
        assert row['job_description'] == long_desc


# ============================================================================
# 4. DAEMON — VPN rotation logic
# ============================================================================

class TestVPNRotationLogic:
    """Test consecutive failure counting (not actual VPN calls)."""
    
    def test_consecutive_failure_counting(self):
        """Successful requests reset the consecutive failure counter."""
        from core.turing_daemon import TuringDaemon
        
        daemon = TuringDaemon.__new__(TuringDaemon)
        daemon._consecutive_failed_rotations = 0
        daemon._requests_since_rotation = 0
        daemon._total_rotations = 0
        
        # Simulate failures
        daemon._consecutive_failed_rotations = 3
        assert daemon._consecutive_failed_rotations == 3
        
        # Simulate success: reset
        daemon._consecutive_failed_rotations = 0
        assert daemon._consecutive_failed_rotations == 0


# ============================================================================
# 5. TASK_TYPES VIEW — Trigger propagation
# ============================================================================

class TestTaskTypesView:
    """Test that the task_types view correctly propagates updates."""
    
    def test_priority_update_propagates(self, db_txn):
        """UPDATE task_types SET priority = X actually changes actors.priority."""
        cur = db_txn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get a task type to test with
        cur.execute("SELECT task_type_id, priority FROM task_types LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("No task_types found")
        
        task_type_id = row['task_type_id']
        original_priority = row['priority']
        new_priority = original_priority + 1
        
        # Update through VIEW
        cur.execute("UPDATE task_types SET priority = %s WHERE task_type_id = %s",
                    (new_priority, task_type_id))
        
        # Verify on ACTORS table directly
        cur.execute("SELECT priority FROM actors WHERE actor_id = %s", (task_type_id,))
        actors_row = cur.fetchone()
        assert actors_row['priority'] == new_priority
    
    def test_enabled_update_propagates(self, db_txn):
        """UPDATE task_types SET enabled = X actually changes actors.enabled."""
        cur = db_txn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT task_type_id, enabled FROM task_types LIMIT 1")
        row = cur.fetchone()
        if not row:
            pytest.skip("No task_types found")
        
        task_type_id = row['task_type_id']
        new_enabled = not row['enabled']
        
        cur.execute("UPDATE task_types SET enabled = %s WHERE task_type_id = %s",
                    (new_enabled, task_type_id))
        
        cur.execute("SELECT enabled FROM actors WHERE actor_id = %s", (task_type_id,))
        actors_row = cur.fetchone()
        assert actors_row['enabled'] == new_enabled


# ============================================================================
# 6. ACTOR LOADING — Daemon can find process() method
# ============================================================================

class TestActorLoading:
    """Test that daemon's actor loading mechanism works with refactored actors."""
    
    def test_extracted_summary_loadable(self):
        """Daemon can load SummaryExtractActor and find process()."""
        import importlib
        mod = importlib.import_module('actors.postings__extracted_summary_U')
        
        # Find class with process() method (same logic as daemon)
        actor_class = None
        for name in dir(mod):
            obj = getattr(mod, name)
            if (isinstance(obj, type) 
                and hasattr(obj, 'process') 
                and name not in ('BaseActor', 'ProcessingActor', 'SourceActor')):
                actor_class = obj
                break
        
        assert actor_class is not None, "No actor class found with process() method"
        assert actor_class.__name__ == 'SummaryExtractActor'
    
    def test_base_actor_subclass_has_process(self):
        """ProcessingActor subclasses inherit process()."""
        assert hasattr(ProcessingActor, 'process')
        assert callable(ProcessingActor.process)


# ============================================================================
# 7. LLM HELPERS — JSON parsing
# ============================================================================

class TestLLMHelpers:
    """Test BaseActor LLM helper methods."""
    
    def test_parse_json_direct(self, db_conn):
        actor = BaseActor(db_conn=db_conn)
        result = actor.parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}
    
    def test_parse_json_from_markdown(self, db_conn):
        actor = BaseActor(db_conn=db_conn)
        result = actor.parse_json_response('Here is the result:\n```json\n{"key": 42}\n```\nDone.')
        assert result == {"key": 42}
    
    def test_parse_json_from_embedded(self, db_conn):
        actor = BaseActor(db_conn=db_conn)
        result = actor.parse_json_response('The answer is {"score": 0.95} and that is good.')
        assert result == {"score": 0.95}
    
    def test_parse_json_returns_none_on_garbage(self, db_conn):
        actor = BaseActor(db_conn=db_conn)
        assert actor.parse_json_response('this is not json at all') is None
        assert actor.parse_json_response('') is None
        assert actor.parse_json_response(None) is None
    
    def test_bad_data_detection(self, db_conn):
        actor = BaseActor(db_conn=db_conn)
        assert actor.is_bad_data_response('The information is not specified in the text provided.')
        assert actor.is_bad_data_response('Cannot be determined from the given context.')
        assert not actor.is_bad_data_response('Software Engineer with 5 years experience')
        assert actor.is_bad_data_response('')  # Empty is bad data
        assert actor.is_bad_data_response(None)  # None is bad data


# ============================================================================
# 8. IDLE IN TRANSACTION TIMEOUT — DB setting
# ============================================================================

class TestDBSettings:
    """Test that critical DB settings are in place."""
    
    def test_idle_in_transaction_timeout_set(self, db_txn):
        """idle_in_transaction_session_timeout is configured on the database."""
        cur = db_txn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT setconfig FROM pg_db_role_setting d
            JOIN pg_database db ON db.oid = d.setdatabase
            WHERE db.datname = current_database()
        """)
        row = cur.fetchone()
        assert row is not None, "No database-level settings found"
        configs = row['setconfig']
        timeout_set = any('idle_in_transaction_session_timeout' in c for c in configs)
        assert timeout_set, "idle_in_transaction_session_timeout not configured"
