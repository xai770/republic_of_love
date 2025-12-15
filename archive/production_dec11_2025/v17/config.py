"""
TY_EXTRACT V14 - Configuration Management
========================================

External configuration with fail-fast validation.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Import config manager components
import sys
import os
try:
    if __name__ == "__main__" or not __package__:
        # Direct execution or no package context
        from config_manager import ConfigManager, ConfigSnapshot, ConfigError  # type: ignore[import-not-found]
    else:
        # Module import - use relative imports  
        from .config_manager import ConfigManager, ConfigSnapshot, ConfigError
except ImportError:
    # Fallback to stub for mypy compatibility
    try:
        from .config_manager_stub import ConfigManager, ConfigSnapshot, ConfigError
    except ImportError:
        from config_manager_stub import ConfigManager, ConfigSnapshot, ConfigError  # type: ignore[import-not-found]

logger = logging.getLogger('ty_extract_v14.config')

@dataclass
class Config:
    """
    Main configuration class - loads from external files
    
    No default values - all configuration must be explicit in external files.
    """
    
    # Core settings (loaded from external config)
    pipeline_version: str
    max_jobs: int
    data_dir: Path
    output_dir: Path
    
    # LLM settings
    llm_model: str
    llm_base_url: str
    llm_timeout: int
    
    # Report settings
    generate_excel: bool
    generate_markdown: bool
    
    # Logging
    log_level: str
    
    # Config tracking
    config_snapshot: Optional[ConfigSnapshot] = None
    
    @classmethod
    def load_from_external(cls, config_dir: Optional[Path] = None) -> 'Config':
        """
        Load configuration from external files
        
        Args:
            config_dir: Directory containing configuration files
            
        Returns:
            Config instance with externally loaded settings
            
        Raises:
            ConfigError: If configuration cannot be loaded
        """
        if config_dir is None:
            # Default to config directory relative to this file
            config_dir = Path(__file__).parent / "config"
        
        try:
            # Load external configuration
            config_manager = ConfigManager(config_dir)
            snapshot = config_manager.load_config()
            
            # Extract configuration values
            pipeline_config = snapshot.pipeline_config
            model_config = snapshot.model_config
            
            # Create Config instance
            config = cls(
                # Pipeline settings
                pipeline_version=pipeline_config['pipeline']['version'],
                max_jobs=pipeline_config['pipeline']['max_jobs'],
                data_dir=Path(pipeline_config['data']['input_dir']),
                output_dir=Path(pipeline_config['data']['output_dir']),
                
                # LLM settings
                llm_model=model_config['model']['name'],
                llm_base_url=pipeline_config['llm']['base_url'],
                llm_timeout=pipeline_config['llm']['timeout'],
                
                # Report settings
                generate_excel=pipeline_config['reports']['generate_excel'],
                generate_markdown=pipeline_config['reports']['generate_markdown'],
                
                # Logging
                log_level=pipeline_config['logging']['level'],
                
                # Store snapshot for tracking
                config_snapshot=snapshot
            )
            
            logger.info(f"✅ Configuration loaded from external files (hash: {snapshot.config_hash[:8]})")
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Failed to load external configuration: {e}")
            raise ConfigError(f"Configuration loading failed: {e}")
    
    def get_template(self, template_name: str) -> str:
        """
        Get template content by name
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template content string
            
        Raises:
            ConfigError: If template not found
        """
        if not self.config_snapshot:
            raise ConfigError("No config snapshot available")
        
        if template_name not in self.config_snapshot.templates:
            available = list(self.config_snapshot.templates.keys())
            raise ConfigError(f"Template '{template_name}' not found. Available: {available}")
        
        return str(self.config_snapshot.templates[template_name])
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model-specific configuration"""
        if not self.config_snapshot:
            raise ConfigError("No config snapshot available")
        
        return dict(self.config_snapshot.model_config)
    
    def save_config_snapshot(self, output_dir: Path) -> None:
        """Save configuration snapshot to output directory"""
        if not self.config_snapshot:
            logger.warning("No config snapshot to save")
            return
        
        config_manager = ConfigManager(Path(__file__).parent / "config")
        config_manager.snapshot = self.config_snapshot
        config_manager.save_config_snapshot(output_dir)

def setup_logging(config: Config) -> logging.Logger:
    """
    Setup clean logging configuration
    
    Args:
        config: Configuration object
        
    Returns:
        Configured logger
    """
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    logger = logging.getLogger('ty_extract_v14')
    
    return logger
