"""
TY Report Base - Independent Reporting Engine

A modular, empathetic reporting system that can be used across
ty_extract versions and other tools in the ecosystem.

Architecture:
- engine/: Core report rendering logic
- templates/: Section and style configurations  
- empathy/: wrap_prompt(), tone heuristics
- qa/: QA prompt modules and validation
- utils/: Trial tracking, metadata, utilities
"""

from .engine.report_generator import ReportGenerator

__version__ = "1.0.0"
__all__ = ["ReportGenerator"]
