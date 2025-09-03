"""
TY_EXTRACT Configuration
=======================

Simple configuration management for the minimal pipeline.
"""

from pathlib import Path
from datetime import datetime

# Base configuration
CONFIG = {
    'data_dir': 'data/postings',
    'output_dir': 'output',
    'max_jobs': 3,
    'excel_filename': 'daily_report_{timestamp}.xlsx',
    'markdown_filename': 'daily_report_{timestamp}.md',
    'pipeline_version': '7.0',
    'extractor_version': '1.0.0'
}

def get_config():
    """Get configuration with timestamp"""
    config = CONFIG.copy()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config['timestamp'] = timestamp
    
    # Replace {timestamp} in filename templates
    config['excel_filename'] = config['excel_filename'].replace('{timestamp}', timestamp)
    config['markdown_filename'] = config['markdown_filename'].replace('{timestamp}', timestamp)
    
    return config

def get_data_dir() -> Path:
    """Get the data directory path"""
    return Path(__file__).parent.parent / "data" / "postings"

def get_output_dir():
    """Get output directory path"""
    output_dir = Path(CONFIG['output_dir'])
    output_dir.mkdir(exist_ok=True)
    return output_dir
