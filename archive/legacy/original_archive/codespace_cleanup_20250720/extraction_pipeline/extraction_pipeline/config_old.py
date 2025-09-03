"""
Configuration Management for Extraction Pipeline
================================================

Centralized configuration for job extraction pipeline V7.0.
Based on ty_extract clean architecture principles.

Author: Arden (migrated from Sandy V7.0)
Version: 7.0
Date: 2025-07-19
"""

from typing import Dict, Any
from pathlib import Path


class Config:
    """Configuration class for extraction pipeline"""
    
    def __init__(self):
        """Initialize default configuration"""
        # Model configuration
        self.model_name = "gemma3n:latest"
        self.model_timeout = 300  # 5 minutes
        
        # Output configuration
        self.output_directory = "output"
        self.output_formats = ["excel", "markdown"]
        
        # Processing configuration
        self.max_retries = 3
        self.batch_size = 10
        self.enable_translation = True
        self.enable_location_validation = True
        
        # Logging configuration
        self.log_level = "INFO"
        self.enable_debug_output = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary
        
        Returns:
            Dictionary representation of configuration
        """
        return {
            "model_name": self.model_name,
            "model_timeout": self.model_timeout,
            "output_directory": self.output_directory,
            "output_formats": self.output_formats,
            "max_retries": self.max_retries,
            "batch_size": self.batch_size,
            "enable_translation": self.enable_translation,
            "enable_location_validation": self.enable_location_validation,
            "log_level": self.log_level,
            "enable_debug_output": self.enable_debug_output
        }
    
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from dictionary
        
        Args:
            config_dict: Dictionary with configuration values
        """
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def ensure_output_directory(self) -> Path:
        """Ensure output directory exists
        
        Returns:
            Path to output directory
        """
        output_path = Path(self.output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path


def load_config(config_path: str = None) -> Config:
    """Load configuration from file or use defaults
    
    Args:
        config_path: Path to configuration file (optional)
        
    Returns:
        Configuration object
    """
    config = Config()
    
    if config_path:
        # TODO: Add JSON/YAML config file loading
        pass
    
    return config


def create_default_config() -> Config:
    """Create default configuration
    
    Returns:
        Default configuration object
    """
    return Config()

from pathlib import Path
from datetime import datetime

# Base configuration
CONFIG = {
    # Data paths
    'data_dir': 'data/postings',
    'output_dir': 'output',
    'logs_dir': 'logs',
    
    # Processing settings
    'max_jobs': 10,
    'pipeline_version': '7.0',
    'extractor_version': '1.0.0',
    
    # Output settings
    'excel_filename': 'extraction_report_{timestamp}.xlsx',
    'markdown_filename': 'daily_report_{timestamp}.md',
    'output_format': 'enhanced_data_dictionary_v4.2',
    
    # LLM settings
    'models': {
        'concise_extraction': 'gemma3n:latest',
        'job_analysis': 'gemma3n:latest', 
        'location_validation': 'gemma3n:latest',
        'translation': 'gemma3n:latest'
    },
    
    # Processing options
    'enable_german_translation': True,
    'enable_location_validation': True,
    'enable_skills_extraction': True,
    'batch_processing': True
}

def get_config():
    """Get configuration with current timestamp"""
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

def get_output_dir() -> Path:
    """Get output directory path"""
    output_dir = Path(CONFIG['output_dir'])
    output_dir.mkdir(exist_ok=True)
    return output_dir

def get_logs_dir() -> Path:
    """Get logs directory path"""
    logs_dir = Path(CONFIG['logs_dir'])
    logs_dir.mkdir(exist_ok=True)
    return logs_dir
