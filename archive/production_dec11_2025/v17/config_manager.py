"""
Config Management for TY_EXTRACT V14
===================================

External configuration load        try:
            with open(pipe        try:
            with open(model_file, 'r') as file:
                config: Dict[str, Any] = yaml.safe_load(file)
            
            if not isinstance(config, dict):
                raise ConfigError(f"Model config must be a dictionary, got {type(config)}")
            
            # Validate required model sections
            required_sections = ['model', 'generation']
            for section in required_sections:
                if section not in config:
                    raise ConfigError(f"Required model config section missing: {section}")
            
            logger.debug(f"✅ Model config loaded: {model_file}")
            return configr') as file:
                config: Dict[str, Any] = yaml.safe_load(file)
            
            if not isinstance(config, dict):
                raise ConfigError(f"Pipeline config must be a dictionary, got {type(config)}")
            
            # Validate required sections
            required_sections = ['pipeline', 'llm', 'templates', 'reports']
            for section in required_sections:
                if section not in config:
                    raise ConfigError(f"Required config section missing: {section}")
            
            logger.debug(f"✅ Pipeline config loaded: {pipeline_file}")
            return configl-fast validation.
No fallbacks - configs must be explicit and complete.
"""

import yaml
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('ty_extract_v14.config_manager')

@dataclass
class ConfigSnapshot:
    """Configuration snapshot for tracking and debugging"""
    config_hash: str
    pipeline_config: Dict[str, Any]
    model_config: Dict[str, Any]
    templates: Dict[str, str]
    loaded_at: datetime
    config_files: Dict[str, str]  # file_name -> file_path

