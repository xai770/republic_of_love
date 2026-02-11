"""
Formatting utilities for the LLMCore Admin GUI
"""

import streamlit as st
from datetime import datetime
from typing import Any, Dict, List, Optional

def format_timestamp(timestamp: Optional[str]) -> str:
    """Format timestamp for display"""
    if not timestamp:
        return "N/A"
    
    try:
        # Try to parse various timestamp formats
        if isinstance(timestamp, str):
            # Common SQLite datetime format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return str(timestamp)
    except (ValueError, TypeError, AttributeError):
        return str(timestamp)

def format_duration(start_time: Optional[str], end_time: Optional[str]) -> str:
    """Format duration between two timestamps"""
    if not start_time or not end_time:
        return "N/A"
    
    try:
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration = end - start
        
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except (ValueError, TypeError):
        return "N/A"

def format_status_indicator(status: str) -> str:
    """Return emoji indicator for status"""
    status_map = {
        'SUCCESS': '✅',
        'FAILED': '❌',
        'RUNNING': '⏳',
        'PENDING': '⏸️',
        'CANCELLED': '🚫',
        True: '✅',
        False: '❌',
        1: '✅',
        0: '❌'
    }
    
    return status_map.get(status, '❓')

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis"""
    if not text:
        return "N/A"
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def format_metric_delta(current: int, target: int = 0) -> tuple:
    """Format metric delta for st.metric"""
    delta = current - target
    
    if delta == 0:
        return f"🎯 Target reached", "normal"
    elif delta > 0:
        return f"{delta} above target", "inverse"
    else:
        return f"{abs(delta)} to target", "normal"

def display_data_table(data: List[Dict[str, Any]], 
                      columns: Optional[List[str]] = None,
                      formatters: Optional[Dict[str, callable]] = None) -> None:
    """Display data as a formatted table"""
    
    if not data:
        st.info("No data to display")
        return
    
    import pandas as pd
    df = pd.DataFrame(data)
    
    # Apply column selection
    if columns:
        available_columns = [col for col in columns if col in df.columns]
        if available_columns:
            df = df[available_columns]
    
    # Apply formatters
    if formatters:
        for column, formatter in formatters.items():
            if column in df.columns:
                df[column] = df[column].apply(formatter)
    
    st.dataframe(df, use_container_width=True, hide_index=True)

def create_progress_indicator(completed: int, total: int) -> str:
    """Create a text-based progress indicator"""
    if total == 0:
        return "N/A"
    
    percentage = (completed / total) * 100
    
    if percentage == 100:
        return f"✅ {completed}/{total} (100%)"
    elif percentage >= 75:
        return f"🟨 {completed}/{total} ({percentage:.0f}%)"
    elif percentage >= 50:
        return f"🟧 {completed}/{total} ({percentage:.0f}%)"
    elif percentage >= 25:
        return f"🟥 {completed}/{total} ({percentage:.0f}%)"
    else:
        return f"⚫ {completed}/{total} ({percentage:.0f}%)"

def safe_get(dictionary: Dict[str, Any], key: str, default: Any = "N/A") -> Any:
    """Safely get value from dictionary with default"""
    return dictionary.get(key, default) if dictionary else default