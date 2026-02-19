"""
Executors - AI models, scripts, and human actors
Author: Sandy (GitHub Copilot)
Date: November 23, 2025
Target: <100 lines
"""

import os
import subprocess
import json
import logging
import time
import psycopg2.extras
from typing import Dict, Any, Optional
from datetime import datetime


class AIModelExecutor:
    """Execute AI model actors via Ollama CLI (matches core/actor_router.py pattern)"""
    
    def __init__(self, db_helper=None, logger=None):
        self.db_helper = db_helper
        self.logger = logger or logging.getLogger(__name__)
        self.timeout = 600  # 10 minute timeout
    
    def _build_ai_prompt(
        self, 
        interaction: Dict[str, Any]
    ) -> str:
        """
        Build AI prompt by querying database (conversation-aware).
        
        CRITICAL ARCHITECTURE: The interactions table IS your template engine!
        Query parent outputs instead of string substitution.
        
        Why NO templates:
        - Template substitution breaks when workflow spans multiple waves
        - In-memory state (posting.outputs dict) lost between waves
        - Database (interactions table) is ALWAYS reliable
        - Proven bug: 122 hallucinated summaries from template substitution
        
        Reference:
        - docs/archive/debugging_sessions/TEMPLATE_SUBSTITUTION_BUG.md
        - docs/SCRIPT_ACTOR_COOKBOOK.md (lines 700-800)
        
        Args:
            interaction: Current interaction dict (with posting_id, conversation_id, etc.)
            
        Returns:
            Prompt string ready for AI model
            
        Raises:
            ValueError: If conversation_id not recognized
        """
        if not self.db_helper:
            raise RuntimeError("AIModelExecutor requires db_helper for prompt building")
        
        conv_id = interaction['conversation_id']
        posting_id = interaction.get('posting_id')  # Can be None for global workflows
        interaction_id = interaction['interaction_id']
        
        # 1. Get prompt template from database (NO hardcoded prompts!)
        prompt_template = self.db_helper.get_instruction_prompt(conv_id)
        if not prompt_template:
            raise ValueError(f"No instruction prompt found for conversation {conv_id}")
        
        # 2. Get posting data (optional - global workflows don't have postings)
        posting = {}
        if posting_id:
            posting = self.db_helper.get_posting_data(posting_id) or {}
        
        # 3. Get parent interaction outputs
        parents = self.db_helper.get_parent_interaction_outputs(interaction_id)
        
        # 3b. Load workflow state (semantic keys) - CRITICAL FIX Nov 25!
        workflow_state = {}
        workflow_run_id = interaction.get('workflow_run_id')
        if workflow_run_id:
            workflow_state = self.db_helper.get_workflow_state(workflow_run_id)
        
        # 3c. Get profile data if workflow_run metadata has profile_id (WF1122)
        profile_raw_text = ''
        if workflow_run_id and self.db_helper:
            cursor = self.db_helper.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                SELECT p.profile_raw_text
                FROM workflow_runs wr
                JOIN profiles p ON (wr.metadata->>'profile_id')::int = p.profile_id
                WHERE wr.workflow_run_id = %s
            """, (workflow_run_id,))
            row = cursor.fetchone()
            if row and row.get('profile_raw_text'):
                profile_raw_text = row['profile_raw_text']
            cursor.close()
        
        # 4. Build variable mapping for template substitution
        # Map template variables to actual data from database
        variables = {
            # Posting data (empty strings if no posting - global workflows)
            'job_description': posting.get('job_description', ''),
            'job_title': posting.get('job_title', ''),
            'posting_id': str(posting_id) if posting_id else '',
            'location_city': posting.get('location_city', ''),
            'location_country': posting.get('location_country', ''),
            'extracted_summary': posting.get('extracted_summary', ''),  # For skills extraction!
            
            # Profile data (for WF1122 and profile workflows)
            'profile_raw_text': profile_raw_text,
            
            # Legacy template variables (some instructions use these)
            'variations_param_1': posting.get('job_description', ''),
            'variations_param_2': posting.get('job_title', ''),
            'variations_param_3': posting.get('location_city', ''),
            
            # Workflow state (semantic keys) - PREFERRED for new templates
            'extract_summary': workflow_state.get('extract_summary', ''),
            'improved_summary': workflow_state.get('improved_summary', ''),
            'current_summary': workflow_state.get('current_summary', ''),
            'extracted_skills': workflow_state.get('extracted_skills', ''),
            'ihl_analyst_verdict': workflow_state.get('ihl_analyst_verdict', ''),
            'ihl_skeptic_verdict': workflow_state.get('ihl_skeptic_verdict', ''),
        }
        
        # 4b. DYNAMIC parent output extraction (replaces hardcoded mappings)
        # This generates conversation_XXXX_output automatically for ANY workflow
        # See: docs/archive/debugging_sessions/TEMPLATE_SUBSTITUTION_BUG.md
        for conv_id, parent_output in parents.items():
            if isinstance(parent_output, dict):
                # AI actor outputs have 'response' key
                response = parent_output.get('response', '')
                
                # Generate conversation_XXXX_output pattern
                variables[f'conversation_{conv_id}_output'] = response
                
                # Also extract all other keys from script outputs
                for key, value in parent_output.items():
                    if key not in ('response', 'model', 'latency_ms') and isinstance(value, (str, int, float)):
                        if key not in variables:
                            variables[key] = str(value)
        
        # 4c. Generate session_X_output patterns based on parent order
        parent_list = list(parents.items())
        for idx, (conv_id, parent_output) in enumerate(parent_list, start=1):
            if isinstance(parent_output, dict):
                response = parent_output.get('response', '')
                variables[f'session_{idx}_output'] = response
        
        # 4d. Set parent_response to the LAST parent's response (most common use case)
        # Templates that use {parent_response} expect the immediate parent's output
        if parent_list:
            last_conv_id, last_parent_output = parent_list[-1]
            if isinstance(last_parent_output, dict):
                # For AI actors, use 'response' key; for scripts, stringify the whole output
                if 'response' in last_parent_output:
                    variables['parent_response'] = last_parent_output['response']
                else:
                    import json
                    variables['parent_response'] = json.dumps(last_parent_output)
        
        # 5a. Add skill context from interaction input (WF3002 - Skill Taxonomy Maintenance)
        input_data = interaction.get('input') or {}
        if 'raw_skill_name' in input_data:
            variables['raw_skill_name'] = input_data.get('raw_skill_name', '')
            variables['skill_key'] = input_data.get('skill_key', '')
            variables['count'] = str(input_data.get('count', 0))
            variables['example_posting_ids'] = str(input_data.get('example_posting_ids', []))
        
        # 5. Substitute variables in template
        # Simple string replacement - database template is the source of truth
        prompt = prompt_template
        for var_name, var_value in variables.items():
            placeholder = '{' + var_name + '}'
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(var_value))
        
        return prompt
    
    def execute(
        self, 
        model_name: str, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = None,
        seed: int = None
    ) -> Dict[str, Any]:
        """
        Execute AI model via Ollama HTTP API.
        
        Uses HTTP API instead of CLI to support temperature/seed for determinism.
        
        Args:
            model_name: Model to use (e.g., 'qwen2.5:7b')
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Model temperature (0.0 = deterministic)
            seed: Random seed for reproducibility
            
        Returns:
            {'response': str, 'latency_ms': int, 'model': str}
        """
        import requests
        
        try:
            start_time = time.time()
            
            # Debug logging
            self.logger.info(f"Calling Ollama API with model={model_name}, temp={temperature}, seed={seed}, prompt_len={len(prompt)}")
            self.logger.debug(f"Prompt preview: {prompt[:200]}...")
            
            # Build request payload for Ollama HTTP API
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False  # Get complete response
            }
            
            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt
            
            # Add options for temperature/seed (critical for determinism!)
            options = {}
            if temperature is not None:
                options["temperature"] = float(temperature)
            if seed is not None:
                options["seed"] = int(seed)
            if options:
                payload["options"] = options
            
            # Call Ollama HTTP API
            response = requests.post(
                os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate',
                json=payload,
                timeout=self.timeout
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Check for errors
            if response.status_code != 200:
                error_msg = f"Ollama API failed (status {response.status_code}): {response.text[:500]}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Parse response
            try:
                result = response.json()
            except ValueError as e:
                raise RuntimeError(f"Ollama returned invalid JSON: {response.text[:200]}")
            
            response_text = result.get("response", "")
            
            # Check for empty response (model error)
            if not response_text and result.get("error"):
                raise RuntimeError(f"Ollama model error: {result.get('error')}")
            
            # Success
            return {
                'response': response_text.strip(),
                'latency_ms': latency_ms,
                'model': model_name
            }
            
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Model {model_name} timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Ollama API not available - is Ollama running?")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {str(e)}")


class ScriptExecutor:
    """Execute script actors via subprocess."""
    
    # Default timeout for script actors (can be overridden via execution_config.timeout)
    DEFAULT_TIMEOUT = 300  # 5 minutes
    
    def execute(
        self, 
        script_path: str, 
        input_data: Dict[str, Any],
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Execute script actor (stdin/stdout JSON contract).
        
        Pattern from SCRIPT_ACTOR_COOKBOOK.md:
        - Input: JSON via stdin
        - Output: JSON via stdout
        - Errors: stderr + non-zero exit code
        
        Args:
            script_path: Absolute path to script
            input_data: Input to pass via stdin
            
        Returns:
            Script output (parsed from stdout JSON)
            
        Raises:
            RuntimeError: If script fails or returns invalid JSON
        """
        try:
            # Set PYTHONPATH to include workspace root for core imports
            import os
            env = os.environ.copy()
            workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            env['PYTHONPATH'] = workspace_root + ':' + env.get('PYTHONPATH', '')
            
            result = subprocess.run(
                ['python3', script_path],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=timeout or self.DEFAULT_TIMEOUT,
                check=True,
                env=env  # Pass environment with PYTHONPATH
            )
            
            # Parse JSON output from stdout
            output = json.loads(result.stdout)
            return output
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Script failed with exit code {e.returncode}: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Script returned invalid JSON: {e}\nStdout was: {repr(result.stdout[:200])}")
        except subprocess.TimeoutExpired:
            actual_timeout = timeout or self.DEFAULT_TIMEOUT
            raise RuntimeError(f"Script execution timed out ({actual_timeout}s)")


class HumanExecutor:
    """Execute human actors (placeholder for manual approval)."""
    
    def execute(self, task_description: str) -> Dict[str, Any]:
        """
        Create human task (to be completed manually).
        
        For Phase 1, this just marks the interaction as 'pending'
        and waits for manual intervention.
        
        Args:
            task_description: Human-readable task description
            
        Returns:
            {'status': 'awaiting_human', 'task': str}
        """
        return {
            'status': 'awaiting_human',
            'task': task_description,
            'message': 'This interaction requires human approval/action'
        }
