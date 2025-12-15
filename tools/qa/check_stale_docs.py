#!/usr/bin/env python3
"""
Stale Documentation Checker

Finds docs that reference code files older than themselves.
If referenced file is newer than doc, doc is probably stale.

═══════════════════════════════════════════════════════════════════════════════
HOW TO RUN
═══════════════════════════════════════════════════════════════════════════════

    cd /home/xai/Documents/ty_learn
    source venv/bin/activate
    python3 tools/check_stale_docs.py

    # With verbose output (shows clean docs too):
    python3 tools/check_stale_docs.py --verbose

═══════════════════════════════════════════════════════════════════════════════
WHAT IT DOES
═══════════════════════════════════════════════════════════════════════════════

1. Scans all .md files in docs/, docs/architecture/, docs/architecture/decisions/
2. Extracts file references like `core/database.py` or 'scripts/q.sh'
3. Compares modification times:
   - If referenced code file is NEWER than the doc → doc is STALE
   - Doc probably needs updating to reflect code changes

Example output:
    ⚠️  STALE DOCUMENTATION
    📄 docs/architecture/WORKFLOW_EXECUTION.md
       Last updated: 2025-11-26 14:30
       Newer files:
         - core/wave_runner/runner.py (2025-11-28 10:15)

═══════════════════════════════════════════════════════════════════════════════
WHY THIS MATTERS
═══════════════════════════════════════════════════════════════════════════════

Docs lie. Code doesn't. This tool catches docs that claim to describe code
that has since changed. Part of our "schema + code = truth" philosophy.

Exit codes:
    0 = All docs are fresh
    1 = Some docs are stale (check output)

═══════════════════════════════════════════════════════════════════════════════
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

# Directories to scan for docs
DOC_DIRS = [
    'docs/architecture',
    'docs/architecture/decisions', 
    'docs',
]

# File extensions that are "code" (things docs might reference)
CODE_EXTENSIONS = {'.py', '.sql', '.sh', '.json', '.yaml', '.yml'}

# Pattern to find file references in markdown
# Matches: `path/to/file.py`, 'path/to/file.sql', "path/to/file.sh"
FILE_PATTERN = re.compile(r'[`\'"]([\w/._-]+\.(?:py|sql|sh|json|yaml|yml))[`\'"]')


def find_docs(base_path: Path) -> list[Path]:
    """Find all markdown docs in doc directories."""
    docs = []
    for doc_dir in DOC_DIRS:
        dir_path = base_path / doc_dir
        if dir_path.exists():
            docs.extend(dir_path.glob('*.md'))
    return docs


def extract_file_references(doc_path: Path) -> list[str]:
    """Extract all code file references from a doc."""
    try:
        content = doc_path.read_text()
        return FILE_PATTERN.findall(content)
    except Exception:
        return []


def find_actual_file(base_path: Path, reference: str) -> Path | None:
    """Try to find the actual file from a reference."""
    # Try exact path first
    exact = base_path / reference
    if exact.exists():
        return exact
    
    # Try common prefixes
    for prefix in ['', 'core/', 'tools/', 'scripts/', 'migrations/', 'sql/']:
        candidate = base_path / prefix / reference
        if candidate.exists():
            return candidate
    
    # Search for filename anywhere
    filename = Path(reference).name
    for found in base_path.rglob(filename):
        if found.is_file():
            return found
    
    return None


def check_doc_staleness(base_path: Path, doc_path: Path, verbose: bool = False) -> dict:
    """Check if a doc is stale based on referenced files."""
    doc_mtime = doc_path.stat().st_mtime
    doc_time = datetime.fromtimestamp(doc_mtime)
    
    references = extract_file_references(doc_path)
    
    result = {
        'doc': str(doc_path.relative_to(base_path)),
        'doc_modified': doc_time.strftime('%Y-%m-%d %H:%M'),
        'references': len(references),
        'stale_refs': [],
        'missing_refs': [],
        'is_stale': False,
    }
    
    for ref in references:
        actual = find_actual_file(base_path, ref)
        if actual is None:
            result['missing_refs'].append(ref)
            continue
        
        file_mtime = actual.stat().st_mtime
        if file_mtime > doc_mtime:
            file_time = datetime.fromtimestamp(file_mtime)
            result['stale_refs'].append({
                'reference': ref,
                'file': str(actual.relative_to(base_path)),
                'file_modified': file_time.strftime('%Y-%m-%d %H:%M'),
            })
            result['is_stale'] = True
    
    return result


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    # Go up to project root (tools/qa -> tools -> ty_learn)
    base_path = Path(__file__).parent.parent.parent
    
    docs = find_docs(base_path)
    print(f"Checking {len(docs)} documentation files...\n")
    
    stale_docs = []
    clean_docs = []
    
    for doc in sorted(docs):
        result = check_doc_staleness(base_path, doc, verbose)
        if result['is_stale']:
            stale_docs.append(result)
        else:
            clean_docs.append(result)
    
    # Report stale docs
    if stale_docs:
        print("=" * 60)
        print("⚠️  STALE DOCUMENTATION")
        print("=" * 60)
        for doc in stale_docs:
            print(f"\n📄 {doc['doc']}")
            print(f"   Last updated: {doc['doc_modified']}")
            print(f"   Newer files:")
            for ref in doc['stale_refs']:
                print(f"     - {ref['reference']} ({ref['file_modified']})")
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Clean docs:  {len(clean_docs)}")
    print(f"⚠️  Stale docs:  {len(stale_docs)}")
    
    if verbose and clean_docs:
        print(f"\nClean docs:")
        for doc in clean_docs:
            refs = f"({doc['references']} refs)" if doc['references'] > 0 else "(no refs)"
            print(f"  ✅ {doc['doc']} {refs}")
    
    # Exit with error if stale docs found
    sys.exit(1 if stale_docs else 0)


if __name__ == '__main__':
    main()
