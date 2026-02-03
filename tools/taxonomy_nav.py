#!/usr/bin/env python3
"""
Interactive Taxonomy Navigator

A human-usable version of the skill taxonomy navigator.
Lets you browse the hierarchy, see what's in each folder, and move skills.

Usage:
    python3 tools/taxonomy_nav.py                    # Browse mode (interactive)
    python3 tools/taxonomy_nav.py --skill "python"   # Classify a skill
    python3 tools/taxonomy_nav.py --move 12345       # Move a skill by owl_id

Non-interactive (for Copilot):
    python3 tools/taxonomy_nav.py ls                 # List root folders
    python3 tools/taxonomy_nav.py ls 39067           # List folder contents
    python3 tools/taxonomy_nav.py path 39150         # Show path to folder
    python3 tools/taxonomy_nav.py skills 39150       # List skills in folder
    python3 tools/taxonomy_nav.py search "cloud"     # Search folders by name
    python3 tools/taxonomy_nav.py tree               # Show full tree (compact)
    python3 tools/taxonomy_nav.py tree 39067         # Show subtree from folder
    python3 tools/taxonomy_nav.py navlog             # Show navigation log & metrics
    python3 tools/taxonomy_nav.py navlog 50          # Show more log entries

Commands (interactive):
    [1-9]  - Enter subfolder
    [U]    - Go up one level  
    [L]    - List skills in current folder
    [P]    - Place/move skill here
    [S]    - Search for folder by name
    [N]    - New subfolder (with validation)
    [D]    - Move to _trash (when classifying)
    [H]    - Request human help
    [?]    - About this project
    [T]    - Taxonomy statistics
    [Q]    - Quit

Minimal version per Sandy's spec: [L], [P], [U], [Q]
"""
import argparse
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection


# Constants
SKILL_ROOT_ID = 39066  # The 'skill' entity - taxonomy root

# Session tracking (for nav logging)
SESSION_ID = str(uuid.uuid4())[:8]  # Short session ID
ACTOR = 'human'  # Can be overridden via --actor flag


