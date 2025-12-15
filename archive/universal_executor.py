#!/usr/bin/env python3
"""
Universal Actor Executor - Calls any actor based on execution registry

Uses actors table as "phone book" to determine HOW to execute each actor.
Supports: Ollama AI models, HTTP APIs, Python scripts, Bash scripts, Human input
"""

import json
import subprocess
import requests
import psycopg2
from typing import Dict, Any, Optional
import sys
import uuid
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

class UniversalExecutor:
    """Execute any actor based on execution registry in actors table"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
    
    def get_job_description(self, job_id: str) -> Optional[str]:
        """Fetch job description from postings table"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT job_description FROM postings WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            return row[0] if row else None
    
    def get_actor(self, actor_id: str) -> Dict[str, Any]:
        """Look up actor execution details from registry"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT actor_id, actor_type, execution_type, execution_path, 
                       url, execution_config, enabled
                FROM actors
                WHERE actor_id = %s
            """, (actor_id,))
            
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Actor '{actor_id}' not found in registry")
            
            return {
                'actor_id': row[0],
                'actor_type': row[1],
                'execution_type': row[2],
                'execution_path': row[3],
                'url': row[4],
                'execution_config': row[5] or {},
                'enabled': row[6]
            }
    
    def call_actor(self, actor_id: str, prompt: str, context: Optional[Dict] = None) -> str:
        """
        Universal actor caller - routes to appropriate executor.
        
        Args:
            actor_id: ID of actor to execute
            prompt: The prompt/instruction to send
            context: Additional context data
        
        Returns:
            Response from actor as string
        """
        actor = self.get_actor(actor_id)
        
        if not actor['enabled']:
            raise ValueError(f"Actor '{actor_id}' is disabled")
        
        config = actor['execution_config']
        
        # Route to appropriate executor
        if actor['execution_type'] == 'ollama_api':
            return self.execute_ollama(actor, prompt, config)
        
        elif actor['execution_type'] == 'http_api':
            return self.execute_http_api(actor, prompt, context, config)
        
        elif actor['execution_type'] == 'python_script':
            return self.execute_python_script(actor, prompt, context, config)
        
        elif actor['execution_type'] == 'bash_script':
            return self.execute_bash_script(actor, prompt, context, config)
        
        elif actor['execution_type'] == 'human_input':
            return self.request_human_input(actor, prompt, config)
        
        else:
            raise ValueError(f"Unknown execution_type: {actor['execution_type']}")
    
    def execute_ollama(self, actor: Dict, prompt: str, config: Dict) -> str:
        """Execute Ollama AI model via HTTP API"""
        payload = {
            'model': actor['execution_path'],  # Model name (e.g., 'phi3:latest')
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': config.get('temperature', 0.7),
                'num_predict': config.get('max_tokens', 4096)
            }
        }
        
        timeout = config.get('timeout_seconds', 120)
        
        try:
            response = requests.post(actor['url'], json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()['response']
        except Exception as e:
            raise RuntimeError(f"Ollama execution failed: {e}")
    
    def execute_http_api(self, actor: Dict, prompt: str, context: Optional[Dict], config: Dict) -> str:
        """Execute HTTP API (e.g., Flask-wrapped services)"""
        payload = {
            'prompt': prompt,
            **(context or {})
        }
        
        timeout = config.get('timeout_seconds', 300)
        retry_count = config.get('retry_count', 1)
        
        for attempt in range(retry_count):
            try:
                response = requests.post(
                    actor['execution_path'],  # Full endpoint URL
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
                
                # Return JSON or text response
                try:
                    return json.dumps(response.json())
                except:
                    return response.text
                    
            except Exception as e:
                if attempt < retry_count - 1:
                    import time
                    time.sleep(config.get('retry_delay_seconds', 2))
                    continue
                raise RuntimeError(f"HTTP API execution failed: {e}")
    
    def execute_python_script(self, actor: Dict, prompt: str, context: Optional[Dict], config: Dict) -> str:
        """Execute Python script via subprocess with JSON input"""
        script_path = actor['execution_path']
        
        # Prepare input as JSON
        input_data = {
            'prompt': prompt,
            'context': context or {},
            'config': config
        }
        
        timeout = config.get('timeout_seconds', 300)
        
        try:
            result = subprocess.run(
                ['python3', script_path, '--json-input'],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Script failed with code {result.returncode}: {result.stderr}")
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Script execution timeout after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Script execution failed: {e}")
    
    def execute_bash_script(self, actor: Dict, prompt: str, context: Optional[Dict], config: Dict) -> str:
        """Execute bash script via subprocess"""
        script_path = actor['execution_path']
        timeout = config.get('timeout_seconds', 60)
        
        try:
            # Pass prompt as stdin
            result = subprocess.run(
                [script_path],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Script failed: {result.stderr}")
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Script timeout after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Script execution failed: {e}")
    
    def request_human_input(self, actor: Dict, prompt: str, config: Dict) -> str:
        """Queue task for human review"""
        task_id = str(uuid.uuid4())
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO human_tasks (task_id, actor_id, prompt, status, created_at)
                VALUES (%s, %s, %s, 'PENDING', NOW())
            """, (task_id, actor['actor_id'], prompt))
            self.conn.commit()
        
        # TODO: Send email notification if configured
        if 'notification_email' in config:
            print(f"📧 Would send email to: {config['notification_email']}")
        
        return f"HUMAN_TASK_QUEUED:{task_id}"
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """CLI test interface"""
    if len(sys.argv) < 3:
        print("Usage: python3 universal_executor.py <actor_id> <prompt>")
        print("\nExample:")
        print("  python3 universal_executor.py skill_gopher 'Extract skills from: Senior Python Dev'")
        print("  python3 universal_executor.py phi3:latest 'Summarize: Machine learning basics'")
        sys.exit(1)
    
    actor_id = sys.argv[1]
    prompt = sys.argv[2]
    
    executor = UniversalExecutor()
    
    try:
        print(f"🤖 Calling actor: {actor_id}")
        print(f"📝 Prompt: {prompt[:100]}...")
        print("-" * 80)
        
        response = executor.call_actor(actor_id, prompt, context={})
        
        print("\n✅ Response:")
        print(response)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        executor.close()


if __name__ == "__main__":
    main()
