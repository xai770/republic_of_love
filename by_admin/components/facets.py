"""
🧬 Facets Component - Hierarchical Drill-Down Navigation

Displays hierarchical drill-down: Facets → Canonicals → Recipes → Sessions → Instructions
"""

import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Any, Optional
from database.queries import (
    get_all_facets, 
    get_facets_by_parent, 
    get_facet_by_id,
    create_facet,
    update_facet,
    delete_facet,
    search_facets
)

# Filter patterns for cleaning remarks
FILTER_PATTERNS = [
    r"^trace results to source",
    r"^output relevant data", 
    r"standardize terms",
    r"rfa_loqa",
    r"Test:.*$",
    r"— count 'r'",
    r"^\s*$"  # Empty or whitespace-only
]

def clean_remark(text: str) -> Optional[str]:
    """Clean and filter remarks to remove unwanted technical content"""
    if not text:
        return None
        
    # Remove test markers and timestamps
    text = re.sub(r"Test:.*$", "", text).strip()
    text = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "", text).strip()
    text = re.sub(r"— count '[^']*'", "", text).strip()
    
    # Check if text should be filtered out
    if len(text) < 4:
        return None
        
    for pattern in FILTER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return None
    
    return text

# ==============================================================================
# HIERARCHICAL DRILL-DOWN INTERFACE
# ==============================================================================

def render_facets_section():
    """Main render function for facets section"""
    
    # Initialize session state
    if 'selected_facet_id' not in st.session_state:
        st.session_state.selected_facet_id = None
    if 'current_parent_filter' not in st.session_state:
        st.session_state.current_parent_filter = None
    
    st.caption("Select a facet to filter canonicals in the Canonicals tab")
    
    # Main facets table with selection buttons
    show_facets_table_with_selection()

