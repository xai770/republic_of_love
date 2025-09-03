#!/usr/bin/env python3
"""
LLM Task Codex Export Script - Production Implementation
Transforms ty_log task configurations into blessed ty_codex format

Based on: Dexi's v2 specification (llm_task_codex_technical_spec_v2_production_ready.md)
Author: Arden (Republic of Love Engineering)
Implementation: All 5 critical blocking issues resolved
Status: Production ready
"""

import sys
import yaml
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExportError(Exception):
    """Custom exception for export-related errors"""
    pass

def find_ty_learn_root() -> Path:
    """
    Dynamically locate ty_learn root directory
    Environment-agnostic path resolution
    """
    current = Path.cwd()
    while current.parent != current:
        # Look for ty_learn workspace markers
        if (current / 'modules').exists() and (current / 'llm_framework').exists():
            logger.info(f"Found ty_learn root: {current}")
            return current
        current = current.parent
    raise ExportError("ty_learn root not found - ensure script runs within ty_learn workspace")

def validate_source_schema(data: Dict[str, Any]) -> None:
    """
    Comprehensive validation of source YAML structure
    Prevents malformed exports from reaching production
    """
    required_fields = ['task_id', 'title', 'model', 'generation_config']
    
    for field in required_fields:
        if field not in data:
            raise ExportError(f"Missing required field: {field}")
    
    # Validate task_id format
    task_id = data['task_id']
    if not isinstance(task_id, str) or not task_id.strip():
        raise ExportError("task_id must be non-empty string")
    
    # Validate nested model structure
    model = data['model']
    if not isinstance(model, dict) or 'model_id' not in model:
        raise ExportError("Missing or invalid model.model_id")
    
    # Validate generation config
    gen_config = data['generation_config']
    if not isinstance(gen_config, dict):
        raise ExportError("generation_config must be dictionary")
    
    required_gen_fields = ['temperature', 'max_tokens']
    for field in required_gen_fields:
        if field not in gen_config:
            raise ExportError(f"Missing generation_config.{field}")
        
        # Type validation
        if field == 'temperature' and not isinstance(gen_config[field], (int, float)):
            raise ExportError("temperature must be numeric")
        if field == 'max_tokens' and not isinstance(gen_config[field], int):
            raise ExportError("max_tokens must be integer")

def extract_prompt_content(source_data: Dict[str, Any], workspace_root: Path) -> str:
    """
    Extract prompt content with explicit configuration requirements
    NO FALLBACKS - fails fast on configuration issues
    """
    task_id = source_data['task_id']
    
    # Task ID to template mapping for V14 integration
    template_mapping = {
        'ty_extract_concise_description': 'concise_description.md',
        'ty_extract_skill_extraction': 'skill_extraction.md'
    }
    
    # Option 1: V14 template (preferred)
    if task_id in template_mapping:
        template_name = template_mapping[task_id]
        template_path = workspace_root / f"modules/ty_extract_versions/ty_extract_v14/config/templates/{template_name}"
        if template_path.exists():
            logger.info(f"Using V14 template: {template_path}")
            try:
                content = template_path.read_text(encoding='utf-8').strip()
                if not content:
                    raise ExportError(f"V14 template is empty: {template_path}")
                return content
            except Exception as e:
                raise ExportError(f"Failed to read V14 template {template_path}: {e}")
        else:
            raise ExportError(f"V14 template not found: {template_path}")
    
    # Option 2: Embedded prompt_template (explicit configuration)
    if 'prompt_template' in source_data:
        logger.info("Using embedded prompt_template")
        prompt_template = source_data['prompt_template']
        if not prompt_template or not str(prompt_template).strip():
            raise ExportError("prompt_template field is empty")
        return str(prompt_template).strip()
    
    # NO FALLBACKS - require explicit configuration
    raise ExportError(
        f"No prompt configuration found for task '{task_id}'. "
        f"Required: Either V14 template mapping OR prompt_template field. "
        f"Available V14 templates: {list(template_mapping.keys())}"
    )

def derive_output_format(source_data: Dict[str, Any]) -> str:
    """
    Derive output format from schema or metadata
    Provides sensible defaults for production use
    """
    # Check output_schema if present
    output_schema = source_data.get('output_schema', [])
    if output_schema and isinstance(output_schema, list):
        first_output = output_schema[0]
        if isinstance(first_output, dict):
            output_type = first_output.get('type', 'string')
            if output_type in ['json', 'object', 'array']:
                return 'json'
            elif output_type in ['markdown', 'text', 'string']:
                return 'markdown'
    
    # Check notes for format hints
    notes = source_data.get('notes', [])
    if isinstance(notes, list):
        for note in notes:
            if isinstance(note, str):
                if 'json' in note.lower():
                    return 'json'
                elif 'markdown' in note.lower():
                    return 'markdown'
    
    # Default to markdown for most text-based tasks
    return 'markdown'

def generate_qa_schema_id(task_id: str) -> str:
    """
    Generate stable, maintainable QA schema ID
    Uses task-based approach per Arden's recommendation
    """
    return f"qa_{task_id}_v1"

