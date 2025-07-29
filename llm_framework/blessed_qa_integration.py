#!/usr/bin/env python3
"""
Blessed Config QA Integration
=============================

Integration layer for QA system to consume blessed ty_codex configurations
instead of source ty_log files. Maintains QA quality while using blessed configs.

Author: Arden (Republic of Love Engineering)
Status: Day 2 Afternoon Implementation
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import QualityAssessor with correct path
import sys
sys.path.append('/home/xai/Documents/ty_learn')
from llm_framework.utils.quality_assessor import QualityAssessor

logger = logging.getLogger(__name__)

class BlessedConfigQALoader:
    """
    QA system integration for blessed configurations
    Loads and validates blessed configs for QA workflows
    """
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize blessed config loader
        
        Args:
            workspace_root: Root of ty_learn workspace (auto-detected if None)
        """
        self.workspace_root = workspace_root or self._find_workspace_root()
        self.blessed_configs_dir = self.workspace_root / 'output/llm_tasks'
        self.quality_assessor = QualityAssessor()
        
    def _find_workspace_root(self) -> Path:
        """Auto-detect workspace root"""
        current = Path.cwd()
        while current.parent != current:
            if (current / 'llm_framework').exists() and (current / 'modules').exists():
                return current
            current = current.parent
        raise ValueError("ty_learn workspace root not found")
    
    def load_blessed_config(self, task_id: str) -> Dict[str, Any]:
        """
        Load blessed configuration by task ID
        
        Args:
            task_id: Task identifier (e.g., 'ty_extract_concise_description')
            
        Returns:
            Dict containing blessed configuration
            
        Raises:
            FileNotFoundError: If blessed config doesn't exist
            ValueError: If config is invalid
        """
        config_path = self.blessed_configs_dir / f"{task_id}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Blessed config not found: {config_path}. "
                f"Run export_llm_task.py to create blessed configs."
            )
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if not config or not isinstance(config, dict):
                raise ValueError(f"Empty or invalid blessed config: {config_path}")
                
            # Validate blessed config structure
            self._validate_blessed_config(config, config_path)
            
            logger.info(f"✅ Blessed config loaded: {task_id}")
            return config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in blessed config {config_path}: {e}")
    
    def _validate_blessed_config(self, config: Dict[str, Any], config_path: Path) -> None:
        """Validate blessed config has required QA fields"""
        required_fields = [
            'task_id', 'title', 'model_id', 'prompt', 'temperature', 
            'max_tokens', 'qa_schema_id', 'blessed_by', 'version'
        ]
        
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(
                f"Blessed config {config_path} missing required fields: {missing_fields}"
            )
    
    def list_available_configs(self) -> List[str]:
        """
        List all available blessed configurations
        
        Returns:
            List of task IDs with blessed configs available
        """
        if not self.blessed_configs_dir.exists():
            return []
            
        config_files = list(self.blessed_configs_dir.glob("*.yaml"))
        task_ids = [f.stem for f in config_files]
        
        logger.info(f"📋 Found {len(task_ids)} blessed configs: {task_ids}")
        return task_ids
    
    def get_qa_config_for_task(self, task_id: str) -> Dict[str, Any]:
        """
        Get QA-specific configuration for a task
        
        Args:
            task_id: Task identifier
            
        Returns:
            QA configuration extracted from blessed config
        """
        blessed_config = self.load_blessed_config(task_id)
        
        # Extract QA-relevant configuration
        qa_config = {
            'task_id': blessed_config['task_id'],
            'qa_schema_id': blessed_config['qa_schema_id'],
            'prompt': blessed_config['prompt'],
            'expected_format': blessed_config.get('format', 'markdown'),
            'expected_behavior': blessed_config.get('expected_behavior', ''),
            'temperature': blessed_config['temperature'],
            'max_tokens': blessed_config['max_tokens'],
            'model_id': blessed_config['model_id'],
            'version': blessed_config['version'],
            'blessed_by': blessed_config['blessed_by'],
            'source_lineage': {
                'source_log_id': blessed_config.get('source_log_id', ''),
                'blessed_on': blessed_config.get('blessed_on', ''),
            }
        }
        
        logger.info(f"🔍 QA config prepared for {task_id} (schema: {qa_config['qa_schema_id']})")
        return qa_config
    
    def validate_qa_compatibility(self, task_id: str) -> bool:
        """
        Validate that blessed config is compatible with QA system
        
        Args:
            task_id: Task identifier to validate
            
        Returns:
            True if config is QA-compatible, False otherwise
        """
        try:
            qa_config = self.get_qa_config_for_task(task_id)
            
            # Check QA schema ID format
            expected_schema_pattern = f"qa_{task_id}_v"
            if not qa_config['qa_schema_id'].startswith(expected_schema_pattern):
                logger.warning(f"⚠️ QA schema ID doesn't match expected pattern: {qa_config['qa_schema_id']}")
                return False
            
            # Check essential QA fields
            if not qa_config['prompt'] or len(qa_config['prompt'].strip()) < 10:
                logger.warning(f"⚠️ Prompt too short or empty for QA: {task_id}")
                return False
                
            # Check temperature and tokens are reasonable for QA
            if not (0.0 <= qa_config['temperature'] <= 2.0):
                logger.warning(f"⚠️ Temperature out of range for QA: {qa_config['temperature']}")
                return False
                
            if qa_config['max_tokens'] < 100:
                logger.warning(f"⚠️ Max tokens too low for QA: {qa_config['max_tokens']}")
                return False
            
            logger.info(f"✅ QA compatibility validated: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ QA compatibility check failed for {task_id}: {e}")
            return False
    
    def create_qa_test_config(self, task_id: str, test_prompt: str) -> Dict[str, Any]:
        """
        Create QA test configuration from blessed config
        
        Args:
            task_id: Task identifier
            test_prompt: Specific prompt for QA testing
            
        Returns:
            Configuration suitable for QA test execution
        """
        blessed_config = self.load_blessed_config(task_id)
        
        qa_test_config = {
            'test_id': f"qa_test_{task_id}",
            'qa_schema_id': blessed_config['qa_schema_id'],
            'model_id': blessed_config['model_id'],
            'prompt': test_prompt,  # Use specific QA test prompt
            'temperature': blessed_config['temperature'],
            'max_tokens': blessed_config['max_tokens'],
            'expected_format': blessed_config.get('format', 'markdown'),
            'baseline_behavior': blessed_config.get('expected_behavior', ''),
            'quality_threshold': 8.0,  # Standard QA threshold
            'metadata': {
                'source_config': task_id,
                'blessed_version': blessed_config['version'],
                'test_type': 'qa_validation'
            }
        }
        
        logger.info(f"🧪 QA test config created for {task_id}")
        return qa_test_config


