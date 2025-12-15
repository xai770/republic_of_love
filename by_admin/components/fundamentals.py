"""
Fundamentals Tab - All design-time entities for building test recipes
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from database.queries import (
    get_all_canonicals, get_canonicals_for_facet, get_all_recipes, 
    get_recipes_for_canonical, get_sessions_for_recipe, get_instructions_for_session,
    get_branches_for_instruction, get_variations_for_recipe, get_all_actors
)
from .facets import render_facets_section

def render_fundamentals_tab():
    """Render all design-time entities in hierarchical order"""
    
    st.header("🏗️ Fundamentals - Design Your Test Recipes")
    st.write("Build and configure all entities needed for testing. Work top-down: Facets → Canonicals → Recipes → Sessions → Instructions → Branches")
    
    # Facets section
    with st.expander("📁 Facets - Capability Taxonomy", expanded=False):
        render_facets_section()
    
    # Canonicals section  
    with st.expander("📋 Canonicals - Master Test Definitions", expanded=False):
        render_canonicals_section()
    
    # Recipes section
    with st.expander("🍳 Recipes - Test Execution Plans", expanded=False):
        render_recipes_section()
    
    # Context preservation: Get selected recipe for filtering
    selected_recipe_id = st.session_state.get('selected_recipe_id', None)
    
    # Variations section (FULL WIDTH)
    with st.expander("📊 Variations - Test Parameters & Inputs", expanded=False):
        render_variations_section(selected_recipe_id)
    
    # Sessions section
    with st.expander("🔗 Sessions - Workflow Organization", expanded=False):
        render_sessions_section(selected_recipe_id)
    
    # Instructions section  
    selected_session_id = st.session_state.get('selected_session_id', None)
    with st.expander("📝 Instructions - Step-by-Step Workflows", expanded=False):
        render_instructions_section(selected_session_id)
    
    # Instruction Branches section
    selected_instruction_id = st.session_state.get('selected_instruction_id', None)
    with st.expander("🔀 Instruction Branches - Conditional Logic", expanded=False):
        render_branches_section(selected_instruction_id)

def render_canonicals_section():
    """Render canonicals management with facet filtering"""
    st.subheader("📋 Canonicals Management")
    
    # Check if a facet is selected in the facets section
    selected_facet_id = st.session_state.get('selected_facet_id', None)
    
    if selected_facet_id:
        st.info(f"🎯 Filtered by facet: **{selected_facet_id}** (selected in Facets section)")
        
        # Get canonicals for the selected facet
        from .facets import get_canonicals_by_facet
        canonicals = get_canonicals_by_facet(selected_facet_id)
        
        # Add clear filter option
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("❌ Clear Facet Filter", key="clear_canonicals_facet_filter"):
                st.session_state.selected_facet_id = None
                st.session_state.current_parent_filter = None  # Also reset facets navigation
                st.rerun()
    else:
        st.caption("💡 Select a facet in the Facets section above to filter canonicals, or view all below")
        canonicals = get_all_canonicals()
    
    if canonicals:
        # Prepare data for display
        df_data = []
        for canonical in canonicals:
            df_data.append({
                'canonical_code': canonical['canonical_code'],
                'facet_id': canonical['facet_id'],
                'capability_description': canonical.get('capability_description', ''),
                'enabled': '✅ Enabled' if canonical['enabled'] else '❌ Disabled',
                'updated_at': canonical.get('updated_at', '-')
            })
        
        df = pd.DataFrame(df_data)
        
        # Display canonicals table with selection
        st.write(f"**Found {len(canonicals)} canonicals** {'(filtered)' if selected_facet_id else '(all)'}")
        
        event = st.dataframe(
            df,
            width='stretch',
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Handle selection for detailed view
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            canonical_data = canonicals[selected_idx]
            
            # Store selected canonical for recipes filtering
            st.session_state.selected_canonical_code = canonical_data['canonical_code']
            
            st.success(f"📌 Selected: **{canonical_data['canonical_code']}**")
            
            # Show canonical details
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Facet ID:** {canonical_data['facet_id']}")
                st.write(f"**Status:** {'✅ Enabled' if canonical_data['enabled'] else '❌ Disabled'}")
                st.write(f"**Updated:** {canonical_data.get('updated_at', 'N/A')}")
            
            with col2:
                if canonical_data.get('capability_description'):
                    st.write("**Capability Description:**")
                    st.write(canonical_data['capability_description'])
            
            # Show prompt and response with dark theme and proper markdown rendering
            if canonical_data.get('prompt'):
                with st.expander("📝 Prompt", expanded=True):
                    st.markdown("**Prompt Content:**")
                    # Add custom CSS for the markdown content styling
                    st.markdown("""
                    <style>
                    .prompt-container {
                        background-color: #0e1117;
                        padding: 15px;
                        border-radius: 8px;
                        border: 1px solid #262730;
                        border-left: 4px solid #1f77b4;
                        overflow-y: auto;
                        max-height: 400px;
                    }
                    .prompt-container p, .prompt-container ul, .prompt-container ol, .prompt-container h1, .prompt-container h2, .prompt-container h3 {
                        color: #fafafa !important;
                        margin-bottom: 0.5em;
                    }
                    .prompt-container code {
                        background-color: #262730 !important;
                        color: #fafafa !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Create container and render markdown
                    st.markdown('<div class="prompt-container">', unsafe_allow_html=True)
                    st.markdown(canonical_data['prompt'])
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if canonical_data.get('response'):
                with st.expander("💬 Response", expanded=True):
                    st.markdown("**Expected Response:**")
                    # Add custom CSS for the markdown content styling
                    st.markdown("""
                    <style>
                    .response-container {
                        background-color: #0e1117;
                        padding: 15px;
                        border-radius: 8px;
                        border: 1px solid #262730;
                        border-left: 4px solid #28a745;
                        overflow-y: auto;
                        max-height: 500px;
                    }
                    .response-container p, .response-container ul, .response-container ol, .response-container h1, .response-container h2, .response-container h3 {
                        color: #fafafa !important;
                        margin-bottom: 0.5em;
                    }
                    .response-container code {
                        background-color: #262730 !important;
                        color: #fafafa !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Create container and render markdown
                    st.markdown('<div class="response-container">', unsafe_allow_html=True)
                    st.markdown(canonical_data['response'])
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if canonical_data.get('review_notes'):
                with st.expander("📋 Review Notes", expanded=False):
                    st.markdown("**Review Notes:**")
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #0e1117; 
                            padding: 15px; 
                            border-radius: 8px; 
                            border: 1px solid #262730;
                            border-left: 4px solid #ffc107;
                            color: #fafafa;
                            font-family: Arial, sans-serif;
                            white-space: pre-wrap;
                            overflow-y: auto;
                            max-height: 200px;
                        ">
                        {canonical_data['review_notes']}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
    else:
        if selected_facet_id:
            st.info(f"No canonicals found for facet '{selected_facet_id}'")
        else:
            st.info("No canonicals found in database")
            
def render_recipes_section():
    """Render recipes management with canonical filtering"""
    st.subheader("🍳 Recipes Management")
    
    # Check if a canonical is selected in the canonicals section
    selected_canonical_code = st.session_state.get('selected_canonical_code', None)
    
    if selected_canonical_code:
        st.info(f"🎯 Filtered by canonical: **{selected_canonical_code}** (selected in Canonicals section)")
        
        # Get recipes for the selected canonical
        recipes = get_recipes_for_canonical(selected_canonical_code)
        
        # Add clear filter option
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("❌ Clear Canonical Filter", key="clear_recipes_canonical_filter"):
                st.session_state.selected_canonical_code = None
                if 'selected_recipe_id' in st.session_state:
                    del st.session_state.selected_recipe_id  # Also clear recipe context
                st.rerun()
    else:
        st.caption("💡 Select a canonical in the Canonicals section above to filter recipes, or view all below")
        recipes = get_all_recipes()
    
    if recipes:
        # Prepare data for display
        df_data = []
        for recipe in recipes:
            df_data.append({
                'recipe_id': recipe['recipe_id'],
                'recipe_name': recipe['recipe_name'],
                'recipe_version': recipe['recipe_version'],
                'session_count': recipe.get('session_count', 0),
                'enabled': '✅ Enabled' if recipe['enabled'] else '❌ Disabled',
                'max_total_session_runs': recipe.get('max_total_session_runs', 100),
                'created_at': recipe.get('created_at', '-')
            })
        
        df = pd.DataFrame(df_data)
        
        # Display recipes table with selection
        st.write(f"**Found {len(recipes)} recipes** {'(filtered)' if selected_canonical_code else '(all)'}")
        
        event = st.dataframe(
            df,
            width='stretch',
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Handle selection for context preservation
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            recipe_data = recipes[selected_idx]
            
            # Store selected recipe for other sections
            st.session_state.selected_recipe_id = recipe_data['recipe_id']
            
            st.success(f"📌 Selected Recipe {recipe_data['recipe_id']} - Context set for sections below")
            
            # Show recipe details
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Recipe Name:** {recipe_data['recipe_name']}")
                st.write(f"**Version:** {recipe_data['recipe_version']}")
                st.write(f"**Status:** {'✅ Enabled' if recipe_data['enabled'] else '❌ Disabled'}")
            
            with col2:
                st.write(f"**Max Session Runs:** {recipe_data.get('max_total_session_runs', 100)}")
                st.write(f"**Sessions:** {recipe_data.get('session_count', 0)}")
                st.write(f"**Created:** {recipe_data.get('created_at', 'N/A')}")
            
            if recipe_data.get('review_notes'):
                with st.expander("📋 Review Notes"):
                    st.text_area("Review Notes", recipe_data['review_notes'], height=100, disabled=True, key="recipe_notes_view")
    else:
        if selected_canonical_code:
            st.info(f"No recipes found for canonical '{selected_canonical_code}'")
        else:
            st.info("No recipes found in database")

def render_variations_section(recipe_id: Optional[int]):
    """Render variations with full-width data editor"""
    st.subheader("📊 Variations Management")
    
    if not recipe_id:
        st.info("👆 Select a recipe above to view/edit its variations")
        return
    
    variations = get_variations_for_recipe(recipe_id)
    
    st.write(f"**Variations for Recipe {recipe_id}:**")
    
    if variations:
        # Convert to DataFrame for data editor
        df = pd.DataFrame(variations)
        
        # Configure data editor (FULL WIDTH - no parallel columns)
        edited_variations = st.data_editor(
            df,
            num_rows="dynamic",
            disabled=["variation_id", "recipe_id"],  # Can't edit these
            column_config={
                "enabled": st.column_config.CheckboxColumn("Enabled"),
                "difficulty_level": st.column_config.NumberColumn(
                    "Difficulty", 
                    min_value=1, 
                    max_value=10,
                    help="Difficulty scale 1-10"
                ),
                "variations_param_1": st.column_config.TextColumn(
                    "Parameter 1",
                    required=True,
                    help="Primary test input"
                ),
                "variations_param_2": st.column_config.TextColumn(
                    "Parameter 2",
                    help="Secondary test input (optional)"
                ),
                "variations_param_3": st.column_config.TextColumn(
                    "Parameter 3", 
                    help="Tertiary test input (optional)"
                ),
                "expected_response": st.column_config.TextColumn(
                    "Expected Response",
                    help="What response indicates success"
                ),
                "complexity_score": st.column_config.NumberColumn(
                    "Complexity",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.2f"
                )
            },
            use_container_width=True,
            hide_index=True,
        )
        
        # Detect changes and show save button
        has_changes = not df.equals(edited_variations)
        
        if has_changes:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.warning("⚠️ You have unsaved changes")
            with col2:
                if st.button("💾 Save Changes", type="primary"):
                    # TODO: Implement save variations
                    st.success("✅ Variations saved! (implementation pending)")
                    st.rerun()
    else:
        st.info(f"No variations found for Recipe {recipe_id}")
        
        # Add new variation form
        with st.form(f"add_variation_{recipe_id}"):
            st.write("**Add New Variation:**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                param1 = st.text_input("Parameter 1", help="Primary test input")
                param2 = st.text_input("Parameter 2", help="Optional")
            
            with col2:
                param3 = st.text_input("Parameter 3", help="Optional")
                difficulty = st.number_input("Difficulty Level", min_value=1, max_value=10, value=1)
            
            with col3:
                expected_response = st.text_input("Expected Response")
                enabled = st.checkbox("Enabled", value=True)
            
            if st.form_submit_button("➕ Add Variation"):
                # TODO: Implement variation creation
                st.success(f"Variation would be created (implementation pending)")

def render_sessions_section(recipe_id: Optional[int]):
    """Render sessions filtered by selected recipe"""
    st.subheader("🔗 Sessions Management")
    
    if not recipe_id:
        st.info("👆 Select a recipe above to view/edit its sessions")
        return
    
    sessions = get_sessions_for_recipe(recipe_id)
    
    st.write(f"**Sessions for Recipe {recipe_id}:**")
    
    if sessions:
        # Display sessions with actor information
        for session in sessions:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Session {session['execution_order']}:** {session['session_name']}")
                    st.caption(f"Actor: {session['actor_id']} ({session['actor_type']})")
                
                with col2:
                    st.write(f"🔗 Context: {session['context_strategy'] or 'default'}")
                    st.caption(f"On Success: {session['on_success_action']} | On Failure: {session['on_failure_action']}")
                
                with col3:
                    status = "✅" if session['enabled'] else "❌"
                    st.write(status)
                    if st.button("Select", key=f"select_session_{session['session_id']}"):
                        st.session_state.selected_session_id = session['session_id']
                        st.success(f"Selected Session {session['session_number']}")
                        st.rerun()
                
                if session['session_description']:
                    st.caption(session['session_description'])
                
                st.divider()
    else:
        st.info(f"No sessions found for Recipe {recipe_id}")

def render_instructions_section(session_id: Optional[int]):
    """Render instructions filtered by selected session"""
    st.subheader("📝 Instructions Management")
    
    if not session_id:
        st.info("👆 Select a session above to view/edit its instructions")
        return
    
    instructions = get_instructions_for_session(session_id)
    
    st.write(f"**Instructions for Session {session_id}:**")
    
    if instructions:
        for instruction in instructions:
            with st.expander(f"Step {instruction['step_number']}: {instruction['step_description']}", expanded=False):
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Actor:** {instruction['actor_id']} ({instruction['actor_type']})")
                    st.write(f"**Timeout:** {instruction['timeout_seconds']}s")
                    st.write(f"**Enabled:** {'✅' if instruction['enabled'] else '❌'}")
                    st.write(f"**Terminal:** {'✅' if instruction['is_terminal'] else '❌'}")
                
                with col2:
                    if st.button("Select for Branches", key=f"select_instruction_{instruction['instruction_id']}"):
                        st.session_state.selected_instruction_id = instruction['instruction_id']
                        st.success(f"Selected Step {instruction['step_number']} for branch editing")
                        st.rerun()
                
                # Show prompt template with syntax highlighting
                st.write("**Prompt Template:**")
                st.code(instruction['prompt_template'], language="text")
                
                if instruction['expected_pattern']:
                    st.write("**Expected Pattern:**")
                    st.code(instruction['expected_pattern'])
                
                if instruction['validation_rules']:
                    st.write("**Validation Rules:**")
                    st.code(instruction['validation_rules'])
    else:
        st.info(f"No instructions found for Session {session_id}")

def render_branches_section(instruction_id: Optional[int]):
    """Render instruction branches filtered by selected instruction"""
    st.subheader("🔀 Instruction Branches Management")
    
    if not instruction_id:
        st.info("👆 Select an instruction above to view/edit its branches")
        return
    
    branches = get_branches_for_instruction(instruction_id)
    
    st.write(f"**Branches for Instruction {instruction_id}:**")
    
    if branches:
        # Display branches in priority order
        for branch in branches:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Priority {branch['branch_priority']}:** {branch['condition_type']}")
                    st.caption(f"Condition: {branch['branch_condition']}")
                
                with col2:
                    st.write(f"**Action:** {branch['branch_action']}")
                    if branch['next_step_id']:
                        st.caption(f"Next Step: {branch['next_step_id']}")
                
                with col3:
                    status = "✅" if branch['enabled'] else "❌"
                    st.write(status)
                
                # Show detailed condition
                if branch['condition_operator'] and branch['condition_value']:
                    st.caption(f"Logic: {branch['condition_operator']} '{branch['condition_value']}'")
                
                st.divider()
    else:
        st.info(f"No branches found for Instruction {instruction_id}")
        st.write("Instructions without branches will proceed linearly to the next step.")

if __name__ == "__main__":
    # For testing this component independently
    st.set_page_config(page_title="Fundamentals Test", layout="wide")
    render_fundamentals_tab()