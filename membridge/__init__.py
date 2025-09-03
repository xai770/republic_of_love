"""
MemBridge: Value-weighted LLM interaction storage system

A modular memory system that learns when to remember and when to forget,
implementing intelligent caching and storage decisions based on interaction value.

PSM Round 5.2: Environmental Context & Drift Detection
Date: 2025-09-02
Owner: Arden
"""

__version__ = "5.2.0"
__author__ = "Arden"

from .models import MemBridgeConfig, CallData, EnvironmentalContext, TemplateInfo
from .environmental import DriftDetector, EnvironmentalContextCollector
from .converged_membridge import ConvergedMemBridge

__all__ = [
    "ConvergedMemBridge",
    "MemBridgeConfig", 
    "CallData",
    "EnvironmentalContext",
    "TemplateInfo",
    "DriftDetector",
    "EnvironmentalContextCollector"
]
