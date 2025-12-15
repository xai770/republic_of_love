"""
Analyze Tab - Bottom-up execution analysis
Shows recent instruction runs first, then drills UP to sessions and recipes
Perfect for debugging: "Why did this fail?" → find instruction → see context
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from database.connection import get_db_connection

def render_analyze_tab():
    """Render bottom-up analysis starting from instruction runs"""
    
    st.header("📈 Bottom-Up Analysis")
    st.write("Find recent instruction runs and drill UP to see which sessions and recipes they belong to")
    
    # Time range filter
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        time_range = st.selectbox(
            "Time Range:",
            ["Last Hour", "Last 6 Hours", "Last 24 Hours", "Last Week", "All Time"],
            index=2,
            help="Filter instruction runs by when they were created"
        )
    
    with col2:
        status_filter = st.selectbox(
            "Status:",
            ["All", "FAILED", "SUCCESS", "RUNNING"],
            help="Filter by execution status"
        )
    
    with col3:
        limit = st.number_input("Limit:", min_value=10, max_value=500, value=50, step=10)
    
    st.divider()
    
    # Get recent instruction runs
    try:
        instruction_runs = get_recent_instruction_runs(
            time_range=time_range,
            status_filter=status_filter,
            limit=limit
        )
        
        if not instruction_runs:
            st.info("No instruction runs found in the selected time range")
            return
        
        # Summary metrics
        render_summary_metrics(instruction_runs)
        
        st.divider()
        
        # Display instruction runs with drill-up
        st.subheader(f"🔍 Recent Instruction Runs ({len(instruction_runs)})")
        
        for idx, instr_run in enumerate(instruction_runs, 1):
            render_instruction_with_context(instr_run, idx)
    
    except Exception as e:
        st.error(f"Failed to load instruction runs: {e}")
        import traceback
        st.code(traceback.format_exc())

def get_recent_instruction_runs(
    time_range: str,
    status_filter: str,
    limit: int
) -> List[Dict[str, Any]]:
    """Get recent instruction runs with drill-up context"""
    
    # Calculate time threshold
    now = datetime.now()
    if time_range == "Last Hour":
        threshold = now - timedelta(hours=1)
    elif time_range == "Last 6 Hours":
        threshold = now - timedelta(hours=6)
    elif time_range == "Last 24 Hours":
        threshold = now - timedelta(days=1)
    elif time_range == "Last Week":
        threshold = now - timedelta(days=7)
    else:
        threshold = datetime(2000, 1, 1)  # All time
    
    # Build query
    query = """
        SELECT 
            ir.instruction_run_id,
            ir.session_run_id,
            ir.instruction_id,
            ir.step_number,
            i.step_description,
            ir.status,
            ir.latency_ms,
            ir.error_details,
            ir.created_at as instruction_created_at,
            ir.prompt_rendered,
            ir.response_received,
            
            -- Session context
            sr.session_run_id,
            sr.recipe_run_id,
            sr.session_number,
            sr.status as session_status,
            s.session_name,
            s.actor_id,
            
            -- Recipe context
            rr.recipe_run_id,
            rr.recipe_id,
            rr.batch_id,
            rr.status as recipe_status,
            r.recipe_name,
            
            -- Canonical context (from first session in recipe)
            c.canonical_code,
            c.facet_id as facet_name
            
        FROM instruction_runs ir
        LEFT JOIN instructions i ON ir.instruction_id = i.instruction_id
        LEFT JOIN session_runs sr ON ir.session_run_id = sr.session_run_id
        LEFT JOIN sessions s ON sr.session_id = s.session_id
        LEFT JOIN recipe_runs rr ON sr.recipe_run_id = rr.recipe_run_id
        LEFT JOIN recipes r ON rr.recipe_id = r.recipe_id
        LEFT JOIN recipe_sessions rs ON r.recipe_id = rs.recipe_id AND rs.execution_order = 1
        LEFT JOIN sessions s_first ON rs.session_id = s_first.session_id
        LEFT JOIN canonicals c ON s_first.canonical_code = c.canonical_code
        
        WHERE ir.created_at >= %s
    """
    
    params = [threshold]
    
    if status_filter != "All":
        query += " AND ir.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY ir.created_at DESC LIMIT %s"
    params.append(limit)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
    
    return results

def render_summary_metrics(instruction_runs: List[Dict[str, Any]]):
    """Display summary metrics for instruction runs"""
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total = len(instruction_runs)
        st.metric("Total Runs", total)
    
    with col2:
        success = len([r for r in instruction_runs if r['status'] == 'SUCCESS'])
        success_rate = (success / total * 100) if total > 0 else 0
        st.metric("Success", f"{success} ({success_rate:.0f}%)")
    
    with col3:
        failed = len([r for r in instruction_runs if r['status'] == 'FAILED'])
        st.metric("Failed", failed, delta=f"-{failed}" if failed > 0 else None, delta_color="inverse")
    
    with col4:
        avg_latency = sum(r['latency_ms'] or 0 for r in instruction_runs) / total if total > 0 else 0
        st.metric("Avg Latency", f"{avg_latency:.0f}ms")
    
    with col5:
        unique_recipes = len(set(r['recipe_id'] for r in instruction_runs if r['recipe_id']))
        st.metric("Unique Recipes", unique_recipes)

def render_instruction_with_context(instr_run: Dict[str, Any], idx: int):
    """Render single instruction run with drill-up to session and recipe context"""
    
    # Status emoji
    if instr_run['status'] == 'SUCCESS':
        emoji = "✅"
        color = "green"
    elif instr_run['status'] == 'FAILED':
        emoji = "❌"
        color = "red"
    elif instr_run['status'] == 'RUNNING':
        emoji = "⏳"
        color = "orange"
    else:
        emoji = "❓"
        color = "gray"
    
    # Build step identifier: session.step (e.g., 1.1, 2.1)
    step_id = f"{instr_run['session_number']}.{instr_run['step_number']}"
    
    # Build breadcrumb context
    breadcrumb = f"{instr_run['facet_name'] or 'Unknown'} > {instr_run['canonical_code'] or 'Unknown'} > Recipe {instr_run['recipe_id']} > Session {instr_run['session_number']} > Step {step_id}"
    
    # Instruction expander
    with st.expander(
        f"{emoji} **#{idx}** - Step {step_id}: {instr_run['step_description'] or 'No description'} - {instr_run['status']}",
        expanded=False
    ):
        # Breadcrumb navigation
        st.caption(f"🧭 **Context:** {breadcrumb}")
        
        st.divider()
        
        # Three-column layout for instruction details
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Instruction Details:**")
            st.write(f"Run ID: {instr_run['instruction_run_id']}")
            st.write(f"Step: {instr_run['step_number']}")
            st.write(f"Status: {emoji} {instr_run['status']}")
            if instr_run['latency_ms']:
                st.write(f"Latency: {instr_run['latency_ms']}ms")
        
        with col2:
            st.write("**Session Context:**")
            st.write(f"Session Run ID: {instr_run['session_run_id']}")
            st.write(f"Session #: {instr_run['session_number']}")
            st.write(f"Session Name: {instr_run['session_name'] or 'Unnamed'}")
            st.write(f"Actor: {instr_run['actor_id'] or 'N/A'}")
        
        with col3:
            st.write("**Recipe Context:**")
            st.write(f"Recipe Run ID: {instr_run['recipe_run_id']}")
            st.write(f"Recipe: {instr_run['recipe_name'] or instr_run['recipe_id']}")
            st.write(f"Batch: {instr_run['batch_id'] or 'N/A'}")
            st.write(f"Facet: {instr_run['facet_name'] or 'N/A'}")
        
        # Show error if failed
        if instr_run['error_details']:
            st.divider()
            st.error(f"**Error:** {instr_run['error_details']}")
        
        # Show prompt and response (collapsible)
        if instr_run['prompt_rendered']:
            with st.expander("📝 View Prompt", expanded=False):
                st.code(instr_run['prompt_rendered'], language="text")
        
        if instr_run['response_received']:
            with st.expander("💬 View Response", expanded=False):
                st.code(instr_run['response_received'], language="text")
        
        # Quick actions
        st.divider()
        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            if st.button(f"🔍 View Full Session Run", key=f"view_session_{instr_run['instruction_run_id']}"):
                st.session_state.view_session_run_id = instr_run['session_run_id']
                st.info(f"Switch to 'Execution History' tab to view Session Run #{instr_run['session_run_id']}")
        
        with action_col2:
            if st.button(f"📋 View Full Recipe Run", key=f"view_recipe_{instr_run['instruction_run_id']}"):
                st.session_state.view_recipe_run_id = instr_run['recipe_run_id']
                st.info(f"Switch to 'Execution History' tab to view Recipe Run #{instr_run['recipe_run_id']}")
        
        with action_col3:
            if st.button(f"🏗️ View Recipe Design", key=f"view_design_{instr_run['instruction_run_id']}"):
                st.session_state.view_recipe_id = instr_run['recipe_id']
                st.info(f"Switch to 'Fundamentals' tab to view Recipe #{instr_run['recipe_id']} design")

if __name__ == "__main__":
    # For testing this component independently
    st.set_page_config(page_title="Analyze Test", layout="wide")
    render_analyze_tab()
