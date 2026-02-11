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
from datetime import datetime, timedelta

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
        except (OSError, json.JSONDecodeError):
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
    W = 68  # Box width
    
    print("╔" + "═" * W + "╗")
    print("║" + "WF3004 - HIERARCHY REORGANIZATION MONITOR".center(W) + "║")
    print("╚" + "═" * W + "╝")
    print()
    
    # Progress section
    print("┌─ PROGRESS " + "─" * (W - 11) + "┐")
    if progress:
        batch = progress.get('batch_num', 0)
        last_update = progress.get('last_update', 'N/A')
        p_stats = progress.get('stats', {})
        skills_done = p_stats.get('skills_assigned', 0)
        errors = len(p_stats.get('errors', []))
        categories = len(p_stats.get('categories_created', []))
        
        # Calculate ETA
        orphans = stats['orphans']
        started_at = p_stats.get('started_at', '')
        eta_str = ""
        eta_time_str = ""
        if started_at and batch > 0 and orphans > 0:
            try:
                start = datetime.fromisoformat(started_at)
                elapsed = (datetime.now() - start).total_seconds()
                rate = skills_done / elapsed if elapsed > 0 else 0  # skills per second
                if rate > 0:
                    remaining_secs = orphans / rate
                    eta_mins = int(remaining_secs / 60)
                    eta_finish = datetime.now() + timedelta(seconds=remaining_secs)
                    eta_str = f"ETA: {eta_mins} min"
                    eta_time_str = f"@ {eta_finish.strftime('%H:%M')}"
            except (ValueError, TypeError, ZeroDivisionError):
                pass
        
        line1 = f"Batch: {batch:4d}        Last Update: {last_update[11:19] if len(last_update) > 11 else 'N/A'}"
        print("│ " + line1.ljust(W - 2) + " │")
        
        line2 = f"Skills Assigned: {skills_done:5d}    Errors: {errors:3d}"
        print("│ " + line2.ljust(W - 2) + " │")
        
        line3 = f"Categories Used: {categories:5d}"
        print("│ " + line3.ljust(W - 2) + " │")
        
        if eta_str:
            line4 = f"{eta_str}  {eta_time_str}"
            print("│ " + line4.ljust(W - 2) + " │")
        
        if p_stats.get('completed_at'):
            line5 = f"✓ COMPLETED at {p_stats['completed_at'][11:19]}"
            print("│ " + line5.ljust(W - 2) + " │")
    else:
        print("│ " + "No progress file found. Waiting for workflow to start...".ljust(W - 2) + " │")
    print("└" + "─" * W + "┘")
    print()
    
    # Hierarchy stats
    pct = (stats['in_hierarchy'] / stats['total_skills'] * 100) if stats['total_skills'] > 0 else 0
    bar_len = 40
    filled = int(bar_len * pct / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    
    print("┌─ HIERARCHY STATS " + "─" * (W - 18) + "┐")
    line1 = f"Total Skills: {stats['total_skills']:5d}    In Hierarchy: {stats['in_hierarchy']:5d}    Orphans: {stats['orphans']:5d}"
    print("│ " + line1.ljust(W - 2) + " │")
    line2 = f"Coverage: [{bar}] {pct:5.1f}%"
    print("│ " + line2.ljust(W - 2) + " │")
    print("└" + "─" * W + "┘")
    print()
    
    # Top categories
    print("┌─ TOP CATEGORIES " + "─" * (W - 17) + "┐")
    for cat, cnt in stats['top_categories'][:8]:
        cat_display = (cat[:45] + '..') if len(cat) > 47 else cat
        line = f"{cat_display:47s} {cnt:4d} skills"
        print("│ " + line.ljust(W - 2) + " │")
    print("└" + "─" * W + "┘")
    print()
    
    # Recent assignments
    print("┌─ RECENT ASSIGNMENTS " + "─" * (W - 21) + "┐")
    for skill, parent in stats['recent']:
        skill_display = (skill[:28] + '..') if len(skill) > 30 else skill
        parent_display = (parent[:28] + '..') if len(parent) > 30 else parent
        line = f"{skill_display:30s} → {parent_display:30s}"
        print("│ " + line.ljust(W - 2) + " │")
    print("└" + "─" * W + "┘")
    
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
