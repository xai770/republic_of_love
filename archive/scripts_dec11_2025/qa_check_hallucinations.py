#!/usr/bin/env python3
"""
Hallucination Detection QA Gate
================================

Simple, maintainable approach: patterns defined in code, easy to add/modify.

Usage:
    python3 scripts/qa_check_hallucinations.py
    
    # Check specific postings:
    python3 scripts/qa_check_hallucinations.py --posting-ids 4650,4651,4652
    
    # Get summary only:
    python3 scripts/qa_check_hallucinations.py --summary
    
    # Export to file:
    python3 scripts/qa_check_hallucinations.py > hallucination_report.txt

Add new patterns by editing the PATTERNS list below.
"""

import sys
import os
import re
from typing import List, Dict, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import get_connection, return_connection


# ============================================================================
# PATTERN DEFINITIONS - Easy to maintain!
# ============================================================================

PATTERNS = [
    # (pattern_name, category, check_function, severity, description)
    
    ('template_session', 'PLACEHOLDER', 
     lambda s: '{session_' in s, 
     'high', 'Literal {session_X} template variable'),
    
    ('template_conversation', 'PLACEHOLDER',
     lambda s: '{conversation_' in s,
     'high', 'Literal {conversation_X} template variable'),
    
    ('instruction_leak', 'INSTRUCTION_LEAK',
     lambda s: 'instruction:' in s.lower(),
     'high', 'Instruction: marker in output'),
    
    ('user_marker', 'INSTRUCTION_LEAK',
     lambda s: 'user:' in s.lower() or 'User:' in s,
     'high', 'User: dialogue marker'),
    
    ('assistant_marker', 'INSTRUCTION_LEAK',
     lambda s: 'assistant:' in s.lower(),
     'high', 'Assistant: marker'),
    
    ('craft_keyword', 'CRAFT_HALLUCINATION',
     lambda s: 'Craft' in s and len(s) < 5000,
     'high', 'Craft instruction keyword'),
    
    ('solution_framework', 'SOLUTION_FRAMEWORK',
     lambda s: 'Solution:' in s or '**Constraints:**' in s or 'AI:' in s,
     'high', 'Solution/Constraints structure'),
    
    ('too_short', 'TOO_SHORT',
     lambda s: len(s) < 300,
     'high', 'Suspiciously short summary'),
    
    ('missing_role', 'MISSING_ROLE',
     lambda s: 'role' not in s.lower() and len(s) < 2000,
     'high', 'No "role" keyword found'),
    
    ('bracket_hallucination', 'BRACKET_HALLUCINATION',
     lambda s: ('[solved' in s or '[Craft' in s) and '[Company Name]' not in s and '[Client Name]' not in s,
     'medium', 'Bracket markers like [solved or [Craft'),
    
    ('code_artifacts', 'CODE_ARTIFACT',
     lambda s: len(s) < 10000 and ('C++ code snippet' in s or 'def ' in s or ('C++' in s and len(s) < 3000)),
     'high', 'Code snippets in summary'),
    
    ('question_marks', 'QUESTION_MARKS',
     lambda s: '?' in s and len(s) < 2000,
     'medium', 'Question marks (uncertainty)'),
    
    ('too_long', 'TOO_LONG',
     lambda s: len(s) > 40000,
     'high', 'Excessive length (hallucination loop)'),
    
    ('given_that', 'GIVEN_THAT_PATTERN',
     lambda s: 'given that' in s.lower() and len(s) < 5000,
     'high', 'Starts with "Given that"'),
    
    ('considering', 'CONSIDERING_PATTERN',
     lambda s: 'considering' in s.lower() and len(s) < 3000,
     'high', 'Starts with "Considering"'),
    
    ('dialogue', 'DIALOGUE_HALLUCINATION',
     lambda s: 'ALEJANDRO:' in s or '[SYS]' in s,
     'high', 'Fake dialogue'),
    
    ('repetition_loop', 'REPETITION_LOOP',
     lambda s: 'per rule 3' in s or 'content merged into' in s or '(content removed' in s,
     'high', 'Meta-instruction repetition'),
    
    ('meta_session_output', 'META_COMMENTARY',
     lambda s: bool(re.search(r'session[_][0-9]+[_]output', s)),
     'high', 'References to session_X_output'),
    
    ('meta_markdown', 'META_COMMENTARY',
     lambda s: 'without markdown formatting' in s.lower(),
     'high', 'Narrates about markdown'),
    
    ('meta_extracted', 'META_COMMENTARY',
     lambda s: 'extracted from session' in s.lower(),
     'high', 'Narrates extraction process'),
    
    ('meta_summarized', 'META_COMMENTARY',
     lambda s: 'summarized here without' in s.lower(),
     'high', 'Narrates summarization'),
    
    ('meta_consistency', 'META_COMMENTARY',
     lambda s: 'for consistency' in s and 'merged into' in s,
     'high', 'Narrates merging for consistency'),
    
    ('meta_rules', 'META_COMMENTARY',
     lambda s: 'according to listed rules' in s.lower(),
     'high', 'References to "listed rules"'),
    
    ('meta_details', 'META_COMMENTARY',
     lambda s: 'as per details provided by original' in s.lower(),
     'high', 'References to "original" posting'),
    
    ('meta_based_on', 'META_COMMENTARY',
     lambda s: bool(re.search(r'(based on|according to|derived from) (the )?(session|original|above)', s, re.IGNORECASE)),
     'high', 'Meta-narrative about source'),
]