def get_next_version(target_path: Path) -> int:
    """
    Handle version increments intelligently
    Prevents version collisions on re-export
    """
    if target_path.exists():
        try:
            with open(target_path, 'r') as f:
                existing = yaml.safe_load(f)
                current_version = existing.get('version', 0)
                return int(current_version) + 1
        except Exception as e:
            logger.warning(f"Could not read existing version from {target_path}: {e}")
            return 1
    return 1

def create_blessed_config(source_data: Dict[str, Any], prompt_content: str, source_path: Path) -> Dict[str, Any]:
    """
    Transform source data into blessed configuration format
    Follows Misty's sacred schema exactly
    """
    task_id = source_data['task_id']
    
    blessed_config = {
        # Core task definition
        'task_id': task_id,
        'title': source_data['title'],
        'model_id': source_data['model']['model_id'],
        'prompt': prompt_content,
        'temperature': source_data['generation_config']['temperature'],
        'max_tokens': source_data['generation_config']['max_tokens'],
        'format': derive_output_format(source_data),
        'expected_behavior': source_data.get('description', '').strip(),
        
        # QA and lineage (sacred metadata)
        'qa_schema_id': generate_qa_schema_id(task_id),
        'source_log_id': source_path.stem,  # filename without extension
        'blessed_by': 'Dexi',
        'blessed_on': datetime.now().strftime('%Y-%m-%d'),
        'version': 1  # Will be updated by get_next_version if needed
    }
    
    return blessed_config

def write_blessed_config_atomic(blessed_config: Dict[str, Any], target_path: Path) -> None:
    """
    Atomic write operation for blessed configuration
    Prevents partial writes and ensures consistency
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temporary file first
    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.yaml', 
        dir=target_path.parent, 
        delete=False
    ) as temp_file:
        temp_path = Path(temp_file.name)
        yaml.dump(
            blessed_config, 
            temp_file, 
            default_flow_style=False, 
            sort_keys=False,
            allow_unicode=True
        )
    
    # Atomic rename
    shutil.move(str(temp_path), str(target_path))
    logger.info(f"Atomic write completed: {target_path}")

def export_llm_task(source_file_path: str, overwrite: bool = False) -> bool:
    """
    Transform ty_log task to ty_codex blessed format
    Production-ready with comprehensive error handling
    
    Args:
        source_file_path: Path to source YAML in ty_log/
        overwrite: If True, overwrite existing exports without version increment
        
    Returns:
        bool: True if export successful, False otherwise
    """
    try:
        # Phase 1: Environment Setup and Validation
        workspace_root = find_ty_learn_root()
        source_path = Path(source_file_path)
        
        if not source_path.exists():
            raise ExportError(f"Source file not found: {source_file_path}")
        
        if not source_path.is_absolute():
            source_path = workspace_root / source_path
            
        logger.info(f"🔍 Processing source: {source_path}")
        
        # Phase 2: Load and Validate Source
        with open(source_path, 'r', encoding='utf-8') as f:
            source_data = yaml.safe_load(f)
            
        if not source_data:
            raise ExportError("Source file is empty or invalid YAML")
            
        validate_source_schema(source_data)
        logger.info(f"✅ Source validation passed: {source_path.name}")
        
        # Phase 3: Extract and Transform
        prompt_content = extract_prompt_content(source_data, workspace_root)
        blessed_config = create_blessed_config(source_data, prompt_content, source_path)
        logger.info(f"✅ Schema transformation completed")
        
        # Phase 4: Handle Versioning and Target Path
        target_dir = workspace_root / 'output/llm_tasks'
        target_path = target_dir / f"{blessed_config['task_id']}.yaml"
        
        if target_path.exists() and not overwrite:
            blessed_config['version'] = get_next_version(target_path)
            logger.info(f"✅ Version incremented to {blessed_config['version']}")
        
        # Phase 5: Atomic Write
        write_blessed_config_atomic(blessed_config, target_path)
        logger.info(f"✅ Export completed: {source_path.name} → {target_path.name}")
        
        # Phase 6: Verification
        # Verify the written file can be loaded back
        try:
            with open(target_path, 'r') as f:
                verification = yaml.safe_load(f)
                assert verification['task_id'] == blessed_config['task_id']
            logger.info(f"✅ Export verification passed")
        except Exception as e:
            raise ExportError(f"Export verification failed: {e}")
        
        return True
        
    except ExportError as e:
        logger.error(f"❌ Export failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during export: {e}", exc_info=True)
        return False

def main():
    """
    Command-line interface for export script
    """
    if len(sys.argv) < 2:
        print("Usage: python export_llm_task.py <source_yaml_path> [--overwrite]")
        print("Example: python export_llm_task.py modules/ty_extract_versions/data/ty_codex/ty_log/llm_task_ty_extract_concise_description.yaml")
        sys.exit(1)
    
    source_file = sys.argv[1]
    overwrite = '--overwrite' in sys.argv
    
    logger.info(f"🚀 Starting LLM Task Codex Export")
    logger.info(f"Source: {source_file}")
    logger.info(f"Overwrite mode: {overwrite}")
    
    success = export_llm_task(source_file, overwrite)
    
    if success:
        logger.info(f"🎉 Export completed successfully")
        sys.exit(0)
    else:
        logger.error(f"💥 Export failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
