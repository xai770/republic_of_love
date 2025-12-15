"""
Results Tab - Execution results with hierarchical drill-down
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from database.queries import (
    get_recent_recipe_runs, get_session_runs_for_recipe_run,
    get_instruction_runs_for_session_run, get_branch_executions_for_instruction_run,
    get_all_recipes, get_variations_for_recipe
)

def render_results_tab():
    """Render execution results with hierarchical drill-down"""
    
    st.header("📊 Execution History")
    st.write("View recipe runs and drill down to sessions and instructions")
    
    # Filters section
    render_filters()
    
    # Recent executions
    st.subheader("🕒 Recent Executions")
    render_recent_executions()
    
    # Detailed results drill-down
    st.subheader("🔬 Detailed Results")
    render_detailed_results()

def render_filters():
    """Render filter controls for results with cascading dropdowns"""
    
    st.subheader("🔍 Filters")
    
    # Four-column layout for cascading filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Recipe filter - dynamic from database
        try:
            all_recipes = get_all_recipes()
            recipe_options = ["All"] + [f"Recipe {r['recipe_id']}: {r['canonical_code']}" for r in all_recipes]
            
            recipe_filter = st.selectbox(
                "Filter by Recipe", 
                recipe_options,
                help="Filter results by specific recipe"
            )
            
            # Extract recipe_id from selection
            selected_recipe_id = None
            if recipe_filter != "All":
                selected_recipe_id = int(recipe_filter.split()[1].replace(":", ""))
            
            st.session_state.recipe_filter = recipe_filter
            st.session_state.selected_recipe_id = selected_recipe_id
        except Exception as e:
            st.error(f"Failed to load recipes: {e}")
            st.session_state.recipe_filter = "All"
            st.session_state.selected_recipe_id = None
    
    with col2:
        # Variation filter - depends on recipe selection
        try:
            selected_recipe_id = st.session_state.get('selected_recipe_id')
            
            if selected_recipe_id:
                variations = get_variations_for_recipe(selected_recipe_id)
                variation_options = ["All"] + [
                    f"Var {v['variation_id']}: Diff {v['difficulty_level']} - {v['variations_param_1'][:30]}..." 
                    for v in variations
                ]
            else:
                variation_options = ["All"]
            
            variation_filter = st.selectbox(
                "Filter by Variation",
                variation_options,
                help="Filter by variation (select recipe first)"
            )
            
            # Extract variation_id from selection
            selected_variation_id = None
            if variation_filter != "All" and variation_filter != "Select recipe first":
                selected_variation_id = int(variation_filter.split()[1].replace(":", ""))
            
            st.session_state.variation_filter = variation_filter
            st.session_state.selected_variation_id = selected_variation_id
        except Exception as e:
            st.session_state.variation_filter = "All"
            st.session_state.selected_variation_id = None
    
    with col3:
        # Status filter
        status_filter = st.selectbox(
            "Status", 
            ["All", "SUCCESS", "FAILED", "RUNNING", "PENDING"],
            help="Filter by execution status"
        )
        st.session_state.status_filter = status_filter
    
    with col4:
        # Batch filter
        batch_filter = st.selectbox(
            "Batch",
            ["All", "1", "2", "3", "4", "5"],
            help="Filter by batch number"
        )
        st.session_state.batch_filter = batch_filter

def render_recent_executions():
    """Display recent recipe runs with basic information"""
    
    try:
        # Get recent recipe runs
        recipe_runs = get_recent_recipe_runs(limit=20)
        
        if not recipe_runs:
            st.info("No recent recipe runs found")
            return
        
        # Apply filters (basic implementation)
        filtered_runs = apply_filters(recipe_runs)
        
        if not filtered_runs:
            st.warning("No results match the current filters")
            return
        
        # Display summary stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            success_count = len([r for r in filtered_runs if r['status'] == 'SUCCESS'])
            st.metric("Successful Runs", success_count)
        
        with col2:
            failed_count = len([r for r in filtered_runs if r['status'] == 'FAILED'])
            st.metric("Failed Runs", failed_count)
        
        with col3:
            running_count = len([r for r in filtered_runs if r['status'] == 'RUNNING'])
            st.metric("Running", running_count)
        
        with col4:
            if filtered_runs:
                avg_steps = sum(r['completed_steps'] or 0 for r in filtered_runs) / len(filtered_runs)
                st.metric("Avg Steps", f"{avg_steps:.1f}")
        
        # Display runs table
        st.write(f"**{len(filtered_runs)} runs** (showing last 20):")
        
        # Convert to DataFrame for better display
        df_runs = pd.DataFrame(filtered_runs)
        
        # Format columns for display
        display_columns = [
            'recipe_run_id', 'canonical_code', 'variation_id', 'difficulty_level',
            'batch_id', 'status', 'started_at', 'completed_steps', 'total_steps'
        ]
        
        if all(col in df_runs.columns for col in display_columns):
            display_df = df_runs[display_columns].copy()
            
            # Format datetime
            if 'started_at' in display_df.columns:
                display_df['started_at'] = pd.to_datetime(display_df['started_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Add progress column
            display_df['progress'] = display_df.apply(
                lambda row: f"{row['completed_steps'] or 0}/{row['total_steps'] or 0}" 
                if row['total_steps'] else "N/A", axis=1
            )
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "recipe_run_id": "Run ID",
                    "canonical_code": "Canonical",
                    "variation_id": "Variation",
                    "difficulty_level": "Difficulty",
                    "batch_id": "Batch",
                    "status": st.column_config.TextColumn(
                        "Status",
                        help="Execution status"
                    ),
                    "started_at": "Started",
                    "progress": "Progress"
                }
            )
        else:
            st.dataframe(df_runs, use_container_width=True, hide_index=True)
    
    except Exception as e:
        st.error(f"Failed to load recent executions: {e}")

def apply_filters(recipe_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply user-selected filters to recipe runs"""
    
    filtered = recipe_runs.copy()
    
    # Recipe filter
    selected_recipe_id = st.session_state.get('selected_recipe_id')
    if selected_recipe_id:
        filtered = [r for r in filtered if r['recipe_id'] == selected_recipe_id]
    
    # Variation filter
    selected_variation_id = st.session_state.get('selected_variation_id')
    if selected_variation_id:
        filtered = [r for r in filtered if r['variation_id'] == selected_variation_id]
    
    # Status filter
    status_filter = st.session_state.get('status_filter', 'All')
    if status_filter != 'All':
        filtered = [r for r in filtered if r['status'] == status_filter]
    
    # Batch filter
    batch_filter = st.session_state.get('batch_filter', 'All')
    if batch_filter != 'All':
        batch_id = int(batch_filter)
        filtered = [r for r in filtered if r['batch_id'] == batch_id]
    
    return filtered

