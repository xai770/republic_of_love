"""
Database queries for LLMCore V3.1 Admin GUI
PostgreSQL (base.yoga) version
"""

from typing import List, Dict, Any, Optional
from .connection import get_db_connection

# =============================================================================
# FACETS
# =============================================================================

def get_all_facets() -> List[Dict[str, Any]]:
    """Get all facets ordered by facet_id"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT facet_id, parent_id, short_description, remarks, enabled
            FROM facets 
            ORDER BY facet_id
        """)
        return cursor.fetchall()

def get_facets_by_parent(parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get facets filtered by parent (None for root facets)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if parent_id is None:
            cursor.execute("""
                SELECT facet_id, parent_id, short_description, remarks, enabled
                FROM facets 
                WHERE parent_id IS NULL
                ORDER BY facet_id
            """)
        else:
            cursor.execute("""
                SELECT facet_id, parent_id, short_description, remarks, enabled
                FROM facets 
                WHERE parent_id = %s
                ORDER BY facet_id
            """, (parent_id,))
        
        return cursor.fetchall()

def get_facet_by_id(facet_id: str) -> Optional[Dict[str, Any]]:
    """Get single facet by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT facet_id, parent_id, short_description, remarks, enabled, created_at
            FROM facets
            WHERE facet_id = %s
        """, (facet_id,))
        result = cursor.fetchone()
        return result

def search_facets(search_term: str) -> List[Dict[str, Any]]:
    """Search facets by ID, description, or remarks"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        search_pattern = f"%{search_term}%"
        cursor.execute("""
            SELECT facet_id, parent_id, short_description, remarks, enabled, created_at
            FROM facets
            WHERE facet_id ILIKE %s 
               OR short_description ILIKE %s
               OR remarks ILIKE %s
            ORDER BY 
                CASE 
                    WHEN facet_id ILIKE %s THEN 1
                    WHEN short_description ILIKE %s THEN 2
                    ELSE 3
                END,
                facet_id
            LIMIT 20
        """, (search_pattern, search_pattern, search_pattern, 
              f"{search_term}%", f"{search_term}%"))
        return cursor.fetchall()

def create_facet(facet_id: str, parent_id: Optional[str], short_description: str, 
                 remarks: Optional[str], enabled: bool) -> tuple[bool, str]:
    """Create new facet"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO facets (facet_id, parent_id, short_description, remarks, enabled)
                VALUES (%s, %s, %s, %s, %s)
            """, (facet_id, parent_id, short_description, remarks, enabled))
            conn.commit()
            return True, f"Facet '{facet_id}' created successfully"
    except Exception as e:
        return False, str(e)

def update_facet(facet_id: str, parent_id: Optional[str], short_description: str,
                 remarks: Optional[str], enabled: bool) -> tuple[bool, str]:
    """Update existing facet"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE facets 
                SET parent_id = %s,
                    short_description = %s,
                    remarks = %s,
                    enabled = %s,
                    updated_at = NOW()
                WHERE facet_id = %s
            """, (parent_id, short_description, remarks, enabled, facet_id))
            conn.commit()
            return True, f"Facet '{facet_id}' updated successfully"
    except Exception as e:
        return False, str(e)

def delete_facet(facet_id: str) -> tuple[bool, str]:
    """Delete facet (only if no children)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check for children
            cursor.execute("""
                SELECT COUNT(*) as count FROM facets WHERE parent_id = %s
            """, (facet_id,))
            child_count = cursor.fetchone()['count']
            
            if child_count > 0:
                return False, f"Cannot delete facet with {child_count} children"
            
            # Delete facet
            cursor.execute("DELETE FROM facets WHERE facet_id = %s", (facet_id,))
            conn.commit()
            return True, f"Facet '{facet_id}' deleted successfully"
    except Exception as e:
        return False, str(e)

# =============================================================================
# CANONICALS  
# =============================================================================

