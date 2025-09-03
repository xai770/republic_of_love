"""
MemBridge Data Models and Configuration Classes

This module contains all the data classes and configuration objects used by MemBridge.
Extracted from converged_membridge.py for better code organization.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


@dataclass
class MemBridgeConfig:
    """Configuration for MemBridge behavior"""
    # Storage bounds
    max_db_size_mb: int = 100
    max_cache_entries: int = 1000
    
    # Value-weighted storage thresholds
    failure_threshold: float = 0.1  # Store all failures if rate > 10%
    learning_phase_calls: int = 10   # Store first N calls per template
    outlier_threshold: float = 1.5   # Store if > 1.5 std devs from mean (more sensitive)
    periodic_sample_rate: float = 0.05  # Store 5% of routine calls
    
    # Fallback behavior
    fallback_mode: str = "conservative"  # "conservative", "cache_only", or "disabled"
    
    # Performance settings
    enable_performance_monitoring: bool = True
    context_cache_duration: float = 1.0  # Cache environmental context for 1 second
    cache_duration_seconds: int = 3600   # Response cache duration
    
    # Environmental context and drift detection
    enable_environmental_context: bool = True
    environmental_context_cache_duration: int = 60  # Cache environmental context for 60 seconds
    drift_config_path: str = "config/drift.yaml"
    
    # Backwards compatibility with old config names
    max_interactions_per_template: int = 50  # Old name for max_cache_entries


@dataclass 
class CallData:
    """Represents a single LLM call with all metadata"""
    prompt: str
    model: str 
    response: str
    latency_ms: float
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    
    def __post_init__(self) -> None:
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class EnvironmentalContext:
    """Environmental context data for drift detection"""
    hour: int
    weekday: int  # 0=Monday, 6=Sunday
    cpu_percent: float
    memory_percent: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            'hour': self.hour,
            'weekday': self.weekday,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentalContext':
        """Create from dictionary loaded from JSON"""
        return cls(
            hour=data['hour'],
            weekday=data['weekday'],
            cpu_percent=data['cpu_percent'],
            memory_percent=data['memory_percent'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )
    
    @property
    def context_key(self) -> str:
        """Generate a key for context caching"""
        return f"{self.hour}_{self.weekday}_{self.cpu_percent:.1f}_{self.memory_percent:.1f}"


@dataclass
class DriftDetectionConfig:
    """Configuration for drift detection with empirically-based thresholds"""
    enabled: bool = True
    
    # Empirically-derived thresholds based on typical system variance
    cpu_threshold: float = 25.0      # 25% CPU change (validated for typical workloads)
    memory_threshold: float = 15.0   # 15% memory change (memory more stable than CPU) 
    time_threshold: float = 40.0     # 40% time change (roughly 5 hours = significant time shift)
    
    # Performance and caching settings
    context_cache_duration: float = 5.0  # 5 seconds (balances performance vs drift detection)
    max_cache_entries: int = 100     # Prevent unbounded cache growth
    
    # Statistical validation settings
    min_baseline_samples: int = 10   # Minimum samples for meaningful baseline
    drift_confidence_threshold: float = 0.8  # Confidence level for drift detection
    
    # Backwards compatibility with old config format
    default_threshold_percent: float = 25.0  # Updated to match new CPU threshold
    baseline_window_hours: int = 24
    min_samples_for_detection: int = 10
    log_drift_events: bool = True
    store_drift_samples: bool = True
    max_drift_samples: int = 10


@dataclass
class TemplateInfo:
    """Information about a prompt template's usage patterns"""
    template_hash: str
    call_count: int = 0
    failure_count: int = 0
    avg_latency: float = 0.0
    latency_std: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    last_cached_context: Optional[str] = None  # For environmental context caching
    last_context_time: Optional[datetime] = None
    
    # Round 5.3: Adaptive Confidence fields (Max's specifications)
    confidence_score: float = 0.5  # Start at neutral confidence
    failure_streak: int = 0
    last_failure_timestamp: Optional[datetime] = None
    lifecycle_stage: str = "learning"  # learning -> developing -> stable -> trusted
    
    def __post_init__(self) -> None:
        # Handle string timestamps from database
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.last_used, str):
            self.last_used = datetime.fromisoformat(self.last_used)
        if isinstance(self.last_context_time, str):
            self.last_context_time = datetime.fromisoformat(self.last_context_time)
        if isinstance(self.last_failure_timestamp, str):
            self.last_failure_timestamp = datetime.fromisoformat(self.last_failure_timestamp)
    
    def update_confidence(self, success: bool, is_timeout: bool = False) -> float:
        """
        Update confidence using Max's asymmetric learning algorithm.
        
        Args:
            success: Whether the interaction was successful
            is_timeout: Whether this was a timeout failure (more severe)
            
        Returns:
            Updated confidence score
        """
        if success:
            # Exponential decay + success bonus (Max's algorithm)
            self.confidence_score = min(0.95, self.confidence_score * 0.9 + 0.1 + 0.05)
            self.failure_streak = 0
        else:
            # Asymmetric failure impact
            if is_timeout:
                self.confidence_score *= 0.5  # 50% drop for timeouts
            else:
                self.confidence_score *= 0.7  # 30% drop for regular failures
            
            self.failure_streak += 1
            self.last_failure_timestamp = datetime.now()
            
            # 3-strike rule: Force back to learning
            if self.failure_streak >= 3:
                self.confidence_score = 0.1
                self.lifecycle_stage = "learning"
        
        # Update lifecycle stage based on confidence (after minimum learning period)
        if self.call_count >= 10:  # Min 10 calls to graduate from learning
            if self.confidence_score >= 0.9:
                self.lifecycle_stage = "trusted"
            elif self.confidence_score >= 0.7:
                self.lifecycle_stage = "stable"
            elif self.confidence_score >= 0.3:
                self.lifecycle_stage = "developing"
            # else remains "learning"
        
        return self.confidence_score
    
    @property
    def total_calls(self) -> int:
        """Total number of calls (for compatibility with existing code)"""
        return self.call_count
    
    @property 
    def stored_count(self) -> int:
        """Estimated stored interactions based on call count and failures"""
        # This is an approximation - in Round 5.3 we'll track this precisely
        return min(self.call_count, 50)  # Storage bounds from Round 5.1
    
    def should_store_based_on_lifecycle(self) -> tuple[bool, str]:
        """
        Determine if interaction should be stored based on lifecycle stage.
        
        Returns:
            (should_store, reason)
        """
        if self.lifecycle_stage == "learning":
            return True, "learning_stage_store_all"
        elif self.lifecycle_stage == "developing":
            # Store every 5th + all failures + outliers (handled elsewhere)
            return (self.call_count + 1) % 5 == 0, "developing_stage_periodic"
        elif self.lifecycle_stage == "stable":
            # Store every 20th + all failures + outliers (handled elsewhere) 
            return (self.call_count + 1) % 20 == 0, "stable_stage_periodic"
        elif self.lifecycle_stage == "trusted":
            # Store every 50th + failures only (handled elsewhere)
            return (self.call_count + 1) % 50 == 0, "trusted_stage_periodic"
        else:
            # Unknown stage - conservative approach
            return True, "unknown_stage_conservative"
