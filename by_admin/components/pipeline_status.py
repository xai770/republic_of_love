"""
Pipeline Status Tab - Health metrics, gap analysis, and execution interface
"""

import streamlit as st
import pandas as pd
import sys
import os
import subprocess
from typing import Dict, Any, List

# Add parent directory for recipe runner import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.views import get_pipeline_health, get_incomplete_items
from database.queries import get_all_canonicals, get_recipes_for_canonical, get_variations_for_recipe, get_pending_recipe_runs

def render_run_all_pending():
    """Render 'Run All Pending' button with status display"""
    
    try:
        # Get pending recipe runs
        pending = get_pending_recipe_runs()
        
        if not pending:
            st.info("✅ **No pending recipe runs found** - All tests complete!")
            return
        
        # Display pending count and summary
        st.write(f"**{len(pending)} pending recipe runs** awaiting execution:")
        
        # Show summary in a data frame
        pending_df = pd.DataFrame(pending)
        st.dataframe(
            pending_df[['recipe_run_id', 'canonical_code', 'difficulty_level', 'batch_id']],
            use_container_width=True,
            hide_index=True
        )
        
        # Big button to run all
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("▶️ RUN ALL PENDING TESTS", type="primary", use_container_width=True):
                execute_all_pending(pending)
    
    except Exception as e:
        st.error(f"Failed to load pending recipe runs: {e}")

def execute_all_pending(pending_runs: List[Dict]):
    """Execute all pending recipe runs with real-time progress tracking"""
    
    try:
        total_runs = len(pending_runs)
        
        # Initialize progress tracking
        progress_bar = st.progress(0)
        status_container = st.empty()
        
        status_container.write(f"🚀 **Starting batch execution of {total_runs} recipe runs...**")
        
        # Execute ALL pending runs via subprocess with progress monitoring
        # The V3.1 runner handles all pending runs automatically
        result = execute_all_pending_subprocess_with_progress(total_runs, progress_bar, status_container)
        
        # Final progress
        progress_bar.progress(1.0)
        
        # Display results summary
        if result['status'] == 'SUCCESS':
            st.success(f"✅ **Batch execution completed successfully!** Check results tab for details.")
            st.write(f"**Completed:** {result.get('completed', 0)} | **Failed:** {result.get('failed', 0)}")
        elif result['status'] == 'TIMEOUT':
            st.warning(f"⏱️ **Runner still executing** - {result.get('completed', 0)} completed so far. Refresh page to see final results.")
        else:
            st.error(f"❌ **Batch execution failed:** {result.get('error', 'Unknown error')}")
            if result.get('stderr'):
                st.write(f"**Error Details:**")
                st.code(result.get('stderr', 'No error details'), language='text')
        
        # Refresh button
        if st.button("🔄 Refresh Page"):
            st.rerun()
    
    except Exception as e:
        st.error(f"❌ **Batch execution failed with error:** {e}")