def render_detailed_results():
    """Render hierarchical drill-down of recipe run details"""
    
    try:
        # Get recent runs for drill-down
        recipe_runs = get_recent_recipe_runs(limit=10)
        
        if not recipe_runs:
            st.info("No recipe runs available for detailed analysis")
            return
        
        # Apply filters
        filtered_runs = apply_filters(recipe_runs)
        
        if not filtered_runs:
            st.warning("No results match the current filters")
            return
        
        st.write(f"**Detailed drill-down** (showing {len(filtered_runs)} runs):")
        
        # Check for auto-selected recipe run from execution
        auto_selected_run_id = st.session_state.get('view_recipe_run_id')
        if auto_selected_run_id:
            st.info(f"🎯 Auto-selected Recipe Run {auto_selected_run_id} from recent execution")
            # Clear the session state
            del st.session_state.view_recipe_run_id
        
        # Display each recipe run with drill-down
        for recipe_run in filtered_runs:
            render_recipe_run_details(recipe_run, auto_selected=(recipe_run['recipe_run_id'] == auto_selected_run_id))
    
    except Exception as e:
        st.error(f"Failed to load detailed results: {e}")

def render_recipe_run_details(recipe_run: Dict[str, Any], auto_selected: bool = False):
    """Render details for a single recipe run with session drill-down"""
    
    run_id = recipe_run['recipe_run_id']
    status = recipe_run['status']
    
    # Status-based styling
    if status == 'SUCCESS':
        status_emoji = "✅"
        status_color = "green"
    elif status == 'FAILED':
        status_emoji = "❌"
        status_color = "red"
    elif status == 'RUNNING':
        status_emoji = "⏳"
        status_color = "orange"
    else:
        status_emoji = "❓"
        status_color = "gray"
    
    # Recipe run expander
    expanded = auto_selected  # Auto-expand if this was just executed
    with st.expander(
        f"{status_emoji} Recipe Run #{run_id} - {status} - {recipe_run['canonical_code']}", 
        expanded=expanded
    ):
        # Basic recipe run info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Recipe ID:** {recipe_run['recipe_id']}")
            st.write(f"**Variation:** {recipe_run['variations_param_1'] or 'N/A'}")
            st.write(f"**Batch:** {recipe_run['batch_id']}")
        
        with col2:
            st.write(f"**Started:** {recipe_run['started_at'] or 'N/A'}")
            st.write(f"**Completed:** {recipe_run['completed_at'] or 'Still running'}")
            st.write(f"**Difficulty:** {recipe_run['difficulty_level'] or 'N/A'}")
        
        with col3:
            progress = f"{recipe_run['completed_steps'] or 0}/{recipe_run['total_steps'] or 0}"
            st.write(f"**Progress:** {progress}")
            if recipe_run['error_details']:
                st.error(f"**Error:** {recipe_run['error_details']}")
        
        # Session runs drill-down
        try:
            session_runs = get_session_runs_for_recipe_run(run_id)
            
            if session_runs:
                st.write(f"**Session Runs ({len(session_runs)}):**")
                
                for session_run in session_runs:
                    render_session_run_details(session_run)
            else:
                st.info("No session runs found (V3.0 legacy execution or incomplete run)")
        
        except Exception as e:
            st.error(f"Failed to load session runs: {e}")