def demo_blessed_qa_integration():
    """
    Demonstration of blessed config QA integration
    Shows how QA system consumes blessed configs instead of source files
    """
    print("🔍 BLESSED CONFIG QA INTEGRATION DEMO")
    print("=" * 50)
    
    try:
        # Initialize QA loader
        qa_loader = BlessedConfigQALoader()
        print(f"✅ QA loader initialized")
        print(f"📁 Blessed configs directory: {qa_loader.blessed_configs_dir}")
        
        # List available configs
        available_configs = qa_loader.list_available_configs()
        print(f"📋 Available blessed configs: {len(available_configs)}")
        
        if available_configs:
            # Test with first available config
            task_id = available_configs[0]
            print(f"\n🧪 Testing with task: {task_id}")
            
            # Load blessed config
            blessed_config = qa_loader.load_blessed_config(task_id)
            print(f"✅ Blessed config loaded")
            print(f"📝 Task title: {blessed_config['title']}")
            print(f"🤖 Model: {blessed_config['model_id']}")
            print(f"🆔 QA Schema: {blessed_config['qa_schema_id']}")
            
            # Get QA configuration
            qa_config = qa_loader.get_qa_config_for_task(task_id)
            print(f"✅ QA config extracted")
            print(f"🔍 QA schema ID: {qa_config['qa_schema_id']}")
            print(f"📏 Prompt length: {len(qa_config['prompt'])} chars")
            
            # Validate QA compatibility
            is_compatible = qa_loader.validate_qa_compatibility(task_id)
            print(f"✅ QA compatibility: {'PASS' if is_compatible else 'FAIL'}")
            
            # Create QA test config
            test_config = qa_loader.create_qa_test_config(
                task_id, 
                "Test prompt for QA validation"
            )
            print(f"✅ QA test config created")
            print(f"🧪 Test ID: {test_config['test_id']}")
            
            print(f"\n🎉 BLESSED CONFIG QA INTEGRATION SUCCESSFUL!")
            
        else:
            print("⚠️ No blessed configs found. Run export_llm_task.py first.")
            
    except Exception as e:
        print(f"❌ QA integration demo failed: {e}")


if __name__ == "__main__":
    demo_blessed_qa_integration()
