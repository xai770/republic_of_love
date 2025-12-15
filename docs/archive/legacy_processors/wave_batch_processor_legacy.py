#!/usr/bin/env python3
"""
Wave Batch Processor - DEPRECATED - Use core.wave_processor instead
====================================================================

This file maintained for backward compatibility only.

MIGRATE TO: core.wave_processor.cli

Usage:
    # OLD (still works):
    python3 -m core.wave_batch_processor --workflow 3001
    
    # NEW (preferred):
    python3 -m core.wave_processor.cli --workflow 3001

The new modular architecture provides:
- Better maintainability (5 focused modules vs 1 monolith)
- Easier testing (each module can be tested independently)
- Clearer separation of concerns
- Same functionality, cleaner code
"""

import sys
import warnings
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Show deprecation warning
warnings.warn(
    "core.wave_batch_processor is deprecated. "
    "Use 'python3 -m core.wave_processor.cli' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from new modular implementation
from core.wave_processor.cli import main

if __name__ == '__main__':
    print("⚠️  NOTE: Using deprecated entry point")
    print("   Migrate to: python3 -m core.wave_processor.cli")
    print()
    main()
