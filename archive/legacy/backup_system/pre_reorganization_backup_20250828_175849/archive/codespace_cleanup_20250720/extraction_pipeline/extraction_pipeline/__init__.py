"""
Extraction Pipeline - Clean Job Requirements Extraction
======================================================

A clean, organized codebase for job requirements extraction following
Enhanced Data Dictionary v4.2 standards.

Based on: Daily Report Pipeline V7.0
Architecture: Inspired by ty_extract clean design principles
"""

__version__ = "7.0.0"
__author__ = "Arden & Team"

from .pipeline import ExtractionPipeline

__all__ = ["ExtractionPipeline"]
