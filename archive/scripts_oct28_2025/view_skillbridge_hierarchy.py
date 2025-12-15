#!/usr/bin/env python3
"""
SkillBridge Hierarchical Viewer
Hierarchical drill-down: Categories → Subcategories → Skills → Occurrences
"""

import streamlit as st
import pandas as pd
import psycopg2
from typing import List, Dict, Any, Optional

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

def get_all_skills():
    """Get all skills with their aliases"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                skill,
                display_name,
                language,
                confidence,
                created_by
            FROM skill_aliases
            ORDER BY skill
        """)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_root_level_skills():
    """Get skills that have no parent (top-level categories)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT sa.skill, sa.display_name
            FROM skill_aliases sa
            WHERE sa.skill NOT IN (
                SELECT DISTINCT skill FROM skill_hierarchy
            )
            AND sa.skill IN (
                SELECT DISTINCT parent_skill FROM skill_hierarchy
            )
            ORDER BY sa.skill
        """)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_children_skills(parent_skill: str):
    """Get direct children of a parent skill"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                sa.skill,
                sa.display_name,
                h.strength
            FROM skill_hierarchy h
            JOIN skill_aliases sa ON h.skill = sa.skill
            WHERE h.parent_skill = %s
            ORDER BY sa.skill
        """, (parent_skill,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_skill_occurrence_count(skill: str):
    """Count how many times a skill appears"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM skill_occurrences 
            WHERE skill = %s
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
                context,
                created_at
            FROM skill_occurrences
            WHERE skill = %s
            ORDER BY created_at DESC
        """, (skill,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def has_children(skill: str):
    """Check if a skill has children"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM skill_hierarchy 
            WHERE parent_skill = %s
        """, (skill,))
        return cursor.fetchone()[0] > 0

def get_skill_path(skill: str):
    """Get full path from root to skill"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            WITH RECURSIVE path AS (
                SELECT 
                    skill, 
                    parent_skill,
                    1 as level,
                    ARRAY[skill] as ancestors
                FROM skill_hierarchy
                WHERE skill = %s
                
                UNION ALL
                
                SELECT 
                    h.skill,
                    h.parent_skill,
                    p.level + 1,
                    p.ancestors || h.parent_skill
                FROM skill_hierarchy h
                JOIN path p ON h.skill = p.parent_skill
            )
            SELECT ancestors FROM path ORDER BY level DESC LIMIT 1
        """, (skill,))
        row = cursor.fetchone()
        return row[0] if row else [skill]

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

def render_skill_tree():
    """Main hierarchical skill tree viewer"""
    
    st.title("🌳 SkillBridge Hierarchy Viewer")
    st.caption("Drill down: Categories → Subcategories → Skills → Occurrences")
    
    # Initialize session state
    if 'current_skill_filter' not in st.session_state:
        st.session_state.current_skill_filter = None
    if 'breadcrumb' not in st.session_state:
        st.session_state.breadcrumb = []
    if 'selected_skill' not in st.session_state:
        st.session_state.selected_skill = None
    
    # Get current level skills
    current_skill = st.session_state.current_skill_filter
    
    if current_skill is None:
        # Show root level
        skills = get_root_level_skills()
        level_info = "📁 Root Level Categories"
    else:
        # Show children of current skill
        skills = get_children_skills(current_skill)
        parent_display = next((s['display_name'] for s in get_all_skills() if s['skill'] == current_skill), current_skill)
        level_info = f"📂 {parent_display}"
    
    # Breadcrumb navigation
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Build breadcrumb
        if st.session_state.breadcrumb:
            breadcrumb_parts = []
            for bc_skill in st.session_state.breadcrumb:
                bc_display = next((s['display_name'] for s in get_all_skills() if s['skill'] == bc_skill), bc_skill)
                breadcrumb_parts.append(bc_display)
            breadcrumb_str = " → ".join(breadcrumb_parts)
            st.caption(f"📍 {breadcrumb_str} → {level_info}")
        else:
            st.caption(f"📍 {level_info}")
    
    with col2:
        if current_skill is not None:
            if st.button("⬆️ Back", key="back_button"):
                # Go back one level
                if st.session_state.breadcrumb:
                    st.session_state.breadcrumb.pop()
                    st.session_state.current_skill_filter = st.session_state.breadcrumb[-1] if st.session_state.breadcrumb else None
                else:
                    st.session_state.current_skill_filter = None
                st.rerun()
    
    if not skills:
        st.info("No skills at this level")
        return
    
    # Prepare dataframe
    df_data = []
    for skill_data in skills:
        skill = skill_data['skill']
        
        # Check if has children
        child_count = len(get_children_skills(skill))
        occurrence_count = get_skill_occurrence_count(skill)
        
        # Determine if this is a category, subcategory, or leaf skill
        if child_count > 0:
            skill_type = "📁 Category" if occurrence_count == 0 else "📂 Mixed"
        else:
            skill_type = "📄 Skill"
        
        df_data.append({
            'skill': skill,
            'display_name': skill_data['display_name'],
            'type': skill_type,
            'children': child_count if child_count > 0 else '-',
            'occurrences': occurrence_count if occurrence_count > 0 else '-'
        })
    
    df = pd.DataFrame(df_data)
    
    # Display table
    st.write(f"**Click a row to drill down ({len(skills)} items):**")
    
    event = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "display_name": st.column_config.TextColumn("Name", width="medium"),
            "type": st.column_config.TextColumn("Type", width="small"),
            "children": st.column_config.TextColumn("Children", width="small"),
            "occurrences": st.column_config.TextColumn("Uses", width="small")
        }
    )
    
    # Handle selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_skill_data = skills[selected_idx]
        selected_skill = selected_skill_data['skill']
        
        # Check if has children
        child_count = len(get_children_skills(selected_skill))
        
        if child_count > 0:
            # Drill down to show children
            st.session_state.breadcrumb.append(current_skill) if current_skill else st.session_state.breadcrumb
            st.session_state.current_skill_filter = selected_skill
            st.session_state.selected_skill = selected_skill
            st.success(f"🔍 Drilling into: **{selected_skill_data['display_name']}** ({child_count} children)")
            st.rerun()
        else:
            # Leaf node - show occurrences
            st.session_state.selected_skill = selected_skill
            show_skill_details(selected_skill, selected_skill_data['display_name'])
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 3])
    
    with col1:
        if st.button("🔄 Refresh", key="refresh_button"):
            st.rerun()
    
    with col2:
        if st.button("🏠 Reset", key="reset_button"):
            st.session_state.current_skill_filter = None
            st.session_state.breadcrumb = []
            st.session_state.selected_skill = None
            st.rerun()
    
    # Summary statistics
    show_summary_stats()

