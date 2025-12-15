"""
🍳 LLMCore Streamlit Admin Interface

A visual admin GUI for managing the LLMCore database without SQL.
Handles recipes, instructions, variations, actors, and execution monitoring.

Author: Arden (Claude Sonnet)
Date: October 13, 2025
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure Streamlit page
st.set_page_config(
    page_title="LLMCore Admin",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection management
@st.cache_resource
def get_db_connection():
    """Cached database connection with row factory for named column access"""
    conn = sqlite3.connect(
        '/home/xai/Documents/ty_learn/data/llmcore.db', 
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def execute_query(query: str, params: tuple = None) -> List[sqlite3.Row]:
    """Execute SELECT query and return results"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        st.error(f"❌ Database query error: {e}")
        return []

def execute_write(query: str, params: tuple = None) -> Optional[int]:
    """Execute INSERT/UPDATE/DELETE and return lastrowid"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        st.error(f"❌ Database integrity error: {e}")
        return None
    except sqlite3.Error as e:
        st.error(f"❌ Database error: {e}")
        return None

# Navigation and routing
def main():
    """Main application entry point with navigation"""
    
    # Sidebar navigation
    st.sidebar.title("🍳 LLMCore Admin")
    st.sidebar.markdown("*Visual Database Management*")
    
    page = st.sidebar.radio("Navigate", [
        "📊 Dashboard",
        "📝 Recipes", 
        "🎯 Instructions",
        "🔀 Variations",
        "🌳 Branches",
        "👤 Actors",
        "🏃 Recipe Runs",
        "📋 Canonicals"
    ])
    
    # Route to appropriate page
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📝 Recipes":
        show_recipes_page()
    elif page == "🎯 Instructions":
        show_instructions_page()
    elif page == "🔀 Variations":
        show_variations_page()
    elif page == "🌳 Branches":
        show_branches_page()
    elif page == "👤 Actors":
        show_actors_page()
    elif page == "🏃 Recipe Runs":
        show_recipe_runs_page()
    elif page == "📋 Canonicals":
        show_canonicals_page()

# Dashboard page
def show_dashboard():
    """Database overview and statistics"""
    st.title("📊 LLMCore Dashboard")
    st.markdown("*Real-time database overview*")
    
    # Fetch key statistics
    stats = {}
    try:
        stats['recipes'] = execute_query("SELECT COUNT(*) as count FROM recipes WHERE enabled = 1")[0]['count']
        stats['instructions'] = execute_query("SELECT COUNT(*) as count FROM instructions WHERE enabled = 1")[0]['count'] 
        stats['variations'] = execute_query("SELECT COUNT(*) as count FROM variations WHERE enabled = 1")[0]['count']
        stats['actors'] = execute_query("SELECT COUNT(*) as count FROM actors WHERE enabled = 1")[0]['count']
        stats['canonicals'] = execute_query("SELECT COUNT(*) as count FROM canonicals WHERE enabled = 1")[0]['count']
        stats['recipe_runs'] = execute_query("SELECT COUNT(*) as count FROM recipe_runs")[0]['count']
    except Exception as e:
        st.error(f"Failed to load statistics: {e}")
        return
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🧪 Active Canonicals", stats['canonicals'])
    col2.metric("📝 Active Recipes", stats['recipes']) 
    col3.metric("🎯 Instructions", stats['instructions'])
    col4.metric("🔀 Variations", stats['variations'])
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("👤 Active Actors", stats['actors'])
    col6.metric("🏃 Recipe Runs", stats['recipe_runs'])
    col7.metric("⚡ Avg Steps/Recipe", 
               f"{stats['instructions']/max(stats['recipes'], 1):.1f}")
    col8.metric("📊 Variations/Recipe", 
               f"{stats['variations']/max(stats['recipes'], 1):.1f}")
    
    # Recent activity
    st.subheader("🕒 Recent Activity")
    
    recent_recipes = execute_query("""
        SELECT r.recipe_id, r.canonical_code, c.capability_description, r.timestamp
        FROM recipes r
        JOIN canonicals c ON r.canonical_code = c.canonical_code
        WHERE r.enabled = 1
        ORDER BY r.timestamp DESC
        LIMIT 10
    """)
    
    if recent_recipes:
        df = pd.DataFrame([
            {
                'Recipe ID': r['recipe_id'],
                'Canonical': r['canonical_code'], 
                'Description': r['capability_description'][:50] + '...' if len(r['capability_description']) > 50 else r['capability_description'],
                'Created': r['timestamp']
            } for r in recent_recipes
        ])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recent recipes found")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    if col1.button("➕ Create Recipe"):
        st.session_state.page = "📝 Recipes"
        st.session_state.show_create_recipe = True
        st.rerun()
    
    if col2.button("👤 Manage Actors"):
        st.session_state.page = "👤 Actors"
        st.rerun()
    
    if col3.button("🏃 View Recipe Runs"):
        st.session_state.page = "🏃 Recipe Runs" 
        st.rerun()

# Recipes page
def show_recipes_page():
    """Recipe management interface"""
    st.title("📝 Recipes")
    st.markdown("*Manage test configurations and cooking instructions*")
    
    # Fetch recipes with canonical info
    recipes = execute_query("""
        SELECT r.recipe_id, r.canonical_code, r.version, 
               r.max_instruction_cycles, r.enabled, r.timestamp,
               c.capability_description
        FROM recipes r
        JOIN canonicals c ON r.canonical_code = c.canonical_code
        ORDER BY r.recipe_id DESC
    """)
    
    if not recipes:
        st.info("No recipes found. Create your first recipe below!")
    else:
        # Display recipes table
        df = pd.DataFrame([
            {
                'ID': r['recipe_id'],
                'Canonical': r['canonical_code'],
                'Version': r['version'],
                'Max Cycles': r['max_instruction_cycles'],
                'Enabled': '✅' if r['enabled'] else '❌',
                'Description': r['capability_description'][:60] + '...' if len(r['capability_description']) > 60 else r['capability_description'],
                'Created': r['timestamp']
            } for r in recipes
        ])
        
        st.dataframe(df, use_container_width=True)
        
        # Recipe detail drill-down
        st.subheader("🔍 Recipe Details")
        recipe_options = {f"Recipe {r['recipe_id']}: {r['canonical_code']}": r['recipe_id'] for r in recipes}
        
        if recipe_options:
            selected_recipe_key = st.selectbox("Select Recipe", options=list(recipe_options.keys()))
            selected_recipe_id = recipe_options[selected_recipe_key]
            
            if selected_recipe_id:
                show_recipe_detail(selected_recipe_id)
    
    # Create new recipe section
    st.subheader("➕ Create New Recipe")
    if st.button("Create Recipe"):
        st.session_state.show_create_recipe = True
    
    if st.session_state.get('show_create_recipe', False):
        show_create_recipe_form()

def show_recipe_detail(recipe_id: int):
    """Detailed view of a specific recipe with tabs"""
    
    # Fetch recipe details
    recipe_data = execute_query(
        "SELECT * FROM recipes WHERE recipe_id = ?", 
        (recipe_id,)
    )
    
    if not recipe_data:
        st.error("Recipe not found!")
        return
        
    recipe = recipe_data[0]
    
    # Display recipe header info
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🧪 Canonical", recipe['canonical_code'])
    col2.metric("📝 Version", recipe['version'])
    col3.metric("🔄 Max Cycles", recipe['max_instruction_cycles'])
    col4.metric("✅ Status", "Enabled" if recipe['enabled'] else "Disabled")
    
    if recipe['review_notes']:
        st.info(f"📝 Notes: {recipe['review_notes']}")
    
    # Tabbed interface for related data
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Instructions", "🔀 Variations", "🏃 Recipe Runs", "⚙️ Settings"])
    
    with tab1:
        show_recipe_instructions(recipe_id)
    
    with tab2:
        show_recipe_variations(recipe_id)
    
    with tab3:
        show_recipe_recipe_runs(recipe_id)
    
    with tab4:
        show_recipe_settings(recipe_id)

def show_recipe_instructions(recipe_id: int):
    """Display and manage instructions for a recipe"""
    
    instructions = execute_query("""
        SELECT i.instruction_id, i.step_number, i.step_description,
               i.actor_id, a.actor_type, i.timeout_seconds, i.enabled,
               i.prompt_template
        FROM instructions i
        LEFT JOIN actors a ON i.actor_id = a.actor_id
        WHERE i.recipe_id = ?
        ORDER BY i.step_number
    """, (recipe_id,))
    
    if instructions:
        st.write(f"**{len(instructions)} instruction(s) defined:**")
        
        for instr in instructions:
            status_icon = "✅" if instr['enabled'] else "❌"
            actor_info = f"{instr['actor_id']} ({instr['actor_type']})" if instr['actor_id'] else "No actor assigned"
            
            with st.expander(f"{status_icon} Step {instr['step_number']}: {instr['step_description'] or 'No description'}"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Actor:** {actor_info}")
                col2.write(f"**Timeout:** {instr['timeout_seconds']}s")
                col3.write(f"**ID:** {instr['instruction_id']}")
                
                # Show prompt template with syntax highlighting
                if instr['prompt_template']:
                    st.write("**Prompt Template:**")
                    st.code(instr['prompt_template'], language="markdown")
                else:
                    st.warning("⚠️ No prompt template defined")
                
                # Action buttons
                col1, col2 = st.columns(2)
                if col1.button(f"✏️ Edit", key=f"edit_instr_{instr['instruction_id']}"):
                    st.session_state[f'edit_instruction_{instr["instruction_id"]}'] = True
                    st.rerun()
                    
                if col2.button(f"🗑️ Delete", key=f"del_instr_{instr['instruction_id']}"):
                    if st.session_state.get(f'confirm_delete_instr_{instr["instruction_id"]}', False):
                        execute_write("DELETE FROM instructions WHERE instruction_id = ?", (instr['instruction_id'],))
                        st.success("✅ Instruction deleted!")
                        st.rerun()
                    else:
                        st.session_state[f'confirm_delete_instr_{instr["instruction_id"]}'] = True
                        st.warning("⚠️ Click Delete again to confirm")
    else:
        st.info("No instructions yet. Add the first one below!")
    
    # Add instruction section
    st.subheader("➕ Add New Instruction")
    if st.button("Add Instruction"):
        st.session_state[f'show_add_instr_{recipe_id}'] = True
    
    if st.session_state.get(f'show_add_instr_{recipe_id}', False):
        show_add_instruction_form(recipe_id)

def show_add_instruction_form(recipe_id: int):
    """Form to add a new instruction to a recipe"""
    
    # Fetch available actors
    actors = execute_query("SELECT actor_id, actor_type FROM actors WHERE enabled = 1 ORDER BY actor_type, actor_id")
    actor_options = {f"{a['actor_id']} ({a['actor_type']})": a['actor_id'] for a in actors}
    
    with st.form(f"add_instruction_{recipe_id}"):
        st.write("**Create New Instruction**")
        
        col1, col2 = st.columns(2)
        step_number = col1.number_input("Step Number", min_value=1, value=1)
        timeout_seconds = col2.number_input("Timeout (seconds)", min_value=30, value=300)
        
        step_description = st.text_input("Step Description", placeholder="Brief description of what this step does")
        
        if actor_options:
            selected_actor_key = st.selectbox("Actor", options=list(actor_options.keys()))
            actor_id = actor_options[selected_actor_key] if selected_actor_key else None
        else:
            st.error("No actors available! Please create actors first.")
            actor_id = None
        
        prompt_template = st.text_area(
            "Prompt Template",
            placeholder="Enter the prompt template with placeholders like {variations_param_1}, {step1_response}",
            height=150
        )
        
        # Template helper
        st.info("""
        **Template Placeholders:**
        - `{variations_param_1}`, `{variations_param_2}`, `{variations_param_3}` - From variations table
        - `{step1_prompt}`, `{step1_response}` - From previous instruction runs  
        - `{stepN_prompt}`, `{stepN_response}` - From step N results
        """)
        
        enabled = st.checkbox("Enabled", value=True)
        
        submitted = st.form_submit_button("✅ Create Instruction")
        
        if submitted and actor_id and prompt_template:
            instruction_id = execute_write("""
                INSERT INTO instructions (
                    recipe_id, step_number, step_description, prompt_template, 
                    actor_id, timeout_seconds, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipe_id, step_number, step_description, prompt_template, 
                  actor_id, timeout_seconds, int(enabled)))
            
            if instruction_id:
                st.success(f"✅ Instruction {instruction_id} created successfully!")
                st.session_state[f'show_add_instr_{recipe_id}'] = False
                st.rerun()
        elif submitted:
            st.error("❌ Please fill in all required fields")

