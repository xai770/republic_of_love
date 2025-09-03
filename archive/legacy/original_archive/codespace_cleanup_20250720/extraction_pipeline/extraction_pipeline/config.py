"""
Configuration Management for Extraction Pipeline
================================================

Centralized configuration for job extraction pipeline V7.0.
Based on ty_extract clean architecture principles.

Author: Arden (migrated from Sandy V7.0)
Version: 7.0
Date: 2025-07-19
"""

from typing import Dict, Any, Optional
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


def load_config(config_path: Optional[str] = None) -> Config:
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