def log_nav_action(action: str, folder_id: int, conn, depth: int = None, folder_path: str = None):
    """Log a navigation action to nav_log table."""
    try:
        with conn.cursor() as cur:
            # Get path if not provided
            if folder_path is None:
                path_parts = get_breadcrumb_path(folder_id, conn)
                folder_path = '/'.join([name for _, name in path_parts]) if path_parts else 'ROOT'
            
            # Get depth if not provided  
            if depth is None:
                path_parts = get_breadcrumb_path(folder_id, conn)
                depth = len(path_parts)
            
            cur.execute("""
                INSERT INTO nav_log (session_id, actor, action, folder_id, folder_path, depth)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (SESSION_ID, ACTOR, action, folder_id, folder_path, depth))
            conn.commit()
    except Exception as e:
        # Don't let logging failures break navigation
        pass


def get_folder_info(folder_id: int, conn) -> dict:
    """Get folder details."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT owl_id, canonical_name, owl_type, status
            FROM owl WHERE owl_id = %s
        """, (folder_id,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)


def get_breadcrumb_path(folder_id: int, conn) -> list:
    """Get path from root to folder as list of (id, name) tuples."""
    path = []
    current = folder_id
    
    with conn.cursor() as cur:
        while current and current != SKILL_ROOT_ID:
            cur.execute("""
                SELECT e.owl_id, e.canonical_name, er.related_owl_id
                FROM owl e
                LEFT JOIN owl_relationships er ON e.owl_id = er.owl_id AND er.relationship = 'is_a'
                WHERE e.owl_id = %s
            """, (current,))
            row = cur.fetchone()
            if not row:
                break
            path.insert(0, (row['owl_id'], row['canonical_name']))
            current = row['related_owl_id']
    
    return path


def get_subfolders(folder_id: int, conn) -> list:
    """Get child folders."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.owl_id, e.canonical_name,
                   (SELECT COUNT(*) FROM owl_relationships er2 
                    JOIN owl e2 ON e2.owl_id = er2.owl_id
                    WHERE er2.related_owl_id = e.owl_id 
                    AND er2.relationship = 'belongs_to'
                    AND e2.owl_type = 'skill' AND e2.status = 'active') as skill_count,
                   (SELECT COUNT(*) FROM owl_relationships er3 
                    WHERE er3.related_owl_id = e.owl_id AND er3.relationship = 'is_a') as subfolder_count
            FROM owl e
            JOIN owl_relationships er ON e.owl_id = er.owl_id
            WHERE er.related_owl_id = %s
            AND er.relationship = 'is_a'
            AND e.owl_type = 'skill_group'
            AND e.status = 'active'
            ORDER BY e.canonical_name
        """, (folder_id,))
        return [dict(row) for row in cur.fetchall()]


def get_skills_in_folder(folder_id: int, conn, limit: int = 50) -> list:
    """Get skills in this folder."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.owl_id, e.canonical_name, e.created_at
            FROM owl e
            JOIN owl_relationships er ON e.owl_id = er.owl_id
            WHERE er.related_owl_id = %s
            AND er.relationship = 'belongs_to'
            AND e.owl_type = 'skill'
            AND e.status = 'active'
            ORDER BY e.canonical_name
            LIMIT %s
        """, (folder_id, limit))
        return [dict(row) for row in cur.fetchall()]


def count_skills_in_folder(folder_id: int, conn) -> int:
    """Count total skills in folder."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt FROM owl_relationships er
            JOIN owl e ON e.owl_id = er.owl_id
            WHERE er.related_owl_id = %s
            AND er.relationship = 'belongs_to'
            AND e.owl_type = 'skill'
            AND e.status = 'active'
        """, (folder_id,))
        return cur.fetchone()['cnt']


def get_skill_current_folder(owl_id: int, conn) -> tuple:
    """Get the folder a skill is currently in. Returns (folder_id, folder_name) or (None, None)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT er.related_owl_id, e.canonical_name
            FROM owl_relationships er
            JOIN owl e ON e.owl_id = er.related_owl_id
            WHERE er.owl_id = %s AND er.relationship = 'belongs_to'
        """, (owl_id,))
        row = cur.fetchone()
        if row:
            return row['related_owl_id'], row['canonical_name']
        return None, None


def move_skill_to_folder(owl_id: int, new_folder_id: int, conn) -> bool:
    """Move a skill to a new folder."""
    with conn.cursor() as cur:
        # Remove existing belongs_to relationship
        cur.execute("""
            DELETE FROM owl_relationships
            WHERE owl_id = %s AND relationship = 'belongs_to'
        """, (owl_id,))
        
        # Add new belongs_to relationship
        cur.execute("""
            INSERT INTO owl_relationships (owl_id, related_owl_id, relationship, created_by)
            VALUES (%s, %s, 'belongs_to', 'taxonomy_nav')
        """, (owl_id, new_folder_id))
        
        conn.commit()
        return True


def search_folders(query: str, conn, limit: int = 20) -> list:
    """Search for folders by name."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT e.owl_id, e.canonical_name,
                   (SELECT COUNT(*) FROM owl_relationships er2 
                    WHERE er2.related_owl_id = e.owl_id AND er2.relationship = 'belongs_to') as skill_count
            FROM owl e
            WHERE e.owl_type = 'skill_group'
            AND e.status = 'active'
            AND e.canonical_name ILIKE %s
            ORDER BY e.canonical_name
            LIMIT %s
        """, (f"%{query}%", limit))
        return [dict(row) for row in cur.fetchall()]


def validate_folder_name(name: str) -> tuple[bool, str]:
    """
    Vera-style validation for folder names.
    Returns (is_valid, error_message).
    """
    import re
    
    # Must be snake_case (no trailing underscore, no double underscore)
    if not re.match(r'^[a-z][a-z0-9]*(_[a-z0-9]+)*$', name):
        return False, "Must be snake_case (lowercase letters, numbers, single underscores between words)"
    
    # Length check
    if len(name) < 3:
        return False, "Too short (min 3 characters)"
    if len(name) > 40:
        return False, "Too long (max 40 characters)"
    
    # Banned words (too generic or experience/duration indicators)
    banned = ['experience', 'years', 'year', 'duration', 'senior', 'junior', 
              'level', 'technology', 'technologies', 'skill', 'skills', 'other']
    for word in banned:
        if word == name or name.startswith(word + '_') or name.endswith('_' + word) or f'_{word}_' in name:
            return False, f"Contains banned word: '{word}'"
    
    return True, ""


def check_duplicate_folder(name: str, conn) -> list:
    """
    Victor-style duplicate check.
    Returns list of similar existing folders.
    """
    # Normalize for comparison
    normalized = name.lower().replace('_', '').replace('-', '')
    
    similar = []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT owl_id, canonical_name FROM owl
            WHERE owl_type = 'skill_group' AND status = 'active'
        """)
        for row in cur.fetchall():
            existing_norm = row['canonical_name'].lower().replace('_', '').replace('-', '')
            
            # Exact match after normalization
            if normalized == existing_norm:
                similar.append((row['owl_id'], row['canonical_name'], 'exact'))
                continue
            
            # Substring match
            if normalized in existing_norm or existing_norm in normalized:
                similar.append((row['owl_id'], row['canonical_name'], 'substring'))
    
    return similar