def get_all_canonicals() -> List[Dict[str, Any]]:
    """Get all canonicals with facet information"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.canonical_code, c.facet_id, c.capability_description, 
                   c.prompt, c.response, c.review_notes, c.enabled,
                   f.short_description as facet_description
            FROM canonicals c
            LEFT JOIN facets f ON c.facet_id = f.facet_id
            ORDER BY c.canonical_code
        """)
        return cursor.fetchall()

def get_canonicals_for_facet(facet_id: str) -> List[Dict[str, Any]]:
    """Get canonicals for a specific facet"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT canonical_code, facet_id, capability_description, 
                   prompt, response, review_notes, enabled
            FROM canonicals 
            WHERE facet_id = %s
            ORDER BY canonical_code
        """, (facet_id,))
        return cursor.fetchall()

# =============================================================================
# RECIPES
# =============================================================================

def get_all_recipes() -> List[Dict[str, Any]]:
    """Get all recipes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.recipe_id, r.recipe_name, r.recipe_description, 
                   r.recipe_version, r.enabled,
                   r.max_total_session_runs, r.review_notes, r.created_at,
                   COUNT(DISTINCT rs.session_id) as session_count
            FROM recipes r
            LEFT JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
            GROUP BY r.recipe_id, r.recipe_name, r.recipe_description,
                     r.recipe_version, r.enabled,
                     r.max_total_session_runs, r.review_notes, r.created_at
            ORDER BY r.recipe_id
        """)
        return cursor.fetchall()

def get_recipes_for_canonical(canonical_code: str) -> List[Dict[str, Any]]:
    """Get recipes for sessions using a specific canonical
    NOTE: In BY schema, sessions link to canonicals, not recipes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT r.recipe_id, r.recipe_name, r.recipe_description,
                   r.recipe_version, r.enabled,
                   r.max_total_session_runs, r.review_notes, r.created_at
            FROM recipes r
            JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
            JOIN sessions s ON rs.session_id = s.session_id
            WHERE s.canonical_code = %s
            ORDER BY r.recipe_version DESC
        """, (canonical_code,))
        return cursor.fetchall()

# =============================================================================
# SESSIONS
# =============================================================================

def get_sessions_for_recipe(recipe_id: int) -> List[Dict[str, Any]]:
    """Get sessions for a specific recipe via recipe_sessions junction table"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.session_id, s.canonical_code, s.session_name,
                   s.session_description, s.context_strategy, s.actor_id, s.enabled,
                   s.max_instruction_runs,
                   rs.execution_order, rs.execute_condition, 
                   rs.on_success_action, rs.on_failure_action, rs.max_retry_attempts,
                   a.actor_type, a.url as actor_url
            FROM sessions s
            JOIN recipe_sessions rs ON s.session_id = rs.session_id
            LEFT JOIN actors a ON s.actor_id = a.actor_id
            WHERE rs.recipe_id = %s
            ORDER BY rs.execution_order
        """, (recipe_id,))
        return cursor.fetchall()

# =============================================================================
# INSTRUCTIONS
# =============================================================================

def get_instructions_for_session(session_id: int) -> List[Dict[str, Any]]:
    """Get instructions for a specific session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.instruction_id, i.session_id, i.step_number, i.step_description,
                   i.prompt_template, i.timeout_seconds, i.enabled, i.expected_pattern,
                   i.validation_rules, i.is_terminal, i.created_at,
                   s.actor_id, a.actor_type
            FROM instructions i
            JOIN sessions s ON i.session_id = s.session_id
            LEFT JOIN actors a ON s.actor_id = a.actor_id
            WHERE i.session_id = %s
            ORDER BY i.step_number
        """, (session_id,))
        return cursor.fetchall()

# =============================================================================
# INSTRUCTION BRANCHES
# =============================================================================

def get_branches_for_instruction(instruction_id: int) -> List[Dict[str, Any]]:
    """Get branches for a specific instruction"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT branch_id, instruction_id, branch_condition, next_step_id,
                   branch_priority, condition_type, condition_operator,
                   condition_value, branch_action, enabled
            FROM instruction_branches
            WHERE instruction_id = %s
            ORDER BY branch_priority
        """, (instruction_id,))
        return cursor.fetchall()

