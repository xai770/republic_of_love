#!/usr/bin/env python3
"""
Deprecated Column Linter - Find usage of deprecated columns in codebase.

Usage:
    python scripts/lint_deprecated_columns.py           # Scan all Python files
    python scripts/lint_deprecated_columns.py --strict  # Exit 1 if found (for CI)

This ensures deprecated columns don't sneak back into new code.
"""

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.posting_columns import DEPRECATED_COLUMNS

# Directories to scan
SCAN_DIRS = ['actors', 'api', 'core', 'scripts', 'lib']

# Files to skip
SKIP_FILES = [
    'posting_columns.py',  # The registry itself
    'schema_audit.py',     # Auditing tool
    'lint_deprecated_columns.py',  # This file
]


def scan_file(filepath: Path) -> list:
    """Scan a file for deprecated column usage."""
    findings = []
    
    try:
        content = filepath.read_text()
        lines = content.split('\n')
        
        for col in DEPRECATED_COLUMNS:
            # Match column name in strings or as identifier
            # Patterns: 'column_name', "column_name", .column_name, [column_name]
            patterns = [
                rf"['\"]({col})['\"]",      # String literal
                rf"\.({col})\b",             # Attribute access
                rf"\[({col})\]",             # Dict access
                rf"\b({col})\s*=",           # Assignment
            ]
            
            for i, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue
                    
                for pattern in patterns:
                    if re.search(pattern, line):
                        findings.append({
                            'file': str(filepath.relative_to(PROJECT_ROOT)),
                            'line': i,
                            'column': col,
                            'code': line.strip()[:80],
                        })
                        break  # One finding per line per column
    except Exception as e:
        print(f"⚠️  Error scanning {filepath}: {e}")
    
    return findings


def main():
    parser = argparse.ArgumentParser(description='Find deprecated column usage')
    parser.add_argument('--strict', action='store_true', help='Exit 1 if deprecated columns found')
    args = parser.parse_args()
    
    print(f"🔍 Scanning for deprecated columns...")
    print(f"   Deprecated: {len(DEPRECATED_COLUMNS)} columns")
    print()
    
    all_findings = []
    
    for scan_dir in SCAN_DIRS:
        dir_path = PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue
            
        for filepath in dir_path.rglob('*.py'):
            if filepath.name in SKIP_FILES:
                continue
            if '__pycache__' in str(filepath):
                continue
                
            findings = scan_file(filepath)
            all_findings.extend(findings)
    
    if not all_findings:
        print("✅ No deprecated column usage found!")
        return 0
    
    # Group by file
    by_file = {}
    for f in all_findings:
        by_file.setdefault(f['file'], []).append(f)
    
    print(f"⚠️  Found {len(all_findings)} deprecated column references:\n")
    
    for filepath, findings in sorted(by_file.items()):
        print(f"📄 {filepath}")
        for f in findings:
            print(f"   L{f['line']:>4}: {f['column']:<30} | {f['code']}")
        print()
    
    print(f"💡 These columns are scheduled for removal. Update code to stop using them.")
    print(f"   See: core/posting_columns.py for removal dates")
    
    if args.strict:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
