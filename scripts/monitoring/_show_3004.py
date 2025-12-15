#!/usr/bin/env python3
"""
WF3004 Monitor - Hierarchy Reorganization Dashboard

Shows real-time progress of the taxonomy rebuild.

Usage:
    python3 tools/_show_3004.py [--once]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

PROGRESS_FILE = 'logs/wf3004_progress.json'

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def load_progress():
    """Load progress from JSON file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except:
            pass
    return None

def get_hierarchy_stats(conn):
    """Get current hierarchy statistics."""
    cursor = conn.cursor()
    
    # Total skills and orphans
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM skill_aliases) as total_skills,
            (SELECT COUNT(DISTINCT skill_id) FROM skill_hierarchy) as in_hierarchy,
            (SELECT COUNT(*) FROM skill_aliases WHERE skill_id NOT IN (SELECT skill_id FROM skill_hierarchy)) as orphans
    """)
    total, in_hier, orphans = cursor.fetchone()
    
    # Top categories by child count
    cursor.execute("""
        WITH cat_counts AS (
            SELECT parent_skill_id, COUNT(*) as cnt
            FROM skill_hierarchy
            GROUP BY parent_skill_id
        )
        SELECT p.display_name, c.cnt
        FROM cat_counts c
        JOIN skill_aliases p ON c.parent_skill_id = p.skill_id
        ORDER BY c.cnt DESC
        LIMIT 10
    """)
    top_categories = cursor.fetchall()
    
    # Recent hierarchy entries
    cursor.execute("""
        SELECT c.display_name as skill, p.display_name as parent
        FROM skill_hierarchy sh
        JOIN skill_aliases c ON sh.skill_id = c.skill_id
        JOIN skill_aliases p ON sh.parent_skill_id = p.skill_id
        ORDER BY sh.created_at DESC
        LIMIT 5
    """)
    recent = cursor.fetchall()
    
    return {
        'total_skills': total,
        'in_hierarchy': in_hier,
        'orphans': orphans,
        'top_categories': top_categories,
        'recent': recent
    }

def display_dashboard(conn, progress):
    """Display the monitoring dashboard."""
    clear_screen()
    
    stats = get_hierarchy_stats(conn)
    
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║           WF3004 - HIERARCHY REORGANIZATION MONITOR              ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
    
    # Progress section
    if progress:
        batch = progress.get('batch_num', 0)
        last_update = progress.get('last_update', 'N/A')
        p_stats = progress.get('stats', {})
        
        print(f"┌─ PROGRESS ──────────────────────────────────────────────────────┐")
        print(f"│ Batch: {batch:4d}          Last Update: {last_update[11:19] if len(last_update) > 11 else 'N/A'}                    │")
        print(f"│ Skills Assigned: {p_stats.get('skills_assigned', 0):5d}   Errors: {len(p_stats.get('errors', [])):3d}                          │")
        print(f"│ Categories Used: {len(p_stats.get('categories_created', [])):5d}                                         │")
        
        if p_stats.get('completed_at'):
            print(f"│ ✓ COMPLETED at {p_stats['completed_at'][11:19]}                                    │")
        
        print(f"└─────────────────────────────────────────────────────────────────┘")
    else:
        print("┌─ PROGRESS ──────────────────────────────────────────────────────┐")
        print("│ No progress file found. Waiting for workflow to start...       │")
        print("└─────────────────────────────────────────────────────────────────┘")
    
    print()
    
    # Hierarchy stats
    pct = (stats['in_hierarchy'] / stats['total_skills'] * 100) if stats['total_skills'] > 0 else 0
    bar_len = 40
    filled = int(bar_len * pct / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    
    print(f"┌─ HIERARCHY STATS ───────────────────────────────────────────────┐")
    print(f"│ Total Skills: {stats['total_skills']:5d}   In Hierarchy: {stats['in_hierarchy']:5d}   Orphans: {stats['orphans']:5d} │")
    print(f"│ Coverage: [{bar}] {pct:5.1f}%   │")
    print(f"└─────────────────────────────────────────────────────────────────┘")
    
    print()
    
    # Top categories
    print(f"┌─ TOP CATEGORIES ────────────────────────────────────────────────┐")
    for cat, cnt in stats['top_categories'][:8]:
        cat_display = (cat[:35] + '..') if len(cat) > 37 else cat
        print(f"│ {cat_display:37s} {cnt:4d} skills                   │")
    print(f"└─────────────────────────────────────────────────────────────────┘")
    
    print()
    
    # Recent assignments
    print(f"┌─ RECENT ASSIGNMENTS ────────────────────────────────────────────┐")
    for skill, parent in stats['recent']:
        skill_display = (skill[:25] + '..') if len(skill) > 27 else skill
        parent_display = (parent[:25] + '..') if len(parent) > 27 else parent
        print(f"│ {skill_display:27s} → {parent_display:27s}   │")
    print(f"└─────────────────────────────────────────────────────────────────┘")
    
    print()
    print(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}  |  Press Ctrl+C to exit")

def main():
    parser = argparse.ArgumentParser(description='Monitor WF3004 progress')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    try:
        while True:
            progress = load_progress()
            display_dashboard(conn, progress)
            
            if args.once:
                break
            
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