def show_recipe_variations(recipe_id: int):
    """Display and manage variations for a recipe"""
    
    variations = execute_query("""
        SELECT variation_id, variations_param_1, variations_param_2, 
               variations_param_3, difficulty_level, expected_response, enabled
        FROM variations
        WHERE recipe_id = ?
        ORDER BY difficulty_level, variation_id
    """, (recipe_id,))
    
    if variations:
        st.write(f"**{len(variations)} variation(s) defined:**")
        
        # Convert to DataFrame for better display
        df = pd.DataFrame([
            {
                'ID': v['variation_id'],
                'Param 1': v['variations_param_1'][:30] + '...' if v['variations_param_1'] and len(v['variations_param_1']) > 30 else v['variations_param_1'],
                'Param 2': v['variations_param_2'][:30] + '...' if v['variations_param_2'] and len(v['variations_param_2']) > 30 else v['variations_param_2'],
                'Param 3': v['variations_param_3'][:30] + '...' if v['variations_param_3'] and len(v['variations_param_3']) > 30 else v['variations_param_3'], 
                'Difficulty': v['difficulty_level'],
                'Expected': v['expected_response'][:20] + '...' if v['expected_response'] and len(v['expected_response']) > 20 else v['expected_response'],
                'Enabled': '✅' if v['enabled'] else '❌'
            } for v in variations
        ])
        
        st.dataframe(df, use_container_width=True)
        
        # Detailed view for selected variation
        variation_options = {f"Variation {v['variation_id']} (Level {v['difficulty_level']})": v['variation_id'] for v in variations}
        selected_var_key = st.selectbox("View Details", options=list(variation_options.keys()))
        
        if selected_var_key:
            selected_var_id = variation_options[selected_var_key]
            variation = next(v for v in variations if v['variation_id'] == selected_var_id)
            
            with st.expander(f"Variation {selected_var_id} Details", expanded=True):
                st.write(f"**Difficulty Level:** {variation['difficulty_level']}")
                st.write(f"**Parameter 1:** {variation['variations_param_1']}")
                if variation['variations_param_2']:
                    st.write(f"**Parameter 2:** {variation['variations_param_2']}")
                if variation['variations_param_3']:
                    st.write(f"**Parameter 3:** {variation['variations_param_3']}")
                st.write(f"**Expected Response:** {variation['expected_response']}")
                
                col1, col2 = st.columns(2)
                if col1.button(f"✏️ Edit Variation", key=f"edit_var_{selected_var_id}"):
                    st.info("Edit functionality coming soon!")
                if col2.button(f"🗑️ Delete Variation", key=f"del_var_{selected_var_id}"):
                    st.warning("Delete functionality coming soon!")
    else:
        st.info("No variations yet. Add test cases below!")
    
    # Add variation section  
    st.subheader("➕ Add New Variation")
    if st.button("Add Variation"):
        st.session_state[f'show_add_var_{recipe_id}'] = True
    
    if st.session_state.get(f'show_add_var_{recipe_id}', False):
        show_add_variation_form(recipe_id)

