"""
LLMCore V3.2 Session-Aware Recipe Test Runner with Session Chaining
====================================================================
Enhanced version with automatic session output passing.

NEW IN V3.2:
    - Automatic {session_N_output} substitution
    - Session output storage in session_runs.session_output
    - Automatic {step_N_output} substitution within sessions
    - Complete audit trail of session outputs

Architecture:
    recipes → sessions → instructions
    recipe_runs → session_runs → instruction_runs

Key Features:
    - Session-based execution with actor inheritance
    - Session dependency handling
    - **Session output passing** ({session_N_output})
    - **Instruction output passing** ({step_N_output})
    - Context management (isolated/inherited/shared)
    - Branch execution tracking
    - Progress callbacks for GUI integration
    
Author: Arden (GitHub Copilot) & Gershon
Date: 2025-10-22
Version: 3.2.0
"""

import sqlite3
import subprocess
import time
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Session:
    """Session configuration"""
    session_id: int
    recipe_id: int
    session_number: int
    session_name: str
    maintain_llm_context: bool
    execution_order: int
    depends_on_session_id: Optional[int]
    context_strategy: str
    actor_id: str
    enabled: bool

@dataclass
class Instruction:
    """Instruction configuration"""
    instruction_id: int
    session_id: int
    step_number: int
    step_description: str
    prompt_template: str
    timeout_seconds: int
    enabled: bool
    expected_pattern: Optional[str]
    is_terminal: bool

@dataclass
class ExecutionResult:
    """Instruction execution result"""
    success: bool
    response: Optional[str]
    latency_ms: int
    error: Optional[str]
    status: str  # SUCCESS, FAILED, TIMEOUT, ERROR, CANCELLED

# =============================================================================
# MAIN RUNNER CLASS
# =============================================================================

