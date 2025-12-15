"""
Minimal stub for config_manager to fix mypy issues
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

class ConfigError(Exception):
    """Configuration error"""
    pass

@dataclass
class ConfigSnapshot:
    """Configuration snapshot"""
    config_hash: str
    pipeline_config: Dict[str, Any]
    model_config: Dict[str, Any]
    templates: Dict[str, str]
    file_paths: Dict[str, str]

class ConfigManager:
    """Minimal config manager stub"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    def load_snapshot(self) -> ConfigSnapshot:
        """Load configuration snapshot"""
        return ConfigSnapshot(
            config_hash="stub",
            pipeline_config={},
            model_config={},
            templates={},
            file_paths={}
        )
