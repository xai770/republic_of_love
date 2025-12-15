#!/usr/bin/env python3
"""
SkillBridge Folder Tree Viewer
Collapsible folder-style hierarchy display
"""

import streamlit as st
import psycopg2
from typing import List, Dict, Any

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "database": "base_yoga",
    "user": "base_admin",
    "password": "base_yoga_secure_2025"
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

# ==============================================================================
# DATABASE QUERIES
# ==============================================================================

def get_root_skills():
    """Get root-level skills (have children but no parent)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT sa.skill, sa.display_name
            FROM skill_aliases sa
            WHERE sa.skill IN (
                -- Has children (is a parent)
                SELECT DISTINCT parent_skill FROM skill_hierarchy
            )
            AND sa.skill NOT IN (
                -- But has no parent (is not a child)
                SELECT DISTINCT skill FROM skill_hierarchy
            )
            ORDER BY sa.skill
        """)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_children(parent_skill: str):
    """Get direct children of a parent"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sa.skill, sa.display_name
            FROM skill_hierarchy h
            JOIN skill_aliases sa ON h.skill = sa.skill
            WHERE h.parent_skill = %s
            ORDER BY sa.skill
        """, (parent_skill,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def has_children(skill: str):
    """Check if skill has children"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM skill_hierarchy WHERE parent_skill = %s
        """, (skill,))
        return cursor.fetchone()[0] > 0

def get_occurrence_count(skill: str):
    """Get number of times skill appears"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM skill_occurrences WHERE skill = %s
        """, (skill,))
        return cursor.fetchone()[0]

