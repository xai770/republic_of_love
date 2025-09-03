"""
ConvergedMemBridge: Core implementation of value-weighted LLM interaction storage.

This module implements the convergence plan from PSM Round 2.5, providing
intelligent caching and storage decisions based on interaction value rather
than simple hit/miss patterns.

Round 5.2 Implementation Goals:
- Environmental context tracking and drift detection
- Value-weighted storage decisions (failures > firsts > outliers > samples)
- Template lifecycle management (learning -> verified -> stable)
- SQLite-based persistence with performance optimization
- Fallback modes for error resilience

Author: Arden
Date: 2025-09-02
PSM Round: 5.2
"""

import hashlib
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union, cast
import json
import logging
import statistics

# Import our modular components
from .models import (
    MemBridgeConfig, CallData, EnvironmentalContext, 
    DriftDetectionConfig, TemplateInfo
)
from .environmental import DriftDetector

# Configure logging for MemBridge operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConvergedMemBridge:
    """
    A memory system that learns when to remember and when to forget.
    
    Implements value-weighted storage decisions where:
    1. Failures always stored (highest debugging value)
    2. First N examples stored (learning value) 
    3. Outliers stored (QA value)
    4. Periodic samples stored (drift monitoring value)
    5. Everything else cached only
    
    Round 5.2 additions:
    - Environmental context collection (hour, weekday, CPU%, memory%)
    - Drift detection for adaptive storage decisions
    - Performance optimization through context caching
    """
    
    def __init__(self, db_path: Union[str, Path], config: Optional[MemBridgeConfig] = None):
        """Initialize MemBridge with database and configuration."""
        self.db_path = Path(db_path)
        self.config = config or MemBridgeConfig()
        
        # Round 5.2: Initialize drift detection
        drift_config_path = Path(self.config.drift_config_path) if hasattr(self.config, 'drift_config_path') else Path("config/drift.yaml")
        self.drift_detector = DriftDetector(drift_config_path)
        
        # Initialize storage systems
        self._fallback_mode = False
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_database()
        except (PermissionError, OSError) as e:
            # Fallback to memory-only mode if we can't create directories
            logger.warning(f"Cannot create database directory {self.db_path.parent}: {e}. Operating in memory-only mode.")
            self._fallback_mode = True
            self.db_path = Path(":memory:")
            try:
                self._init_database()
            except Exception as db_error:
                logger.error(f"Failed to initialize in-memory database: {db_error}. Operating in direct-call mode.")
                # Complete fallback - no storage at all
                self._fallback_mode = True
        
        # Cache for template information and interactions
        self._template_cache: Dict[str, TemplateInfo] = {}
        self._interaction_cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            'total_calls': 0,
            'cache_hits': 0, 
            'cache_misses': 0,
            'storage_decisions': {'stored': 0, 'cached_only': 0}
        }
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        # Use string path for in-memory databases
        db_path_str = str(self.db_path) if self.db_path != Path(":memory:") else ":memory:"
        
        try:
            with sqlite3.connect(db_path_str, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=memory")
                
                # Templates table - stores template metadata (renamed to match tests)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS template_status (
                        template_hash TEXT PRIMARY KEY,
                        call_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        avg_latency REAL DEFAULT 0.0,
                        latency_std REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_cached_context TEXT,
                        last_context_time TIMESTAMP,
                        
                        -- Round 5.3: Adaptive Confidence fields (Max's specifications)
                        confidence_score REAL DEFAULT 0.5,
                        failure_streak INTEGER DEFAULT 0,
                        last_failure_timestamp TIMESTAMP,
                        lifecycle_stage TEXT DEFAULT 'learning'
                    )
                """)
                
                # Interactions table - stores full interaction data
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        template_hash TEXT,
                        prompt TEXT,
                        model TEXT,
                        response TEXT,
                        latency_ms REAL,
                        success BOOLEAN,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        error TEXT,
                        storage_reason TEXT,
                        environmental_context TEXT
                    )
                """)
                
                # Interaction metadata table - stores additional metadata
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS interaction_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        interaction_id INTEGER,
                        key TEXT,
                        value TEXT,
                        FOREIGN KEY (interaction_id) REFERENCES interactions(id)
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_template_status_last_used ON template_status(last_used)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_template ON interactions(template_hash)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)")
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except sqlite3.DatabaseError as e:
            # Handle corrupted database by creating a new one
            logger.warning(f"Database corruption detected: {e}. Creating new database.")
            try:
                # Skip file operations for in-memory databases
                if self.db_path != Path(":memory:"):
                    # Remove corrupted database
                    if self.db_path.exists():
                        backup_path = self.db_path.with_suffix('.corrupted')
                        self.db_path.rename(backup_path)
                        logger.info(f"Corrupted database moved to {backup_path}")
                
                # Retry initialization with new database
                with sqlite3.connect(db_path_str, timeout=30.0) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute("PRAGMA cache_size=10000")
                    conn.execute("PRAGMA temp_store=memory")
                    
                    conn.execute("""
                        CREATE TABLE template_status (
                            template_hash TEXT PRIMARY KEY,
                            call_count INTEGER DEFAULT 0,
                            failure_count INTEGER DEFAULT 0,
                            avg_latency REAL DEFAULT 0.0,
                            latency_std REAL DEFAULT 0.0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_cached_context TEXT,
                            last_context_time TIMESTAMP,
                            confidence_score REAL DEFAULT 0.6,
                            failure_streak INTEGER DEFAULT 0,
                            last_failure_timestamp TIMESTAMP
                        )
                    """)
                    
                    conn.execute("""
                        CREATE TABLE interactions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            template_hash TEXT,
                            prompt TEXT,
                            model TEXT,
                            response TEXT,
                            latency_ms REAL,
                            success BOOLEAN,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            error TEXT,
                            storage_reason TEXT,
                            environmental_context TEXT
                        )
                    """)
                    
                    conn.execute("CREATE INDEX idx_template_status_last_used ON template_status(last_used)")
                    conn.execute("CREATE INDEX idx_interactions_template ON interactions(template_hash)")
                    conn.execute("CREATE INDEX idx_interactions_timestamp ON interactions(timestamp)")
                    
                    conn.commit()
                    logger.info(f"New database created successfully at {self.db_path}")
                    
            except Exception as recovery_error:
                logger.error(f"Failed to recover from database corruption: {recovery_error}")
                raise
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _get_db_path(self) -> str:
        """Get database path as string, handling in-memory databases."""
        return str(self.db_path) if self.db_path != Path(":memory:") else ":memory:"
    
    def _hash_template(self, prompt: str, model: str) -> str:
        """Generate consistent hash for prompt template identification."""
        # Normalize prompt by removing excess whitespace
        normalized = ' '.join(prompt.split())
        template_string = f"{normalized}|{model}"
        return hashlib.sha256(template_string.encode()).hexdigest()[:16]
    
    def _get_template_info(self, template_hash: str) -> TemplateInfo:
        """Get or create template information."""
        if template_hash in self._template_cache:
            return self._template_cache[template_hash]
        
        try:
            with sqlite3.connect(self._get_db_path(), timeout=5.0) as conn:
                cursor = conn.execute("""
                    SELECT call_count, failure_count, avg_latency, latency_std, 
                           created_at, last_used, last_cached_context, last_context_time,
                           confidence_score, failure_streak, last_failure_timestamp, lifecycle_stage
                    FROM template_status WHERE template_hash = ?
                """, (template_hash,))
                
                row = cursor.fetchone()
                if row:
                    template_info = TemplateInfo(
                        template_hash=template_hash,
                        call_count=row[0],
                        failure_count=row[1],
                        avg_latency=row[2],
                        latency_std=row[3],
                        created_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                        last_used=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                        last_cached_context=row[6],
                        last_context_time=datetime.fromisoformat(row[7]) if row[7] else None,
                        # Round 5.3: Confidence fields with defaults for backward compatibility
                        confidence_score=row[8] if row[8] is not None else 0.5,
                        failure_streak=row[9] if row[9] is not None else 0,
                        last_failure_timestamp=datetime.fromisoformat(row[10]) if row[10] else None,
                        lifecycle_stage=row[11] if row[11] else "learning"
                    )
                else:
                    # Create new template with Round 5.3 defaults
                    template_info = TemplateInfo(template_hash=template_hash)
                    conn.execute("""
                        INSERT INTO template_status 
                        (template_hash, created_at, last_used, confidence_score, failure_streak, lifecycle_stage)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (template_hash, template_info.created_at.isoformat(), 
                         template_info.last_used.isoformat(), 0.5, 0, "learning"))
                    conn.commit()
                
                self._template_cache[template_hash] = template_info
                return template_info
                
        except Exception as e:
            logger.warning(f"Failed to get template info: {e}")
            # Return minimal template info for fallback
            return TemplateInfo(template_hash=template_hash)
    
    def _get_cached_response(self, template_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and valid."""
        # First check in-memory cache
        if template_hash in self._interaction_cache:
            cached = self._interaction_cache[template_hash]
            cache_time = datetime.fromisoformat(cached['cached_at'])
            
            # Check if cache is still valid
            if datetime.now() - cache_time < timedelta(seconds=self.config.cache_duration_seconds):
                self._stats['cache_hits'] = cast(int, self._stats['cache_hits']) + 1
                logger.debug(f"Cache hit for template {template_hash[:8]}")
                return cast(Dict[str, Any], cached['response'])
        
        # Fallback to database cache for backwards compatibility
        try:
            with sqlite3.connect(self._get_db_path(), timeout=2.0) as conn:
                cursor = conn.execute("""
                    SELECT response, timestamp FROM interactions 
                    WHERE template_hash = ? AND success = 1
                    ORDER BY timestamp DESC LIMIT 1
                """, (template_hash,))
                
                row = cursor.fetchone()
                if row:
                    response, timestamp_str = row
                    cache_time = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                    
                    # Check if database cache is still valid
                    if datetime.now() - cache_time < timedelta(seconds=self.config.cache_duration_seconds):
                        self._stats['cache_hits'] = cast(int, self._stats['cache_hits']) + 1
                        logger.debug(f"Database cache hit for template {template_hash[:8]}")
                        return {'response': response, 'success': True, 'from_database': True}
        except Exception as e:
            logger.debug(f"Database cache lookup failed: {e}")
        
        self._stats['cache_misses'] = cast(int, self._stats['cache_misses']) + 1
        return None
    
    def should_store_interaction(self, call_data: CallData, template_info: TemplateInfo) -> Tuple[bool, str]:
        """
        Determine if interaction should be stored based on value-weighted algorithm
        integrated with Round 5.3 adaptive confidence lifecycle management.
        
        Returns:
            Tuple of (should_store, reason)
        """
        # Skip storage decision in fallback mode
        if hasattr(self, '_fallback_mode') and self._fallback_mode:
            return False, "safe_mode_corruption"
            
        # Rule 0: Check storage bounds first (enforced for all interactions)
        try:
            with sqlite3.connect(self._get_db_path(), timeout=2.0) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM interactions WHERE template_hash = ?
                """, (template_info.template_hash,))
                current_stored = cursor.fetchone()[0]
                
                if current_stored >= self.config.max_interactions_per_template:
                    return False, "storage_bounds_exceeded"
        except Exception as e:
            logger.debug(f"Failed to check storage bounds: {e}")

        # Rule 1: Always store failures (highest debugging value + confidence learning)
        if not call_data.success:
            return True, "failure_analysis"

        # Rule 2: Round 5.3 Lifecycle-based storage (Max's specifications)
        lifecycle_should_store, lifecycle_reason = template_info.should_store_based_on_lifecycle()
        if lifecycle_should_store:
            return True, lifecycle_reason

        # Rule 3: Check for environmental drift (Round 5.2)
        should_store_drift, drift_reason = self.drift_detector.should_store_for_drift(template_info)
        if should_store_drift:
            return True, "drift_monitoring"
        
        # Rule 4: Store performance outliers (QA value)
        if template_info.call_count >= 5:  # Need some data for statistics
            try:
                # Get recent latencies for this template
                with sqlite3.connect(self.db_path, timeout=2.0) as conn:
                    cursor = conn.execute("""
                        SELECT latency_ms FROM interactions 
                        WHERE template_hash = ? AND success = 1
                        ORDER BY timestamp DESC LIMIT 20
                    """, (template_info.template_hash,))
                    
                    latencies = [row[0] for row in cursor.fetchall()]
                    if len(latencies) >= 3:
                        mean_latency = statistics.mean(latencies)
                        if len(latencies) > 1:
                            std_latency = statistics.stdev(latencies)
                            if call_data.latency_ms > mean_latency + (self.config.outlier_threshold * std_latency):
                                return True, "performance_outlier"
            except Exception as e:
                logger.debug(f"Outlier detection failed: {e}")
        
        # Rule 5: Low confidence templates get extra attention
        if template_info.confidence_score < 0.3:
            import random
            if random.random() < 0.2:  # 20% sampling for low confidence templates
                return True, "low_confidence_monitoring"

        # Rule 6: Periodic sampling for general system health (reduced from 5% to 2%)
        import random
        if random.random() < 0.02:
            return True, "system_health_sample"
        
        # Default: cache only
        return False, "routine_interaction"
    
    def _store_full_interaction(self, template_hash: str, call_data: CallData, 
                               reason: str, context: Optional[EnvironmentalContext] = None) -> None:
        """Store complete interaction data in database."""
        # Skip storage entirely in fallback mode
        if hasattr(self, '_fallback_mode') and self._fallback_mode:
            logger.debug(f"Skipping storage in fallback mode: {reason}")
            return
            
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                # Store the interaction
                conn.execute("""
                    INSERT INTO interactions 
                    (template_hash, prompt, model, response, latency_ms, success, 
                     error, environmental_context, storage_reason, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template_hash,
                    call_data.prompt,
                    call_data.model,
                    call_data.response,
                    call_data.latency_ms,
                    call_data.success,
                    call_data.error,
                    json.dumps(context.to_dict()) if context else None,
                    reason,
                    call_data.timestamp.isoformat()
                ))
                
                conn.commit()
                storage_decisions = cast(Dict[str, int], self._stats['storage_decisions'])
                storage_decisions['stored'] += 1
                logger.debug(f"Stored interaction for template {template_hash[:8]}: {reason}")
                
        except Exception as e:
            logger.error(f"Failed to store interaction: {e}")
    
    def _store_metadata_only(self, template_hash: str, call_data: CallData, reason: str) -> None:
        """Store interaction in cache only, not in persistent database."""
        # Cache the response for potential reuse
        self._interaction_cache[template_hash] = {
            'response': {
                'response': call_data.response,
                'latency_ms': call_data.latency_ms,
                'success': call_data.success
            },
            'cached_at': datetime.now().isoformat(),
            'reason': reason
        }
        
        storage_decisions = cast(Dict[str, int], self._stats['storage_decisions'])
        storage_decisions['cached_only'] += 1
        logger.debug(f"Cached interaction for template {template_hash[:8]}: {reason}")
    
    def _update_template_status(self, template_hash: str, call_data: CallData, stored: bool) -> None:
        """Update template statistics and metadata."""
        template_info = self._template_cache.get(template_hash)
        if not template_info:
            return
        
        # Update statistics
        template_info.call_count += 1
        template_info.last_used = call_data.timestamp
        
        if not call_data.success:
            template_info.failure_count += 1
        
        # Round 5.3: Update confidence based on success/failure
        is_timeout = bool(call_data.error and "timeout" in call_data.error.lower())
        new_confidence = template_info.update_confidence(call_data.success, is_timeout)
        
        logger.debug(f"Template {template_hash[:8]} confidence: {new_confidence:.3f}, "
                    f"stage: {template_info.lifecycle_stage}, streak: {template_info.failure_streak}")
        
        # Update latency statistics
        if call_data.success and call_data.latency_ms > 0:
            if template_info.avg_latency == 0:
                template_info.avg_latency = call_data.latency_ms
            else:
                # Running average
                n = template_info.call_count
                template_info.avg_latency = ((template_info.avg_latency * (n-1)) + call_data.latency_ms) / n
        
        # Update environmental context if we have it
        current_context = self.drift_detector.get_current_context()
        if current_context:
            self.drift_detector.update_template_context(template_info, current_context)
        
        # Persist template updates with Round 5.3 confidence fields
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute("""
                    UPDATE template_status 
                    SET call_count = ?, failure_count = ?, avg_latency = ?, 
                        last_used = ?, last_cached_context = ?, last_context_time = ?,
                        confidence_score = ?, failure_streak = ?, last_failure_timestamp = ?,
                        lifecycle_stage = ?
                    WHERE template_hash = ?
                """, (
                    template_info.call_count,
                    template_info.failure_count, 
                    template_info.avg_latency,
                    template_info.last_used.isoformat(),
                    template_info.last_cached_context,
                    template_info.last_context_time.isoformat() if template_info.last_context_time else None,
                    template_info.confidence_score,
                    template_info.failure_streak,
                    template_info.last_failure_timestamp.isoformat() if template_info.last_failure_timestamp else None,
                    template_info.lifecycle_stage,
                    template_hash  # Missing parameter
                ))
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update template status: {e}")
    
    def get_or_compute(self, prompt: str, model: str, compute_fn: Callable[[], str]) -> Dict[str, Any]:
        """
        Legacy API compatibility method. 
        Get cached response or compute new one using provided function.
        
        Args:
            prompt: The input prompt
            model: Model identifier  
            compute_fn: Function that returns the response string
            
        Returns:
            Dict containing response and metadata
        """
        def wrapped_compute_fn() -> Tuple[str, bool, Optional[str]]:
            try:
                response = compute_fn()
                return response, True, None
            except Exception as e:
                return "", False, str(e)
        
        result = self.handle_interaction(prompt, model, wrapped_compute_fn)
        
        # Transform to legacy format
        result_dict = {
            'response': result['response'],
            'success': result['success'],
            'cached': result['cached'],
            'stored': result.get('storage_decision') not in [
                'routine_interaction', 'no_significant_drift', 'fallback_cache_only', 'storage_bounds_exceeded', 'safe_mode_corruption'
            ],
            'storage_decision': result.get('storage_decision', 'unknown'),
            'latency_ms': result['latency_ms'],
            'duration_ms': result['latency_ms'],  # Legacy compatibility
            'template_hash': result['template_hash']
        }
        
        # Round 5.3: Add confidence information
        template_info = self._template_cache.get(result['template_hash'])
        if template_info:
            result_dict['confidence'] = {
                'score': template_info.confidence_score,
                'stage': template_info.lifecycle_stage,
                'failure_streak': template_info.failure_streak,
                'call_count': template_info.call_count
            }
        
        # Add environmental context if available (but not for database-cached responses for backwards compatibility)
        if self.config.enable_environmental_context and not (result.get('cached', False) and result.get('from_database', False)):
            env_context = self._collect_environmental_context()
            if env_context:
                # Handle both integer and string weekday values for test compatibility
                if isinstance(env_context.weekday, str):
                    weekday_str = env_context.weekday
                else:
                    weekday_str = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][env_context.weekday]
                
                # Format context for test compatibility
                result_dict['environmental_context'] = {
                    'hour': env_context.hour,
                    'weekday': weekday_str,
                    'cpu': env_context.cpu_percent,
                    'mem': env_context.memory_percent,
                    'timestamp': env_context.timestamp
                }
        
        # Add drift detection flag if performance drift was detected
        storage_decision = result.get('storage_decision', '')
        if 'performance_outlier' in storage_decision or 'drift_monitoring' in storage_decision:
            result_dict['drift_detected'] = True
            
        return result_dict
    
    def _collect_environmental_context(self) -> Optional[EnvironmentalContext]:
        """Collect current environmental context (for test compatibility)"""
        return self.drift_detector.get_current_context()
    
    def handle_interaction(self, prompt: str, model: str, 
                          get_response: Callable[[], Tuple[str, bool, Optional[str]]]) -> Dict[str, Any]:
        """
        Main entry point for handling LLM interactions.
        
        Args:
            prompt: The input prompt
            model: Model identifier
            get_response: Function that returns (response, success, error)
            
        Returns:
            Dict containing response and metadata
        """
        start_time = time.time()
        self._stats['total_calls'] = cast(int, self._stats['total_calls']) + 1
        
        # Generate template hash
        template_hash = self._hash_template(prompt, model)
        
        # Check for cached response first
        cached_response = self._get_cached_response(template_hash)
        if cached_response:
            # For cached responses, don't add environmental context 
            # (preserves backwards compatibility)
            return {
                'response': cached_response['response'],
                'cached': True,
                'success': cached_response['success'],
                'latency_ms': 0.1,  # Very fast for cached responses
                'duration_ms': 0.1,  # Legacy compatibility - very fast
                'template_hash': template_hash,
                'from_database': cached_response.get('from_database', False)
            }
        
        # Get template info for storage decision
        template_info = self._get_template_info(template_hash)
        
        # Collect environmental context for Round 5.2
        environmental_context = self.drift_detector.get_current_context()
        
        # Execute the LLM call
        try:
            response, success, error = get_response()
            latency_ms = (time.time() - start_time) * 1000
            
            # Create call data
            call_data = CallData(
                prompt=prompt,
                model=model,
                response=response,
                latency_ms=latency_ms,
                success=success,
                error=error,
                timestamp=datetime.now()
            )
            
            # Make storage decision with fallback handling
            try:
                should_store, reason = self.should_store_interaction(call_data, template_info)
            except Exception as e:
                logger.warning(f"Storage decision failed: {e}")
                if self.config.fallback_mode == "conservative":
                    should_store, reason = True, "fallback_conservative"
                elif self.config.fallback_mode == "cache_only":
                    should_store, reason = False, "fallback_cache_only"
                else:
                    # Re-raise if no fallback mode
                    raise
            
            if should_store:
                self._store_full_interaction(template_hash, call_data, reason, environmental_context)
            
            # Always cache successful responses for future hits (whether stored or not)
            if success:
                self._store_metadata_only(template_hash, call_data, reason)
            
            # Update template statistics
            self._update_template_status(template_hash, call_data, should_store)
            
            return {
                'response': response,
                'cached': False,
                'latency_ms': latency_ms,
                'success': success,
                'storage_decision': reason,
                'template_hash': template_hash,
                'environmental_context': environmental_context.to_dict() if environmental_context else None
            }
            
        except Exception as e:
            logger.error(f"Error in interaction handling: {e}")
            
            # Fallback behavior
            if self.config.fallback_mode == "conservative":
                # Store error for debugging
                error_call_data = CallData(
                    prompt=prompt,
                    model=model,
                    response="",
                    latency_ms=(time.time() - start_time) * 1000,
                    success=False,
                    error=str(e),
                    timestamp=datetime.now()
                )
                self._store_full_interaction(template_hash, error_call_data, "fallback_error", environmental_context)
            
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about MemBridge performance."""
        total_calls = cast(int, self._stats['total_calls'])
        cache_hits = cast(int, self._stats['cache_hits'])
        cache_misses = cast(int, self._stats['cache_misses'])
        
        cache_hit_rate = (cache_hits / max(total_calls, 1)) * 100
        
        # Get database statistics
        db_stats = {}
        try:
            with sqlite3.connect(self.db_path, timeout=2.0) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM template_status")
                db_stats['total_templates'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM interactions")
                db_stats['total_interactions'] = cursor.fetchone()[0]
                
                # Get database file size
                db_stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
                
        except Exception as e:
            logger.warning(f"Failed to get database statistics: {e}")
            db_stats = {'error': str(e)}
        
        return {
            'total_requests': total_calls,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': cache_hits / max(total_calls, 1),
            'cache_performance': {
                'hit_rate_percent': cache_hit_rate,
                'total_calls': total_calls,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses
            },
            'storage_decisions': self._stats['storage_decisions'],
            'database': db_stats,
            'drift_detection': {
                'enabled': self.drift_detector.config.enabled,
                'config': self.drift_detector.config.__dict__
            }
        }
    
    def get_db_size(self) -> Dict[str, Any]:
        """Get database size and statistics."""
        try:
            size_bytes = self.db_path.stat().st_size
            
            # Get interaction and template counts
            with sqlite3.connect(self.db_path, timeout=2.0) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM interactions")
                interactions_stored = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM template_status")
                templates_tracked = cursor.fetchone()[0]
            
            return {
                'db_size_bytes': size_bytes,
                'db_size_mb': size_bytes / (1024 * 1024),
                'interactions_stored': interactions_stored,
                'templates_tracked': templates_tracked
            }
        except Exception as e:
            logger.warning(f"Failed to get database size info: {e}")
            return {
                'db_size_bytes': 0,
                'db_size_mb': 0.0,
                'interactions_stored': 0,
                'templates_tracked': 0,
                'error': str(e)
            }
