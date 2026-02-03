#!/usr/bin/env python3
"""
navigator.py - OWL Navigator Library for Clara
===============================================

Provides programmatic access to the OWL hierarchy for classification actors.
This is the library that Clara (and other classifiers) use to navigate.

Usage:
------
    from core.navigator import Navigator
    
    nav = Navigator(conn)
    
    # Get current position info
    state = nav.get_state()
    
    # Navigate
    nav.go_to(folder_id)
    nav.go_up()
    nav.go_to_root()
    
    # Get options at current position
    subfolders = nav.get_subfolders()
    entities = nav.get_entities_here()
    
    # Place an entity
    nav.place_entity(owl_id)
    
    # Propose new folder
    result = nav.propose_folder("new_folder_name")

Author: Sandy
Date: 2026-01-19
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

import psycopg2
import psycopg2.extras


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NavState:
    """Current navigation state."""
    current_owl_id: Optional[int] = None  # None = ROOT
    current_name: str = "ROOT"
    path: List[str] = field(default_factory=list)
    path_ids: List[int] = field(default_factory=list)
    depth: int = 0


@dataclass
class FolderInfo:
    """Information about a folder."""
    owl_id: int
    canonical_name: str
    display_name: str
    owl_type: str
    child_count: int
    entity_count: int


@dataclass
class EntityInfo:
    """Information about an entity."""
    owl_id: int
    canonical_name: str
    display_name: str
    owl_type: str


# =============================================================================
# NAVIGATOR CLASS
# =============================================================================

class Navigator:
    """
    OWL Hierarchy Navigator for classification actors.
    
    Provides a programmatic interface to navigate the taxonomy hierarchy,
    view subfolders and entities, and place entities in folders.
    """
    
    # Maximum hierarchy depth (prevent infinite loops)
    MAX_DEPTH = 10
    
    # Root folder types (treated as top-level categories)
    ROOT_TYPES = ('folder', 'category', 'taxonomy_root')
    
    def __init__(self, conn, classifying_owl_id: Optional[int] = None):
        """
        Initialize Navigator.
        
        Args:
            conn: Database connection
            classifying_owl_id: The entity being classified (for display)
        """
        self.conn = conn
        self.classifying_owl_id = classifying_owl_id
        self.classifying_info: Optional[EntityInfo] = None
        self.state = NavState()
        
        if classifying_owl_id:
            self._load_classifying_info()
    
    def _load_classifying_info(self):
        """Load info about the entity being classified."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT o.owl_id, o.canonical_name, o.owl_type,
                   COALESCE(n.display_name, o.canonical_name) as display_name
            FROM owl o
            LEFT JOIN owl_names n ON o.owl_id = n.owl_id AND n.is_primary = true
            WHERE o.owl_id = %s
        """, (self.classifying_owl_id,))
        row = cursor.fetchone()
        if row:
            self.classifying_info = EntityInfo(
                owl_id=row['owl_id'],
                canonical_name=row['canonical_name'],
                display_name=row['display_name'],
                owl_type=row['owl_type']
            )
    
    # =========================================================================
    # NAVIGATION METHODS
    # =========================================================================
    
    def go_to(self, folder_id: int) -> bool:
        """
        Navigate to a specific folder.
        
        Returns True if successful, False if folder doesn't exist or isn't navigable.
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT owl_id, canonical_name, owl_type
            FROM owl
            WHERE owl_id = %s AND status = 'active'
        """, (folder_id,))
        row = cursor.fetchone()
        
        if not row:
            return False
        
        # Update state
        self.state.current_owl_id = row['owl_id']
        self.state.current_name = row['canonical_name']
        
        # Rebuild path
        self._rebuild_path()
        
        return True
    
    def go_up(self) -> bool:
        """
        Navigate up one level.
        
        Returns True if successful, False if already at root.
        """
        if self.state.current_owl_id is None:
            return False  # Already at root
        
        # Find parent
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT related_owl_id
            FROM owl_relationships
            WHERE owl_id = %s AND relationship = 'belongs_to'
            LIMIT 1
        """, (self.state.current_owl_id,))
        row = cursor.fetchone()
        
        if row:
            return self.go_to(row['related_owl_id'])
        else:
            # No parent - go to root
            return self.go_to_root()
    
    def go_to_root(self) -> bool:
        """Navigate to root level."""
        self.state = NavState()
        return True
    
    def _rebuild_path(self):
        """Rebuild the path from root to current position."""
        if self.state.current_owl_id is None:
            self.state.path = []
            self.state.path_ids = []
            self.state.depth = 0
            return
        
        path = []
        path_ids = []
        current = self.state.current_owl_id
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Walk up the tree
        visited = set()
        while current and len(path) < self.MAX_DEPTH:
            if current in visited:
                break  # Cycle detection
            visited.add(current)
            
            cursor.execute("""
                SELECT o.owl_id, o.canonical_name, r.related_owl_id as parent_id
                FROM owl o
                LEFT JOIN owl_relationships r ON o.owl_id = r.owl_id 
                    AND r.relationship = 'belongs_to'
                WHERE o.owl_id = %s
            """, (current,))
            row = cursor.fetchone()
            
            if not row:
                break
            
            path.insert(0, row['canonical_name'])
            path_ids.insert(0, row['owl_id'])
            current = row['parent_id']
        
        self.state.path = path
        self.state.path_ids = path_ids
        self.state.depth = len(path)
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_state(self) -> NavState:
        """Get current navigation state."""
        return self.state
    
    def get_subfolders(self) -> List[FolderInfo]:
        """Get subfolders of current position."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        if self.state.current_owl_id is None:
            # At ROOT - show only taxonomy_root entries as top-level categories
            cursor.execute("""
                SELECT o.owl_id, o.canonical_name, o.owl_type,
                       COALESCE(n.display_name, o.canonical_name) as display_name,
                       (SELECT COUNT(*) FROM owl_relationships r2 
                        WHERE r2.related_owl_id = o.owl_id 
                        AND r2.relationship = 'belongs_to') as child_count,
                       0 as entity_count
                FROM owl o
                LEFT JOIN owl_names n ON o.owl_id = n.owl_id AND n.is_primary = true
                WHERE o.owl_type = 'taxonomy_root'
                  AND o.status = 'active'
                ORDER BY 
                    CASE o.canonical_name
                        WHEN 'all_skills' THEN 1
                        WHEN 'certificates' THEN 2
                        WHEN 'industry_domains' THEN 3
                        WHEN 'seniority_contexts' THEN 4
                        ELSE 5
                    END
            """)
        else:
            # Get children of current folder
            cursor.execute("""
                SELECT o.owl_id, o.canonical_name, o.owl_type,
                       COALESCE(n.display_name, o.canonical_name) as display_name,
                       (SELECT COUNT(*) FROM owl_relationships r2 
                        WHERE r2.related_owl_id = o.owl_id 
                        AND r2.relationship = 'belongs_to') as child_count,
                       0 as entity_count
                FROM owl o
                JOIN owl_relationships r ON o.owl_id = r.owl_id
                LEFT JOIN owl_names n ON o.owl_id = n.owl_id AND n.is_primary = true
                WHERE r.related_owl_id = %s
                  AND r.relationship = 'belongs_to'
                  AND o.owl_type IN ('folder', 'category', 'skill_dimension')
                  AND o.status = 'active'
                ORDER BY o.canonical_name
            """, (self.state.current_owl_id,))
        
        return [
            FolderInfo(
                owl_id=r['owl_id'],
                canonical_name=r['canonical_name'],
                display_name=r['display_name'],
                owl_type=r['owl_type'],
                child_count=r['child_count'],
                entity_count=r['entity_count']
            )
            for r in cursor.fetchall()
        ]
    
    def get_entities_here(self) -> List[EntityInfo]:
        """Get non-folder entities at current position."""
        if self.state.current_owl_id is None:
            return []  # No entities at root
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT o.owl_id, o.canonical_name, o.owl_type,
                   COALESCE(n.display_name, o.canonical_name) as display_name
            FROM owl o
            JOIN owl_relationships r ON o.owl_id = r.owl_id
            LEFT JOIN owl_names n ON o.owl_id = n.owl_id AND n.is_primary = true
            WHERE r.related_owl_id = %s
              AND r.relationship = 'belongs_to'
              AND o.owl_type NOT IN ('folder', 'category', 'taxonomy_root', 'skill_dimension')
              AND o.status = 'active'
            ORDER BY o.canonical_name
            LIMIT 50
        """, (self.state.current_owl_id,))
        
        return [
            EntityInfo(
                owl_id=r['owl_id'],
                canonical_name=r['canonical_name'],
                display_name=r['display_name'],
                owl_type=r['owl_type']
            )
            for r in cursor.fetchall()
        ]
    
    def search_folders(self, query: str, limit: int = 10) -> List[FolderInfo]:
        """Search for folders by name."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Normalize query
        query_norm = query.lower().replace(' ', '_')
        
        cursor.execute("""
            SELECT o.owl_id, o.canonical_name, o.owl_type,
                   COALESCE(n.display_name, o.canonical_name) as display_name,
                   0 as child_count, 0 as entity_count
            FROM owl o
            LEFT JOIN owl_names n ON o.owl_id = n.owl_id AND n.is_primary = true
            WHERE o.owl_type IN ('folder', 'category', 'taxonomy_root')
              AND o.status = 'active'
              AND (o.canonical_name ILIKE %s OR n.display_name ILIKE %s)
            ORDER BY 
                CASE WHEN o.canonical_name = %s THEN 0
                     WHEN o.canonical_name ILIKE %s THEN 1
                     ELSE 2 END,
                o.canonical_name
            LIMIT %s
        """, (f'%{query_norm}%', f'%{query}%', query_norm, f'{query_norm}%', limit))
        
        return [
            FolderInfo(
                owl_id=r['owl_id'],
                canonical_name=r['canonical_name'],
                display_name=r['display_name'],
                owl_type=r['owl_type'],
                child_count=r['child_count'],
                entity_count=r['entity_count']
            )
            for r in cursor.fetchall()
        ]
    
    # =========================================================================
    # ACTION METHODS
    # =========================================================================
    
    def place_entity(self, owl_id: int, commit: bool = True) -> Dict[str, Any]:
        """
        Place an entity in the current folder.
        
        Returns result dict with status and details.
        """
        if self.state.current_owl_id is None:
            return {
                'success': False,
                'error': 'Cannot place entity at ROOT level'
            }
        
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check entity exists
        cursor.execute("""
            SELECT owl_id, canonical_name FROM owl WHERE owl_id = %s AND status IN ('active', 'pending_review')
        """, (owl_id,))
        entity = cursor.fetchone()
        
        if not entity:
            return {
                'success': False,
                'error': f'Entity {owl_id} not found'
            }
        
        # Check if already placed here
        cursor.execute("""
            SELECT 1 FROM owl_relationships
            WHERE owl_id = %s AND related_owl_id = %s AND relationship = 'belongs_to'
        """, (owl_id, self.state.current_owl_id))
        
        if cursor.fetchone():
            return {
                'success': True,
                'action': 'already_placed',
                'owl_id': owl_id,
                'parent_owl_id': self.state.current_owl_id,
                'path': self.state.path
            }
        
        # Create relationship
        cursor.execute("""
            INSERT INTO owl_relationships (owl_id, related_owl_id, relationship, 
                                          strength, is_primary, created_by)
            VALUES (%s, %s, 'belongs_to', 1.0, true, 'Clara')
            ON CONFLICT DO NOTHING
        """, (owl_id, self.state.current_owl_id))
        
        if commit:
            self.conn.commit()
        
        return {
            'success': True,
            'action': 'placed',
            'owl_id': owl_id,
            'parent_owl_id': self.state.current_owl_id,
            'path': self.state.path
        }
    
    def create_folder(self, name: str, commit: bool = True) -> Dict[str, Any]:
        """
        Create a new folder at current position.
        
        Note: This should only be called after Vera validates and Victor approves.
        
        Returns result dict with new folder info.
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if folder already exists
        cursor.execute("""
            SELECT owl_id FROM owl WHERE canonical_name = %s AND status = 'active'
        """, (name,))
        existing = cursor.fetchone()
        
        if existing:
            return {
                'success': False,
                'error': f'Folder {name} already exists (owl_id={existing["owl_id"]})',
                'existing_owl_id': existing['owl_id']
            }
        
        # Create folder entity
        cursor.execute("""
            INSERT INTO owl (canonical_name, owl_type, status, created_by)
            VALUES (%s, 'folder', 'active', 'Clara')
            RETURNING owl_id
        """, (name,))
        new_owl_id = cursor.fetchone()['owl_id']
        
        # Create owl_names entry
        cursor.execute("""
            INSERT INTO owl_names (owl_id, display_name, name_type, is_primary, 
                                  confidence, created_by)
            VALUES (%s, %s, 'canonical', true, 1.0, 'Clara')
        """, (new_owl_id, name.replace('_', ' ').title()))
        
        # Link to parent (if not at root)
        if self.state.current_owl_id is not None:
            cursor.execute("""
                INSERT INTO owl_relationships (owl_id, related_owl_id, relationship,
                                              strength, is_primary, created_by)
                VALUES (%s, %s, 'belongs_to', 1.0, true, 'Clara')
            """, (new_owl_id, self.state.current_owl_id))
        
        if commit:
            self.conn.commit()
        
        return {
            'success': True,
            'action': 'folder_created',
            'owl_id': new_owl_id,
            'canonical_name': name,
            'parent_owl_id': self.state.current_owl_id,
            'path': self.state.path + [name]
        }
    
    # =========================================================================
    # DISPLAY METHODS (for LLM prompts)
    # =========================================================================
    
    def render_menu(self) -> str:
        """
        Render the Navigator menu as a text string for LLM consumption.
        
        This is what Clara sees when making decisions.
        """
        lines = []
        
        # Header
        lines.append("╔" + "═" * 70 + "╗")
        lines.append("║" + "SKILL TAXONOMY NAVIGATOR".center(70) + "║")
        lines.append("║" + " " * 70 + "║")
        
        # Current position
        if self.state.path:
            path_str = " → ".join(self.state.path)
        else:
            path_str = "ROOT"
        lines.append(f"║  📍 YOU ARE HERE: {path_str}".ljust(71) + "║")
        
        # Classifying entity
        if self.classifying_info:
            lines.append(f"║  🎯 CLASSIFYING: {self.classifying_info.display_name}".ljust(71) + "║")
        
        lines.append("╠" + "═" * 70 + "╣")
        
        # Subfolders
        subfolders = self.get_subfolders()
        if subfolders:
            lines.append("║" + " " * 70 + "║")
            folder_loc = self.state.current_name if self.state.current_owl_id else "ROOT"
            lines.append(f"║  SUBFOLDERS IN {folder_loc}:".ljust(71) + "║")
            for i, folder in enumerate(subfolders[:20], 1):
                child_info = f"({folder.child_count} children)" if folder.child_count else ""
                line = f"    [{i}] {folder.canonical_name} {child_info}"
                lines.append(f"║{line.ljust(70)}║")
            if len(subfolders) > 20:
                lines.append(f"║    ... and {len(subfolders) - 20} more (use [S] to search)".ljust(71) + "║")
        
        # Entities here
        entities = self.get_entities_here()
        if entities:
            lines.append("║" + " " * 70 + "║")
            lines.append("║  ENTITIES ALREADY HERE:".ljust(71) + "║")
            entity_names = ", ".join(e.canonical_name for e in entities[:10])
            if len(entities) > 10:
                entity_names += f", ... (+{len(entities) - 10} more)"
            # Word wrap
            while entity_names:
                chunk = entity_names[:65]
                if len(entity_names) > 65:
                    # Find last comma
                    last_comma = chunk.rfind(',')
                    if last_comma > 0:
                        chunk = entity_names[:last_comma + 1]
                lines.append(f"║    {chunk.ljust(66)}║")
                entity_names = entity_names[len(chunk):].lstrip(', ')
        
        # Commands
        lines.append("║" + " " * 70 + "║")
        lines.append("╠" + "═" * 70 + "╣")
        lines.append("║  COMMANDS:".ljust(71) + "║")
        lines.append("║    [1-20] → Enter subfolder by number".ljust(71) + "║")
        lines.append("║    [P]    → PLACE entity here (if this is the right folder)".ljust(71) + "║")
        lines.append("║    [N name] → Propose NEW subfolder (requires approval)".ljust(71) + "║")
        lines.append("║    [U]    → Go UP one level".ljust(71) + "║")
        lines.append("║    [T]    → Go to TOP (root)".ljust(71) + "║")
        lines.append("╚" + "═" * 70 + "╝")
        lines.append("")
        lines.append("Your choice: ")
        
        return "\n".join(lines)
    
    def execute_command(self, command: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Execute a Navigator command.
        
        Args:
            command: The command string (e.g., "[1]", "[P]", "[N] folder_name")
        
        Returns:
            (success, message, result_dict)
        """
        command = command.strip().upper()
        
        # Number command - enter subfolder
        if command.startswith('[') and command.endswith(']'):
            inner = command[1:-1]
            
            if inner.isdigit():
                num = int(inner)
                subfolders = self.get_subfolders()
                if 1 <= num <= len(subfolders):
                    folder = subfolders[num - 1]
                    self.go_to(folder.owl_id)
                    return True, f"Entered {folder.canonical_name}", None
                else:
                    return False, f"Invalid folder number: {num}", None
            
            elif inner == 'P':
                # Place entity
                if not self.classifying_owl_id:
                    return False, "No entity to place", None
                result = self.place_entity(self.classifying_owl_id)
                if result['success']:
                    return True, f"Placed entity in {self.state.current_name}", result
                else:
                    return False, result.get('error', 'Failed to place'), result
            
            elif inner == 'U':
                # Go up
                if self.go_up():
                    return True, f"Moved up to {self.state.current_name}", None
                else:
                    return False, "Already at root", None
            
            elif inner == 'T':
                # Go to root
                self.go_to_root()
                return True, "Returned to ROOT", None
            
            elif inner.startswith('N ') or inner.startswith('N]'):
                # Propose new folder - extract name
                # This is just navigation prep; actual creation needs Vera/Victor
                return True, "New folder proposal noted", {'action': 'propose_folder'}
            
            elif inner.startswith('S '):
                # Search with query
                query = inner[2:].strip()
                results = self.search_folders(query)
                return True, f"Found {len(results)} folders", {'folders': results}
            
            elif inner == 'S':
                # Bare [S] - cannot search without query
                return False, "Search requires a query: [S query]", None
        
        return False, f"Unknown command: {command}", None


# =============================================================================
# VERA - FOLDER NAME VALIDATOR (Script, no LLM)
# =============================================================================

class Vera:
    """
    Vera - The Folder Name Validator
    
    Validates proposed folder names against strict rules.
    No LLM - pure script validation.
    """
    
    # Banned words in folder names
    BANNED_WORDS = {
        'experience', 'years', 'skills', 'ability', 'abilities', 
        'knowledge', 'proficiency', 'proficient', 'expertise',
        'competency', 'competencies', 'understanding', 'familiar',
        'familiarity', 'strong', 'excellent', 'good', 'basic',
        'advanced', 'senior', 'junior', 'level', 'required'
    }
    
    # Maximum folder name length
    MAX_LENGTH = 50
    
    # Minimum folder name length
    MIN_LENGTH = 2
    
    @classmethod
    def validate(cls, name: str) -> Tuple[bool, str]:
        """
        Validate a proposed folder name.
        
        Returns:
            (is_valid, reason)
        """
        if not name:
            return False, "Empty name"
        
        # Strip whitespace
        name = name.strip()
        
        # Length check
        if len(name) < cls.MIN_LENGTH:
            return False, f"Too short (min {cls.MIN_LENGTH} chars)"
        
        if len(name) > cls.MAX_LENGTH:
            return False, f"Too long (max {cls.MAX_LENGTH} chars)"
        
        # ASCII only
        if not name.isascii():
            return False, "Non-ASCII characters detected"
        
        # Snake_case pattern
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            return False, "Must be snake_case (lowercase, underscores, start with letter)"
        
        # No double underscores
        if '__' in name:
            return False, "No double underscores allowed"
        
        # No trailing underscore
        if name.endswith('_'):
            return False, "Cannot end with underscore"
        
        # Banned words check
        words = set(name.split('_'))
        banned_found = words & cls.BANNED_WORDS
        if banned_found:
            return False, f"Contains banned word(s): {', '.join(banned_found)}"
        
        return True, "Valid"
    
    @classmethod
    def suggest_fix(cls, name: str) -> str:
        """
        Attempt to fix an invalid name.
        
        Returns the fixed name or empty string if unfixable.
        """
        if not name:
            return ""
        
        # Normalize
        fixed = name.lower().strip()
        
        # Replace spaces and hyphens with underscores
        fixed = re.sub(r'[\s\-]+', '_', fixed)
        
        # Remove non-alphanumeric except underscore
        fixed = re.sub(r'[^a-z0-9_]', '', fixed)
        
        # Collapse multiple underscores
        fixed = re.sub(r'_+', '_', fixed)
        
        # Strip leading/trailing underscores
        fixed = fixed.strip('_')
        
        # Remove banned words
        words = fixed.split('_')
        words = [w for w in words if w not in cls.BANNED_WORDS]
        fixed = '_'.join(words)
        
        # Ensure starts with letter
        if fixed and not fixed[0].isalpha():
            fixed = 'x_' + fixed
        
        return fixed if len(fixed) >= cls.MIN_LENGTH else ""
