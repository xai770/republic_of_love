#!/usr/bin/env python3
"""
Path Configuration for Turing System
=====================================

Centralized path management with environment variable override support.
Set TURING_BASE_DIR environment variable to override default location.

Example:
    export TURING_BASE_DIR=/mnt/ai-workstation/turing
    python3 -m core.wave_batch_processor --workflow 3001

Default:
    /home/xai/Documents/ty_learn (laptop development)
"""

import os
from pathlib import Path

# Base directory - can be overridden via environment variable
# This allows the system to run on any machine without code changes
BASE_DIR = Path(os.getenv('TURING_BASE_DIR', '/home/xai/Documents/ty_learn'))

# Core directories
CONFIG_DIR = BASE_DIR / 'config'
CORE_DIR = BASE_DIR / 'core'
DATA_DIR = BASE_DIR / 'data'
DOCS_DIR = BASE_DIR / 'docs'
LOGS_DIR = BASE_DIR / 'logs'
MIGRATIONS_DIR = BASE_DIR / 'sql' / 'migrations'
OUTPUT_DIR = BASE_DIR / 'output'
REPORTS_DIR = BASE_DIR / 'reports'
SCRIPTS_DIR = BASE_DIR / 'scripts'
SQL_DIR = BASE_DIR / 'sql'
TEMP_DIR = BASE_DIR / 'temp'
TESTS_DIR = BASE_DIR / 'tests'
TOOLS_DIR = BASE_DIR / 'tools'

# Data subdirectories
BACKUPS_DIR = BASE_DIR / 'backups'
POSTINGS_DIR = DATA_DIR / 'postings'

# Output directories
SKILLS_TAXONOMY_DIR = BASE_DIR / 'skills_taxonomy'

# Ensure critical directories exist
def ensure_directories():
    """Create directories if they don't exist"""
    for directory in [LOGS_DIR, OUTPUT_DIR, TEMP_DIR, SKILLS_TAXONOMY_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# String versions for backwards compatibility
# (some scripts may need string paths instead of Path objects)
BASE_DIR_STR = str(BASE_DIR)
SKILLS_TAXONOMY_DIR_STR = str(SKILLS_TAXONOMY_DIR)
TOOLS_DIR_STR = str(TOOLS_DIR)
SCRIPTS_DIR_STR = str(SCRIPTS_DIR)
