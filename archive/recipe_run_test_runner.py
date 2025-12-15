#!/usr/bin/env python3
"""
LLMCore V3.1 Session-Aware Recipe Test Runner
=============================================
⚠️  PLACEHOLDER FOR V3.1 SESSION ARCHITECTURE ⚠️

This is a temporary placeholder. The original recipe runner was designed for
the V3.0 schema where instructions belonged directly to recipes. 

V3.1 introduces session-based architecture:
- recipes → sessions → instructions
- actors assigned at session level
- session_runs → instruction_runs execution model

TODO: Rebuild this runner to support:
1. Session-based execution (not direct instruction execution)
2. Session context management and dependency handling
3. Actor inheritance from sessions to instructions
4. Branch execution tracking in instruction_branch_executions table
5. Progress callbacks for GUI integration
"""

import sqlite3
import subprocess
import time
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

class RecipeRunTestRunner:
    def __init__(self, db_path: str = "/home/xai/Documents/ty_learn/data/llmcore.db"):
        self.db_path = db_path
        self.ollama_timeout = 300  # 5 minutes per instruction
        self.recipe_runs_completed = 0
        self.start_time = None
        
        # V3.1 Session Architecture Support (TODO)
        self.session_context = {}  # Maintain context between sessions
        self.progress_callback = None  # For GUI progress updates
        
    def execute_recipe_with_progress(self, recipe_id: int, variation_id: int, batch_id: int, 
                                   progress_callback: Optional[Callable[[float, str], None]] = None) -> Dict[str, Any]:
        """
        V3.1 Session-Aware Recipe Execution (PLACEHOLDER)
        
        This method will replace the old execute_recipe_run() to support:
        - Session-based execution workflow
        - Progress callbacks for GUI integration
        - Session context management
        - Branch execution tracking
        
        Returns:
            {
                'status': 'SUCCESS' | 'FAILED' | 'RUNNING',
                'recipe_run_id': int,
                'error': str (if failed),
                'sessions_completed': int,
                'total_sessions': int
            }
        """
        # TODO: Implement V3.1 session-aware execution
        # For now, return a placeholder response
        return {
            'status': 'FAILED',
            'recipe_run_id': None,
            'error': 'V3.1 session architecture not yet implemented',
            'sessions_completed': 0,
            'total_sessions': 0
        }
    
    def get_next_incomplete_recipe_run(self) -> Optional[Dict[str, Any]]:
        """
        Get next recipe_run that needs execution
        
        ⚠️  TODO: Update for V3.1 session architecture
        - Check session_runs table for incomplete sessions
        - Handle session dependencies (depends_on_session_id)
        - Return session-aware execution context
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # TODO: V3.1 - Update query to use session-based execution model
            # This query is V3.0 legacy - needs session_runs integration
            cursor.execute("""
                SELECT 
                    rr.recipe_run_id,
                    rr.recipe_id,
                    rr.variation_id,
                    rr.batch_id,
                    rr.status,
                    rr.completed_steps,
                    rr.total_steps,
                    r.canonical_code,
                    v.variations_param_1 as test_input,
                    v.difficulty_level
                FROM recipe_runs rr
                JOIN recipes r ON rr.recipe_id = r.recipe_id
                JOIN variations v ON rr.variation_id = v.variation_id
                WHERE rr.status IN ('RUNNING', 'PENDING')
                -- TODO: Add session_runs JOIN and dependency checking
                ORDER BY rr.recipe_run_id
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'recipe_run_id': result[0],
                    'recipe_id': result[1],
                    'variation_id': result[2],
                    'batch_id': result[3],
                    'status': result[4],
                    'completed_steps': result[5],
                    'total_steps': result[6],
                    'canonical_code': result[7],
                    'test_input': result[8],
                    'difficulty_level': result[9]
                }
            return None
            
        except Exception as e:
            print(f"Error getting next recipe run: {e}")
            return None
    
    def get_recipe_instructions(self, recipe_id: int) -> List[Dict[str, Any]]:
        """Get all instructions for a recipe ordered by step_number"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    instruction_id,
                    step_number,
                    step_description,
                    prompt_template,
                    actor_id,
                    timeout_seconds,
                    expected_runtime_seconds
                FROM instructions
                WHERE recipe_id = ? AND enabled = 1
                ORDER BY step_number
            """, (recipe_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'instruction_id': row[0],
                    'step_number': row[1],
                    'step_description': row[2],
                    'prompt_template': row[3],
                    'actor_id': row[4],
                    'timeout_seconds': row[5] or self.ollama_timeout,
                    'expected_runtime_seconds': row[6]
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"Error getting recipe instructions: {e}")
            return []
    
    def get_completed_instruction_runs(self, recipe_run_id: int) -> Dict[int, Dict[str, Any]]:
        """Get completed instruction runs for parameter passing"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    ir.step_number,
                    ir.prompt_rendered,
                    ir.response_received,
                    ir.status,
                    i.step_description
                FROM instruction_runs ir
                JOIN instructions i ON ir.instruction_id = i.instruction_id
                WHERE ir.recipe_run_id = ? AND ir.status = 'SUCCESS'
                ORDER BY ir.step_number
            """, (recipe_run_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return {
                row[0]: {  # step_number as key
                    'prompt': row[1],
                    'response': row[2],
                    'status': row[3],
                    'description': row[4]
                }
                for row in results
            }
            
        except Exception as e:
            print(f"Error getting completed instruction runs: {e}")
            return {}
    
    def render_prompt_with_parameters(self, template: str, test_input: str, 
                                    completed_steps: Dict[int, Dict[str, Any]]) -> str:
        """Render prompt template with test input and previous step outputs"""
        rendered = template
        
        # Replace basic payload parameters
        rendered = rendered.replace('{{payload}}', test_input)
        rendered = rendered.replace('{payload}', test_input)
        
        # Replace step-specific parameters
        for step_num, step_data in completed_steps.items():
            step_prompt_var = f'{{step{step_num}_prompt}}'
            step_response_var = f'{{step{step_num}_response}}'
            
            rendered = rendered.replace(step_prompt_var, step_data.get('prompt', ''))
            rendered = rendered.replace(step_response_var, step_data.get('response', ''))
        
        # Handle any remaining single placeholders with test_input
        import re
        remaining_placeholders = re.findall(r'\{([^}]+)\}', rendered)
        for placeholder in remaining_placeholders:
            if not placeholder.startswith('step') and placeholder != 'payload':
                rendered = rendered.replace(f'{{{placeholder}}}', test_input)
        
        return rendered
    
    def get_actor_info(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get actor information for execution"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT domain, url, enabled
                FROM actors
                WHERE actor_id = ? AND enabled = 1
            """, (actor_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'actor_id': actor_id,
                    'domain': result[0],
                    'url': result[1],
                    'enabled': result[2]
                }
            return None
            
        except Exception as e:
            print(f"Error getting actor info: {e}")
            return None
    
    def execute_ai_instruction(self, actor_id: str, prompt: str, timeout: int) -> Dict[str, Any]:
        """Execute instruction with AI actor via Ollama"""
        try:
            start = time.time()
            
            result = subprocess.run(
                ['ollama', 'run', actor_id, prompt],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            elapsed_ms = int((time.time() - start) * 1000)
            
            if result.returncode == 0:
                response = result.stdout.strip()
                return {
                    'success': True,
                    'response': response,
                    'latency_ms': elapsed_ms,
                    'error': None,
                    'status': 'SUCCESS'
                }
            else:
                return {
                    'success': False,
                    'response': None,
                    'latency_ms': elapsed_ms,
                    'error': result.stderr.strip(),
                    'status': 'FAILED'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'response': None,
                'latency_ms': timeout * 1000,
                'error': f'Timeout after {timeout}s',
                'status': 'TIMEOUT'
            }
        except Exception as e:
            return {
                'success': False,
                'response': None,
                'latency_ms': 0,
                'error': str(e),
                'status': 'ERROR'
            }
    
    def execute_human_instruction(self, actor_id: str, prompt: str, timeout: int) -> Dict[str, Any]:
        """Handle human actor instruction via CLI interface"""
        actor_info = self.get_actor_info(actor_id)
        
        print(f"\n{'='*70}")
        print(f"🧑 HUMAN GRADING NEEDED")
        print(f"{'='*70}")
        print(f"Actor: {actor_id} ({actor_info['url'] if actor_info else 'unknown'})")
        print(f"Timeout: {timeout} seconds ({timeout//3600}h {(timeout%3600)//60}m)")
        print(f"{'='*70}")
        print()
        print("GRADING PROMPT:")
        print("-" * 50)
        print(prompt)
        print("-" * 50)
        print()
        
        # Interactive grading loop
        while True:
            try:
                grade_input = input("Enter your grade [A/B/C/D/F] or 'quit' to cancel: ").strip().upper()
                
                if grade_input == 'QUIT':
                    return {
                        'success': False,
                        'response': None,
                        'latency_ms': 0,
                        'error': 'Human grading cancelled by user',
                        'status': 'CANCELLED'
                    }
                
                if grade_input in ['A', 'B', 'C', 'D', 'F']:
                    # Optional: Ask for brief reasoning
                    reasoning = input(f"Optional - brief reasoning for grade {grade_input}: ").strip()
                    
                    response_text = f"[{grade_input}]"
                    if reasoning:
                        response_text += f"\n\nHuman grader reasoning: {reasoning}"
                    
                    print(f"\n✅ Grade recorded: {grade_input}")
                    if reasoning:
                        print(f"📝 Reasoning: {reasoning}")
                    
                    return {
                        'success': True,
                        'response': response_text,
                        'latency_ms': 0,  # Human time not measured
                        'error': None,
                        'status': 'SUCCESS'
                    }
                else:
                    print(f"❌ Invalid grade '{grade_input}'. Please enter A, B, C, D, or F.")
                    
            except KeyboardInterrupt:
                print(f"\n\n⚠️ Grading interrupted. Marking as cancelled.")
                return {
                    'success': False,
                    'response': None,
                    'latency_ms': 0,
                    'error': 'Human grading interrupted (Ctrl+C)',
                    'status': 'CANCELLED'
                }
            except Exception as e:
                print(f"\n❌ Error during grading: {e}")
                return {
                    'success': False,
                    'response': None,
                    'latency_ms': 0,
                    'error': f'Human grading error: {str(e)}',
                    'status': 'ERROR'
                }
    
    def execute_script_instruction(self, actor_id: str, prompt: str, timeout: int) -> Dict[str, Any]:
        """Handle script actor instruction (placeholder for future implementation)"""
        print(f"  🤖 Script actor {actor_id} instruction queued")
        script_command = self.get_actor_info(actor_id)['url']
        print(f"  💻 Command: {script_command}")
        
        # For now, return a placeholder response
        return {
            'success': False,
            'response': None,
            'latency_ms': 0,
            'error': 'Script actor integration not yet implemented',
            'status': 'PENDING'
        }
    
    def execute_instruction(self, recipe_run_id: int, instruction: Dict[str, Any], 
                          rendered_prompt: str) -> Dict[str, Any]:
        """Execute single instruction with appropriate actor"""
        actor_info = self.get_actor_info(instruction['actor_id'])
        
        if not actor_info:
            return {
                'success': False,
                'response': None,
                'latency_ms': 0,
                'error': f'Actor {instruction["actor_id"]} not found or disabled',
                'status': 'ERROR'
            }
        
        print(f"    Actor: {actor_info['domain']} - {instruction['actor_id']}")
        
        if actor_info['domain'] == 'AI':
            return self.execute_ai_instruction(
                instruction['actor_id'], 
                rendered_prompt, 
                instruction['timeout_seconds']
            )
        elif actor_info['domain'] == 'human':
            return self.execute_human_instruction(
                instruction['actor_id'],
                rendered_prompt,
                instruction['timeout_seconds']
            )
        elif actor_info['domain'] == 'script':
            return self.execute_script_instruction(
                instruction['actor_id'],
                rendered_prompt,
                instruction['timeout_seconds']
            )
        else:
            return {
                'success': False,
                'response': None,
                'latency_ms': 0,
                'error': f'Unknown actor domain: {actor_info["domain"]}',
                'status': 'ERROR'
            }
    
    def get_instruction_branches(self, instruction_id: int) -> List[Dict[str, Any]]:
        """Get branches for instruction ordered by priority"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    branch_id,
                    condition_type,
                    condition_operator,
                    condition_value,
                    next_step_id,
                    branch_action,
                    branch_metadata,
                    branch_priority
                FROM instruction_branches
                WHERE instruction_id = ? AND enabled = 1
                ORDER BY branch_priority ASC
            """, (instruction_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'branch_id': row[0],
                    'condition_type': row[1],
                    'condition_operator': row[2],
                    'condition_value': row[3],
                    'next_step_id': row[4],
                    'branch_action': row[5],
                    'branch_metadata': row[6],
                    'branch_priority': row[7]
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"Error getting instruction branches: {e}")
            return []
    
    def evaluate_branch_condition(self, branch: Dict[str, Any], response: str) -> bool:
        """Evaluate if branch condition is satisfied"""
        condition_type = branch['condition_type']
        operator = branch['condition_operator']
        value = branch['condition_value']
        
        try:
            if condition_type == 'pattern_match':
                if operator == 'regex_match':
                    return bool(re.search(value, response, re.IGNORECASE))
                elif operator == 'contains':
                    return value.lower() in response.lower()
                    
            elif condition_type == 'length_check':
                response_length = len(response) if response else 0
                threshold = int(value)
                
                if operator == 'less_than':
                    return response_length < threshold
                elif operator == 'greater_than':
                    return response_length > threshold
                elif operator == 'greater_equal':
                    return response_length >= threshold
                elif operator == 'less_equal':
                    return response_length <= threshold
                    
            elif condition_type == 'ai_evaluation':
                # TODO: Implement AI evaluation logic
                print(f"    AI evaluation not yet implemented: {branch}")
                return False
                
            elif condition_type == 'default':
                return True  # Default branch always matches
                
        except Exception as e:
            print(f"    Error evaluating branch condition: {e}")
            return False
        
        return False
    
    def determine_next_instruction(self, instruction_id: int, response: str, 
                                 instructions: List[Dict[str, Any]]) -> Optional[int]:
        """Determine next instruction using branching logic"""
        
        # Get branches for current instruction
        branches = self.get_instruction_branches(instruction_id)
        
        # Evaluate branches in priority order
        for branch in branches:
            if self.evaluate_branch_condition(branch, response):
                print(f"    Branch taken: {branch['branch_action']} -> Step {branch['next_step_id']}")
                
                # Handle special next_step_id values
                if branch['next_step_id'] == -1:
                    return None  # End recipe
                elif branch['next_step_id'] == 0:
                    return None  # Go to completion
                else:
                    return branch['next_step_id']
        
        # No branches matched - use sequential progression
        current_step = next((i['step_number'] for i in instructions if i['instruction_id'] == instruction_id), None)
        if current_step is not None:
            next_instruction = next((i for i in instructions if i['step_number'] == current_step + 1), None)
            if next_instruction:
                print(f"    Sequential progression to step {next_instruction['step_number']}")
                return next_instruction['instruction_id']
        
        return None  # End of recipe
    
    def save_instruction_run(self, recipe_run_id: int, instruction: Dict[str, Any],
                           rendered_prompt: str, result: Dict[str, Any]) -> Optional[int]:
        """Save instruction execution result"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO instruction_runs (
                    recipe_run_id,
                    instruction_id,
                    step_number,
                    prompt_rendered,
                    response_received,
                    latency_ms,
                    error_details,
                    status,
                    pass_fail,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recipe_run_id,
                instruction['instruction_id'],
                instruction['step_number'],
                rendered_prompt,
                result.get('response'),
                result.get('latency_ms', 0),
                result.get('error'),
                result.get('status', 'ERROR'),
                1 if result.get('success', False) else 0,
                datetime.now().isoformat()
            ))
            
            instruction_run_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return instruction_run_id
            
        except Exception as e:
            print(f"Error saving instruction run: {e}")
            return None
    
    def update_recipe_run_progress(self, recipe_run_id: int, completed_steps: int, 
                                 total_steps: int, status: str = 'RUNNING', 
                                 error_details: str = None):
        """Update recipe run progress"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status == 'SUCCESS':
                cursor.execute("""
                    UPDATE recipe_runs 
                    SET completed_steps = ?, status = ?, completed_at = ?, error_details = ?
                    WHERE recipe_run_id = ?
                """, (completed_steps, status, datetime.now().isoformat(), error_details, recipe_run_id))
            else:
                cursor.execute("""
                    UPDATE recipe_runs 
                    SET completed_steps = ?, status = ?, error_details = ?
                    WHERE recipe_run_id = ?
                """, (completed_steps, status, error_details, recipe_run_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error updating recipe run progress: {e}")
    
    def execute_recipe_run(self, recipe_run: Dict[str, Any]) -> bool:
        """Execute complete recipe run with branching support"""
        recipe_run_id = recipe_run['recipe_run_id']
        recipe_id = recipe_run['recipe_id']
        
        print(f"\n🍳 Executing Recipe Run {recipe_run_id}")
        print(f"  Recipe: {recipe_run['canonical_code']}")
        print(f"  Input: {recipe_run['test_input'][:60]}...")
        print(f"  Batch: {recipe_run['batch_id']}, Difficulty: {recipe_run['difficulty_level']}")
        
        # Get recipe instructions
        instructions = self.get_recipe_instructions(recipe_id)
        if not instructions:
            print("  ❌ No instructions found")
            self.update_recipe_run_progress(recipe_run_id, 0, 0, 'FAILED', 'No instructions found')
            return False
        
        # Update total steps
        total_steps = len(instructions)
        self.update_recipe_run_progress(recipe_run_id, 0, total_steps, 'RUNNING')
        
        # Get completed steps for parameter passing
        completed_steps_data = self.get_completed_instruction_runs(recipe_run_id)
        completed_step_count = len(completed_steps_data)
        
        # Find next instruction to execute
        if completed_step_count == 0:
            # Start from first instruction
            current_instruction_id = instructions[0]['instruction_id']
        else:
            # Find where to continue (this handles resume after interruption)
            last_completed_step = max(completed_steps_data.keys())
            next_step_num = last_completed_step + 1
            next_instruction = next((i for i in instructions if i['step_number'] == next_step_num), None)
            if next_instruction:
                current_instruction_id = next_instruction['instruction_id']
            else:
                print(f"  ✅ Recipe already completed ({completed_step_count}/{total_steps} steps)")
                self.update_recipe_run_progress(recipe_run_id, completed_step_count, total_steps, 'SUCCESS')
                return True
        
        # Execute instructions with branching
        while current_instruction_id:
            # Find current instruction
            current_instruction = next((i for i in instructions if i['instruction_id'] == current_instruction_id), None)
            if not current_instruction:
                print(f"  ❌ Instruction {current_instruction_id} not found")
                break
            
            print(f"\n  📋 Step {current_instruction['step_number']}: {current_instruction['step_description']}")
            
            # Render prompt with parameters
            rendered_prompt = self.render_prompt_with_parameters(
                current_instruction['prompt_template'],
                recipe_run['test_input'],
                completed_steps_data
            )
            
            print(f"    Prompt: {rendered_prompt[:100]}...")
            
            # Execute instruction
            print(f"    Executing...", end=" ", flush=True)
            result = self.execute_instruction(recipe_run_id, current_instruction, rendered_prompt)
            
            if result['success']:
                print(f"✅ {result['status']} ({result['latency_ms']}ms)")
                if result['response']:
                    print(f"    Response: {result['response'][:100]}...")
            else:
                print(f"❌ {result['status']}")
                if result['error']:
                    print(f"    Error: {result['error']}")
            
            # Save instruction run
            instruction_run_id = self.save_instruction_run(recipe_run_id, current_instruction, rendered_prompt, result)
            
            # Update completed steps data for next iteration
            if result['success']:
                completed_steps_data[current_instruction['step_number']] = {
                    'prompt': rendered_prompt,
                    'response': result['response'],
                    'status': result['status'],
                    'description': current_instruction['step_description']
                }
                completed_step_count += 1
            
            # Update recipe run progress
            self.update_recipe_run_progress(recipe_run_id, completed_step_count, total_steps, 'RUNNING')
            
            # Determine next instruction using branching logic
            next_instruction_id = self.determine_next_instruction(
                current_instruction_id,
                result.get('response', ''),
                instructions
            )
            
            # Handle recipe completion or failure
            if not next_instruction_id:
                if result['success']:
                    print(f"  ✅ Recipe completed successfully ({completed_step_count}/{total_steps} steps)")
                    self.update_recipe_run_progress(recipe_run_id, completed_step_count, total_steps, 'SUCCESS')
                    return True
                else:
                    print(f"  ❌ Recipe failed at step {current_instruction['step_number']}")
                    self.update_recipe_run_progress(recipe_run_id, completed_step_count, total_steps, 'FAILED', result.get('error'))
                    return False
            
            current_instruction_id = next_instruction_id
            time.sleep(0.5)  # Brief pause between steps


# =============================================================================
# V3.1 SESSION ARCHITECTURE MIGRATION REQUIRED
# =============================================================================
"""
This entire RecipeRunTestRunner class was built for LLMCore V3.0 schema where:
- instructions belonged directly to recipes
- actors were assigned per instruction
- execution was linear recipe → instructions

