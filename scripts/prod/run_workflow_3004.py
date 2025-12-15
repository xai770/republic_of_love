#!/usr/bin/env python3
"""
WF3004 Runner - Hierarchy Reorganization (Nuclear Rebuild)

Runs the domain-agnostic taxonomy rebuild:
1. Reset hierarchy (backup + clear)
2. Loop: Fetch 50 orphans → LLM classify → Apply hierarchy
3. Repeat until no orphans remain

Usage:
    python3 scripts/prod/run_workflow_3004.py [--no-reset] [--max-batches N]
    
    --no-reset     Skip the reset step (just process orphans)
    --max-batches  Limit number of batches to process (default: unlimited)
"""

import argparse
import json
import os
import sys
import time
import subprocess
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Config
BATCH_SIZE = 50
LLM_ACTOR_ID = 45  # qwen2.5:7b
INSTRUCTION_ID = 3427  # Classify Skills to Categories

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)

def reset_hierarchy(conn):
    """Step 1: Backup and clear skill_hierarchy."""
    log("STEP 1: Resetting hierarchy...")
    
    result = subprocess.run(
        ['python3', 'core/wave_runner/actors/hierarchy_resetter.py'],
        input='{}',
        capture_output=True,
        text=True
    )
    
    output = json.loads(result.stdout)
    if output.get('status') == 'success':
        log(f"  ✓ Backed up {output.get('rows_backed_up', 0)} rows to {output.get('backup_table', 'N/A')}")
        log(f"  ✓ Cleared hierarchy table")
        return True
    else:
        log(f"  ✗ Reset failed: {output.get('error', 'Unknown error')}")
        return False

def fetch_orphans():
    """Step 2: Fetch batch of orphan skills."""
    result = subprocess.run(
        ['python3', 'core/wave_runner/actors/orphan_skills_fetcher.py'],
        input='{}',
        capture_output=True,
        text=True
    )
    
    output = json.loads(result.stdout)
    return output

def call_llm(skills_batch, conn):
    """Step 3: Call LLM to classify skills via Ollama API."""
    cursor = conn.cursor()
    
    # Get instruction template
    cursor.execute("""
        SELECT prompt_template FROM instructions WHERE instruction_id = %s
    """, (INSTRUCTION_ID,))
    row = cursor.fetchone()
    if not row:
        return {"error": "Instruction not found"}
    
    prompt = row[0].replace('{skills_batch}', skills_batch)
    
    # Call Ollama API directly
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        return {"response": result.get('response', '')}
    except Exception as e:
        return {"error": f"LLM call failed: {str(e)}"}

def apply_hierarchy(llm_response, skill_ids, skill_names):
    """Step 4: Apply hierarchy from LLM response."""
    input_data = {
        "response": llm_response,
        "skill_ids": skill_ids,
        "skill_names": skill_names
    }
    
    result = subprocess.run(
        ['python3', 'core/wave_runner/actors/hierarchy_applier.py'],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )
    
    output = json.loads(result.stdout)
    return output

def save_progress(batch_num, stats, filename='logs/wf3004_progress.json'):
    """Save progress to file for monitoring."""
    progress = {
        'batch_num': batch_num,
        'last_update': datetime.now().isoformat(),
        'stats': stats
    }
    with open(filename, 'w') as f:
        json.dump(progress, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Run WF3004 Hierarchy Reorganization')
    parser.add_argument('--no-reset', action='store_true', help='Skip reset step')
    parser.add_argument('--max-batches', type=int, default=0, help='Max batches (0=unlimited)')
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    log("=" * 60)
    log("WF3004 - HIERARCHY REORGANIZATION")
    log("=" * 60)
    
    stats = {
        'started_at': datetime.now().isoformat(),
        'reset_done': False,
        'batches_processed': 0,
        'skills_assigned': 0,
        'categories_created': set(),
        'errors': []
    }
    
    # Step 1: Reset (unless --no-reset)
    if not args.no_reset:
        if not reset_hierarchy(conn):
            log("ABORT: Reset failed")
            return 1
        stats['reset_done'] = True
    else:
        log("Skipping reset (--no-reset)")
    
    # Main loop: Process batches
    batch_num = 0
    while True:
        batch_num += 1
        
        if args.max_batches > 0 and batch_num > args.max_batches:
            log(f"Reached max batches ({args.max_batches})")
            break
        
        log(f"\n--- BATCH {batch_num} ---")
        
        # Fetch orphans
        fetch_result = fetch_orphans()
        if fetch_result.get('status') != 'success':
            log(f"  ✗ Fetch failed: {fetch_result.get('error')}")
            stats['errors'].append(f"Batch {batch_num}: fetch failed")
            break
        
        remaining = fetch_result.get('remaining', 0)
        skills_batch = fetch_result.get('skills_batch', '')
        skill_ids = fetch_result.get('skill_ids', [])
        skill_names = fetch_result.get('skill_names', [])
        
        if not skills_batch:
            log("  ✓ No more orphans - DONE!")
            break
        
        log(f"  Fetched {fetch_result.get('batch_size', 0)} skills, {remaining} remaining")
        
        # Call LLM
        log("  Calling LLM...")
        llm_start = time.time()
        llm_result = call_llm(skills_batch, conn)
        llm_time = time.time() - llm_start
        
        if llm_result.get('error'):
            log(f"  ✗ LLM failed: {llm_result['error']}")
            stats['errors'].append(f"Batch {batch_num}: LLM failed")
            continue
        
        log(f"  LLM responded in {llm_time:.1f}s")
        
        # Apply hierarchy
        apply_result = apply_hierarchy(llm_result['response'], skill_ids, skill_names)
        
        if not apply_result.get('success'):
            log(f"  ✗ Apply failed: {apply_result.get('error')}")
            stats['errors'].append(f"Batch {batch_num}: apply failed")
            continue
        
        inserted = apply_result.get('inserted', 0)
        domain = apply_result.get('domain_detected', 'Unknown')
        categories = apply_result.get('category_names', [])
        
        log(f"  ✓ Domain: {domain}")
        log(f"  ✓ Inserted {inserted} assignments")
        log(f"  ✓ Categories: {', '.join(categories[:3])}...")
        
        stats['batches_processed'] += 1
        stats['skills_assigned'] += inserted
        stats['categories_created'].update(categories)
        
        # Save progress
        progress_stats = {**stats, 'categories_created': list(stats['categories_created'])}
        save_progress(batch_num, progress_stats)
        
        # Brief pause to avoid hammering
        time.sleep(0.5)
    
    # Final summary
    log("\n" + "=" * 60)
    log("COMPLETE")
    log("=" * 60)
    log(f"Batches processed: {stats['batches_processed']}")
    log(f"Skills assigned: {stats['skills_assigned']}")
    log(f"Categories used: {len(stats['categories_created'])}")
    log(f"Errors: {len(stats['errors'])}")
    
    # Final progress save
    stats['completed_at'] = datetime.now().isoformat()
    progress_stats = {**stats, 'categories_created': list(stats['categories_created'])}
    save_progress(batch_num, progress_stats)
    
    conn.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
