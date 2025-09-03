"""
MemBridge Registry System - Round 5.4

Implements the config-driven LLM call system with:
- Template registry (linking call numbers to model + prompt combinations)
- Prompt registry (markdown-based prompt storage)
- Call logging (detailed transaction logs)
- Validation layer (input/output format validation)

Architecture: ty_extract script → config → template registry → model + prompt → validation → LLM call → call log
"""

import sqlite3
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime
import re
import hashlib

from .models import (
    PromptRegistryEntry, 
    TemplateRegistryEntry, 
    CallLogEntry, 
    MemBridgeConfig
)


class RegistrySystem:
    """
    Main registry system managing prompts, templates, and call logging.
    
    xai's Requirements:
    - Simple table access to mb_template_registry, prompt_registry, call_log
    - Markdown-based prompt storage
    - Config-driven LLM calls (not hard-coded)
    - External configs control MemBridge calls
    """
    
    def __init__(self, db_path: str, config: MemBridgeConfig):
        self.db_path = db_path
        self.config = config
        self.prompt_dir = Path(config.prompt_registry_path)
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize registry tables in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                -- Prompt Registry: Markdown-based prompt storage
                CREATE TABLE IF NOT EXISTS prompt_registry (
                    prompt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    content TEXT NOT NULL,
                    version TEXT DEFAULT '1.0',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    tags TEXT,  -- JSON array of tags
                    file_path TEXT  -- Path to markdown file
                );
                
                -- Template Registry: Links call numbers to model + prompt combinations
                CREATE TABLE IF NOT EXISTS mb_template_registry (
                    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_number INTEGER NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    config TEXT,  -- JSON config for LLM
                    enabled BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (prompt_id) REFERENCES prompt_registry (prompt_id)
                );
                
                -- Call Log: All LLM transactions with QA metrics
                CREATE TABLE IF NOT EXISTS mb_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    call_number INTEGER NOT NULL,
                    template_id INTEGER NOT NULL,
                    input_text TEXT NOT NULL,
                    output_text TEXT,
                    model TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    latency_ms REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    error_message TEXT,
                    validation_passed BOOLEAN DEFAULT 1,
                    validation_errors TEXT,  -- JSON array
                    output_word_count INTEGER,
                    output_has_json BOOLEAN DEFAULT 0,
                    output_quality_score REAL,
                    FOREIGN KEY (template_id) REFERENCES mb_template_registry (template_id)
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_call_number ON mb_template_registry(call_number);
                CREATE INDEX IF NOT EXISTS idx_mb_log_call_number ON mb_log(call_number);
                CREATE INDEX IF NOT EXISTS idx_mb_log_timestamp ON mb_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_prompt_name ON prompt_registry(name);
            ''')
    
    def add_prompt(self, name: str, content: str, description: str = "", 
                   tags: Optional[List[str]] = None, save_to_file: bool = True) -> int:
        """
        Add a new prompt to the registry.
        
        Args:
            name: Unique name for the prompt
            content: The prompt text
            description: Optional description
            tags: Optional list of tags
            save_to_file: Whether to save as markdown file
            
        Returns:
            prompt_id of the created prompt
        """
        if tags is None:
            tags = []
        
        now = datetime.now().isoformat()
        file_path = None
        
        if save_to_file:
            # Save as markdown file
            safe_name = name.replace(' ', '_').lower()
            file_path_obj = self.prompt_dir / f"{safe_name}.md"
            markdown_content = f"""# {name}

{description}

## Tags
{', '.join(tags) if tags else 'None'}

## Prompt Content

{content}

---
*Created: {now}*
*Updated: {now}*
"""
            file_path_obj.write_text(markdown_content, encoding='utf-8')
            # Use relative path from current working directory
            try:
                file_path = str(file_path_obj.relative_to(Path.cwd()))
            except ValueError:
                # If relative path fails, use absolute path
                file_path = str(file_path_obj)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO prompt_registry 
                (name, description, content, created_at, updated_at, tags, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, content, now, now, json.dumps(tags), file_path))
            return cursor.lastrowid or 0
    
    def add_template(self, call_number: int, name: str, model: str, 
                     prompt_id: int, config: Optional[Dict[str, Any]] = None) -> int:
        """
        Add a new template linking call number to model + prompt.
        
        Args:
            call_number: Unique call number for config reference
            name: Descriptive name for the template
            model: Model name (e.g., "codegemma:latest")
            prompt_id: Reference to prompt in prompt_registry
            config: Optional LLM configuration parameters
            
        Returns:
            template_id of the created template
        """
        if config is None:
            config = {}
        
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO mb_template_registry 
                (call_number, name, model, prompt_id, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (call_number, name, model, prompt_id, json.dumps(config), now, now))
            return cursor.lastrowid or 0
    
    def get_template_by_call_number(self, call_number: int) -> Optional[TemplateRegistryEntry]:
        """Get template configuration by call number"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM mb_template_registry WHERE call_number = ? AND enabled = 1
            ''', (call_number,))
            row = cursor.fetchone()
            
            if row:
                return TemplateRegistryEntry(
                    template_id=row['template_id'],
                    call_number=row['call_number'],
                    name=row['name'],
                    model=row['model'],
                    prompt_id=row['prompt_id'],
                    config=json.loads(row['config']),
                    enabled=bool(row['enabled']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            return None
    
    def get_prompt_by_id(self, prompt_id: int) -> Optional[PromptRegistryEntry]:
        """Get prompt by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM prompt_registry WHERE prompt_id = ?
            ''', (prompt_id,))
            row = cursor.fetchone()
            
            if row:
                return PromptRegistryEntry(
                    prompt_id=row['prompt_id'],
                    name=row['name'],
                    description=row['description'],
                    content=row['content'],
                    version=row['version'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    tags=json.loads(row['tags']) if row['tags'] else [],
                    file_path=row['file_path']
                )
            return None
    
    def validate_llm_call(self, input_text: str, call_number: int) -> Tuple[bool, List[str]]:
        """
        MemBridge validation checks before LLM submission.
        
        xai's Requirements:
        - Input not too small/empty
        - No JSON output requests (use output templates instead)
        - Prompt/call compliance with recommendations
        - Call request validation before LLM submission
        
        Returns:
            (validation_passed, list_of_errors)
        """
        errors = []
        
        # Input validation
        if not input_text or input_text.strip() == "":
            errors.append("Input text is empty")
        elif len(input_text.strip()) < 10:
            errors.append("Input text too short (minimum 10 characters)")
        
        # Check for JSON output requests
        json_patterns = [
            r'\bjson\b',
            r'\{.*\}',
            r'return.*json',
            r'format.*json',
            r'output.*json'
        ]
        for pattern in json_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                errors.append("JSON output requests not allowed - use output templates instead")
                break
        
        # Template validation
        template = self.get_template_by_call_number(call_number)
        if not template:
            errors.append(f"Call number {call_number} not found in template registry")
        elif not template.enabled:
            errors.append(f"Template for call number {call_number} is disabled")
        
        # Model validation (basic check)
        if template and ':' not in template.model:
            errors.append(f"Model name '{template.model}' should include version (e.g., 'model:latest')")
        
        return len(errors) == 0, errors
    
    def log_call(self, call_number: int, input_text: str, output_text: str, 
                 model: str, success: bool, latency_ms: float, 
                 error_message: Optional[str] = None, validation_passed: bool = True,
                 validation_errors: Optional[List[str]] = None) -> int:
        """
        Log an LLM call transaction.
        
        Returns:
            log_id of the created log entry
        """
        if validation_errors is None:
            validation_errors = []
        
        # Get template ID
        template = self.get_template_by_call_number(call_number)
        template_id = template.template_id if template else 0
        
        # Create call log entry
        entry = CallLogEntry(
            log_id=0,  # Will be set by database
            call_number=call_number,
            template_id=template_id,
            input_text=input_text,
            output_text=output_text or "",
            model=model,
            success=success,
            latency_ms=latency_ms,
            timestamp=datetime.now(),
            error_message=error_message,
            validation_passed=validation_passed,
            validation_errors=validation_errors
        )
        
        now = entry.timestamp.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO mb_log 
                (call_number, template_id, input_text, output_text, model, success, 
                 latency_ms, timestamp, error_message, validation_passed, 
                 validation_errors, output_word_count, output_has_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                call_number, template_id, input_text, output_text, model, success,
                latency_ms, now, error_message, validation_passed,
                json.dumps(validation_errors), entry.output_word_count, entry.output_has_json
            ))
            return cursor.lastrowid or 0
    
    def get_recent_calls(self, limit: int = 100) -> List[CallLogEntry]:
        """Get recent call log entries for xai's simple table access"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM mb_log 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            entries = []
            for row in cursor.fetchall():
                entry = CallLogEntry(
                    log_id=row['log_id'],
                    call_number=row['call_number'],
                    template_id=row['template_id'],
                    input_text=row['input_text'],
                    output_text=row['output_text'],
                    model=row['model'],
                    success=bool(row['success']),
                    latency_ms=row['latency_ms'],
                    timestamp=row['timestamp'],
                    error_message=row['error_message'],
                    validation_passed=bool(row['validation_passed']),
                    validation_errors=json.loads(row['validation_errors']) if row['validation_errors'] else []
                )
                entry.output_word_count = row['output_word_count']
                entry.output_has_json = bool(row['output_has_json'])
                entries.append(entry)
            
            return entries
    
    def get_all_templates(self) -> List[TemplateRegistryEntry]:
        """Get all templates for xai's simple table access"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM mb_template_registry ORDER BY call_number')
            
            templates = []
            for row in cursor.fetchall():
                template = TemplateRegistryEntry(
                    template_id=row['template_id'],
                    call_number=row['call_number'],
                    name=row['name'],
                    model=row['model'],
                    prompt_id=row['prompt_id'],
                    config=json.loads(row['config']),
                    enabled=bool(row['enabled']),
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                templates.append(template)
            
            return templates
    
    def get_all_prompts(self) -> List[PromptRegistryEntry]:
        """Get all prompts for xai's simple table access"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM prompt_registry ORDER BY name')
            
            prompts = []
            for row in cursor.fetchall():
                prompt = PromptRegistryEntry(
                    prompt_id=row['prompt_id'],
                    name=row['name'],
                    description=row['description'],
                    content=row['content'],
                    version=row['version'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    tags=json.loads(row['tags']) if row['tags'] else [],
                    file_path=row['file_path']
                )
                prompts.append(prompt)
            
            return prompts


class ConfigDrivenLLMCall:
    """
    Config-driven LLM call interface for ty_extract integration.
    
    Usage:
        caller = ConfigDrivenLLMCall(registry_system)
        result = caller.call_llm(call_number=1, input_text="CV content here")
    """
    
    def __init__(self, registry: RegistrySystem):
        self.registry = registry
    
    def call_llm(self, call_number: int, input_text: str, 
                 llm_function: Optional[Callable[..., str]] = None) -> Dict[str, Any]:
        """
        Make a config-driven LLM call.
        
        Args:
            call_number: Call number from config
            input_text: Input text for the LLM
            llm_function: Function to call LLM (for testing/mocking)
            
        Returns:
            {
                'success': bool,
                'output': str,
                'error': str,
                'latency_ms': float,
                'validation_passed': bool,
                'validation_errors': List[str],
                'template_used': str,
                'model_used': str
            }
        """
        start_time = datetime.now()
        
        # Validation
        validation_passed, validation_errors = self.registry.validate_llm_call(
            input_text, call_number
        )
        
        if not validation_passed:
            # Log failed validation
            self.registry.log_call(
                call_number=call_number,
                input_text=input_text,
                output_text="",
                model="validation_failed",
                success=False,
                latency_ms=0,
                error_message="Validation failed",
                validation_passed=False,
                validation_errors=validation_errors
            )
            
            return {
                'success': False,
                'output': '',
                'error': 'Validation failed: ' + '; '.join(validation_errors),
                'latency_ms': 0,
                'validation_passed': False,
                'validation_errors': validation_errors,
                'template_used': '',
                'model_used': ''
            }
        
        # Get template and prompt
        template = self.registry.get_template_by_call_number(call_number)
        if not template:
            error_msg = f"Template not found for call number {call_number}"
            self.registry.log_call(
                call_number=call_number,
                input_text=input_text,
                output_text="",
                model="unknown",
                success=False,
                latency_ms=0,
                error_message=error_msg
            )
            return {
                'success': False,
                'output': '',
                'error': error_msg,
                'latency_ms': 0,
                'validation_passed': True,
                'validation_errors': [],
                'template_used': '',
                'model_used': ''
            }
        
        prompt_entry = self.registry.get_prompt_by_id(template.prompt_id)
        if not prompt_entry:
            error_msg = f"Prompt not found for prompt_id {template.prompt_id}"
            self.registry.log_call(
                call_number=call_number,
                input_text=input_text,
                output_text="",
                model=template.model,
                success=False,
                latency_ms=0,
                error_message=error_msg
            )
            return {
                'success': False,
                'output': '',
                'error': error_msg,
                'latency_ms': 0,
                'validation_passed': True,
                'validation_errors': [],
                'template_used': template.name,
                'model_used': template.model
            }
        
        # Prepare full prompt
        full_prompt = prompt_entry.content + "\n\n" + input_text
        
        # Make LLM call (placeholder - will integrate with actual LLM in Phase 2)
        if llm_function:
            try:
                output = llm_function(full_prompt, template.model, template.config)
                success = True
                error_message = None
            except Exception as e:
                output = ""
                success = False
                error_message = str(e)
        else:
            # Placeholder response for Phase 1 testing
            output = f"[PLACEHOLDER] Processed with {template.model} using prompt '{prompt_entry.name}'"
            success = True
            error_message = None
        
        # Calculate latency
        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # Log the call
        self.registry.log_call(
            call_number=call_number,
            input_text=input_text,
            output_text=output,
            model=template.model,
            success=success,
            latency_ms=latency_ms,
            error_message=error_message
        )
        
        return {
            'success': success,
            'output': output,
            'error': error_message or '',
            'latency_ms': latency_ms,
            'validation_passed': True,
            'validation_errors': [],
            'template_used': template.name,
            'model_used': template.model
        }