def check_posting(posting_id: int, summary: str) -> List[Tuple[str, str, str]]:
    """
    Check a single posting against all patterns.
    
    Returns:
        List of (pattern_name, category, severity) for matching patterns
    """
    matches = []
    for pattern_name, category, check_func, severity, description in PATTERNS:
        try:
            if check_func(summary):
                matches.append((pattern_name, category, severity, description))
        except Exception as e:
            print(f"Warning: Pattern {pattern_name} failed on posting {posting_id}: {e}", file=sys.stderr)
    
    return matches


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='QA check for hallucinations in job summaries')
    parser.add_argument('--posting-ids', help='Comma-separated posting IDs to check (default: all)')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    args = parser.parse_args()
    
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        if args.posting_ids:
            posting_ids = [int(x.strip()) for x in args.posting_ids.split(',')]
            cur.execute("""
                SELECT posting_id, extracted_summary
                FROM postings
                WHERE posting_id = ANY(%s) AND extracted_summary IS NOT NULL
            """, (posting_ids,))
        else:
            cur.execute("""
                SELECT posting_id, extracted_summary
                FROM postings
                WHERE extracted_summary IS NOT NULL
            """)
        
        postings = cur.fetchall()
        
        # Check each posting
        results = []
        for posting in postings:
            matches = check_posting(posting['posting_id'], posting['extracted_summary'])
            if matches:
                results.append({
                    'posting_id': posting['posting_id'],
                    'summary': posting['extracted_summary'],
                    'matches': matches
                })
        
        # Output results
        if args.summary:
            # Summary view
            if not results:
                print("✅ No hallucinations detected!")
            else:
                print(f"❌ Found {len(results)} postings with hallucinations:\n")
                
                # Group by category
                from collections import defaultdict
                by_category = defaultdict(list)
                for result in results:
                    for pattern_name, category, severity, desc in result['matches']:
                        by_category[category].append(result['posting_id'])
                
                for category, posting_ids in sorted(by_category.items()):
                    print(f"{category}: {len(set(posting_ids))} postings")
                    print(f"  Posting IDs: {sorted(set(posting_ids))}")
                    print()
        else:
            # Detailed view
            if not results:
                print("✅ No hallucinations detected!")
                sys.exit(0)
            
            print(f"❌ Found {len(results)} postings with hallucinations:\n")
            print("=" * 80)
            
            for result in results:
                print(f"\nPosting ID: {result['posting_id']}")
                print(f"Length: {len(result['summary'])} characters")
                print(f"Preview: {result['summary'][:200]}...")
                print(f"\nMatched patterns:")
                
                for pattern_name, category, severity, description in result['matches']:
                    print(f"  [{severity.upper()}] {category}: {description}")
                
                print("-" * 80)
            
            sys.exit(1)  # Exit with error code if hallucinations found
    
    finally:
        return_connection(conn)


if __name__ == '__main__':
    main()