def execute_all_pending_subprocess_with_progress(total_runs, progress_bar, status_container) -> Dict[str, Any]:
    """Execute ALL pending recipe runs via subprocess with real-time progress monitoring
    
    Note: The V3.1 runner processes all pending recipe_runs in one invocation.
    This function monitors the database to show progress in real-time.
    """
    
    import time
    import sqlite3
    
    try:
        # Path to the V3.1 runner script
        runner_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'recipe_run_test_runner_v32.py'
        )
        
        # Start subprocess in background (no timeout!)
        process = subprocess.Popen(
            ['python3', runner_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Monitor progress by querying database
        db_path = '/home/xai/Documents/ty_learn/data/llmcore.db'
        initial_pending = total_runs
        
        while process.poll() is None:  # While process is still running
            time.sleep(2)  # Check every 2 seconds
            
            try:
                # Query database for current status
                conn = sqlite3.connect(db_path, timeout=1.0)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM recipe_runs rr
                    JOIN recipes r ON rr.recipe_id = r.recipe_id
                    WHERE r.canonical_code = 'ld_classify_joke_quality'
                    GROUP BY status
                """)
                
                status_counts = dict(cursor.fetchall())
                conn.close()
                
                # Calculate progress
                completed = status_counts.get('SUCCESS', 0)
                failed = status_counts.get('FAILED', 0)
                pending = status_counts.get('PENDING', 0)
                
                progress = (completed + failed) / (initial_pending + completed + failed) if (initial_pending + completed + failed) > 0 else 0
                progress_bar.progress(min(progress, 0.99))  # Cap at 99% until fully done
                
                status_container.write(f"⚙️ **Running:** {completed} completed, {failed} failed, {pending} pending...")
                
            except sqlite3.OperationalError:
                # Database locked - runner is writing, that's fine
                pass
        
        # Process completed - get final output
        stdout, stderr = process.communicate()
        
        # Get final counts
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM recipe_runs rr
            JOIN recipes r ON rr.recipe_id = r.recipe_id
            WHERE r.canonical_code = 'ld_classify_joke_quality'
            GROUP BY status
        """)
        status_counts = dict(cursor.fetchall())
        conn.close()
        
        completed = status_counts.get('SUCCESS', 0)
        failed = status_counts.get('FAILED', 0)
        
        # Check return code
        if process.returncode == 0:
            return {
                'status': 'SUCCESS',
                'completed': completed,
                'failed': failed,
                'stdout': stdout
            }
        else:
            return {
                'status': 'FAILED',
                'error': f"Exit code {process.returncode}",
                'completed': completed,
                'failed': failed,
                'stderr': stderr,
                'stdout': stdout
            }
    
    except Exception as e:
        return {
            'status': 'FAILED',
            'error': str(e)
        }

def render_selective_execution():
    """Render interface for filtering and selecting specific tests to run"""
    
    try:
        # Get all pending recipe runs
        pending = get_pending_recipe_runs()
        
        if not pending:
            st.info("✅ **No pending recipe runs found** - All tests complete!")
            return
        
        pending_df = pd.DataFrame(pending)
        
        st.write(f"**{len(pending)} pending recipe runs** available for selection")
        
        # Filter controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filter by canonical
            canonicals = sorted(pending_df['canonical_code'].unique())
            selected_canonical = st.selectbox(
                "Filter by Canonical:",
                options=['All'] + canonicals,
                key='filter_canonical'
            )
        
        with col2:
            # Filter by model (actor_id)
            models = sorted(pending_df['actor_id'].unique()) if 'actor_id' in pending_df.columns else []
            selected_model = st.selectbox(
                "Filter by Model:",
                options=['All'] + models,
                key='filter_model'
            )
        
        with col3:
            # Filter by topic (variations_param_1)
            topics = sorted(pending_df['variations_param_1'].unique()) if 'variations_param_1' in pending_df.columns else []
            selected_topic = st.selectbox(
                "Filter by Topic:",
                options=['All'] + topics,
                key='filter_topic'
            )
        
        # Apply filters
        filtered_df = pending_df.copy()
        
        if selected_canonical != 'All':
            filtered_df = filtered_df[filtered_df['canonical_code'] == selected_canonical]
        
        if selected_model != 'All':
            filtered_df = filtered_df[filtered_df['actor_id'] == selected_model]
        
        if selected_topic != 'All':
            filtered_df = filtered_df[filtered_df['variations_param_1'] == selected_topic]
        
        st.write(f"**{len(filtered_df)} tests** match your filters")
        
        if len(filtered_df) == 0:
            st.warning("No tests match your filter criteria")
            return
        
        # Display filtered tests with selection checkboxes
        st.write("**Select tests to run:**")
        
        # Use session state to track selections
        if 'selected_tests' not in st.session_state:
            st.session_state.selected_tests = set()
        
        # Quick selection buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Select All", key='select_all'):
                st.session_state.selected_tests = set(filtered_df['recipe_run_id'].tolist())
                st.rerun()
        with col2:
            if st.button("❌ Clear All", key='clear_all'):
                st.session_state.selected_tests = set()
                st.rerun()
        with col3:
            if st.button("🔄 Select First 10", key='select_first_10'):
                st.session_state.selected_tests = set(filtered_df['recipe_run_id'].head(10).tolist())
                st.rerun()
        
        # Display table with selection column - only show columns that exist
        display_columns = ['recipe_run_id', 'canonical_code']
        if 'actor_id' in filtered_df.columns:
            display_columns.append('actor_id')
        if 'variations_param_1' in filtered_df.columns:
            display_columns.append('variations_param_1')
        if 'batch_id' in filtered_df.columns:
            display_columns.append('batch_id')
        if 'difficulty_level' in filtered_df.columns:
            display_columns.append('difficulty_level')
        
        display_df = filtered_df[display_columns].copy()
        display_df.insert(0, 'Select', display_df['recipe_run_id'].isin(st.session_state.selected_tests))
        
        # Use data editor for selection
        edited_df = st.data_editor(
            display_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select tests to run",
                    default=False,
                )
            },
            disabled=['recipe_run_id', 'canonical_code', 'actor_id', 'variations_param_1', 'batch_id', 'difficulty_level']
        )
        
        # Update session state with selections
        st.session_state.selected_tests = set(edited_df[edited_df['Select']]['recipe_run_id'].tolist())
        
        # Run selected button
        selected_count = len(st.session_state.selected_tests)
        
        if selected_count > 0:
            st.write(f"**{selected_count} tests selected**")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(f"▶️ RUN {selected_count} SELECTED TESTS", type="primary", use_container_width=True, key='run_selected'):
                    execute_selected_tests(list(st.session_state.selected_tests))
        else:
            st.info("👆 Select one or more tests above to run them")
    
    except Exception as e:
        st.error(f"Failed to load pending recipe runs: {e}")
        import traceback
        st.code(traceback.format_exc())