def find_similar_skills(skill_name: str, conn, limit: int = 5) -> list:
    """
    Find skills with similar names in the taxonomy.
    Helps agents understand what's already classified.
    """
    # Normalize for comparison
    words = skill_name.lower().replace('_', ' ').replace('-', ' ').split()
    
    similar = []
    with conn.cursor() as cur:
        # Search for skills containing any of the words
        for word in words:
            if len(word) < 3:
                continue
            cur.execute("""
                SELECT e.owl_id, e.canonical_name, 
                       (SELECT sg.canonical_name FROM owl sg 
                        JOIN owl_relationships er ON sg.owl_id = er.related_owl_id
                        WHERE er.owl_id = e.owl_id AND er.relationship = 'is_a'
                        LIMIT 1) as folder_name
                FROM owl e
                WHERE e.owl_type = 'skill' AND e.status = 'active'
                AND e.canonical_name ILIKE %s
                LIMIT %s
            """, (f"%{word}%", limit))
            for row in cur.fetchall():
                if row['owl_id'] not in [s[0] for s in similar]:
                    similar.append((row['owl_id'], row['canonical_name'], row['folder_name']))
                    if len(similar) >= limit:
                        break
            if len(similar) >= limit:
                break
    
    return similar[:limit]


def request_human_help(skill_name: str, skill_id: int, current_folder_id: int, 
                        reason: str, conn) -> bool:
    """
    [H] Help command - flag a skill for human review.
    Creates a help request record so humans know an agent got stuck.
    """
    folder_info = get_folder_info(current_folder_id, conn)
    folder_name = folder_info['canonical_name'] if folder_info else 'ROOT'
    
    # Store in a simple log format (could be a table later)
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    
    help_file = Path("logs/taxonomy_help_requests.log")
    help_file.parent.mkdir(exist_ok=True)
    
    with open(help_file, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"HELP REQUEST: {timestamp}\n")
        f.write(f"Skill: {skill_name} (ID: {skill_id})\n")
        f.write(f"Current location: {folder_name} (ID: {current_folder_id})\n")
        f.write(f"Reason: {reason}\n")
        f.write(f"{'='*60}\n")
    
    print(f"\n  📨 Help request logged!")
    print(f"  A human will review: {skill_name}")
    print(f"  Your note: {reason[:60]}..." if len(reason) > 60 else f"  Your note: {reason}")
    
    return True


