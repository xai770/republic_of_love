#!/usr/bin/env python3
"""
Continuous Recipe Runner - Maintains LLM Context Across Sessions

This runner executes recipes with maintain_llm_context=1 using Ollama's /api/chat
endpoint, preserving conversation history across multiple sessions for intelligent
multi-turn interactions.
"""

import sqlite3
import requests
import json
import sys
import time
from datetime import datetime

OLLAMA_API = "http://localhost:11434/api/chat"

class ContinuousRecipeRunner:
    def __init__(self, db_path='data/llmcore.db'):
        self.db_path = db_path
        self.conversation_history = []
        
    def execute_recipe(self, recipe_id, variation_id=None):
        """Execute a recipe with continuous context support"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get recipe info
            cursor.execute("SELECT canonical_code, review_notes FROM recipes WHERE recipe_id = ?", (recipe_id,))
            recipe_row = cursor.fetchone()
            if not recipe_row:
                print(f"❌ Recipe {recipe_id} not found")
                return False
            
            recipe_code, recipe_notes = recipe_row
            print(f"🚀 Executing Recipe {recipe_id}: {recipe_code}")
            print(f"   {recipe_notes}")
            print("=" * 70)
            print()
            
            # Get variation data if provided
            variation_data = {}
            if variation_id:
                cursor.execute("SELECT variations_param_1 FROM variations WHERE variation_id = ?", (variation_id,))
                var_row = cursor.fetchone()
                if var_row and var_row[0]:
                    try:
                        variation_data = json.loads(var_row[0])
                        print(f"📋 Loaded variation {variation_id}")
                        print(f"   Parameters: {list(variation_data.keys())}\n")
                    except:
                        pass
            
            self.variation_data = variation_data  # Store for template rendering
            
            # Create recipe_run
            batch_id = f"continuous_test_{int(time.time())}"
            cursor.execute("""
                INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status, started_at)
                VALUES (?, ?, ?, 'RUNNING', datetime('now'))
            """, (recipe_id, variation_id, batch_id))
            recipe_run_id = cursor.lastrowid
            conn.commit()
            
            print(f"📋 Recipe Run {recipe_run_id} created (batch: {batch_id})\n")
            
            # Get all sessions in order
            cursor.execute("""
                SELECT s.session_id, s.session_number, s.session_name, s.actor_id, a.actor_type,
                       s.context_strategy, s.maintain_llm_context, s.depends_on_session_id
                FROM sessions s
                LEFT JOIN actors a ON s.actor_id = a.actor_id
                WHERE s.recipe_id = ? AND s.enabled = 1
                ORDER BY s.execution_order
            """, (recipe_id,))
            
            sessions = cursor.fetchall()
            
            for session in sessions:
                session_id, num, name, actor_id, actor_type, strategy, maintain, depends = session
                
                success = self._execute_session(
                    cursor, recipe_run_id, session_id, num, name, 
                    actor_id, actor_type, strategy, maintain, depends
                )
                
                if not success:
                    print(f"\n❌ Session {num} failed, aborting recipe")
                    cursor.execute("""
                        UPDATE recipe_runs 
                        SET status = 'FAILED', completed_at = datetime('now')
                        WHERE recipe_run_id = ?
                    """, (recipe_run_id,))
                    conn.commit()
                    return False
                
                conn.commit()
            
            # Mark recipe as successful
            cursor.execute("""
                UPDATE recipe_runs 
                SET status = 'SUCCESS', completed_at = datetime('now')
                WHERE recipe_run_id = ?
            """, (recipe_run_id,))
            conn.commit()
            
            print("\n" + "=" * 70)
            print(f"✅ Recipe {recipe_id} completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Error executing recipe: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            conn.close()
    
    def _execute_session(self, cursor, recipe_run_id, session_id, num, name, 
                        actor_id, actor_type, strategy, maintain, depends):
        """Execute a single session"""
        
        print(f"{'━' * 70}")
        print(f"Session {num}: {name}")
        print(f"Actor: {actor_id} ({actor_type})")
        print(f"Strategy: {strategy}")
        if maintain:
            print(f"Context: CONTINUOUS (conversation history preserved)")
        else:
            print(f"Context: ISOLATED (new conversation)")
            self.conversation_history = []  # Reset for isolated sessions
        print(f"{'━' * 70}\n")
        
        # Create session_run
        cursor.execute("""
            INSERT INTO session_runs (recipe_run_id, session_id, session_number, status, started_at)
            VALUES (?, ?, ?, 'RUNNING', datetime('now'))
        """, (recipe_run_id, session_id, num))
        session_run_id = cursor.lastrowid
        
        # Commit immediately so scripts can see this session_run
        cursor.connection.commit()
        
        if actor_type in ('llm', 'ai_model'):
            success = self._execute_llm_session(cursor, session_run_id, session_id, actor_id)
        elif actor_type == 'script':
            success = self._execute_script_session(cursor, session_run_id, session_id, actor_id)
        else:
            print(f"❌ Unknown actor type: {actor_type}")
            success = False
        
        # Update session_run status
        status = 'SUCCESS' if success else 'FAILED'
        cursor.execute("""
            UPDATE session_runs 
            SET status = ?, completed_at = datetime('now')
            WHERE session_run_id = ?
        """, (status, session_run_id))
        
        return success
    
    def _execute_llm_session(self, cursor, session_run_id, session_id, actor_id):
        """Execute LLM session using Ollama /api/chat"""
        
        # Get instruction
        cursor.execute("""
            SELECT instruction_id, step_number, step_description, prompt_template
            FROM instructions
            WHERE session_id = ? AND enabled = 1
            ORDER BY step_number
            LIMIT 1
        """, (session_id,))
        
        instruction_row = cursor.fetchone()
        if not instruction_row:
            print("⚠️  No instruction found for session")
            return True  # Not an error, just empty session
        
        instruction_id, step_num, step_desc, prompt_template = instruction_row
        
        print(f"📝 Instruction: {step_desc}")
        
        # Render template with variation data
        rendered_prompt = prompt_template
        if hasattr(self, 'variation_data') and self.variation_data:
            try:
                rendered_prompt = prompt_template.format(**self.variation_data)
                print(f"\n✓ Template rendered with variation data")
            except KeyError as e:
                print(f"\n⚠️  Template key not found in variation: {e}")
                print(f"   Using template as-is")
        
        print(f"\nPrompt Preview:")
        print(f"   {rendered_prompt[:150]}...")
        print()
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": rendered_prompt
        })
        
        # Create instruction_run
        cursor.execute("""
            INSERT INTO instruction_runs (
                session_run_id, recipe_run_id, instruction_id, step_number,
                prompt_rendered, status
            ) VALUES (?, (SELECT recipe_run_id FROM session_runs WHERE session_run_id = ?), 
                     ?, ?, ?, 'RUNNING')
        """, (session_run_id, session_run_id, instruction_id, step_num, rendered_prompt))
        instruction_run_id = cursor.lastrowid
        
        start_time = time.time()
        
        try:
            # Call Ollama API with conversation history
            print(f"🤖 Calling {actor_id} (conversation has {len(self.conversation_history)} messages)...\n")
            
            response = requests.post(OLLAMA_API, json={
                "model": actor_id,
                "messages": self.conversation_history,
                "stream": False
            }, timeout=300)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result["message"]["content"]
                
                # Add assistant response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                
                print(f"💬 Response ({latency_ms}ms):")
                print(f"{'─' * 70}")
                print(assistant_message)
                print(f"{'─' * 70}\n")
                
                # Update instruction_run
                cursor.execute("""
                    UPDATE instruction_runs
                    SET response_received = ?,
                        latency_ms = ?,
                        status = 'SUCCESS'
                    WHERE instruction_run_id = ?
                """, (assistant_message, latency_ms, instruction_run_id))
                
                # Store response in session_runs for scripts to access
                cursor.execute("""
                    UPDATE session_runs
                    SET session_output = ?
                    WHERE session_run_id = ?
                """, (assistant_message, session_run_id))
                
                return True
            else:
                print(f"❌ Ollama API error: {response.status_code}")
                print(response.text)
                
                cursor.execute("""
                    UPDATE instruction_runs
                    SET status = 'FAILED'
                    WHERE instruction_run_id = ?
                """, (instruction_run_id,))
                
                return False
                
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            import traceback
            traceback.print_exc()
            
            cursor.execute("""
                UPDATE instruction_runs
                SET status = 'FAILED'
                WHERE instruction_run_id = ?
            """, (instruction_run_id,))
            
            return False
    
    def _execute_script_session(self, cursor, session_run_id, session_id, actor_id):
        """Execute script session"""
        import subprocess
        
        # Get script URL from actors table
        cursor.execute("SELECT url FROM actors WHERE actor_id = ?", (actor_id,))
        script_row = cursor.fetchone()
        if not script_row:
            print(f"❌ Script actor {actor_id} not found in actors table")
            return False
        
        script_path = script_row[0]
        
        print(f"🔧 Executing script: {script_path}")
        print(f"   Session run ID: {session_run_id}\n")
        
        try:
            # Execute the script
            result = subprocess.run(
                ['python3', script_path, str(session_run_id)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            print(result.stdout)
            
            if result.returncode == 0:
                print("✅ Script completed successfully\n")
                return True
            else:
                print(f"❌ Script failed with exit code {result.returncode}")
                if result.stderr:
                    print(f"Error output:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Script execution timeout (60s)")
            return False
        except Exception as e:
            print(f"❌ Error executing script: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_continuous_recipe.py <recipe_id> [variation_id]")
        print()
        print("Example: python3 run_continuous_recipe.py 1118")
        sys.exit(1)
    
    recipe_id = int(sys.argv[1])
    variation_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    runner = ContinuousRecipeRunner()
    success = runner.execute_recipe(recipe_id, variation_id)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