def get_skill_occurrences(skill: str):
    """Get all occurrences of a skill"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                skill_source,
                source_id,
                skill_alias,
                confidence,
                LEFT(context, 100) as context_preview,
                created_at
            FROM skill_occurrences
            WHERE skill = %s
            ORDER BY created_at DESC
        """, (skill,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# ==============================================================================
# FOLDER TREE RENDERING
# ==============================================================================

def render_skill_folder(skill: str, display_name: str, level: int = 0, expanded_by_default: bool = False, visited: set = None):
    """Render a skill as a folder with collapsible children"""
    
    # Prevent infinite recursion with cycle detection
    if visited is None:
        visited = set()
    
    if skill in visited:
        st.warning(f"⚠️ Circular reference detected: {skill}")
        return
    
    # Limit depth to prevent runaway recursion
    if level > 10:
        st.caption(f"⚠️ Max depth reached at {skill}")
        return
    
    visited = visited | {skill}  # Add to visited set
    
    # Get stats
    has_kids = has_children(skill)
    occurrence_count = get_occurrence_count(skill)
    
    # Determine icon and label
    indent = "　" * level  # Japanese space for indentation
    
    if has_kids and occurrence_count == 0:
        # Pure category
        icon = "📁"
        label = f"{indent}{icon} **{display_name}**"
    elif has_kids and occurrence_count > 0:
        # Mixed: has both children and direct mentions
        icon = "📂"
        label = f"{indent}{icon} **{display_name}** ({occurrence_count} uses)"
    else:
        # Leaf skill
        icon = "📄"
        label = f"{indent}{icon} {display_name} ({occurrence_count} uses)"
    
    # If it's a leaf skill, show details directly
    if not has_kids:
        if occurrence_count > 0:
            with st.expander(label, expanded=False):
                show_skill_details(skill, display_name)
        else:
            st.write(label + " _(no uses)_")
        return
    
    # If it has children, make it expandable
    with st.expander(label, expanded=expanded_by_default):
        # Show direct occurrences if any
        if occurrence_count > 0:
            with st.container():
                st.caption(f"_Direct mentions of {display_name}:_")
                show_skill_details_compact(skill)
                st.divider()
        
        # Render children recursively
        children = get_children(skill)
        if children:
            for child in children:
                render_skill_folder(
                    child['skill'], 
                    child['display_name'], 
                    level + 1,
                    expanded_by_default=False,
                    visited=visited  # Pass visited set
                )
        else:
            st.caption("_(no children)_")

def show_skill_details_compact(skill: str):
    """Show compact skill details"""
    occurrences = get_skill_occurrences(skill)
    
    if not occurrences:
        return
    
    # Group by source
    sources = {}
    for occ in occurrences:
        source_id = occ['source_id']
        if source_id not in sources:
            sources[source_id] = []
        sources[source_id].append(occ)
    
    st.caption(f"Found in {len(sources)} source(s):")
    for source_id in list(sources.keys())[:5]:  # Show first 5
        occs = sources[source_id]
        st.caption(f"• {source_id} ({len(occs)}x)")

def show_skill_details(skill: str, display_name: str):
    """Show detailed skill information"""
    occurrences = get_skill_occurrences(skill)
    
    if not occurrences:
        st.info("No occurrences found")
        return
    
    # Summary
    unique_sources = len(set(o['source_id'] for o in occurrences))
    avg_confidence = sum(float(o['confidence']) for o in occurrences) / len(occurrences)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Mentions", len(occurrences))
    with col2:
        st.metric("Unique Sources", unique_sources)
    
    st.caption(f"Average Confidence: {avg_confidence:.2f}")
    
    # Show sources
    st.write("**Sources:**")
    sources = {}
    for occ in occurrences:
        source_id = occ['source_id']
        if source_id not in sources:
            sources[source_id] = []
        sources[source_id].append(occ)
    
    for source_id, occs in list(sources.items())[:10]:  # Show first 10
        with st.container():
            st.write(f"📌 **{source_id}** ({len(occs)} mention{'s' if len(occs) > 1 else ''})")
            for occ in occs[:3]:  # Show first 3 per source
                alias = occ['skill_alias']
                context = occ['context_preview']
                if alias and alias != skill:
                    st.caption(f"  • As: _{alias}_")
                if context:
                    st.caption(f"    {context}...")

# ==============================================================================
# MAIN UI
# ==============================================================================

def main():
    """Main app"""
    
    st.set_page_config(
        page_title="SkillBridge Folder View",
        page_icon="📁",
        layout="wide"
    )
    
    st.title("📁 SkillBridge Folder Tree")
    st.caption("Collapsible folder-style hierarchy • Click any folder to expand")
    
    # Get stats
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT skill) FROM skill_aliases")
        total_skills = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM skill_occurrences")
        total_mentions = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT source_id) FROM skill_occurrences")
        total_sources = cursor.fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Skills", total_skills)
    with col2:
        st.metric("Total Mentions", total_mentions)
    with col3:
        st.metric("Unique Sources", total_sources)
    
    st.divider()
    
    # Control panel
    col1, col2 = st.columns([1, 3])
    with col1:
        expand_all = st.checkbox("Expand All Roots", value=False)
    
    st.divider()
    
    # Render root folders
    roots = get_root_skills()
    
    if not roots:
        st.warning("No root-level skills found")
        return
    
    for root in roots:
        render_skill_folder(
            root['skill'], 
            root['display_name'],
            level=0,
            expanded_by_default=expand_all
        )
    
    # Show orphan skills
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sa.skill, sa.display_name
            FROM skill_aliases sa
            LEFT JOIN skill_hierarchy h ON sa.skill = h.skill
            WHERE h.skill IS NULL
            AND sa.skill NOT IN (SELECT parent_skill FROM skill_hierarchy)
            ORDER BY sa.skill
        """)
        orphans = cursor.fetchall()
    
    if orphans:
        st.divider()
        with st.expander(f"🔍 Orphan Skills ({len(orphans)})", expanded=False):
            st.caption("Skills with no parent or children:")
            for skill, display_name in orphans:
                count = get_occurrence_count(skill)
                st.write(f"• {display_name} ({count} uses)")

if __name__ == "__main__":
    main()
