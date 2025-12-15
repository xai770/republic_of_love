#!/usr/bin/env python3
"""
Show MemBridge mb_log Table in Terminal
======================================

Display the mb_log table contents in a readable format in the terminal.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

def show_mb_log_table() -> None:
    """Display mb_log table contents in terminal"""
    
    db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    print("📊 MemBridge mb_log Table Contents")
    print("=" * 80)
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get all mb_log entries
        cursor = conn.execute('''
            SELECT log_id, call_number, input_text, output_text, model, 
                   success, latency_ms, timestamp, error_message
            FROM mb_log 
            ORDER BY log_id
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            print("❌ No entries found in mb_log table")
            return
        
        print(f"Found {len(rows)} call log entries:")
        print()
        
        for row in rows:
            print(f"🔍 Call Log ID: {row['log_id']}")
            print(f"   Call Number: #{row['call_number']}")
            print(f"   Model: {row['model']}")
            print(f"   Success: {'✅ YES' if row['success'] else '❌ NO'}")
            print(f"   Latency: {row['latency_ms']:.1f}ms")
            print(f"   Timestamp: {row['timestamp']}")
            
            if row['error_message']:
                print(f"   Error: {row['error_message']}")
            
            # Show input (truncated)
            input_preview = row['input_text'][:100].replace('\n', ' ')
            if len(row['input_text']) > 100:
                input_preview += "..."
            print(f"   Input: {input_preview}")
            
            # Show output (truncated)
            if row['output_text']:
                output_preview = row['output_text'][:100].replace('\n', ' ')
                if len(row['output_text']) > 100:
                    output_preview += "..."
                print(f"   Output: {output_preview}")
            else:
                print(f"   Output: (empty)")
            
            print("-" * 60)
        
        print(f"\n📈 Summary:")
        print(f"   Total calls: {len(rows)}")
        successful = sum(1 for row in rows if row['success'])
        failed = len(rows) - successful
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        
        # Show call number breakdown
        call_1_count = sum(1 for row in rows if row['call_number'] == 1)
        call_2_count = sum(1 for row in rows if row['call_number'] == 2)
        print(f"   Call #1 (skills): {call_1_count}")
        print(f"   Call #2 (description): {call_2_count}")

if __name__ == "__main__":
    show_mb_log_table()