LLMCore V3.1 introduces session-based architecture requiring complete rebuild:

REQUIRED CHANGES:
1. Session Execution Model:
   - recipe_runs → session_runs → instruction_runs
   - Handle session dependencies (depends_on_session_id)
   - Maintain session context between instructions
   - Support session-level actor inheritance

2. New Database Tables to Support:
   - sessions (session organization within recipes)
   - session_runs (session-level execution tracking)
   - instruction_branch_executions (branch execution audit trail)

3. Context Management:
   - maintain_llm_context flag support
   - context_strategy implementation
   - Cross-session variable passing

4. GUI Integration:
   - Progress callbacks for real-time updates
   - Session-level status reporting
   - Branch execution visualization support

5. Actor Architecture:
   - Actors assigned at session level (not instruction level)
   - Instructions inherit actor from parent session
   - Multi-actor session orchestration

IMPLEMENTATION PRIORITY:
1. Rebuild session execution engine (highest)
2. Add progress callback support for GUI (high)
3. Implement branch execution tracking (medium)
4. Add context strategy support (medium)
5. Session dependency handling (low - most recipes single session initially)

BACKWARD COMPATIBILITY:
- Existing recipe_runs table structure preserved
- instruction_runs table enhanced but compatible
- Migration scripts needed for existing data

This class should be completely rewritten to support V3.1 session architecture
before the new GUI can fully utilize execution capabilities.
"""

# End of V3.0 Legacy Code - All methods above need session architecture updates for V3.1

# V3.1 SESSION ARCHITECTURE IMPLEMENTATION NEEDED
# See class docstring above for complete rebuild requirements

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run multi-step recipe tests')
    parser.add_argument('--max-recipes', type=int, default=None,
                       help='Maximum number of recipe runs to execute (default: unlimited)')
    parser.add_argument('--db', type=str, 
                       default='/home/xai/Documents/ty_learn/data/llmcore.db',
                       help='Path to database')
    
    args = parser.parse_args()
    
    runner = RecipeRunTestRunner(db_path=args.db)
    runner.run_recipe_tests(max_recipe_runs=args.max_recipes)