def execute_selected_tests(recipe_run_ids: List[int]):
    """Execute only the selected recipe runs"""
    
    try:
        # Write selected IDs to a temp file for the runner to process
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'recipe_run_ids': recipe_run_ids}, f)
            temp_file = f.name
        
        st.info(f"🚀 Starting execution of {len(recipe_run_ids)} selected tests...")
        
        # Run the test runner with the selected IDs
        runner_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'recipe_run_test_runner_v32.py')
        
        # Execute in subprocess (background)
        process = subprocess.Popen(
            ['python3', runner_path, '--ids-file', temp_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Initialize progress tracking
        progress_bar = st.progress(0)
        status_container = st.empty()
        
        # Poll database for progress
        import time
        from database.connection import get_db_connection
        
        start_time = time.time()
        last_completed = 0
        
        while True:
            # Check if process is still running
            poll_result = process.poll()
            
            # Query database for completion status
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END) as running
                FROM recipe_runs
                WHERE recipe_run_id IN ({})
            """.format(','.join(map(str, recipe_run_ids))))
            
            result = cursor.fetchone()
            conn.close()
            
            completed = result[0] or 0
            failed = result[1] or 0
            running = result[2] or 0
            
            # Update progress
            progress = completed / len(recipe_run_ids) if len(recipe_run_ids) > 0 else 0
            progress_bar.progress(progress)
            
            elapsed = int(time.time() - start_time)
            status_container.write(f"⏱️ {elapsed}s elapsed | ✅ {completed} completed | ❌ {failed} failed | 🔄 {running} running")
            
            # If process finished, break
            if poll_result is not None:
                break
            
            # If all tests complete, break
            if completed + failed >= len(recipe_run_ids):
                break
            
            time.sleep(2)  # Poll every 2 seconds
        
        # Final status
        progress_bar.progress(1.0)
        
        if completed + failed >= len(recipe_run_ids):
            st.success(f"✅ **Execution completed!** {completed} succeeded, {failed} failed")
            
            # Clear selections
            st.session_state.selected_tests = set()
            
            # Cleanup temp file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
            
            if st.button("🔄 Refresh Page"):
                st.rerun()
        else:
            st.warning("⚠️ **Process ended but not all tests completed.** Check logs for details.")
    
    except Exception as e:
        st.error(f"Failed to execute selected tests: {e}")
        import traceback
        st.code(traceback.format_exc())


def render_pipeline_status_tab():
    """Render health metrics, gap analysis, and execution interface"""
    
    st.header("⚙️ Pipeline Status - Quality Control & Execution")
    st.write("Monitor pipeline health, identify configuration gaps, and execute tests")
    
    # ============================================================================
    # TEST SELECTION & EXECUTION - Priority Feature
    # ============================================================================
    st.subheader("🚀 Test Execution")
    
    # Tab switcher for different execution modes
    exec_tab1, exec_tab2 = st.tabs(["🎯 Select Tests", "▶️ Run All Pending"])
    
    with exec_tab1:
        render_selective_execution()
    
    with exec_tab2:
        render_run_all_pending()
    
    st.divider()
    
    # Health Metrics Section
    st.header("📊 Pipeline Health Metrics")
    render_health_metrics()
    
    # Incomplete Items Section
    st.subheader("🔍 Incomplete Items - Action Required")
    render_incomplete_items()
    
    # Quick Execute Section
    st.subheader("🎯 Quick Execute (Single Recipe Run)")
    render_execute_interface()

def render_health_metrics():
    """Display pipeline health metrics with color-coded indicators"""
    
    try:
        health = get_pipeline_health()
        
        # Display metrics in columns
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                label="Canonicals Without Recipes",
                value=health['canonicals_orphaned'],
                delta=f"{-health['canonicals_orphaned']} to goal",
                delta_color="inverse"  # Red if positive, green if zero
            )
        
        with col2:
            st.metric(
                label="Recipes Without Variations",
                value=health['recipes_missing_variations'],
                delta=f"{-health['recipes_missing_variations']} to goal",
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                label="Recipes Without Sessions", 
                value=health['recipes_missing_sessions'],
                delta=f"{-health['recipes_missing_sessions']} to goal",
                delta_color="inverse"
            )
        
        with col4:
            st.metric(
                label="Sessions Without Instructions",
                value=health['sessions_missing_instructions'], 
                delta=f"{-health['sessions_missing_instructions']} to goal",
                delta_color="inverse"
            )
        
        with col5:
            st.metric(
                label="Ready for Testing",
                value=health['recipes_ready_for_testing'],
                delta="Fully configured recipes",
                delta_color="normal"
            )
        
        # Overall health indicator
        total_issues = (health['canonicals_orphaned'] + 
                       health['recipes_missing_variations'] + 
                       health['recipes_missing_sessions'] + 
                       health['sessions_missing_instructions'])
        
        if total_issues == 0:
            st.success("🎉 **Perfect Pipeline Health!** All entities properly configured.")
        elif total_issues <= 5:
            st.warning(f"⚠️ **{total_issues} configuration issues** found. Please review incomplete items below.")
        else:
            st.error(f"❌ **{total_issues} configuration issues** found. Significant gaps in pipeline configuration.")
    
    except Exception as e:
        st.error(f"Failed to load health metrics: {e}")

def render_incomplete_items():
    """Display incomplete items with navigation to fix them"""
    
    # Canonicals without recipes
    with st.expander("📋 Canonicals Without Recipes", expanded=False):
        try:
            orphaned_canonicals = get_incomplete_items('v_canonicals_orphaned')
            
            if orphaned_canonicals:
                st.write(f"**{len(orphaned_canonicals)} canonicals** need recipes:")
                
                for canonical in orphaned_canonicals:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**{canonical['canonical_code']}**: {canonical['capability_description'][:80]}...")
                        st.caption(f"Facet: {canonical['facet_id']}")
                    
                    with col2:
                        if st.button("Create Recipe", key=f"create_recipe_{canonical['canonical_code']}"):
                            # Set session state for navigation to Fundamentals tab
                            st.session_state.action = "create_recipe"
                            st.session_state.target_canonical = canonical['canonical_code']
                            st.balloons()
                            st.success(f"Navigate to Fundamentals tab to create recipe for {canonical['canonical_code']}")
            else:
                st.success("✅ All canonicals have recipes!")
        
        except Exception as e:
            st.error(f"Failed to load orphaned canonicals: {e}")
    
    # Recipes missing variations
    with st.expander("📊 Recipes Missing Variations", expanded=False):
        try:
            recipes_missing_variations = get_incomplete_items('v_recipes_missing_variations')
            
            if recipes_missing_variations:
                st.write(f"**{len(recipes_missing_variations)} recipes** need variations:")
                
                for recipe in recipes_missing_variations:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Recipe {recipe['recipe_id']}**: {recipe['canonical_code']} v{recipe['recipe_version']}")
                    
                    with col2:
                        if st.button("Add Variations", key=f"add_variations_{recipe['recipe_id']}"):
                            st.session_state.action = "add_variations"
                            st.session_state.target_recipe_id = recipe['recipe_id']
                            st.success(f"Navigate to Fundamentals tab to add variations for Recipe {recipe['recipe_id']}")
            else:
                st.success("✅ All recipes have variations!")
        
        except Exception as e:
            st.error(f"Failed to load recipes missing variations: {e}")
    
    # Recipes missing sessions
    with st.expander("🔗 Recipes Missing Sessions", expanded=False):
        try:
            recipes_missing_sessions = get_incomplete_items('v_recipes_missing_sessions')
            
            if recipes_missing_sessions:
                st.write(f"**{len(recipes_missing_sessions)} recipes** need sessions:")
                
                for recipe in recipes_missing_sessions:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Recipe {recipe['recipe_id']}**: {recipe['canonical_code']} v{recipe['recipe_version']}")
                    
                    with col2:
                        if st.button("Add Sessions", key=f"add_sessions_{recipe['recipe_id']}"):
                            st.session_state.action = "add_sessions"
                            st.session_state.target_recipe_id = recipe['recipe_id']
                            st.success(f"Navigate to Fundamentals tab to add sessions for Recipe {recipe['recipe_id']}")
            else:
                st.success("✅ All recipes have sessions!")
        
        except Exception as e:
            st.error(f"Failed to load recipes missing sessions: {e}")
    
    # Sessions missing instructions
    with st.expander("📝 Sessions Missing Instructions", expanded=False):
        try:
            sessions_missing_instructions = get_incomplete_items('v_sessions_missing_instructions')
            
            if sessions_missing_instructions:
                st.write(f"**{len(sessions_missing_instructions)} sessions** need instructions:")
                
                for session in sessions_missing_instructions:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Session {session['session_number']}**: {session['session_name']}")
                        st.caption(f"Recipe {session['recipe_id']} | Session ID: {session['session_id']}")
                    
                    with col2:
                        if st.button("Add Instructions", key=f"add_instructions_{session['session_id']}"):
                            st.session_state.action = "add_instructions"
                            st.session_state.target_session_id = session['session_id']
                            st.success(f"Navigate to Fundamentals tab to add instructions for Session {session['session_number']}")
            else:
                st.success("✅ All sessions have instructions!")
        
        except Exception as e:
            st.error(f"Failed to load sessions missing instructions: {e}")
    
    # Ready for testing
    with st.expander("🎯 Ready for Testing", expanded=False):
        try:
            ready_recipes = get_incomplete_items('v_recipes_ready_for_testing')
            
            if ready_recipes:
                st.write(f"**{len(ready_recipes)} recipes** are fully configured and ready for testing:")
                
                for recipe in ready_recipes:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Recipe {recipe['recipe_id']}**: {recipe['canonical_code']} v{recipe['recipe_version']}")
                        st.caption(f"Variations: {recipe['variation_count']} | Sessions: {recipe['session_count']} | Instructions: {recipe['instruction_count']}")
                        st.caption(f"Runs completed: {recipe['run_count']} | Runs needed: {recipe['runs_needed']}")
                    
                    with col2:
                        if st.button("Execute Tests", key=f"execute_{recipe['recipe_id']}"):
                            st.session_state.quick_execute_recipe = recipe['recipe_id']
                            st.success(f"Recipe {recipe['recipe_id']} selected for execution below!")
                            st.rerun()
            else:
                st.info("No fully configured recipes found. Complete the items above first.")
        
        except Exception as e:
            st.error(f"Failed to load ready recipes: {e}")

def render_execute_interface():
    """Render quick execution interface with progress tracking"""
    
    try:
        # Get dropdown options
        canonicals = get_all_canonicals()
        canonical_options = [""] + [f"{c['canonical_code']}: {c['capability_description'][:50]}..." for c in canonicals]
        
        # Four-column layout for selection
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            selected_canonical_display = st.selectbox("Select Canonical", canonical_options)
            canonical_code = selected_canonical_display.split(":")[0] if selected_canonical_display else None
        
        # Cascade: recipes depend on canonical
        recipes = []
        if canonical_code:
            recipes = get_recipes_for_canonical(canonical_code)
        
        with col2:
            recipe_options = [""] + [f"Recipe {r['recipe_id']} v{r['recipe_version']}" for r in recipes]
            selected_recipe_display = st.selectbox("Select Recipe", recipe_options)
            recipe_id = None
            if selected_recipe_display:
                recipe_id = int(selected_recipe_display.split()[1])
        
        # Cascade: variations depend on recipe
        variations = []
        if recipe_id:
            variations = get_variations_for_recipe(recipe_id)
        
        with col3:
            variation_options = [""] + [f"Var {v['variation_id']}: {v['variations_param_1'][:20]}... (diff {v['difficulty_level']})" for v in variations]
            selected_variation_display = st.selectbox("Select Variation", variation_options)
            variation_id = None
            if selected_variation_display:
                variation_id = int(selected_variation_display.split()[1].replace(":", ""))
        
        with col4:
            batch_id = st.selectbox("Batch", [""] + [1, 2, 3, 4, 5])
        
        # Auto-populate from "Ready for Testing" selection
        if st.session_state.get('quick_execute_recipe'):
            auto_recipe_id = st.session_state.quick_execute_recipe
            st.info(f"🎯 Auto-selected Recipe {auto_recipe_id} from Ready for Testing section")
            
            # Clear the session state
            del st.session_state.quick_execute_recipe
        
        # Execute button
        all_selected = canonical_code and recipe_id and variation_id and batch_id
        
        if all_selected:
            # Show selection summary
            st.write("**Execution Summary:**")
            selected_recipe = next(r for r in recipes if r['recipe_id'] == recipe_id)
            selected_variation = next(v for v in variations if v['variation_id'] == variation_id)
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"• **Canonical:** {canonical_code}")
                st.write(f"• **Recipe:** {recipe_id} v{selected_recipe['recipe_version']}")
            
            with col2:
                st.write(f"• **Variation:** {selected_variation['variations_param_1']} (difficulty {selected_variation['difficulty_level']})")
                st.write(f"• **Batch:** {batch_id}")
            
            # Big execute button
            if st.button("▶️ RUN RECIPE", type="primary", use_container_width=True):
                execute_recipe(recipe_id, variation_id, batch_id)
        else:
            st.info("👆 Select all parameters above to enable recipe execution")
    
    except Exception as e:
        st.error(f"Failed to load execution interface: {e}")

def execute_recipe(recipe_id: int, variation_id: int, batch_id: int):
    """Execute recipe with progress tracking (single recipe run via Quick Execute)"""
    
    try:
        # Note: This creates a new recipe_run record via database insertion
        # Then executes it via the V3.1 runner
        
        st.warning("⚠️ **Quick Execute not yet implemented for V3.1**")
        st.write("Please use SQL to create recipe_run records manually, then use 'Run All Pending' button above")
        st.code(f"""
-- SQL to create recipe_run for Quick Execute:
INSERT INTO recipe_runs (recipe_id, variation_id, batch_id, status)
VALUES ({recipe_id}, {variation_id}, {batch_id}, 'PENDING');
        """, language="sql")
        
        # TODO: Implement recipe_run creation + execution in V3.1
        # For now, users should create recipe_runs via SQL and use "Run All Pending"
    
    except Exception as e:
        st.error(f"❌ **Execution failed with error:** {e}")

if __name__ == "__main__":
    # For testing this component independently
    st.set_page_config(page_title="Pipeline Status Test", layout="wide")
    render_pipeline_status_tab()