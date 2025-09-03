"""
LLM Optimization Framework
=========================

A comprehensive framework for evaluating, comparing, and optimizing Large Language Models (LLMs).

Main Components:
- DialogueParser: Parse and structure LLM response data
- QualityAssessor: Multi-dimensional quality scoring
- PerformanceMetrics: Comprehensive performance evaluation
- BaselineComparator: Compare models against baseline performance
- MarkdownReporter: Generate professional reports
- OptimizationConfig: Flexible configuration management

Quick Start:
    from llm_optimization_framework import quick_optimization
    from llm_optimization_framework.configs.settings import PresetConfigs
    
    results = quick_optimization("path/to/dialogue/logs", "baseline_model")
"""

from typing import Optional

__version__ = "1.0.0"
__author__ = "LLM Optimization Team"
__description__ = "Comprehensive framework for LLM evaluation and optimization"

# Core framework components
try:
    from .core.metrics import PerformanceMetrics, MetricsBenchmarker, ModelMetrics
    from .core.comparator import BaselineComparator, BatchBaselineComparator
    # Note: Main framework class has import issues, will be fixed in next update
    # from .core import LLMOptimizationFramework
except ImportError as e:
    print(f"Warning: Some core modules have import issues: {e}")

# Utility components
try:
    from .utils.dialogue_parser import DialogueParser, DialogueEntry
    from .utils.quality_assessor import QualityAssessor, AdvancedQualityAssessor
except ImportError as e:
    print(f"Warning: Some utility modules have import issues: {e}")

# Reporting components
try:
    from .reporters.markdown import MarkdownReporter, QuickReporter
except ImportError as e:
    print(f"Warning: Reporting modules have import issues: {e}")

# Configuration components
try:
    from .configs.settings import (
        OptimizationConfig, ConfigurationManager, PresetConfigs, 
        TemplateConfigs, TestConfiguration
    )
except ImportError as e:
    print(f"Warning: Configuration modules have import issues: {e}")

# Quick access functions
def quick_optimization(data_source: str, baseline_model: Optional[str] = None, output_dir: str = "results"):
    """
    Run quick optimization with default settings
    
    Args:
        data_source: Path to dialogue data
        baseline_model: Optional baseline model name
        output_dir: Output directory for results
        
    Returns:
        Optimization results dictionary
    """
    try:
        from .configs.settings import TemplateConfigs
        config = TemplateConfigs.general_purpose()
        config.baseline_model = baseline_model
        config.output_directory = output_dir
        
        # Note: Main framework class needs fixes, this is a placeholder
        print(f"🚀 Quick optimization: {data_source} -> {output_dir}")
        print(f"   Baseline: {baseline_model or 'None'}")
        return {"status": "Framework ready, some components need fixes"}
    except Exception as e:
        print(f"❌ Quick optimization failed: {e}")
        return {"status": "error", "message": str(e)}

# Available exports
__all__ = [
    # Core classes
    'PerformanceMetrics',
    'MetricsBenchmarker', 
    'ModelMetrics',
    'BaselineComparator',
    'BatchBaselineComparator',
    
    # Utility classes
    'DialogueParser',
    'DialogueEntry', 
    'QualityAssessor',
    'AdvancedQualityAssessor',
    
    # Reporting classes
    'MarkdownReporter',
    'QuickReporter',
    
    # Configuration classes
    'OptimizationConfig',
    'ConfigurationManager',
    'PresetConfigs',
    'TemplateConfigs',
    'TestConfiguration',
    
    # Quick functions
    'quick_optimization',
    
    # Metadata
    '__version__',
    '__author__',
    '__description__'
]
