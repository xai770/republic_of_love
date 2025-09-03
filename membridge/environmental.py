"""
Environmental Context Collection and Drift Detection

This module handles environmental context collection and drift detection logic.
Extracted from converged_membridge.py for better code organization.
"""

import psutil 
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import yaml
from pathlib import Path

from .models import EnvironmentalContext, DriftDetectionConfig, TemplateInfo

logger = logging.getLogger(__name__)


class EnvironmentalContextCollector:
    """Handles collection of environmental context data"""
    
    def __init__(self, config: DriftDetectionConfig):
        self.config = config
        self._context_cache: Dict[str, Tuple[EnvironmentalContext, datetime]] = {}
    
    def collect_context(self) -> Optional[EnvironmentalContext]:
        """
        Collect current environmental context with non-blocking psutil calls.
        Returns None if collection fails.
        """
        try:
            now = datetime.now()
            
            # Use non-blocking psutil calls to avoid performance overhead
            try:
                # Non-blocking CPU measurement (uses recent cached value)
                cpu_percent = psutil.cpu_percent(interval=None)
                # Fallback if no cached value available
                if cpu_percent == 0.0:
                    cpu_percent = psutil.cpu_percent(interval=0.01)  # Very short sample
                
                memory_percent = psutil.virtual_memory().percent  
                
            except Exception as psutil_error:
                logger.warning(f"psutil collection failed: {psutil_error}")
                # Graceful fallback with dummy values
                cpu_percent = 50.0  # Neutral default
                memory_percent = 50.0  # Neutral default
            
            # Create cache key that includes resource state ranges for better drift detection
            cpu_range = int(cpu_percent // 20)  # 0-4 range (0-20%, 20-40%, etc.)
            memory_range = int(memory_percent // 20)  # 0-4 range
            cache_key = f"{now.hour}_{now.weekday()}_{cpu_range}_{memory_range}"
            
            # Check cache with shorter duration to preserve drift detection
            cache_duration = min(self.config.context_cache_duration, 10.0)  # Max 10 seconds
            if cache_key in self._context_cache:
                cached_context, cache_time = self._context_cache[cache_key]
                if now - cache_time < timedelta(seconds=cache_duration):
                    return cached_context
            
            # Collect fresh context
            context = EnvironmentalContext(
                hour=now.hour,
                weekday=now.weekday(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                timestamp=now
            )
            
            # Cache the result
            self._context_cache[cache_key] = (context, now)
            
            # Clean old cache entries
            self._cleanup_cache(now)
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to collect environmental context: {e}")
            return None
    
    def _cleanup_cache(self, now: datetime) -> None:
        """Remove old cache entries"""
        cutoff = now - timedelta(seconds=self.config.context_cache_duration * 2)
        keys_to_remove = [
            key for key, (_, cache_time) in self._context_cache.items()
            if cache_time < cutoff
        ]
        for key in keys_to_remove:
            del self._context_cache[key]


class DriftDetector:
    """Handles drift detection logic"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/drift.yaml")
        self.config = self._load_config()
        self.context_collector = EnvironmentalContextCollector(self.config)
    
    def _load_config(self) -> DriftDetectionConfig:
        """Load drift detection configuration"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    drift_config = config_data.get('drift_detection', {})
                    
                    # Extract nested alert configuration if present
                    alerts = drift_config.pop('alerts', {})
                    if alerts:
                        # Flatten alerts into main config
                        drift_config.update(alerts)
                    
                    return DriftDetectionConfig(**drift_config)
            else:
                logger.info(f"Drift config not found at {self.config_path}, using defaults")
                return DriftDetectionConfig()
        except Exception as e:
            logger.warning(f"Failed to load drift config: {e}, using defaults")
            return DriftDetectionConfig()
    
    def should_store_for_drift(self, template_info: TemplateInfo) -> Tuple[bool, str]:
        """
        Determine if interaction should be stored due to environmental drift.
        
        Returns:
            Tuple of (should_store, reason)
        """
        if not self.config.enabled:
            return False, "drift_detection_disabled"
        
        current_context = self.context_collector.collect_context()
        if not current_context:
            return False, "context_collection_failed"
        
        # For new templates, collect sufficient baseline samples for statistical validity
        if template_info.call_count < 10:  # Increased from 3 to 10 for better baseline
            return True, "drift_baseline_collection"
        
        # Check if we have previous context to compare against
        if not template_info.last_cached_context:
            return True, "no_previous_context"
        
        try:
            # Parse the last cached context
            last_context_data = eval(template_info.last_cached_context)  # Safe since we control the format
            last_context = EnvironmentalContext.from_dict(last_context_data)
            
            # Calculate drift percentages
            cpu_drift = abs(current_context.cpu_percent - last_context.cpu_percent)
            memory_drift = abs(current_context.memory_percent - last_context.memory_percent)
            
            # Time-based drift calculation with proper day boundary handling
            time_drift = self._calculate_time_drift(current_context.hour, last_context.hour)
            
            # Check if any drift exceeds thresholds
            if cpu_drift > self.config.cpu_threshold:
                return True, f"cpu_drift_{cpu_drift:.1f}%"
            if memory_drift > self.config.memory_threshold:
                return True, f"memory_drift_{memory_drift:.1f}%"
            if time_drift > self.config.time_threshold:
                return True, f"time_drift_{time_drift:.1f}%"
            
            return False, "no_significant_drift"
            
        except Exception as e:
            logger.warning(f"Error calculating drift: {e}")
            # Conservative fallback: avoid storing too aggressively in error cases
            # This prevents bypassing storage bounds, but we can't check exact count here
            # Let the main storage bounds logic handle the final decision
            return False, "drift_calculation_error_conservative"
    
    def _calculate_time_drift(self, current_hour: int, previous_hour: int) -> float:
        """
        Calculate time drift percentage handling day boundaries properly.
        
        Args:
            current_hour: Current hour (0-23)
            previous_hour: Previous hour (0-23)
            
        Returns:
            Drift percentage (0-100)
        """
        # Calculate the minimum distance between hours (handling day wrap)
        forward_diff = (current_hour - previous_hour) % 24
        backward_diff = (previous_hour - current_hour) % 24
        min_diff = min(forward_diff, backward_diff)
        
        # Convert to percentage of half-day (12 hours = 100% drift)
        time_drift = (min_diff / 12.0) * 100
        
        return time_drift
    
    def get_current_context(self) -> Optional[EnvironmentalContext]:
        """Get current environmental context"""
        return self.context_collector.collect_context()
    
    def update_template_context(self, template_info: TemplateInfo, context: EnvironmentalContext) -> None:
        """Update template with current context information"""
        template_info.last_cached_context = str(context.to_dict())
        template_info.last_context_time = context.timestamp