# =============================================================================
# VARIATIONS
# =============================================================================

def get_variations_for_recipe(recipe_id: int) -> List[Dict[str, Any]]:
    """Get variations for a specific recipe (test mode parameters)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT variation_id, recipe_id, test_data, enabled, created_at
            FROM variations
            WHERE recipe_id = %s
            ORDER BY variation_id
        """, (recipe_id,))
        return cursor.fetchall()

# =============================================================================
# ACTORS
# =============================================================================

def get_all_actors() -> List[Dict[str, Any]]:
    """Get all actors"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT actor_id, actor_type, url, enabled
            FROM actors
            WHERE enabled = TRUE
            ORDER BY actor_type, actor_id
        """)
        return cursor.fetchall()

# =============================================================================
# EXECUTION RESULTS
# =============================================================================

def get_pending_recipe_runs() -> List[Dict[str, Any]]:
    """Get all pending recipe runs ordered by recipe_run_id"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rr.recipe_run_id, rr.recipe_id, rr.variation_id, rr.batch_id,
                   rr.status, r.recipe_name, v.test_data
            FROM recipe_runs rr
            JOIN recipes r ON rr.recipe_id = r.recipe_id
            LEFT JOIN variations v ON rr.variation_id = v.variation_id
            WHERE rr.status IN ('PENDING', 'RUNNING')
            ORDER BY rr.recipe_run_id
        """)
        return cursor.fetchall()

def get_recent_recipe_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent recipe runs with status information"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rr.recipe_run_id, rr.recipe_id, rr.variation_id, rr.batch_id,
                   rr.started_at, rr.completed_at, rr.status, rr.total_sessions,
                   rr.completed_sessions, rr.error_details,
                   r.recipe_name, v.test_data
            FROM recipe_runs rr
            JOIN recipes r ON rr.recipe_id = r.recipe_id
            LEFT JOIN variations v ON rr.variation_id = v.variation_id
            ORDER BY rr.started_at DESC
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()

def get_session_runs_for_recipe_run(recipe_run_id: int) -> List[Dict[str, Any]]:
    """Get session runs for a recipe run"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sr.session_run_id, sr.recipe_run_id, sr.session_id, 
                   sr.started_at, sr.completed_at, sr.status,
                   sr.llm_conversation_id, sr.error_details,
                   s.session_name, s.actor_id, s.canonical_code
            FROM session_runs sr
            LEFT JOIN sessions s ON sr.session_id = s.session_id
            WHERE sr.recipe_run_id = %s
            ORDER BY sr.session_run_id
        """, (recipe_run_id,))
        return cursor.fetchall()

def get_instruction_runs_for_session_run(session_run_id: int) -> List[Dict[str, Any]]:
    """Get instruction runs for a session run"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ir.instruction_run_id, ir.session_run_id, ir.recipe_run_id,
                   ir.instruction_id, ir.step_number, ir.prompt_rendered,
                   ir.response, ir.latency_ms, ir.error_details,
                   ir.status, ir.created_at, ir.quality_score,
                   i.step_description
            FROM instruction_runs ir
            LEFT JOIN instructions i ON ir.instruction_id = i.instruction_id
            WHERE ir.session_run_id = %s
            ORDER BY ir.step_number
        """, (session_run_id,))
        return cursor.fetchall()

def get_branch_executions_for_instruction_run(instruction_run_id: int) -> List[Dict[str, Any]]:
    """Get branch executions for an instruction run"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT be.execution_id, be.recipe_run_id, be.instruction_run_id,
                   be.branch_id, be.condition_result, be.taken, be.created_at,
                   ib.branch_condition, ib.condition_type, ib.branch_action
            FROM instruction_branch_executions be
            LEFT JOIN instruction_branches ib ON be.branch_id = ib.branch_id
            WHERE be.instruction_run_id = %s
            ORDER BY be.created_at
        """, (instruction_run_id,))
        return cursor.fetchall()