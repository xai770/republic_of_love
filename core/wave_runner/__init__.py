"""
Wave Runner V2 - Event-Driven Workflow Engine
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Phase: 1 (Foundation)

Architecture:
- Posting-centric processing (each posting progresses independently)
- Interaction-based execution (query interactions table for pending work)
- Staging tables (safety net for script actors)
- Drift detection (prevent crashes from stale scripts)
"""

from .runner import WaveRunner
from .database import DatabaseHelper
from .audit import AuditLogger
from .script_sync import ScriptSyncManager
from .work_grouper import WorkGrouper
from .model_cache import ModelCache
from .branching import BranchEvaluator

__all__ = [
    'WaveRunner', 
    'DatabaseHelper', 
    'AuditLogger', 
    'ScriptSyncManager',
    'WorkGrouper',
    'ModelCache',
    'BranchEvaluator'
]
__version__ = '2.0.0-alpha'