def show_add_variation_form(recipe_id: int):
    """Form to add a new variation to a recipe"""
    
    with st.form(f"add_variation_{recipe_id}"):
        st.write("**Create New Variation**")
        
        col1, col2 = st.columns(2)
        difficulty_level = col1.number_input("Difficulty Level", min_value=1, max_value=10, value=1)
        enabled = col2.checkbox("Enabled", value=True)
        
        variations_param_1 = st.text_input("Parameter 1 *", placeholder="Primary test input (required)")
        variations_param_2 = st.text_input("Parameter 2", placeholder="Secondary test input (optional)")
        variations_param_3 = st.text_input("Parameter 3", placeholder="Tertiary test input (optional)")
        
        expected_response = st.text_area(
            "Expected Response",
            placeholder="What should the perfect response look like?",
            height=100
        )
        
        submitted = st.form_submit_button("✅ Create Variation")
        
        if submitted and variations_param_1:
            variation_id = execute_write("""
                INSERT INTO variations (
                    recipe_id, variations_param_1, variations_param_2, variations_param_3,
                    difficulty_level, expected_response, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipe_id, variations_param_1, variations_param_2 or None, 
                  variations_param_3 or None, difficulty_level, expected_response, int(enabled)))
            
            if variation_id:
                st.success(f"✅ Variation {variation_id} created successfully!")
                st.session_state[f'show_add_var_{recipe_id}'] = False
                st.rerun()
        elif submitted:
            st.error("❌ Parameter 1 is required")

def show_recipe_recipe_runs(recipe_id: int):
    """Display recipe runs for this recipe"""
    
    recipe_runs = execute_query("""
        SELECT rr.recipe_run_id, rr.variation_id, rr.batch_id, rr.status,
               rr.started_at, rr.completed_at, rr.total_steps, rr.completed_steps,
               v.variations_param_1, v.difficulty_level
        FROM recipe_runs rr
        LEFT JOIN variations v ON rr.variation_id = v.variation_id
        WHERE rr.recipe_id = ?
        ORDER BY rr.recipe_run_id DESC
    """, (recipe_id,))
    
    if recipe_runs:
        df = pd.DataFrame([
            {
                'Run ID': rr['recipe_run_id'],
                'Variation': f"{rr['variation_id']} (L{rr['difficulty_level']})" if rr['variation_id'] else 'N/A',
                'Batch': rr['batch_id'],
                'Status': rr['status'],
                'Progress': f"{rr['completed_steps'] or 0}/{rr['total_steps'] or 0}",
                'Started': rr['started_at'],
                'Completed': rr['completed_at']
            } for rr in recipe_runs
        ])
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No recipe runs found for this recipe")

def show_recipe_settings(recipe_id: int):
    """Recipe configuration and settings"""
    
    recipe = execute_query("SELECT * FROM recipes WHERE recipe_id = ?", (recipe_id,))[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚙️ Configuration")
        st.write(f"**Recipe ID:** {recipe['recipe_id']}")
        st.write(f"**Canonical Code:** {recipe['canonical_code']}")
        st.write(f"**Version:** {recipe['version']}")
        st.write(f"**Max Instruction Cycles:** {recipe['max_instruction_cycles']}")
        st.write(f"**Enabled:** {'Yes' if recipe['enabled'] else 'No'}")
        st.write(f"**Created:** {recipe['timestamp']}")
    
    with col2:
        st.subheader("📝 Notes")
        if recipe['review_notes']:
            st.write(recipe['review_notes'])
        else:
            st.write("*No notes added*")
        
        if st.button("✏️ Edit Recipe"):
            st.info("Edit functionality coming soon!")

def show_create_recipe_form():
    """Form to create a new recipe"""
    
    # Fetch canonical options
    canonicals = execute_query("SELECT canonical_code, capability_description FROM canonicals WHERE enabled = 1")
    canonical_options = {f"{c['canonical_code']}: {c['capability_description'][:50]}...": c['canonical_code'] for c in canonicals}
    
    with st.form("create_recipe"):
        st.subheader("Create New Recipe")
        
        if not canonical_options:
            st.error("No canonicals available! Please create canonicals first.")
            return
        
        selected_canonical_key = st.selectbox("Canonical Code", options=list(canonical_options.keys()))
        canonical_code = canonical_options[selected_canonical_key] if selected_canonical_key else None
        
        col1, col2 = st.columns(2)
        max_cycles = col1.number_input("Max Instruction Cycles", min_value=1, value=10, 
                                      help="Maximum execution cycles to prevent infinite loops")
        version = col2.number_input("Version", min_value=1, value=1)
        
        enabled = st.checkbox("Enabled", value=True)
        review_notes = st.text_area("Review Notes (optional)", 
                                   placeholder="Any notes about this recipe configuration")
        
        submitted = st.form_submit_button("✅ Create Recipe")
        
        if submitted and canonical_code:
            recipe_id = execute_write("""
                INSERT INTO recipes (canonical_code, max_instruction_cycles, version, enabled, review_notes)
                VALUES (?, ?, ?, ?, ?)
            """, (canonical_code, max_cycles, version, int(enabled), review_notes or None))
            
            if recipe_id:
                st.success(f"✅ Recipe {recipe_id} created successfully!")
                st.session_state.show_create_recipe = False
                st.rerun()
        elif submitted:
            st.error("❌ Please select a canonical code")

# Placeholder pages (to be implemented)
def show_instructions_page():
    st.title("🎯 Instructions")
    st.info("Instructions overview page coming soon! Use the Recipes page to manage instructions for now.")

def show_variations_page():
    st.title("🔀 Variations") 
    st.info("Variations overview page coming soon! Use the Recipes page to manage variations for now.")

def show_branches_page():
    st.title("🌳 Branches")
    st.info("Instruction branches page coming soon!")

def show_actors_page():
    st.title("👤 Actors")
    st.info("Actor management page coming soon!")

def show_recipe_runs_page():
    st.title("🏃 Recipe Runs")
    st.info("Recipe execution monitoring page coming soon!")

def show_canonicals_page():
    st.title("📋 Canonicals")
    st.info("Canonicals management page coming soon!")

# Run the application
if __name__ == "__main__":
    main()