def show_skill_details(skill: str, display_name: str):
    """Show detailed information about a selected skill"""
    
    st.divider()
    st.subheader(f"📄 Skill Details: {display_name}")
    
    # Get occurrences
    occurrences = get_skill_occurrences(skill)
    
    if not occurrences:
        st.info(f"No occurrences found for '{display_name}'")
        return
    
    # Show summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Mentions", len(occurrences))
    
    with col2:
        unique_sources = len(set(o['source_id'] for o in occurrences))
        st.metric("Unique Sources", unique_sources)
    
    with col3:
        avg_confidence = sum(float(o['confidence']) for o in occurrences) / len(occurrences)
        st.metric("Avg Confidence", f"{avg_confidence:.2f}")
    
    # Show occurrences table
    st.write("**Occurrences:**")
    
    df = pd.DataFrame(occurrences)
    
    # Truncate context for display
    if 'context' in df.columns:
        df['context'] = df['context'].apply(lambda x: (x[:100] + '...') if x and len(x) > 100 else x)
    
    st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        column_config={
            "skill_source": "Source Type",
            "source_id": "Source ID",
            "skill_alias": "Original Text",
            "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
            "context": "Context",
            "created_at": st.column_config.DatetimeColumn("Extracted At")
        }
    )

def show_summary_stats():
    """Show overall summary statistics"""
    
    st.divider()
    st.subheader("📊 Overall Statistics")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Count total skills
        cursor.execute("SELECT COUNT(DISTINCT skill) FROM skill_aliases")
        total_skills = cursor.fetchone()[0]
        
        # Count hierarchy relationships
        cursor.execute("SELECT COUNT(*) FROM skill_hierarchy")
        hierarchy_count = cursor.fetchone()[0]
        
        # Count occurrences
        cursor.execute("SELECT COUNT(*) FROM skill_occurrences")
        occurrence_count = cursor.fetchone()[0]
        
        # Count unique sources
        cursor.execute("SELECT COUNT(DISTINCT source_id) FROM skill_occurrences")
        source_count = cursor.fetchone()[0]
        
        # Get top 5 skills
        cursor.execute("""
            SELECT sa.display_name, COUNT(*) as count
            FROM skill_occurrences so
            JOIN skill_aliases sa ON so.skill = sa.skill
            GROUP BY sa.skill, sa.display_name
            ORDER BY count DESC
            LIMIT 5
        """)
        top_skills = cursor.fetchall()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Skills", total_skills)
    
    with col2:
        st.metric("Hierarchy Links", hierarchy_count)
    
    with col3:
        st.metric("Total Mentions", occurrence_count)
    
    with col4:
        st.metric("Unique Sources", source_count)
    
    # Top skills
    st.write("**🏆 Top 5 Most Mentioned Skills:**")
    for i, (skill_name, count) in enumerate(top_skills, 1):
        st.write(f"{i}. **{skill_name}** - {count} mentions")

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Main app entry point"""
    
    st.set_page_config(
        page_title="SkillBridge Hierarchy",
        page_icon="🌳",
        layout="wide"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
        /* Blue selection for dataframes */
        [data-testid="stDataFrame"] [aria-selected="true"],
        [data-testid="stDataFrame"] [aria-selected="true"] * {
            background-color: rgba(30, 144, 255, 0.3) !important;
        }
        
        .stMetric {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 1rem;
            border-radius: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    render_skill_tree()

if __name__ == "__main__":
    main()