class ConfigManager:
    """
    Manages external configuration loading with validation
    
    Features:
    - Fail-fast validation (no defaults)
    - Config hash tracking
    - Template loading with validation
    - Config snapshots for debugging
    """
    
    def __init__(self, config_dir: Path):
        """
        Initialize config manager
        
        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)
        self.snapshot: Optional[ConfigSnapshot] = None
        
        # Validate config directory exists
        if not self.config_dir.exists():
            raise ConfigError(f"Configuration directory not found: {config_dir}")
        
        logger.info(f"✅ Config manager initialized: {config_dir}")
    
    def load_config(self) -> ConfigSnapshot:
        """
        Load complete configuration with validation
        
        Returns:
            ConfigSnapshot with all loaded configuration
            
        Raises:
            ConfigError: If any required configuration is missing or invalid
        """
        logger.info("🔧 Loading external configuration...")
        
        try:
            # Load main pipeline config
            pipeline_config = self._load_pipeline_config()
            
            # Load model config
            model_config = self._load_model_config(pipeline_config)
            
            # Load templates
            templates = self._load_templates(pipeline_config)
            
            # Generate config hash for tracking
            config_hash = self._generate_config_hash(pipeline_config, model_config, templates)
            
            # Create snapshot
            self.snapshot = ConfigSnapshot(
                config_hash=config_hash,
                pipeline_config=pipeline_config,
                model_config=model_config,
                templates=templates,
                loaded_at=datetime.now(),
                config_files=self._get_config_file_paths(pipeline_config)
            )
            
            logger.info(f"✅ Configuration loaded successfully (hash: {config_hash[:8]})")
            
            return self.snapshot
            
        except Exception as e:
            logger.error(f"❌ Configuration loading failed: {e}")
            raise ConfigError(f"Failed to load configuration: {e}")
    
    def _load_pipeline_config(self) -> Dict[str, Any]:
        """Load main pipeline configuration"""
        
        pipeline_file = self.config_dir / "pipeline.yaml"
        if not pipeline_file.exists():
            raise ConfigError(f"Pipeline config not found: {pipeline_file}")
        
        try:
            with open(pipeline_file, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            if not isinstance(raw_config, dict):
                raise ConfigError(f"Pipeline config must be a dictionary, got {type(raw_config)}")
            
            config: Dict[str, Any] = raw_config
            
            # Validate required sections
            required_sections = ['pipeline', 'llm', 'templates', 'reports']
            for section in required_sections:
                if section not in config:
                    raise ConfigError(f"Required config section missing: {section}")
            
            logger.debug(f"✅ Pipeline config loaded: {pipeline_file}")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in pipeline config: {e}")
    
    def _load_model_config(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """Load model-specific configuration"""
        
        model_config_path = pipeline_config['llm']['model_config']
        model_file = self.config_dir.parent / model_config_path
        
        if not model_file.exists():
            raise ConfigError(f"Model config not found: {model_file}")
        
        try:
            with open(model_file, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            if not isinstance(raw_config, dict):
                raise ConfigError(f"Model config must be a dictionary, got {type(raw_config)}")
            
            config: Dict[str, Any] = raw_config
            
            # Validate required model sections
            required_sections = ['model', 'generation']
            for section in required_sections:
                if section not in config:
                    raise ConfigError(f"Required model config section missing: {section}")
            
            logger.debug(f"✅ Model config loaded: {model_file}")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in model config: {e}")
    
    def _load_templates(self, pipeline_config: Dict[str, Any]) -> Dict[str, str]:
        """Load all template files"""
        
        templates = {}
        template_config = pipeline_config['templates']
        
        for template_name, template_path in template_config.items():
            template_file = self.config_dir.parent / template_path
            
            if not template_file.exists():
                raise ConfigError(f"Template not found: {template_file}")
            
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract just the prompt template from markdown
                template_text = self._extract_template_from_markdown(content)
                templates[template_name] = template_text
                
                logger.debug(f"✅ Template loaded: {template_name}")
                
            except Exception as e:
                raise ConfigError(f"Failed to load template {template_name}: {e}")
        
        return templates
    
    def _extract_template_from_markdown(self, markdown_content: str) -> str:
        """Extract the actual prompt template from the markdown documentation"""
        
        # Look for the template between markdown code blocks
        lines = markdown_content.split('\n')
        in_template = False
        template_lines = []
        
        for line in lines:
            if line.strip() == '```' and not in_template:
                in_template = True
                continue
            elif line.strip() == '```' and in_template:
                break
            elif in_template:
                template_lines.append(line)
        
        if not template_lines:
            raise ConfigError("No template found in markdown (missing code block?)")
        
        return '\n'.join(template_lines)
    
    def _generate_config_hash(self, pipeline_config: Dict[str, Any], model_config: Dict[str, Any], templates: Dict[str, str]) -> str:
        """Generate hash of all configuration for tracking"""
        
        # Combine all config data
        combined_data = {
            'pipeline': pipeline_config,
            'model': model_config,
            'templates': templates
        }
        
        # Create hash
        config_str = str(combined_data)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _get_config_file_paths(self, pipeline_config: Dict[str, Any]) -> Dict[str, str]:
        """Get all config file paths for snapshot"""
        
        paths = {
            'pipeline': str(self.config_dir / "pipeline.yaml"),
            'model': str(self.config_dir.parent / pipeline_config['llm']['model_config'])
        }
        
        # Add template paths
        for name, path in pipeline_config['templates'].items():
            paths[f'template_{name}'] = str(self.config_dir.parent / path)
        
        return paths
    
    def save_config_snapshot(self, output_dir: Path) -> None:
        """Save configuration snapshot to output directory"""
        
        if not self.snapshot:
            logger.warning("No config snapshot to save")
            return
        
        snapshot_dir = output_dir / "config_snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all config files
        for file_type, file_path in self.snapshot.config_files.items():
            source_file = Path(file_path)
            if source_file.exists():
                target_file = snapshot_dir / f"{file_type}_{source_file.name}"
                target_file.write_text(source_file.read_text())
        
        # Create snapshot metadata
        metadata = {
            'config_hash': self.snapshot.config_hash,
            'loaded_at': self.snapshot.loaded_at.isoformat(),
            'config_files': self.snapshot.config_files
        }
        
        metadata_file = snapshot_dir / "snapshot_metadata.yaml"
        with open(metadata_file, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False)
        
        logger.info(f"✅ Config snapshot saved: {snapshot_dir}")

class ConfigError(Exception):
    """Configuration loading or validation error"""
    pass