def render_session_run_details(session_run: Dict[str, Any]):
    """Render details for a single session run with instruction drill-down"""
    
    session_id = session_run['session_run_id']
    session_status = session_run['status']
    session_number = session_run['session_number']
    
    # Session status emoji
    if session_status == 'SUCCESS':
        session_emoji = "✅"
    elif session_status == 'FAILED':
        session_emoji = "❌"
    elif session_status == 'RUNNING':
        session_emoji = "⏳"
    else:
        session_emoji = "❓"
    
    # Session run expander (nested)
    with st.expander(f"  └─ {session_emoji} Session #{session_number} - {session_status}", expanded=False):
        
        # Session run info
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Session Name:** {session_run['session_name'] or 'Unnamed'}")
            st.write(f"**Actor:** {session_run['actor_id'] or 'N/A'}")
            st.write(f"**Started:** {session_run['started_at'] or 'N/A'}")
        
        with col2:
            st.write(f"**Completed:** {session_run['completed_at'] or 'Still running'}")
            st.write(f"**LLM Conversation:** {session_run['llm_conversation_id'] or 'N/A'}")
            if session_run['error_details']:
                st.error(f"**Error:** {session_run['error_details']}")
        
        # Instruction runs drill-down
        try:
            instruction_runs = get_instruction_runs_for_session_run(session_id)
            
            if instruction_runs:
                st.write(f"**Instruction Runs ({len(instruction_runs)}):**")
                
                for instruction_run in instruction_runs:
                    render_instruction_run_details(instruction_run)
            else:
                st.info("No instruction runs found")
        
        except Exception as e:
            st.error(f"Failed to load instruction runs: {e}")

def render_instruction_run_details(instruction_run: Dict[str, Any]):
    """Render details for a single instruction run with branch drill-down"""
    
    run_id = instruction_run['instruction_run_id']
    step_number = instruction_run['step_number']
    status = instruction_run['status']
    
    # Instruction status emoji
    if status == 'SUCCESS':
        instr_emoji = "✅"
    elif status == 'FAILED':
        instr_emoji = "❌"
    elif status == 'RUNNING':
        instr_emoji = "⏳"
    else:
        instr_emoji = "❓"
    
    # Instruction run expander (double nested)
    with st.expander(f"    └─ {instr_emoji} Step #{step_number} - {status}", expanded=False):
        
        # Instruction run info
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Description:** {instruction_run['step_description'] or 'N/A'}")
            st.write(f"**Status:** {status}")
            if instruction_run['latency_ms']:
                st.write(f"**Latency:** {instruction_run['latency_ms']}ms")
        
        with col2:
            st.write(f"**Pass/Fail:** {instruction_run['pass_fail'] or 'N/A'}")
            st.write(f"**Academic Score:** {instruction_run['academic_score'] or 'N/A'}")
            if instruction_run['error_details']:
                st.error(f"**Error:** {instruction_run['error_details']}")
        
        # Show prompt and response
        if instruction_run['prompt_rendered']:
            st.write("**Prompt Rendered:**")
            st.code(instruction_run['prompt_rendered'], language="text")
        
        if instruction_run['response_received']:
            st.write("**Response Received:**")
            st.code(instruction_run['response_received'], language="text")
        
        # Branch executions drill-down
        try:
            branch_executions = get_branch_executions_for_instruction_run(run_id)
            
            if branch_executions:
                st.write(f"**Branch Executions ({len(branch_executions)}):**")
                render_branch_executions(branch_executions)
            else:
                st.caption("No branch executions (linear instruction flow)")
        
        except Exception as e:
            st.error(f"Failed to load branch executions: {e}")

def render_branch_executions(branch_executions: List[Dict[str, Any]]):
    """Render branch execution details"""
    
    for execution in branch_executions:
        taken_emoji = "✅" if execution['taken'] else "❌"
        
        with st.container():
            st.write(f"      └─ {taken_emoji} **Branch {execution['branch_id']}**: {execution['branch_condition']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.caption(f"Condition Type: {execution['condition_type']}")
                st.caption(f"Result: {execution['condition_result']}")
            
            with col2:
                st.caption(f"Taken: {'Yes' if execution['taken'] else 'No'}")
                st.caption(f"Action: {execution['branch_action'] or 'N/A'}")

if __name__ == "__main__":
    # For testing this component independently
    st.set_page_config(page_title="Results Test", layout="wide")
    render_results_tab()