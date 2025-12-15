"""
LLMCore V3.1 Database Views for Pipeline Health Monitoring
=========================================================
Creates and manages SQL views for the three-tab GUI interface.
PostgreSQL (base.yoga) version with new schema structure.
"""

from typing import Dict, Any
from .connection import get_db_connection

def create_all_views():
    """Create all SQL views needed for the GUI on startup"""
    
    views = {
        'v_canonicals_orphaned': """
            CREATE OR REPLACE VIEW v_canonicals_orphaned AS
            SELECT 
                c.canonical_code,
                c.facet_id,
                c.capability_description
            FROM canonicals c
            WHERE c.enabled = TRUE
              AND NOT EXISTS (
                SELECT 1 FROM sessions s 
                WHERE s.canonical_code = c.canonical_code 
                AND s.enabled = TRUE
              )
            ORDER BY c.canonical_code
        """,
        
        'v_recipes_missing_variations': """
            CREATE OR REPLACE VIEW v_recipes_missing_variations AS
            SELECT 
                r.recipe_id,
                r.recipe_name,
                r.recipe_description,
                r.recipe_version
            FROM recipes r
            WHERE r.enabled = TRUE
              AND NOT EXISTS (
                SELECT 1 FROM variations v 
                WHERE v.recipe_id = r.recipe_id 
                AND v.enabled = TRUE
              )
            ORDER BY r.recipe_id
        """,
        
        'v_recipes_missing_sessions': """
            CREATE OR REPLACE VIEW v_recipes_missing_sessions AS
            SELECT 
                r.recipe_id,
                r.recipe_name,
                r.recipe_description,
                r.recipe_version
            FROM recipes r
            WHERE r.enabled = TRUE
              AND NOT EXISTS (
                SELECT 1 FROM recipe_sessions rs 
                WHERE rs.recipe_id = r.recipe_id
              )
            ORDER BY r.recipe_id
        """,
        
        'v_sessions_missing_instructions': """
            CREATE OR REPLACE VIEW v_sessions_missing_instructions AS
            SELECT 
                s.session_id,
                s.canonical_code,
                s.session_name
            FROM sessions s
            WHERE s.enabled = TRUE
              AND NOT EXISTS (
                SELECT 1 FROM instructions i 
                WHERE i.session_id = s.session_id 
                AND i.enabled = TRUE
              )
            ORDER BY s.session_id
        """,
        
        'v_recipes_ready_for_testing': """
            CREATE OR REPLACE VIEW v_recipes_ready_for_testing AS
            SELECT 
                r.recipe_id,
                r.recipe_name,
                r.recipe_description,
                r.recipe_version,
                COUNT(DISTINCT v.variation_id) as variation_count,
                COUNT(DISTINCT rs.session_id) as session_count,
                COUNT(DISTINCT i.instruction_id) as instruction_count,
                COALESCE(
                    (SELECT COUNT(*) FROM recipe_runs rr WHERE rr.recipe_id = r.recipe_id), 
                    0
                ) as run_count,
                5 as runs_needed
            FROM recipes r
            LEFT JOIN variations v ON v.recipe_id = r.recipe_id AND v.enabled = TRUE
            LEFT JOIN recipe_sessions rs ON rs.recipe_id = r.recipe_id
            LEFT JOIN sessions s ON s.session_id = rs.session_id AND s.enabled = TRUE
            LEFT JOIN instructions i ON i.session_id = s.session_id AND i.enabled = TRUE
            WHERE r.enabled = TRUE
              AND EXISTS (SELECT 1 FROM variations v2 WHERE v2.recipe_id = r.recipe_id AND v2.enabled = TRUE)
              AND EXISTS (SELECT 1 FROM recipe_sessions rs2 WHERE rs2.recipe_id = r.recipe_id)
              AND EXISTS (
                  SELECT 1 FROM recipe_sessions rs3
                  JOIN sessions s3 ON rs3.session_id = s3.session_id
                  JOIN instructions i2 ON i2.session_id = s3.session_id
                  WHERE rs3.recipe_id = r.recipe_id AND i2.enabled = TRUE
              )
            GROUP BY r.recipe_id, r.recipe_name, r.recipe_description, r.recipe_version
            ORDER BY r.recipe_id
        """,
        
        'v_pipeline_health': """
            CREATE OR REPLACE VIEW v_pipeline_health AS
            SELECT 
                (SELECT COUNT(*) FROM v_canonicals_orphaned) as canonicals_orphaned,
                (SELECT COUNT(*) FROM v_recipes_missing_variations) as recipes_missing_variations,
                (SELECT COUNT(*) FROM v_recipes_missing_sessions) as recipes_missing_sessions,
                (SELECT COUNT(*) FROM v_sessions_missing_instructions) as sessions_missing_instructions,
                (SELECT COUNT(*) FROM v_recipes_ready_for_testing) as recipes_ready_for_testing
        """
    }
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Drop views if they exist (to handle schema changes) - PostgreSQL syntax
        for view_name in views.keys():
            cursor.execute(f"DROP VIEW IF EXISTS {view_name} CASCADE")
        
        # Create all views
        for view_name, view_sql in views.items():
            try:
                cursor.execute(view_sql)
                print(f"✅ Created view: {view_name}")
            except Exception as e:
                print(f"❌ Failed to create view {view_name}: {e}")
        
        conn.commit()

def get_pipeline_health() -> Dict[str, int]:
    """Get current pipeline health metrics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get each metric separately to avoid aggregate issues
        metrics = {}
        
        cursor.execute("SELECT COUNT(*) as count FROM v_canonicals_orphaned")
        metrics['canonicals_orphaned'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM v_recipes_missing_variations")
        metrics['recipes_missing_variations'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM v_recipes_missing_sessions")
        metrics['recipes_missing_sessions'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM v_sessions_missing_instructions")
        metrics['sessions_missing_instructions'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM v_recipes_ready_for_testing")
        metrics['recipes_ready_for_testing'] = cursor.fetchone()['count']
        
        return metrics

def get_incomplete_items(view_name: str) -> list:
    """Get items from a specific incomplete items view"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {view_name}")
        results = cursor.fetchall()
        
        return results