def show_facets_table_with_selection():
    """Show facets table with hierarchical filtering - clicking a facet shows its children"""
    
    st.subheader("🎯 Facets")
    
    # Get current filter state
    current_parent = st.session_state.get('current_parent_filter', None)
    
    # Get all facets data
    all_facets = get_all_facets()
    
    if not all_facets:
        st.info("No facets found in database")
        return
    
    # Filter facets based on current parent
    if current_parent is None:
        # Show root level facets (no parent or parent is None/empty)
        filtered_facets = [f for f in all_facets if not f.get('parent_id')]
        level_info = "Root Level"
    else:
        # Show child facets of the selected parent
        filtered_facets = [f for f in all_facets if f.get('parent_id') == current_parent]
        parent_facet = next((f for f in all_facets if f['facet_id'] == current_parent), None)
        level_info = f"Children of '{current_parent}'" + (f" - {parent_facet['short_description']}" if parent_facet else "")
    
    # Navigation breadcrumb
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if current_parent is None:
            st.caption("📍 " + level_info)
        else:
            st.caption("📍 " + level_info)
    
    with col2:
        if current_parent is not None:
            if st.button("⬆️ Back to Parent", key="back_to_parent"):
                # Go back one level up
                parent_facet = next((f for f in all_facets if f['facet_id'] == current_parent), None)
                if parent_facet and parent_facet.get('parent_id'):
                    st.session_state.current_parent_filter = parent_facet['parent_id']
                else:
                    st.session_state.current_parent_filter = None
                st.session_state.selected_facet_id = None
                st.rerun()
    
    if not filtered_facets:
        if current_parent is None:
            st.info("No root-level facets found")
        else:
            st.info(f"No child facets found for '{current_parent}'")
        return
    
    # Prepare data for dataframe display
    df_data = []
    for facet in filtered_facets:
        # Count canonicals for this facet
        canonicals_count = len(get_canonicals_by_facet(facet['facet_id']))
        
        # Count child facets
        child_count = len([f for f in all_facets if f.get('parent_id') == facet['facet_id']])
        
        df_data.append({
            'facet_id': facet['facet_id'],
            'short_description': facet['short_description'],
            'child_facets': child_count,
            'canonicals_count': canonicals_count,
            'enabled': '✅ Enabled' if facet['enabled'] else '❌ Disabled',
            'updated_at': facet.get('updated_at', '-')
        })
    
    df = pd.DataFrame(df_data)
    
    # Display table with selection and custom CSS injection
    st.write(f"**Click a row to drill down ({len(filtered_facets)} facets):**")
    
    # Inject custom CSS specifically for this dataframe
    st.markdown("""
    <style>
        /* Target the dataframe that's about to render */
        div[data-testid="stDataFrame"]:last-of-type [aria-selected="true"],
        div[data-testid="stDataFrame"]:last-of-type [aria-selected="true"] * {
            background-color: rgba(30, 144, 255, 0.3) !important;
            background: rgba(30, 144, 255, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    event = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    # Handle selection - drill down to show children
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_facet_data = filtered_facets[selected_idx]  # Use filtered data
        
        # Convert sqlite3.Row to dict if needed
        selected_facet = dict(selected_facet_data)
        selected_facet_id = selected_facet['facet_id']
        
        # Check if this facet has children
        child_count = len([f for f in all_facets if f.get('parent_id') == selected_facet_id])
        
        if child_count > 0:
            # Drill down to show children
            st.session_state.current_parent_filter = selected_facet_id
            st.session_state.selected_facet_id = selected_facet_id
            st.success(f"🔍 Drilling down to children of: **{selected_facet_id}** ({child_count} children)")
            st.rerun()
        else:
            # No children, just select for canonicals view
            st.session_state.selected_facet_id = selected_facet_id
            st.success(f"📌 Selected: **{selected_facet_id}** - {selected_facet['short_description']} (leaf node)")
    
    # Action buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    with col1:
        if st.button("🔄 Refresh", key="facets_refresh"):
            st.rerun()
    
    with col2:
        if st.button("🏠 Reset to Root", key="reset_to_root"):
            st.session_state.current_parent_filter = None
            st.session_state.selected_facet_id = None
            st.rerun()
    
    with col3:
        selected_facet_id = st.session_state.get('selected_facet_id')
        clear_disabled = not selected_facet_id
        if st.button("❌ Clear Selection", disabled=clear_disabled, key="clear_facet_selection_table"):
            st.session_state.selected_facet_id = None
            st.rerun()
    
    with col4:
        if selected_facet_id:
            canonicals_count = len(get_canonicals_by_facet(selected_facet_id))
            st.caption(f"Selected facet has {canonicals_count} canonicals")

# ==============================================================================
# DATABASE HELPER FUNCTIONS
# ==============================================================================

def get_canonicals_by_facet(facet_id: str):
    """Get all canonicals for a facet (including disabled ones)"""
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM canonicals WHERE facet_id = %s ORDER BY enabled DESC, canonical_code", (facet_id,))
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching canonicals: {e}")
        return []

def get_canonical_by_code(canonical_code: str):
    """Get a canonical by its code"""
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM canonicals WHERE canonical_code = %s", (canonical_code,))
            row = cursor.fetchone()
            return row
    except Exception as e:
        st.error(f"Error fetching canonical: {e}")
        return None

def get_recipes_by_canonical(canonical_code: str):
    """Get all recipes for a canonical"""
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT r.* 
                FROM recipes r
                JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id
                JOIN sessions s ON rs.session_id = s.session_id
                WHERE s.canonical_code = %s AND r.enabled = TRUE
            """, (canonical_code,))
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching recipes: {e}")
        return []

def get_recipe_by_id(recipe_id: int):
    """Get a recipe by its ID"""
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recipes WHERE recipe_id = %s", (recipe_id,))
            row = cursor.fetchone()
            return row
    except Exception as e:
        st.error(f"Error fetching recipe: {e}")
        return None

def get_sessions_by_recipe(recipe_id: int):
    """Get all sessions for a recipe via recipe_sessions junction"""
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, rs.execution_order 
                FROM sessions s
                JOIN recipe_sessions rs ON s.session_id = rs.session_id
                WHERE rs.recipe_id = %s AND s.enabled = TRUE 
                ORDER BY rs.execution_order
            """, (recipe_id,))
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching sessions: {e}")
        return []

def get_session_by_id(session_id: int):
    """Get a session by its ID"""
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = %s", (session_id,))
            row = cursor.fetchone()
            return row
    except Exception as e:
        st.error(f"Error fetching session: {e}")
        return None

def get_instructions_by_session(session_id: int):
    """Get all instructions for a session"""
    try:
        from database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM instructions WHERE session_id = %s AND enabled = TRUE ORDER BY step_number", (session_id,))
            return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching instructions: {e}")
        return []

