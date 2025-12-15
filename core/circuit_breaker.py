#!/usr/bin/env python3
"""
Circuit Breaker Pattern for Actor Resilience
============================================

Prevents repeated calls to failing actors, protecting system resources
and preventing cascading failures.

Pattern:
- Track failure rate per actor
- After threshold failures → OPEN circuit (pause calls)
- After cooldown period → HALF_OPEN (test recovery)
- On success → CLOSED (normal operation)
- On continued failure → back to OPEN

Usage:
    breaker = CircuitBreaker()
    
    if breaker.can_call(actor_id):
        result = call_actor(actor_id, ...)
        if success:
            breaker.record_success(actor_id)
        else:
            breaker.record_failure(actor_id)
    else:
        # Circuit is open, skip this call
        pass
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from core.db_context import db_transaction
from core.logging_config import get_logger


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"          # Normal operation
    OPEN = "OPEN"              # Failing, blocking calls
    HALF_OPEN = "HALF_OPEN"    # Testing recovery


@dataclass
class CircuitStatus:
    """Status of a single circuit"""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    opened_at: Optional[float]
    open_count: int  # Number of times circuit has opened


class CircuitBreaker:
    """
    Circuit breaker for protecting against failing actors.
    
    Configuration:
    - failure_threshold: Failures before opening circuit (default: 5)
    - cooldown_seconds: Time to wait before testing recovery (default: 300 = 5 min)
    - max_open_count: Opens before disabling actor (default: 3)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: int = 300,
        max_open_count: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.max_open_count = max_open_count
        
        # Track status per actor
        self._circuits: Dict[int, CircuitStatus] = {}
        
        # Structured logging
        self.logger = get_logger(__name__)
    
    def _get_circuit(self, actor_id: int) -> CircuitStatus:
        """Get or create circuit status for actor"""
        if actor_id not in self._circuits:
            self._circuits[actor_id] = CircuitStatus(
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure_time=None,
                opened_at=None,
                open_count=0
            )
        return self._circuits[actor_id]
    
    def can_call(self, actor_id: int) -> bool:
        """
        Check if actor can be called.
        
        Returns:
            True if call is allowed, False if circuit is open
        """
        circuit = self._get_circuit(actor_id)
        
        # Check if permanently disabled (too many failures)
        if circuit.open_count >= self.max_open_count:
            return False
        
        if circuit.state == CircuitState.CLOSED:
            return True
        
        if circuit.state == CircuitState.OPEN:
            # Check if cooldown period has elapsed
            if circuit.opened_at is None:
                # Shouldn't happen, but reset if corrupt
                circuit.state = CircuitState.CLOSED
                return True
            
            elapsed = time.time() - circuit.opened_at
            if elapsed >= self.cooldown_seconds:
                # Try recovery - move to half-open
                circuit.state = CircuitState.HALF_OPEN
                return True
            else:
                return False
        
        if circuit.state == CircuitState.HALF_OPEN:
            # Allow one test call
            return True
        
        return False
    
    def record_success(self, actor_id: int):
        """Record successful actor call"""
        circuit = self._get_circuit(actor_id)
        circuit.success_count += 1
        
        # Log success event
        self._log_event(actor_id, 'success', circuit.failure_count)
        
        if circuit.state == CircuitState.HALF_OPEN:
            # Recovery successful - close circuit
            circuit.state = CircuitState.CLOSED
            circuit.failure_count = 0
            circuit.last_failure_time = None
            circuit.opened_at = None
            
            # Log circuit closed
            self._log_event(actor_id, 'closed', 0)
            self.logger.info("circuit_breaker_closed", extra={'actor_id': actor_id})
    
    def record_failure(self, actor_id: int):
        """Record failed actor call"""
        circuit = self._get_circuit(actor_id)
        circuit.failure_count += 1
        circuit.last_failure_time = time.time()
        
        # Log failure event
        self._log_event(actor_id, 'failure', circuit.failure_count)
        
        if circuit.state == CircuitState.HALF_OPEN:
            # Recovery failed - reopen circuit
            circuit.state = CircuitState.OPEN
            circuit.opened_at = time.time()
            circuit.open_count += 1
            
            # Log circuit opened
            self._log_event(actor_id, 'open', circuit.failure_count, self.cooldown_seconds)
            self.logger.warning("circuit_breaker_opened", extra={
                'actor_id': actor_id,
                'failure_count': circuit.failure_count,
                'cooldown_seconds': self.cooldown_seconds
            })
        
        elif circuit.state == CircuitState.CLOSED:
            # Check if threshold reached
            if circuit.failure_count >= self.failure_threshold:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.time()
                circuit.open_count += 1
                
                # Log circuit opened
                self._log_event(actor_id, 'open', circuit.failure_count, self.cooldown_seconds)
                self.logger.warning("circuit_breaker_opened", extra={
                    'actor_id': actor_id,
                    'failure_count': circuit.failure_count,
                    'cooldown_seconds': self.cooldown_seconds
                })
    
    def get_status(self, actor_id: int) -> dict:
        """Get current circuit status for reporting"""
        circuit = self._get_circuit(actor_id)
        
        status = {
            'state': circuit.state.value,
            'failure_count': circuit.failure_count,
            'success_count': circuit.success_count,
            'open_count': circuit.open_count,
            'permanently_disabled': circuit.open_count >= self.max_open_count
        }
        
        if circuit.state == CircuitState.OPEN and circuit.opened_at:
            elapsed = time.time() - circuit.opened_at
            remaining = max(0, self.cooldown_seconds - elapsed)
            status['cooldown_remaining_sec'] = int(remaining)
        
        return status
    
    def _log_event(self, actor_id: int, event_type: str, failure_count: int, 
                   cooldown_seconds: Optional[int] = None):
        """Log circuit breaker event to database"""
        try:
            with db_transaction() as cursor:
                cursor.execute("""
                    INSERT INTO circuit_breaker_events 
                    (actor_id, event_type, failure_count, cooldown_seconds)
                    VALUES (%s, %s, %s, %s)
                """, (actor_id, event_type, failure_count, cooldown_seconds))
        except Exception as e:
            self.logger.warning("failed_to_log_circuit_breaker_event", extra={'error': str(e)})
    
    def reset(self, actor_id: int):
        """Manually reset circuit (admin operation)"""
        if actor_id in self._circuits:
            del self._circuits[actor_id]
    
    def get_all_status(self) -> Dict[int, dict]:
        """Get status of all circuits"""
        return {
            actor_id: self.get_status(actor_id)
            for actor_id in self._circuits.keys()
        }
