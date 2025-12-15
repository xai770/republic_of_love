"""
MemBridge Origin Tracking Utility

Provides utilities for automatically tracking the origin of MemBridge calls.
Use this to easily include script path information in MemBridge log entries.
"""

import inspect
import os
import sqlite3
from datetime import datetime
from typing import Optional, Any, Dict

def get_origin_script(stack_depth: int = 2) -> str:
    """
    Get the path of the script that initiated the MemBridge call.
    
    Args:
        stack_depth: How many stack frames to go back (default: 2)
                    1 = this function
                    2 = calling function (default - usually what you want)
                    3 = caller's caller, etc.
    
    Returns:
        Absolute path of the originating script
    """
    try:
        frame = inspect.stack()[stack_depth]
        return os.path.abspath(frame.filename)
    except (IndexError, AttributeError):
        return "unknown_origin"

def log_membridge_call(
    db_path: str,
    template_id: int,
    input_text: str,
    output_text: Optional[str] = None,
    success: bool = True,
    latency: Optional[str] = None,
    error_message: Optional[str] = None,
    remarks: Optional[str] = None,
    validation_passed: bool = True,
    validation_errors: Optional[str] = None,
    output_word_count: Optional[int] = None,
    output_has_json: bool = False,
    output_quality_score: Optional[float] = None,
    origin_script: Optional[str] = None
) -> int:
    """
    Log a MemBridge call with automatic origin tracking.
    
    Args:
        db_path: Path to MemBridge database
        template_id: ID of template used
        input_text: Input text for the call
        output_text: Generated output (optional)
        success: Whether the call succeeded
        latency: Response time (optional)
        error_message: Error details if failed (optional)
        remarks: Additional notes (optional)
        validation_passed: Whether validation passed
        validation_errors: Validation error details (optional)
        output_word_count: Word count of output (optional)
        output_has_json: Whether output contains JSON
        output_quality_score: Quality score (optional)
        origin_script: Override origin detection (optional)
    
    Returns:
        log_id of the created entry
    """
    
    # Auto-detect origin if not provided
    if origin_script is None:
        origin_script = get_origin_script(stack_depth=2)
    
    # Default timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO log (
                template_id, input_text, output_text, success, latency, 
                timestamp, error_message, validation_passed, validation_errors,
                output_word_count, output_has_json, output_quality_score, 
                remarks, origin_script
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            template_id, input_text, output_text, success, latency,
            timestamp, error_message, validation_passed, validation_errors,
            output_word_count, output_has_json, output_quality_score,
            remarks, origin_script
        ))
        
        conn.commit()
        log_id = cursor.lastrowid
        
        if log_id is None:
            raise ValueError("Failed to get log_id from database")
        
        return log_id
        
    finally:
        conn.close()

def get_origin_summary(db_path: str) -> Dict[str, Any]:
    """
    Get a summary of MemBridge calls by origin script.
    
    Args:
        db_path: Path to MemBridge database
        
    Returns:
        Dictionary with origin statistics
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get call counts by origin
        cursor.execute('''
            SELECT 
                origin_script,
                COUNT(*) as call_count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(CASE WHEN success = 1 AND latency IS NOT NULL 
                    THEN CAST(REPLACE(REPLACE(latency, 's', ''), ':', '') AS REAL) 
                    ELSE NULL END) as avg_response_time
            FROM log 
            WHERE origin_script IS NOT NULL
            GROUP BY origin_script
            ORDER BY call_count DESC
        ''')
        
        origins = []
        for row in cursor.fetchall():
            origin_script, call_count, success_count, avg_response_time = row
            origins.append({
                'script': origin_script,
                'total_calls': call_count,
                'successful_calls': success_count,
                'success_rate': success_count / call_count if call_count > 0 else 0,
                'avg_response_time': avg_response_time
            })
        
        # Get total stats
        cursor.execute('SELECT COUNT(*) FROM log WHERE origin_script IS NOT NULL')
        total_tracked = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM log WHERE origin_script IS NULL OR origin_script = "legacy_pre_tracking"')
        legacy_count = cursor.fetchone()[0]
        
        return {
            'total_tracked_calls': total_tracked,
            'legacy_calls': legacy_count,
            'origins': origins
        }
        
    finally:
        conn.close()

def print_origin_report(db_path: str) -> None:
    """Print a formatted report of MemBridge usage by origin script."""
    
    summary = get_origin_summary(db_path)
    
    print("📊 MemBridge Origin Tracking Report")
    print("=" * 50)
    print(f"Total tracked calls: {summary['total_tracked_calls']}")
    print(f"Legacy calls: {summary['legacy_calls']}")
    print()
    
    if summary['origins']:
        print("📂 Calls by Origin Script:")
        print("-" * 50)
        
        for origin in summary['origins']:
            script_name = os.path.basename(origin['script'])
            success_rate = origin['success_rate'] * 100
            avg_time = origin['avg_response_time']
            
            print(f"🔸 {script_name}")
            print(f"   Path: {origin['script']}")
            print(f"   Calls: {origin['total_calls']} ({origin['successful_calls']} successful)")
            print(f"   Success Rate: {success_rate:.1f}%")
            if avg_time:
                print(f"   Avg Response Time: {avg_time:.1f}s")
            print()
    else:
        print("No origin-tracked calls found.")

# Example usage functions
def example_membridge_call_with_tracking() -> int:
    """Example of how to use origin tracking in a MemBridge call."""
    
    db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
    
    # Simple way - automatic origin detection
    log_id = log_membridge_call(
        db_path=db_path,
        template_id=1,
        input_text="Example input text",
        output_text="Example output text",
        success=True,
        latency="2.5s",
        remarks="Example call with automatic origin tracking"
    )
    
    print(f"✅ Logged MemBridge call with ID: {log_id}")
    return log_id

def example_manual_origin_tracking() -> int:
    """Example of manual origin specification."""
    
    db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
    
    # Manual origin specification
    log_id = log_membridge_call(
        db_path=db_path,
        template_id=2,
        input_text="Manual tracking example",
        output_text="Manual output",
        success=True,
        latency="1.2s",
        origin_script="/custom/script/path.py",
        remarks="Example with manual origin specification"
    )
    
    print(f"✅ Logged MemBridge call with manual origin: {log_id}")
    return log_id

if __name__ == "__main__":
    # Test the utility functions
    print("🧪 Testing MemBridge Origin Tracking Utility")
    
    db_path = "/home/xai/Documents/ty_learn/data/membridge.db"
    
    # Test automatic origin detection
    log_id1 = example_membridge_call_with_tracking()
    
    # Test manual origin specification
    log_id2 = example_manual_origin_tracking()
    
    # Show origin report
    print("\n" + "="*50)
    print_origin_report(db_path)
