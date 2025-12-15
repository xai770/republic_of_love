#!/usr/bin/env python3
"""
Entity Skill Resolver - Shared by WF3001 and WF1127

Resolves raw skill names to entity_id.
Pattern: Try match → if no match → queue for WF3005

Usage (as script actor):
    result = execute({'skills': ['Python', 'Machine Learning']}, db_conn)
    # Returns: {'resolved': {skill: entity_id}, 'pending': [skills]}

Usage (as class):
    resolver = SkillResolver(db_conn)
    entity_id = resolver.resolve("Machine Learning")
    # Returns entity_id if match found, else None (and queues for pending)

Author: Sandy
Date: December 8, 2025
"""

import json
from typing import Optional

from core.database import fetch_scalar


class SkillResolver:
    """
    Resolves raw skill names to entity_id.
    
    Resolution order:
    1. Check in-memory cache (for batch efficiency)
    2. Check entity_aliases (exact lowercase match)
    3. Check entities.canonical_name (normalized match)
    4. If no match: insert into entities_pending, return None
    
    Note: Only returns active entities. Merged entities are filtered out.
    TODO: If we add resolve_by_id(entity_id), follow merged_into_entity_id chain.
    """
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self._cache = {}  # normalized_alias → entity_id
        self._pending_count = 0
        
    def resolve(self, raw_skill_name: str, source_context: dict = None) -> Optional[int]:
        """
        Resolve a raw skill name to an entity_id.
        
        Args:
            raw_skill_name: The skill name to resolve
            source_context: Optional context (posting_id, source, etc.)
            
        Returns:
            entity_id if match found, None if queued to entities_pending
        """
        if not raw_skill_name or not raw_skill_name.strip():
            return None
            
        normalized = self._normalize(raw_skill_name)
        
        # Check cache first (batch efficiency)
        if normalized in self._cache:
            return self._cache[normalized]
        
        cursor = self.db_conn.cursor()
        
        # 1. Check entity_aliases (exact lowercase match)
        cursor.execute("""
            SELECT e.entity_id 
            FROM entity_aliases ea
            JOIN entities e ON ea.entity_id = e.entity_id
            WHERE LOWER(ea.alias) = %s
              AND e.entity_type = 'skill'
              AND e.status = 'active'
            LIMIT 1
        """, (normalized,))
        
        row = cursor.fetchone()
        if row:
            entity_id = row['entity_id'] if isinstance(row, dict) else row[0]
            self._cache[normalized] = entity_id
            cursor.close()
            return entity_id
        
        # 2. Check entities.canonical_name (normalized)
        cursor.execute("""
            SELECT entity_id 
            FROM entities
            WHERE LOWER(REPLACE(canonical_name, '_', ' ')) = %s
              AND entity_type = 'skill'
              AND status = 'active'
            LIMIT 1
        """, (normalized.replace('_', ' '),))
        
        row = cursor.fetchone()
        if row:
            entity_id = row['entity_id'] if isinstance(row, dict) else row[0]
            self._cache[normalized] = entity_id
            # Also add as alias for future matches
            self._add_alias(entity_id, normalized, cursor)
            cursor.close()
            return entity_id
        
        # 3. No match - queue for WF3005
        self._queue_pending(raw_skill_name, source_context, cursor)
        cursor.close()
        return None
    
    def resolve_batch(self, skills: list, source_context: dict = None) -> dict:
        """
        Resolve multiple skills efficiently.
        
        Returns:
            {
                'resolved': {raw_skill_name: entity_id, ...},
                'pending': [raw_skill_names that were queued]
            }
        """
        resolved = {}
        pending = []
        
        for skill in skills:
            entity_id = self.resolve(skill, source_context)
            if entity_id:
                resolved[skill] = entity_id
            else:
                pending.append(skill)
        
        return {
            'resolved': resolved,
            'pending': pending,
            'resolved_count': len(resolved),
            'pending_count': len(pending)
        }
    
    def get_pending_count(self) -> int:
        """Get total pending skills count (for WF3005 trigger check)."""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities_pending WHERE status = 'pending'")
        count = fetch_scalar(cursor)
        cursor.close()
        return count
    
    def _normalize(self, s: str) -> str:
        """Normalize skill name for matching."""
        return s.lower().strip()
    
    def _add_alias(self, entity_id: int, alias: str, cursor):
        """Add a new alias for an entity (when found via canonical_name)."""
        try:
            cursor.execute("""
                INSERT INTO entity_aliases (entity_id, alias, language, alias_type, confidence, created_by)
                VALUES (%s, %s, 'en', 'resolved', 0.9, 'skill_resolver')
                ON CONFLICT (alias, language) DO NOTHING
            """, (entity_id, alias))
            self.db_conn.commit()
        except Exception:
            self.db_conn.rollback()
    
    def _queue_pending(self, raw_skill_name: str, source_context: dict, cursor):
        """Queue skill for WF3005 classification."""
        try:
            cursor.execute("""
                INSERT INTO entities_pending (entity_type, raw_value, source_context, status, created_at)
                VALUES ('skill', %s, %s::jsonb, 'pending', NOW())
                ON CONFLICT (entity_type, raw_value) DO NOTHING
            """, (raw_skill_name, json.dumps(source_context or {})))
            self.db_conn.commit()
            self._pending_count += 1
        except Exception:
            self.db_conn.rollback()


def execute(interaction_data: dict, db_conn=None) -> dict:
    """
    Script actor interface for entity_skill_resolver.
    
    Input:
        interaction_data: {
            'skills': ['Python', 'Machine Learning', ...],
            'source': 'posting' | 'profile',
            'source_id': posting_id or profile_id
        }
        
    Output:
        {
            'status': 'success',
            'resolved': {'Python': 8431, ...},
            'pending': ['New Skill 1', ...],
            'resolved_count': N,
            'pending_count': M,
            'total_pending': X  # Total in entities_pending
        }
    """
    if not db_conn:
        return {"status": "error", "error": "No database connection"}
    
    try:
        skills = interaction_data.get('skills', [])
        source = interaction_data.get('source', 'unknown')
        source_id = interaction_data.get('source_id')
        
        if not skills:
            return {
                "status": "success",
                "resolved": {},
                "pending": [],
                "resolved_count": 0,
                "pending_count": 0,
                "message": "No skills provided"
            }
        
        # Build source context
        source_context = {
            "source": source,
            "source_id": source_id,
            "resolved_at": None  # Will be filled when WF3005 processes
        }
        
        # Resolve skills
        resolver = SkillResolver(db_conn)
        result = resolver.resolve_batch(skills, source_context)
        
        # Check if WF3005 should be triggered
        total_pending = resolver.get_pending_count()
        
        return {
            "status": "success",
            "resolved": result['resolved'],
            "pending": result['pending'],
            "resolved_count": result['resolved_count'],
            "pending_count": result['pending_count'],
            "total_pending": total_pending,
            "trigger_wf3005": total_pending >= 50
        }
        
    except Exception as e:
        if db_conn:
            db_conn.rollback()
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Test mode
    import psycopg2
    import os
    
    conn = psycopg2.connect(
        dbname='turing',
        user=os.environ.get('PGUSER', 'postgres'),
        password=os.environ.get('PGPASSWORD', ''),
        host=os.environ.get('PGHOST', 'localhost')
    )
    
    test_skills = ['Python', 'Machine Learning', 'Unknown Skill XYZ', 'Data Analysis']
    result = execute({'skills': test_skills, 'source': 'test'}, db_conn=conn)
    
    print(json.dumps(result, indent=2))
    conn.close()