class SessionAwareRecipeRunner:
    """V3.2 Session-Based Recipe Execution Engine with Output Passing"""
    
    def __init__(self, db_path: str = "/home/xai/Documents/ty_learn/data/llmcore.db"):
        self.db_path = db_path
        self.ollama_timeout = 300  # 5 minutes default
        
        # Progress tracking
        self.progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        
        # Execution context
        self.current_recipe_run_id: Optional[int] = None
        self.session_context: Dict[int, Dict[str, Any]] = {}  # session_id → context
        self.conversation_ids: Dict[int, str] = {}  # session_run_id → conversation_id
        
    # =========================================================================
    # DATABASE HELPERS
    # =========================================================================
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def cleanup_stale_runs(self):
        """Reset stale RUNNING records and clean up orphaned execution records"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Find RUNNING records older than 1 hour (likely stuck from crashed runner)
        cursor.execute("""
            SELECT recipe_run_id 
            FROM recipe_runs 
            WHERE status = 'RUNNING' 
                AND started_at < datetime('now', '-1 hour')
        """)
        
        stale_ids = [row[0] for row in cursor.fetchall()]
        
        if stale_ids:
            print(f"\n⚠️  Found {len(stale_ids)} stale RUNNING records (>1 hour old)")
            print(f"    Recipe Run IDs: {stale_ids}")
            
            # Delete orphaned execution records
            ids_str = ','.join(map(str, stale_ids))
            cursor.execute(f"DELETE FROM instruction_runs WHERE recipe_run_id IN ({ids_str})")
            cursor.execute(f"DELETE FROM session_runs WHERE recipe_run_id IN ({ids_str})")
            
            # Reset to PENDING
            cursor.execute(f"""
                UPDATE recipe_runs 
                SET status = 'PENDING', started_at = NULL 
                WHERE recipe_run_id IN ({ids_str})
            """)
            
            conn.commit()
            print(f"    ✅ Reset {len(stale_ids)} stale records to PENDING")
        
        # Also clean up any orphaned session_runs/instruction_runs for PENDING records
        # (These shouldn't exist but can occur from previous constraint errors)
        # CRITICAL: Only delete non-SUCCESS sessions to preserve completed work!
        cursor.execute("""
            DELETE FROM instruction_runs 
            WHERE recipe_run_id IN (
                SELECT recipe_run_id FROM recipe_runs WHERE status = 'PENDING'
            )
            AND session_run_id IN (
                SELECT session_run_id FROM session_runs WHERE status != 'SUCCESS'
            )
        """)
        orphaned_instructions = cursor.rowcount
        
        cursor.execute("""
            DELETE FROM session_runs 
            WHERE recipe_run_id IN (
                SELECT recipe_run_id FROM recipe_runs WHERE status = 'PENDING'
            )
            AND status != 'SUCCESS'
        """)
        orphaned_sessions = cursor.rowcount
        
        if orphaned_instructions > 0 or orphaned_sessions > 0:
            print(f"\n🧹 Cleaned up {orphaned_sessions} orphaned session_runs, {orphaned_instructions} orphaned instruction_runs")
        
        conn.commit()
        conn.close()
    
    def emit_progress(self, event: str, data: Dict[str, Any]):
        """Emit progress event for GUI/logging"""
        if self.progress_callback:
            self.progress_callback(event, data)
        
        # Also print to console for CLI usage
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {event}: {data}")
    
    # =========================================================================
    # SESSION QUERIES
    # =========================================================================
    
    def get_recipe_sessions(self, recipe_id: int) -> List[Session]:
        """Get all sessions for recipe in execution order"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                session_id,
                recipe_id,
                session_number,
                session_name,
                maintain_llm_context,
                execution_order,
                depends_on_session_id,
                context_strategy,
                actor_id,
                enabled
            FROM sessions
            WHERE recipe_id = ? AND enabled = 1
            ORDER BY execution_order, session_number
        """, (recipe_id,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append(Session(
                session_id=row[0],
                recipe_id=row[1],
                session_number=row[2],
                session_name=row[3],
                maintain_llm_context=bool(row[4]),
                execution_order=row[5],
                depends_on_session_id=row[6],
                context_strategy=row[7],
                actor_id=row[8],
                enabled=bool(row[9])
            ))
        
        conn.close()
        return sessions
    
    def get_session_instructions(self, session_id: int) -> List[Instruction]:
        """Get all instructions for session ordered by step_number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                instruction_id,
                session_id,
                step_number,
                step_description,
                prompt_template,
                timeout_seconds,
                enabled,
                expected_pattern,
                is_terminal
            FROM instructions
            WHERE session_id = ? AND enabled = 1
            ORDER BY step_number
        """, (session_id,))
        
        instructions = []
        for row in cursor.fetchall():
            instructions.append(Instruction(
                instruction_id=row[0],
                session_id=row[1],
                step_number=row[2],
                step_description=row[3],
                prompt_template=row[4],
                timeout_seconds=row[5] or self.ollama_timeout,
                enabled=bool(row[6]),
                expected_pattern=row[7],
                is_terminal=bool(row[8])
            ))
        
        conn.close()
        return instructions
    
    def get_actor_info(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Get actor information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT actor_id, actor_type, url, enabled
            FROM actors
            WHERE actor_id = ? AND enabled = 1
        """, (actor_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'actor_id': result[0],
                'actor_type': result[1],  # V3.1 uses actor_type instead of domain
                'url': result[2],
                'enabled': result[3]
            }
        return None
    
    # =========================================================================
    # SESSION DEPENDENCY CHECKING
    # =========================================================================
    
    def check_session_dependencies(self, session: Session, recipe_run_id: int) -> bool:
        """Check if session dependencies are met"""
        if not session.depends_on_session_id:
            return True  # No dependency
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if dependent session completed successfully
        cursor.execute("""
            SELECT status
            FROM session_runs
            WHERE recipe_run_id = ? AND session_id = ?
            ORDER BY session_run_id DESC
            LIMIT 1
        """, (recipe_run_id, session.depends_on_session_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False  # Dependency not yet run
        
        return result[0] == 'SUCCESS'
    
    def get_existing_session_run(self, recipe_run_id: int, session_number: int) -> Optional[Dict[str, Any]]:
        """Check if a session_run already exists for this recipe_run and session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_run_id, session_id, session_number, status
            FROM session_runs
            WHERE recipe_run_id = ? AND session_number = ?
            ORDER BY session_run_id DESC
            LIMIT 1
        """, (recipe_run_id, session_number))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'session_run_id': result[0],
                'session_id': result[1],
                'session_number': result[2],
                'status': result[3]
            }
        
        return None
    
    # =========================================================================
    # V3.2 NEW: SESSION OUTPUT MANAGEMENT
    # =========================================================================
    
    def store_session_output(self, session_run_id: int) -> bool:
        """Store final instruction output in session_runs.session_output"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get final instruction response from this session
            cursor.execute("""
                SELECT response_received 
                FROM instruction_runs 
                WHERE session_run_id = ? 
                    AND status = 'SUCCESS'
                ORDER BY step_number DESC 
                LIMIT 1
            """, (session_run_id,))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                final_output = result[0]
                
                # Store in session_runs.session_output
                cursor.execute("""
                    UPDATE session_runs 
                    SET session_output = ?
                    WHERE session_run_id = ?
                """, (final_output, session_run_id))
                
                conn.commit()
                print(f"       💾 Stored session output ({len(final_output)} chars)")
                return True
            else:
                print(f"       ⚠️  No output to store")
                return False
                
        except Exception as e:
            print(f"       ❌ Error storing session output: {e}")
            return False
        finally:
            conn.close()
    
    def get_session_output(self, recipe_run_id: int, session_number: int) -> Optional[str]:
        """Get session output by recipe_run_id and session_number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_output 
            FROM session_runs 
            WHERE recipe_run_id = ? 
                AND session_number = ?
                AND status = 'SUCCESS'
            ORDER BY session_run_id DESC
            LIMIT 1
        """, (recipe_run_id, session_number))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        return None
    
    def render_with_session_outputs(self, template: str, recipe_run_id: int) -> str:
        """Replace {session_N_output} placeholders with actual session outputs"""
        # Find all {session_N_output} placeholders
        pattern = r'\{session_(\d+)_output\}'
        matches = re.findall(pattern, template)
        
        if not matches:
            return template  # No session output placeholders
        
        rendered = template
        
        for session_num_str in matches:
            session_num = int(session_num_str)
            placeholder = f'{{session_{session_num}_output}}'
            
            # Get the output from that session
            output = self.get_session_output(recipe_run_id, session_num)
            
            if output:
                rendered = rendered.replace(placeholder, output)
                print(f"       🔗 Replaced {placeholder} with session {session_num} output ({len(output)} chars)")
            else:
                print(f"       ⚠️  Warning: {placeholder} found but session {session_num} has no output")
                # Leave placeholder as-is if output not found
        
        return rendered
    
    def render_with_step_outputs(self, template: str, session_run_id: int, 
                                 current_step: int) -> str:
        """Replace {step_N_output} placeholders with previous instruction outputs in same session"""
        # Find all {step_N_output} placeholders
        pattern = r'\{step_(\d+)_output\}'
        matches = re.findall(pattern, template)
        
        if not matches:
            return template  # No step output placeholders
        
        rendered = template
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for step_num_str in matches:
            step_num = int(step_num_str)
            placeholder = f'{{step_{step_num}_output}}'
            
            # Validate: can't reference current or future steps
            if step_num >= current_step:
                print(f"       ⚠️  Warning: Cannot reference future step {step_num} from step {current_step}")
                continue
            
            # Get the output from that step
            cursor.execute("""
                SELECT response_received 
                FROM instruction_runs 
                WHERE session_run_id = ? 
                    AND step_number = ?
                    AND status = 'SUCCESS'
            """, (session_run_id, step_num))
            
            result = cursor.fetchone()
            
            if result and result[0]:
                output = result[0]
                rendered = rendered.replace(placeholder, output)
                print(f"       🔗 Replaced {placeholder} with step {step_num} output ({len(output)} chars)")
            else:
                print(f"       ⚠️  Warning: {placeholder} found but step {step_num} has no output")
        
        conn.close()
        return rendered
    
    # =========================================================================
    # SESSION RUN MANAGEMENT
    # =========================================================================
    
    def create_session_run(self, recipe_run_id: int, session: Session) -> int:
        """Create session_run record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO session_runs (
                recipe_run_id,
                session_id,
                session_number,
                started_at,
                status
            ) VALUES (?, ?, ?, ?, 'RUNNING')
        """, (
            recipe_run_id,
            session.session_id,
            session.session_number,
            datetime.now().isoformat()
        ))
        
        session_run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.emit_progress('session_started', {
            'session_run_id': session_run_id,
            'session_number': session.session_number,
            'session_name': session.session_name,
            'actor_id': session.actor_id
        })
        
        return session_run_id
    
    def update_session_run(self, session_run_id: int, status: str, error_details: Optional[str] = None):
        """Update session_run status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status in ['SUCCESS', 'FAILED', 'ERROR']:
            cursor.execute("""
                UPDATE session_runs 
                SET status = ?, completed_at = ?, error_details = ?
                WHERE session_run_id = ?
            """, (status, datetime.now().isoformat(), error_details, session_run_id))
        else:
            cursor.execute("""
                UPDATE session_runs 
                SET status = ?, error_details = ?
                WHERE session_run_id = ?
            """, (status, error_details, session_run_id))
        
        conn.commit()
        conn.close()
        
        self.emit_progress('session_updated', {
            'session_run_id': session_run_id,
            'status': status,
            'error': error_details
        })
    
    # =========================================================================
    # PROMPT RENDERING
    # =========================================================================
    
    def render_prompt_with_parameters(self, template: str, variation_params: Dict[str, str], 
                                    instruction_results: Dict[int, Dict[str, Any]]) -> str:
        """Render prompt template with variation parameters and previous instruction outputs"""
        rendered = template
        
        # Replace variation parameters
        for param_name, param_value in variation_params.items():
            rendered = rendered.replace(f'{{{param_name}}}', str(param_value))
            rendered = rendered.replace(f'{{{{{param_name}}}}}', str(param_value))  # Double braces
        
        # Replace instruction step outputs (legacy compatibility)
        for step_num, step_data in instruction_results.items():
            step_response_var = f'{{step{step_num}_response}}'
            rendered = rendered.replace(step_response_var, step_data.get('response', ''))
        
        return rendered
    
    def load_dependent_session_results(self, recipe_run_id: int, 
                                      depends_on_session_id: int) -> Dict[int, Dict[str, Any]]:
        """Load instruction results from a dependent session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get the session_run_id for the dependent session
        cursor.execute("""
            SELECT session_run_id
            FROM session_runs
            WHERE recipe_run_id = ?
              AND session_id = ?
              AND status = 'SUCCESS'
        """, (recipe_run_id, depends_on_session_id))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {}
        
        session_run_id = row[0]
        
        # Load all instruction runs from that session
        cursor.execute("""
            SELECT step_number, response_received
            FROM instruction_runs
            WHERE session_run_id = ?
              AND status = 'SUCCESS'
            ORDER BY step_number
        """, (session_run_id,))
        
        results = {}
        for row in cursor.fetchall():
            step_number, response = row
            results[step_number] = {
                'response': response,
                'status': 'SUCCESS'
            }
        
        conn.close()
        return results
    
    # =========================================================================
    # ACTOR EXECUTION (COPIED FROM V3.0 - THESE WORK WELL)
    # =========================================================================
    
    def execute_ai_instruction(self, actor_id: str, prompt: str, timeout: int) -> ExecutionResult:
        """Execute instruction with AI actor via Ollama"""
        try:
            start = time.time()
            
            result = subprocess.run(
                ['ollama', 'run', actor_id, prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL  # Fix: Prevent "bad file descriptor" in background mode
            )
            
            elapsed_ms = int((time.time() - start) * 1000)
            
            if result.returncode == 0:
                response = result.stdout.strip()
                return ExecutionResult(
                    success=True,
                    response=response,
                    latency_ms=elapsed_ms,
                    error=None,
                    status='SUCCESS'
                )
            else:
                return ExecutionResult(
                    success=False,
                    response=None,
                    latency_ms=elapsed_ms,
                    error=result.stderr.strip(),
                    status='FAILED'
                )
                
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                response=None,
                latency_ms=timeout * 1000,
                error=f'Timeout after {timeout}s',
                status='TIMEOUT'
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                response=None,
                latency_ms=0,
                error=str(e),
                status='ERROR'
            )
    
    def execute_human_instruction(self, actor_id: str, prompt: str, timeout: int) -> ExecutionResult:
        """Handle human actor instruction via CLI interface"""
        print(f"\n{'='*70}")
        print(f"🧑 HUMAN GRADING NEEDED")
        print(f"{'='*70}")
        print(f"Actor: {actor_id}")
        print(f"Timeout: {timeout} seconds")
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
                    return ExecutionResult(
                        success=False,
                        response=None,
                        latency_ms=0,
                        error='Human grading cancelled by user',
                        status='CANCELLED'
                    )
                
                if grade_input in ['A', 'B', 'C', 'D', 'F']:
                    reasoning = input(f"Optional - brief reasoning for grade {grade_input}: ").strip()
                    
                    response_text = f"[{grade_input}]"
                    if reasoning:
                        response_text += f"\n\nHuman grader reasoning: {reasoning}"
                    
                    print(f"\n✅ Grade recorded: {grade_input}")
                    if reasoning:
                        print(f"📝 Reasoning: {reasoning}")
                    
                    return ExecutionResult(
                        success=True,
                        response=response_text,
                        latency_ms=0,
                        error=None,
                        status='SUCCESS'
                    )
                else:
                    print(f"❌ Invalid grade '{grade_input}'. Please enter A, B, C, D, or F.")
                    
            except KeyboardInterrupt:
                print(f"\n\n⚠️ Grading interrupted.")
                return ExecutionResult(
                    success=False,
                    response=None,
                    latency_ms=0,
                    error='Human grading interrupted (Ctrl+C)',
                    status='CANCELLED'
                )
            except Exception as e:
                print(f"\n❌ Error during grading: {e}")
                return ExecutionResult(
                    success=False,
                    response=None,
                    latency_ms=0,
                    error=f'Human grading error: {str(e)}',
                    status='ERROR'
                )
    
    def execute_script_instruction(self, actor_id: str, prompt: str, timeout: int) -> ExecutionResult:
        """Handle script actor instruction (placeholder)"""
        print(f"  🤖 Script actor {actor_id} instruction queued")
        
        return ExecutionResult(
            success=False,
            response=None,
            latency_ms=0,
            error='Script actor integration not yet implemented',
            status='PENDING'
        )
    
    def execute_instruction(self, instruction: Instruction, actor_id: str, 
                          rendered_prompt: str) -> ExecutionResult:
        """Execute single instruction with appropriate actor"""
        actor_info = self.get_actor_info(actor_id)
        
        if not actor_info:
            return ExecutionResult(
                success=False,
                response=None,
                latency_ms=0,
                error=f'Actor {actor_id} not found or disabled',
                status='ERROR'
            )
        
        actor_type = actor_info['actor_type']
        
        if actor_type == 'ai_model':
            return self.execute_ai_instruction(actor_id, rendered_prompt, instruction.timeout_seconds)
        elif actor_type == 'human':
            return self.execute_human_instruction(actor_id, rendered_prompt, instruction.timeout_seconds)
        elif actor_type == 'script':
            return self.execute_script_instruction(actor_id, rendered_prompt, instruction.timeout_seconds)
        else:
            return ExecutionResult(
                success=False,
                response=None,
                latency_ms=0,
                error=f'Unknown actor type: {actor_type}',
                status='ERROR'
            )
    
    # =========================================================================
    # INSTRUCTION RUN MANAGEMENT
    # =========================================================================
    
    def save_instruction_run(self, recipe_run_id: int, session_run_id: int, 
                           instruction: Instruction, rendered_prompt: str, 
                           result: ExecutionResult) -> int:
        """Save instruction execution result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO instruction_runs (
                session_run_id,
                recipe_run_id,
                instruction_id,
                step_number,
                prompt_rendered,
                response_received,
                latency_ms,
                error_details,
                status,
                timestamp,
                pass_fail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_run_id,
            recipe_run_id,
            instruction.instruction_id,
            instruction.step_number,
            rendered_prompt,
            result.response,
            result.latency_ms,
            result.error,
            result.status,
            datetime.now().isoformat(),
            1 if result.success else 0
        ))
        
        instruction_run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.emit_progress('instruction_completed', {
            'instruction_run_id': instruction_run_id,
            'step_number': instruction.step_number,
            'status': result.status,
            'latency_ms': result.latency_ms
        })
        
        return instruction_run_id
    
    # =========================================================================
    # SESSION EXECUTION
    # =========================================================================
    
    def execute_session(self, session: Session, session_run_id: int, 
                       recipe_run: Dict[str, Any]) -> bool:
        """Execute all instructions in session with context management"""
        
        print(f"\n  📋 Session {session.session_number}: {session.session_name}")
        print(f"     Actor: {session.actor_id}")
        print(f"     Context: {session.context_strategy}")
        
        # Get instructions for this session
        instructions = self.get_session_instructions(session.session_id)
        
        if not instructions:
            print(f"     ⚠️  No instructions found")
            self.update_session_run(session_run_id, 'FAILED', 'No instructions found')
            return False
        
        print(f"     Instructions: {len(instructions)}")
        
        # Track instruction results for parameter passing
        instruction_results = {}
        
        # If this session depends on another session, load its instruction results
        if session.depends_on_session_id:
            instruction_results = self.load_dependent_session_results(
                recipe_run['recipe_run_id'], 
                session.depends_on_session_id
            )
        
        # Execute each instruction
        for instruction in instructions:
            print(f"\n     Step {instruction.step_number}: {instruction.step_description}")
            
            # Render prompt with parameters
            rendered_prompt = self.render_prompt_with_parameters(
                instruction.prompt_template,
                recipe_run['variation_params'],
                instruction_results
            )
            
            # V3.2 NEW: Replace {session_N_output} placeholders
            rendered_prompt = self.render_with_session_outputs(
                rendered_prompt,
                recipe_run['recipe_run_id']
            )
            
            # V3.2 NEW: Replace {step_N_output} placeholders
            rendered_prompt = self.render_with_step_outputs(
                rendered_prompt,
                session_run_id,
                instruction.step_number
            )
            
            print(f"       Prompt: {rendered_prompt[:100]}...")
            print(f"       Executing...", end=" ", flush=True)
            
            # Execute instruction
            result = self.execute_instruction(instruction, session.actor_id, rendered_prompt)
            
            if result.success:
                print(f"✅ {result.status} ({result.latency_ms}ms)")
                if result.response:
                    print(f"       Response: {result.response[:100]}...")
            else:
                print(f"❌ {result.status}")
                if result.error:
                    print(f"       Error: {result.error}")
            
            # Save instruction run
            instruction_run_id = self.save_instruction_run(
                recipe_run['recipe_run_id'],
                session_run_id,
                instruction,
                rendered_prompt,
                result
            )
            
            # Store result for next instruction's parameter passing
            if result.success:
                instruction_results[instruction.step_number] = {
                    'response': result.response,
                    'status': result.status
                }
            else:
                # Instruction failed - stop session execution
                self.update_session_run(session_run_id, 'FAILED', result.error)
                return False
        
        # V3.2 NEW: Store final session output after all instructions complete
        self.store_session_output(session_run_id)
        
        # All instructions completed successfully
        self.update_session_run(session_run_id, 'SUCCESS')
        return True
    
    # =========================================================================
    # RECIPE RUN EXECUTION (MAIN ENTRY POINT)
    # =========================================================================
    
    def get_next_incomplete_recipe_run(self, specific_ids: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
        """Get next recipe_run that needs execution, optionally filtered by specific IDs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause based on specific_ids filter
        where_clause = "WHERE rr.status IN ('PENDING', 'RUNNING')"
        if specific_ids:
            ids_str = ','.join(map(str, specific_ids))
            where_clause += f" AND rr.recipe_run_id IN ({ids_str})"
        
        cursor.execute(f"""
            SELECT 
                rr.recipe_run_id,
                rr.recipe_id,
                rr.variation_id,
                rr.batch_id,
                rr.status,
                r.canonical_code,
                v.variations_param_1,
                v.variations_param_2,
                v.variations_param_3,
                v.difficulty_level
            FROM recipe_runs rr
            JOIN recipes r ON rr.recipe_id = r.recipe_id
            JOIN variations v ON rr.variation_id = v.variation_id
            {where_clause}
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
                'canonical_code': result[5],
                'variation_params': {
                    'variations_param_1': result[6] or '',
                    'variations_param_2': result[7] or '',
                    'variations_param_3': result[8] or ''
                },
                'difficulty_level': result[9]
            }
        return None
    
    def update_recipe_run(self, recipe_run_id: int, status: str, error_details: Optional[str] = None):
        """Update recipe_run status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status in ['SUCCESS', 'FAILED', 'ERROR']:
            cursor.execute("""
                UPDATE recipe_runs 
                SET status = ?, completed_at = ?, error_details = ?
                WHERE recipe_run_id = ?
            """, (status, datetime.now().isoformat(), error_details, recipe_run_id))
        else:
            cursor.execute("""
                UPDATE recipe_runs 
                SET status = ?, error_details = ?
                WHERE recipe_run_id = ?
            """, (status, error_details, recipe_run_id))
        
        conn.commit()
        conn.close()
    
    def execute_recipe_run(self, recipe_run: Dict[str, Any]) -> bool:
        """Execute complete recipe run with session-based architecture"""
        recipe_run_id = recipe_run['recipe_run_id']
        recipe_id = recipe_run['recipe_id']
        
        self.current_recipe_run_id = recipe_run_id
        
        print(f"\n{'='*70}")
        print(f"🍳 Recipe Run {recipe_run_id}")
        print(f"{'='*70}")
        print(f"Recipe: {recipe_run['canonical_code']}")
        print(f"Input: {recipe_run['variation_params']['variations_param_1'][:100]}...")
        print(f"Batch: {recipe_run['batch_id']}, Difficulty: {recipe_run['difficulty_level']}")
        
        # Mark recipe as running
        self.update_recipe_run(recipe_run_id, 'RUNNING')
        
        # Get sessions for recipe
        sessions = self.get_recipe_sessions(recipe_id)
        
        if not sessions:
            print("❌ No sessions found for recipe")
            self.update_recipe_run(recipe_run_id, 'FAILED', 'No sessions found')
            return False
        
        print(f"Sessions: {len(sessions)}")
        
        # Execute each session in order
        for session in sessions:
            # Check if this session has already been completed
            existing_session_run = self.get_existing_session_run(recipe_run_id, session.session_number)
            
            if existing_session_run and existing_session_run['status'] == 'SUCCESS':
                print(f"\n  ✅ Session {session.session_number}: {session.session_name} (already completed, skipping)")
                continue  # Skip this session, it's already done
            
            # Check session dependencies
            if not self.check_session_dependencies(session, recipe_run_id):
                print(f"\n  ⏸️  Session {session.session_number} blocked by dependency")
                self.update_recipe_run(recipe_run_id, 'FAILED', f'Session {session.session_number} dependency not met')
                return False
            
            # Create session run (or reuse existing if FAILED/PENDING)
            if existing_session_run and existing_session_run['status'] in ('FAILED', 'PENDING', 'RUNNING'):
                print(f"\n  🔄 Retrying Session {session.session_number} (previous status: {existing_session_run['status']})")
                session_run_id = existing_session_run['session_run_id']
                # Update status to RUNNING
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE session_runs SET status = 'RUNNING', started_at = ? WHERE session_run_id = ?",
                             (datetime.now().isoformat(), session_run_id))
                conn.commit()
                conn.close()
            else:
                # Create new session run
                session_run_id = self.create_session_run(recipe_run_id, session)
            
            # Execute session
            success = self.execute_session(session, session_run_id, recipe_run)
            
            if not success:
                print(f"\n  ❌ Session {session.session_number} failed")
                self.update_recipe_run(recipe_run_id, 'FAILED', f'Session {session.session_number} failed')
                return False
            
            print(f"\n  ✅ Session {session.session_number} completed")
        
        # All sessions completed successfully
        print(f"\n{'='*70}")
        print(f"✅ Recipe Run {recipe_run_id} COMPLETED SUCCESSFULLY")
        print(f"{'='*70}")
        
        self.update_recipe_run(recipe_run_id, 'SUCCESS')
        return True
    
    # =========================================================================
    # BATCH EXECUTION
    # =========================================================================
    
    def run_all_pending(self, max_runs: Optional[int] = None, specific_ids: Optional[List[int]] = None) -> Dict[str, int]:
        """Run all pending recipe runs or specific ones if IDs provided"""
        print(f"\n{'='*70}")
        print(f"🚀 LLMCORE V3.2 RECIPE RUNNER (with Session Chaining)")
        print(f"{'='*70}")
        print(f"Database: {self.db_path}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if specific_ids:
            print(f"Mode: Selective execution ({len(specific_ids)} specific recipe_runs)")
        print(f"{'='*70}")
        
        # Clean up any stale RUNNING records before starting
        self.cleanup_stale_runs()
        
        runs_completed = 0
        runs_failed = 0
        
        while True:
            # Check if we've hit the limit
            if max_runs and (runs_completed + runs_failed) >= max_runs:
                print(f"\n⏹️  Reached maximum runs limit ({max_runs})")
                break
            
            # Get next recipe run
            recipe_run = self.get_next_incomplete_recipe_run(specific_ids=specific_ids)
            
            if not recipe_run:
                print(f"\n✅ No more pending recipe runs")
                break
            
            # Execute recipe run
            success = self.execute_recipe_run(recipe_run)
            
            if success:
                runs_completed += 1
            else:
                runs_failed += 1
            
            time.sleep(0.5)  # Brief pause between runs
        
        # Summary
        print(f"\n{'='*70}")
        print(f"📊 EXECUTION SUMMARY")
        print(f"{'='*70}")
        print(f"Completed: {runs_completed}")
        print(f"Failed: {runs_failed}")
        print(f"Total: {runs_completed + runs_failed}")
        print(f"Success Rate: {runs_completed / (runs_completed + runs_failed) * 100:.1f}%" if (runs_completed + runs_failed) > 0 else "N/A")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        return {
            'completed': runs_completed,
            'failed': runs_failed,
            'total': runs_completed + runs_failed
        }

# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='LLMCore V3.2 Session-Aware Recipe Test Runner with Session Chaining',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all pending recipe runs
  python recipe_run_test_runner_v32.py
  
  # Run maximum 5 recipe runs
  python recipe_run_test_runner_v32.py --max-runs 5
  
  # Use different database
  python recipe_run_test_runner_v32.py --db /path/to/llmcore.db
        """
    )
    
    parser.add_argument(
        '--max-runs',
        type=int,
        default=None,
        help='Maximum number of recipe runs to execute (default: unlimited)'
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='/home/xai/Documents/ty_learn/data/llmcore.db',
        help='Path to database (default: %(default)s)'
    )
    
    parser.add_argument(
        '--ids-file',
        type=str,
        default=None,
        help='JSON file containing specific recipe_run_ids to execute'
    )
    
    args = parser.parse_args()
    
    # Load specific IDs if provided
    specific_ids = None
    if args.ids_file:
        import json
        with open(args.ids_file, 'r') as f:
            data = json.load(f)
            specific_ids = data.get('recipe_run_ids', [])
        print(f"Loaded {len(specific_ids)} specific recipe_run_ids from {args.ids_file}")
    
    # Create runner and execute
    runner = SessionAwareRecipeRunner(db_path=args.db)
    results = runner.run_all_pending(max_runs=args.max_runs, specific_ids=specific_ids)
    
    # Exit with appropriate code
    if results['failed'] > 0:
        exit(1)  # Some runs failed
    elif results['total'] == 0:
        exit(2)  # No runs found
    else:
        exit(0)  # All successful

if __name__ == "__main__":
    main()