def create_new_folder(parent_folder_id: int, conn) -> int | None:
    """
    Create a new folder as child of current folder.
    Includes Vera (validation) and Victor (duplicate check).
    Returns new folder_id or None if cancelled.
    """
    folder_info = get_folder_info(parent_folder_id, conn)
    parent_name = folder_info['canonical_name'] if folder_info else 'ROOT'
    
    print()
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║  [N] CREATE NEW SUBFOLDER                                              ║")
    print(f"║  Parent: {parent_name:<61}║")
    print("╠════════════════════════════════════════════════════════════════════════╣")
    print("║  Requirements:                                                         ║")
    print("║    • snake_case (lowercase, underscores)                               ║")
    print("║    • 3-40 characters                                                   ║")
    print("║    • No banned words (experience, years, etc.)                         ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")
    print()
    
    name = input("  Folder name (or Enter to cancel): ").strip().lower()
    if not name:
        print("  Cancelled.")
        return None
    
    # Vera: Validate format
    valid, error = validate_folder_name(name)
    if not valid:
        print(f"  ❌ Vera says: {error}")
        return None
    
    # Victor: Check duplicates
    similar = check_duplicate_folder(name, conn)
    if similar:
        print(f"\n  ⚠️  Victor found similar folders:")
        for eid, ename, match_type in similar:
            print(f"     [{eid}] {ename} ({match_type} match)")
        
        confirm = input("\n  Create anyway? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("  Cancelled.")
            return None
    
    # Create the folder
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO owl (owl_type, canonical_name, created_by, status)
            VALUES ('skill_group', %s, 'taxonomy_nav', 'active')
            RETURNING owl_id
        """, (name,))
        new_id = cur.fetchone()['owl_id']
        
        # Create is_a relationship to parent (NO ORPHAN!)
        cur.execute("""
            INSERT INTO owl_relationships (owl_id, related_owl_id, relationship, created_by)
            VALUES (%s, %s, 'is_a', 'taxonomy_nav')
        """, (new_id, parent_folder_id))
    
    conn.commit()
    print(f"\n  ✅ Created '{name}' (ID: {new_id}) under {parent_name}")
    return new_id


def display_menu(folder_id: int, conn, skill_to_classify: str = None, skill_entity_id: int = None):
    """Display the navigation menu."""
    path = get_breadcrumb_path(folder_id, conn)
    subfolders = get_subfolders(folder_id, conn)
    skill_count = count_skills_in_folder(folder_id, conn)
    skills_here = get_skills_in_folder(folder_id, conn, limit=8)
    folder_info = get_folder_info(folder_id, conn)
    folder_name = folder_info['canonical_name'] if folder_info else 'ROOT'
    
    # Build path string
    if path:
        path_str = "ROOT > " + " > ".join([name for _, name in path])
    else:
        path_str = "ROOT"
    
    depth = len(path)
    
    print()
    print("=" * 72)
    print("SKILL TAXONOMY NAVIGATOR")
    print("=" * 72)
    print(f"PATH: {path_str}")
    
    if skill_to_classify:
        print(f"CLASSIFYING: {skill_to_classify}")
    elif skill_entity_id:
        print(f"MOVING SKILL: {skill_entity_id}")
    
    if depth >= 8:
        print(f"WARNING: {depth} levels deep - consider placing here")
    
    print("-" * 72)
    
    if subfolders:
        print("SUBFOLDERS:")
        for i, sf in enumerate(subfolders[:12], 1):
            sub_indicator = f" [+{sf['subfolder_count']}]" if sf['subfolder_count'] > 0 else ""
            print(f"  [{i:2}] {sf['canonical_name']} ({sf['skill_count']} skills){sub_indicator}")
        if len(subfolders) > 12:
            print(f"  ... and {len(subfolders) - 12} more subfolders")
        print()
        # Show skills summary when there are subfolders
        if skills_here:
            print("SKILLS HERE:")
            skills_str = ", ".join([s['canonical_name'][:25] for s in skills_here])
            if skill_count > 8:
                skills_str += f" (+{skill_count - 8} more)"
            print(f"  {skills_str}")
        else:
            print("SKILLS HERE: (none)")
    else:
        # No subfolders - show full skill list automatically!
        print("(no subfolders)")
        print()
        if skill_count > 0:
            print(f"SKILLS HERE ({skill_count} total):")
            all_skills = get_skills_in_folder(folder_id, conn, limit=50)
            for i, s in enumerate(all_skills, 1):
                print(f"  {i:2}. [{s['owl_id']}] {s['canonical_name']}")
            if skill_count > 50:
                print(f"  ... and {skill_count - 50} more")
        else:
            print("SKILLS HERE: (none)")
    
    # Show similar skills hint when classifying
    if skill_to_classify:
        similar = find_similar_skills(skill_to_classify, conn, limit=3)
        if similar:
            print()
            print("SIMILAR SKILLS IN TAXONOMY:")
            for eid, sname, folder in similar:
                folder_hint = folder if folder else '(root)'
                print(f"  {sname[:30]} -> {folder_hint}")
    
    print("-" * 72)
    print("COMMANDS:")
    print("  [1-99] Enter subfolder    [L] List all skills    [S] Search folders")
    print("  [N] New subfolder         [U] Go up              [Q] Quit")
    if skill_to_classify or skill_entity_id:
        print("  [P] Place skill here      [H] I need help         [D] Trash skill")
    print("  [?] About this project    [T] Taxonomy stats")
    print("=" * 72)
    print()


def show_about():
    """Show project context - helps LLM agents understand what they're doing."""
    print()
    print("=" * 72)
    print("ABOUT THIS PROJECT: talent.yoga")
    print("=" * 72)
    print()
    print("  We match real jobs with real people and help them apply.")
    print()
    print("  HOW IT WORKS:")
    print("  1. Job postings mention skills (\"Python\", \"project management\")")
    print("  2. Candidate profiles list skills too")
    print("  3. We connect BOTH to this unified skill taxonomy")
    print("  4. Then we can match: posting <-> skills <-> profile")
    print()
    print("  YOUR TASK AS NAVIGATOR:")
    print("  - Place skills from job postings into the right folder")
    print("  - Create new folders [N] when needed (but not too deep!)")
    print("  - Flag ambiguous cases [H] for human review")
    print("  - Trash [D] things that aren't skills (experience requirements, etc.)")
    print()
    print("  GOOD SKILL: \"kubernetes\", \"financial modeling\", \"team leadership\"")
    print("  NOT A SKILL: \"5 years experience\", \"Bachelor's degree\", \"competitive salary\"")
    print()
    print("=" * 72)
    print()


def show_stats(conn):
    """Show taxonomy statistics."""
    with conn.cursor() as cur:
        # Count folders
        cur.execute("SELECT COUNT(*) as cnt FROM owl WHERE owl_type = 'skill_group' AND status = 'active'")
        folder_count = cur.fetchone()['cnt']
        
        # Count skills
        cur.execute("SELECT COUNT(*) as cnt FROM owl WHERE owl_type = 'skill' AND status = 'active'")
        skill_count = cur.fetchone()['cnt']
        
        # Count skills in trash
        cur.execute("""
            SELECT COUNT(*) as cnt FROM owl e
            JOIN owl_relationships er ON e.owl_id = er.owl_id
            JOIN owl trash ON er.related_owl_id = trash.owl_id
            WHERE trash.canonical_name = '_trash' AND e.owl_type = 'skill'
        """)
        trash_count = cur.fetchone()['cnt']
        
        # Count unclassified (in _NeedsReview or at root)
        cur.execute("""
            SELECT COUNT(*) as cnt FROM owl e
            JOIN owl_relationships er ON e.owl_id = er.owl_id
            JOIN owl folder ON er.related_owl_id = folder.owl_id
            WHERE folder.canonical_name IN ('_NeedsReview', 'skill')
            AND e.owl_type = 'skill' AND e.status = 'active'
        """)
        unclassified = cur.fetchone()['cnt']
        
        # Max depth
        cur.execute("""
            WITH RECURSIVE folder_depth AS (
                SELECT owl_id, canonical_name, 0 as depth
                FROM owl WHERE owl_id = 39066
                UNION ALL
                SELECT e.owl_id, e.canonical_name, fd.depth + 1
                FROM owl e
                JOIN owl_relationships er ON e.owl_id = er.owl_id
                JOIN folder_depth fd ON er.related_owl_id = fd.owl_id
                WHERE er.relationship = 'is_a' AND e.owl_type = 'skill_group'
            )
            SELECT MAX(depth) as cnt FROM folder_depth
        """)
        max_depth = cur.fetchone()['cnt'] or 0
        
        # Top-level categories
        cur.execute("""
            SELECT COUNT(*) as cnt FROM owl_relationships 
            WHERE related_owl_id = 39066 AND relationship = 'is_a'
        """)
        top_level = cur.fetchone()['cnt']
    
    print()
    print("=" * 72)
    print("TAXONOMY STATISTICS")
    print("=" * 72)
    print()
    print(f"  Folders (skill_group):     {folder_count:,}")
    print(f"  Skills (skill):            {skill_count:,}")
    print(f"  Top-level categories:      {top_level}")
    print(f"  Maximum depth:             {max_depth} levels")
    print()
    print(f"  In _trash:                 {trash_count}")
    print(f"  Unclassified:              {unclassified}")
    print()
    classified = skill_count - unclassified - trash_count
    if skill_count > 0:
        pct = (classified / skill_count) * 100
        print(f"  Classification progress:   {classified:,} / {skill_count:,} ({pct:.1f}%)")
    print()
    print("=" * 72)
    print()


def list_skills(folder_id: int, conn):
    """Show skills in the current folder."""
    skills = get_skills_in_folder(folder_id, conn, limit=100)
    total = count_skills_in_folder(folder_id, conn)
    
    print()
    print(f"═══ Skills in this folder ({total} total) ═══")
    if not skills:
        print("  (no skills)")
    else:
        for i, skill in enumerate(skills, 1):
            print(f"  {i:3}. [{skill['owl_id']}] {skill['canonical_name']}")
    print()


def interactive_nav(start_folder_id: int = SKILL_ROOT_ID, 
                    skill_to_classify: str = None,
                    skill_entity_id: int = None):
    """Main interactive navigation loop."""
    
    with get_connection() as conn:
        current_folder = start_folder_id
        parent_stack = [SKILL_ROOT_ID]
        
        # Log session start
        log_nav_action('enter', current_folder, conn)
        
        # If moving a skill, show its current location
        if skill_entity_id:
            current_loc_id, current_loc_name = get_skill_current_folder(skill_entity_id, conn)
            if current_loc_id:
                print(f"\n📌 Skill {skill_entity_id} is currently in: {current_loc_name}")
        
        while True:
            subfolders = get_subfolders(current_folder, conn)
            display_menu(current_folder, conn, skill_to_classify, skill_entity_id)
            
            try:
                choice = input("Your choice: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye!")
                break
            
            if not choice:
                continue
            
            # Quit
            if choice == 'Q':
                log_nav_action('quit', current_folder, conn)
                print("\nGoodbye!")
                break
            
            # Go up
            elif choice == 'U':
                if len(parent_stack) > 1:
                    current_folder = parent_stack.pop()
                    log_nav_action('up', current_folder, conn)
                else:
                    print("\n⚠️  Already at ROOT")
            
            # List skills
            elif choice == 'L':
                list_skills(current_folder, conn)
                input("Press Enter to continue...")
            
            # Search
            elif choice == 'S':
                query = input("Search for folder: ").strip()
                if query:
                    results = search_folders(query, conn)
                    if results:
                        print(f"\n═══ Found {len(results)} folders ═══")
                        for i, r in enumerate(results, 1):
                            print(f"  {i}. [{r['owl_id']}] {r['canonical_name']} ({r['skill_count']} skills)")
                        print()
                        go_to = input("Enter number to go there (or Enter to cancel): ").strip()
                        if go_to.isdigit():
                            idx = int(go_to) - 1
                            if 0 <= idx < len(results):
                                parent_stack.append(current_folder)
                                current_folder = results[idx]['owl_id']
                                log_nav_action('search_goto', current_folder, conn)
                    else:
                        print("\n⚠️  No folders found")
            
            # Place skill
            elif choice == 'P' and skill_entity_id:
                folder_info = get_folder_info(current_folder, conn)
                confirm = input(f"Place skill {skill_entity_id} in '{folder_info['canonical_name']}'? [y/N]: ").strip().lower()
                if confirm == 'y':
                    move_skill_to_folder(skill_entity_id, current_folder, conn)
                    log_nav_action('place', current_folder, conn)
                    print(f"\n✅ Skill moved to {folder_info['canonical_name']}")
                    break
            
            # [N] New subfolder (with Vera/Victor validation)
            elif choice == 'N':
                result = create_new_folder(current_folder, conn)
                if result:
                    log_nav_action('new_folder', result, conn)
                    # Optionally navigate into the new folder
                    go_in = input("Navigate into new folder? [y/N]: ").strip().lower()
                    if go_in == 'y':
                        parent_stack.append(current_folder)
                        current_folder = result
            
            # [H] Help - flag for human review
            elif choice == 'H' and (skill_to_classify or skill_entity_id):
                print()
                print("╔════════════════════════════════════════════════════════════════════════╗")
                print("║  [H] REQUEST HUMAN HELP                                                ║")
                print("╠════════════════════════════════════════════════════════════════════════╣")
                print("║  Why are you stuck? (This helps the human understand)                  ║")
                print("║  Examples:                                                             ║")
                print("║    - 'Could fit in multiple folders'                                   ║")
                print("║    - 'Not sure if this is a skill or a tool'                           ║")
                print("║    - 'Need new category for this type'                                 ║")
                print("╚════════════════════════════════════════════════════════════════════════╝")
                print()
                reason = input("  Your reason: ").strip()
                if reason:
                    skill_name = skill_to_classify or f"entity_{skill_entity_id}"
                    request_human_help(skill_name, skill_entity_id or 0, current_folder, reason, conn)
                    log_nav_action('help', current_folder, conn)
                else:
                    print("  Cancelled (no reason provided)")
            
            # [D] Delete/Trash - move skill to _trash folder
            elif choice == 'D' and (skill_to_classify or skill_entity_id):
                # Find _trash folder
                with conn.cursor() as cur:
                    cur.execute("SELECT owl_id FROM owl WHERE canonical_name = '_trash' AND owl_type = 'skill_group'")
                    trash = cur.fetchone()
                    if trash:
                        trash_id = trash['owl_id']
                        skill_name = skill_to_classify or f"entity_{skill_entity_id}"
                        confirm = input(f"Move '{skill_name}' to _trash? [y/N]: ").strip().lower()
                        if confirm == 'y':
                            if skill_entity_id:
                                move_skill_to_folder(skill_entity_id, trash_id, conn)
                                log_nav_action('trash', trash_id, conn)
                                print(f"\n🗑️  Moved to _trash")
                                break
                            else:
                                print("\n⚠️  No skill entity to move (simulation mode)")
                    else:
                        print("\n⚠️  _trash folder not found")
            
            # [?] About this project
            elif choice == '?':
                show_about()
                input("Press Enter to continue...")
            
            # [T] Taxonomy stats
            elif choice == 'T':
                show_stats(conn)
                input("Press Enter to continue...")
            
            # Navigate to subfolder by number
            elif choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(subfolders):
                    parent_stack.append(current_folder)
                    current_folder = subfolders[num - 1]['owl_id']
                    log_nav_action('down', current_folder, conn)
                else:
                    print(f"\n⚠️  Invalid option [{num}]")
            
            else:
                print(f"\n⚠️  Unknown command: {choice}")


# ═══════════════════════════════════════════════════════════════════════════════
# NON-INTERACTIVE COMMANDS (for Copilot / scripting)
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_ls(folder_id: int = SKILL_ROOT_ID):
    """List folder contents (subfolders and skill count)."""
    with get_connection() as conn:
        folder_info = get_folder_info(folder_id, conn)
        if folder_info:
            print(f"📁 {folder_info['canonical_name']} (ID: {folder_id})")
        else:
            print(f"📁 ROOT (ID: {folder_id})")
        
        path = get_breadcrumb_path(folder_id, conn)
        if path:
            path_str = " → ".join([name for _, name in path])
            print(f"📍 Path: ROOT → {path_str}")
        
        print()
        
        subfolders = get_subfolders(folder_id, conn)
        skill_count = count_skills_in_folder(folder_id, conn)
        
        if subfolders:
            print(f"Subfolders ({len(subfolders)}):")
            for sf in subfolders:
                sub_indicator = f" [+{sf['subfolder_count']} sub]" if sf['subfolder_count'] > 0 else ""
                print(f"  [{sf['owl_id']:>5}] {sf['canonical_name']} ({sf['skill_count']} skills){sub_indicator}")
        else:
            print("  (no subfolders)")
        
        print(f"\nSkills in this folder: {skill_count}")


def cmd_path(folder_id: int):
    """Show full path to a folder."""
    with get_connection() as conn:
        path = get_breadcrumb_path(folder_id, conn)
        folder_info = get_folder_info(folder_id, conn)
        
        if not folder_info:
            print(f"❌ Folder {folder_id} not found")
            return
        
        if path:
            print("ROOT")
            for i, (eid, name) in enumerate(path):
                indent = "  " * (i + 1)
                print(f"{indent}└── {name} (ID: {eid})")
        else:
            print(f"ROOT/{folder_info['canonical_name']} (ID: {folder_id})")


def cmd_skills(folder_id: int, limit: int = 50):
    """List skills in a folder."""
    with get_connection() as conn:
        folder_info = get_folder_info(folder_id, conn)
        if folder_info:
            print(f"📁 Skills in: {folder_info['canonical_name']}")
        
        skills = get_skills_in_folder(folder_id, conn, limit=limit)
        total = count_skills_in_folder(folder_id, conn)
        
        print(f"   (showing {min(limit, total)} of {total})\n")
        
        if not skills:
            print("  (no skills)")
        else:
            for skill in skills:
                print(f"  [{skill['owl_id']:>6}] {skill['canonical_name']}")


def cmd_search(query: str):
    """Search folders by name."""
    with get_connection() as conn:
        results = search_folders(query, conn, limit=30)
        
        if not results:
            print(f"❌ No folders matching '{query}'")
            return
        
        print(f"🔍 Folders matching '{query}' ({len(results)} found):\n")
        for r in results:
            path = get_breadcrumb_path(r['owl_id'], conn)
            path_str = " → ".join([name for _, name in path]) if path else ""
            print(f"  [{r['owl_id']:>5}] {r['canonical_name']} ({r['skill_count']} skills)")
            if path_str:
                print(f"          └── {path_str}")


def cmd_tree(folder_id: int = SKILL_ROOT_ID, max_depth: int = 3, indent: int = 0):
    """Show tree view of hierarchy."""
    with get_connection() as conn:
        _print_tree(folder_id, conn, max_depth, indent)


def _print_tree(folder_id: int, conn, max_depth: int, indent: int):
    """Recursive tree printer."""
    if indent > max_depth * 2:
        return
    
    folder_info = get_folder_info(folder_id, conn)
    if folder_info:
        skill_count = count_skills_in_folder(folder_id, conn)
        prefix = "  " * indent + ("└── " if indent > 0 else "")
        print(f"{prefix}{folder_info['canonical_name']} [{folder_id}] ({skill_count} skills)")
    
    if indent // 2 < max_depth:
        subfolders = get_subfolders(folder_id, conn)
        for sf in subfolders:
            _print_tree(sf['owl_id'], conn, max_depth, indent + 2)


def cmd_info(owl_id: int):
    """Get detailed info about an entity (skill or folder)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT owl_id, owl_type, canonical_name, status, 
                       created_at, created_by, description, metadata
                FROM owl WHERE owl_id = %s
            """, (owl_id,))
            row = cur.fetchone()
            
            if not row:
                print(f"❌ Entity {owl_id} not found")
                return
            
            print(f"{'═' * 60}")
            print(f"Entity ID:   {row['owl_id']}")
            print(f"Type:        {row['owl_type']}")
            print(f"Name:        {row['canonical_name']}")
            print(f"Status:      {row['status']}")
            print(f"Created:     {row['created_at']}")
            print(f"Created by:  {row['created_by'] or '(unknown)'}")
            
            if row['description']:
                print(f"Description: {row['description']}")
            
            # Show relationships
            cur.execute("""
                SELECT er.relationship, e.owl_id, e.canonical_name, e.owl_type
                FROM owl_relationships er
                JOIN owl e ON er.related_owl_id = e.owl_id
                WHERE er.owl_id = %s
            """, (owl_id,))
            rels = cur.fetchall()
            
            if rels:
                print(f"\nRelationships:")
                for rel in rels:
                    print(f"  {rel['relationship']} → {rel['canonical_name']} [{rel['owl_id']}] ({rel['owl_type']})")
            
            # If it's a folder, show children count
            if row['owl_type'] == 'skill_group':
                skill_count = count_skills_in_folder(owl_id, conn)
                subfolders = get_subfolders(owl_id, conn)
                print(f"\nContains: {skill_count} skills, {len(subfolders)} subfolders")
            
            print(f"{'═' * 60}")


def cmd_stats():
    """Show taxonomy statistics."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT owl_type, COUNT(*) as cnt
                FROM owl
                WHERE status = 'active'
                GROUP BY owl_type
                ORDER BY cnt DESC
            """)
            types = cur.fetchall()
            
            cur.execute("""
                SELECT COUNT(*) as cnt FROM owl_relationships
            """)
            rel_count = cur.fetchone()['cnt']
            
            print("═══ TAXONOMY STATISTICS ═══\n")
            print("Entity counts:")
            for t in types:
                print(f"  {t['owl_type']:<20} {t['cnt']:>6}")
            print(f"\nTotal relationships: {rel_count}")
            
            # Skills without folders
            cur.execute("""
                SELECT COUNT(*) as cnt FROM owl e
                WHERE e.owl_type = 'skill'
                AND e.status = 'active'
                AND NOT EXISTS (
                    SELECT 1 FROM owl_relationships er
                    WHERE er.owl_id = e.owl_id
                    AND er.relationship = 'belongs_to'
                )
            """)
            orphans = cur.fetchone()['cnt']
            print(f"Unclassified skills: {orphans}")


def cmd_navlog(limit: int = 20):
    """Show recent navigation log entries and metrics."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Recent entries
            cur.execute("""
                SELECT session_id, actor, action, folder_path, depth, created_at
                FROM nav_log
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            
            print("═══ NAVIGATION LOG ═══\n")
            print(f"{'Session':<10} {'Actor':<8} {'Action':<12} {'Path':<35} Depth")
            print("-" * 80)
            for row in rows:
                path = row['folder_path'] or 'ROOT'
                if len(path) > 35:
                    path = '...' + path[-32:]
                print(f"{row['session_id']:<10} {row['actor']:<8} {row['action']:<12} {path:<35} {row['depth']}")
            
            # Summary stats
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT session_id) as sessions,
                    COUNT(*) as total_actions,
                    MAX(depth) as max_depth,
                    COUNT(*) FILTER (WHERE action = 'help') as help_requests,
                    COUNT(*) FILTER (WHERE action = 'place') as placements,
                    COUNT(*) FILTER (WHERE action = 'trash') as trashed
                FROM nav_log
            """)
            stats = cur.fetchone()
            
            print(f"\n═══ SUMMARY ═══")
            print(f"  Sessions:      {stats['sessions']}")
            print(f"  Total actions: {stats['total_actions']}")
            print(f"  Max depth:     {stats['max_depth']}")
            print(f"  Help requests: {stats['help_requests']}")
            print(f"  Placements:    {stats['placements']}")
            print(f"  Trashed:       {stats['trashed']}")
            
            # Loop detection: folders visited more than 3 times in one session
            cur.execute("""
                SELECT session_id, folder_path, COUNT(*) as visits
                FROM nav_log
                WHERE folder_id IS NOT NULL
                GROUP BY session_id, folder_path
                HAVING COUNT(*) >= 3
                ORDER BY visits DESC
                LIMIT 5
            """)
            loops = cur.fetchall()
            
            if loops:
                print(f"\n⚠️  POTENTIAL LOOPS (folder visited 3+ times in session):")
                for loop in loops:
                    print(f"  Session {loop['session_id']}: {loop['folder_path']} ({loop['visits']}x)")


def main():
    # Check for non-interactive commands first
    if len(sys.argv) > 1 and sys.argv[1] in ('ls', 'path', 'skills', 'search', 'tree', 'info', 'stats', 'navlog'):
        cmd = sys.argv[1]
        
        if cmd == 'ls':
            folder_id = int(sys.argv[2]) if len(sys.argv) > 2 else SKILL_ROOT_ID
            cmd_ls(folder_id)
        elif cmd == 'path':
            if len(sys.argv) < 3:
                print("Usage: taxonomy_nav.py path FOLDER_ID")
                sys.exit(1)
            cmd_path(int(sys.argv[2]))
        elif cmd == 'skills':
            if len(sys.argv) < 3:
                print("Usage: taxonomy_nav.py skills FOLDER_ID [LIMIT]")
                sys.exit(1)
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            cmd_skills(int(sys.argv[2]), limit)
        elif cmd == 'search':
            if len(sys.argv) < 3:
                print("Usage: taxonomy_nav.py search QUERY")
                sys.exit(1)
            cmd_search(sys.argv[2])
        elif cmd == 'tree':
            folder_id = int(sys.argv[2]) if len(sys.argv) > 2 else SKILL_ROOT_ID
            max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
            cmd_tree(folder_id, max_depth)
        elif cmd == 'info':
            if len(sys.argv) < 3:
                print("Usage: taxonomy_nav.py info ENTITY_ID")
                sys.exit(1)
            cmd_info(int(sys.argv[2]))
        elif cmd == 'stats':
            cmd_stats()
        elif cmd == 'navlog':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            cmd_navlog(limit)
        
        return
    
    # Interactive mode
    parser = argparse.ArgumentParser(description="Interactive Taxonomy Navigator")
    parser.add_argument("--skill", help="Skill name to classify (simulation mode)")
    parser.add_argument("--move", type=int, help="Skill owl_id to move")
    parser.add_argument("--folder", type=int, default=SKILL_ROOT_ID, help="Starting folder ID")
    
    args = parser.parse_args()
    
    interactive_nav(
        start_folder_id=args.folder,
        skill_to_classify=args.skill,
        skill_entity_id=args.move
    )


if __name__ == "__main__":
    main()
