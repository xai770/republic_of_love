"""
LLMCore V3.1 Admin GUI - Three-Tab Interface
==========================================
Streamlit-based interface for session-aware recipe management, 
pipeline health monitoring, and execution results analysis.
"""

import streamlit as st
import sys
import os

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.fundamentals import render_fundamentals_tab
from components.pipeline_status import render_pipeline_status_tab  
from components.results import render_results_tab
from components.analyze import render_analyze_tab
from database.views import create_all_views
from database.connection import test_connection

def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title="LLMCore V3.1 Admin",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="collapsed"  # No sidebar needed
    )
    
    # ============================================================================
    # CUSTOM CSS - INJECTED EARLY TO OVERRIDE STREAMLIT DEFAULTS
    # ============================================================================
    st.markdown("""
    <style>
        /* ===== BLUE SELECTION OVERRIDE - ALL DATAFRAMES ===== */
        
        /* Target the actual row element that gets selected */
        [data-testid="stDataFrame"] [aria-selected="true"],
        [data-testid="stDataFrame"] [aria-selected="true"] > *,
        [data-testid="stDataFrame"] [aria-selected="true"] td,
        [data-testid="stDataFrame"] [aria-selected="true"] th,
        div[data-testid="stDataFrame"] [aria-selected="true"],
        div[data-testid="stDataFrame"] [aria-selected="true"] > *,
        div[data-testid="stDataFrame"] [aria-selected="true"] td,
        div[data-testid="stDataFrame"] [aria-selected="true"] th {
            background-color: rgba(30, 144, 255, 0.4) !important;
            background: rgba(30, 144, 255, 0.4) !important;
        }
        
        /* Additional targeting for table rows specifically */
        [data-testid="stDataFrame"] tbody tr[aria-selected="true"],
        [data-testid="stDataFrame"] tbody tr[aria-selected="true"] > td,
        div[data-testid="stDataFrame"] tbody tr[aria-selected="true"],
        div[data-testid="stDataFrame"] tbody tr[aria-selected="true"] > td {
            background-color: rgba(30, 144, 255, 0.4) !important;
            background: rgba(30, 144, 255, 0.4) !important;
            border-left: 3px solid #1e90ff !important;
        }
        
        /* NUCLEAR: Override any RGB values close to red */
        [data-testid="stDataFrame"] [style*="rgb(255"],
        [data-testid="stDataFrame"] [style*="rgba(255"] {
            background-color: rgba(30, 144, 255, 0.4) !important;
            background: rgba(30, 144, 255, 0.4) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Additional styling for metrics and general UI
    st.markdown("""
    <style>
        .stMetric {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .metric-good {
            border-color: rgba(0, 255, 0, 0.3);
        }
        
        .metric-warning {
            border-color: rgba(255, 255, 0, 0.3);
        }
        
        .metric-error {
            border-color: rgba(255, 0, 0, 0.3);
        }
        
        .success-text {
            color: #00ff00;
        }
        
        .warning-text {
            color: #ffff00;
        }
        
        .error-text {
            color: #ff0000;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Test database connection
    if not test_connection():
        st.error("❌ Cannot connect to database. Please check the database path.")
        st.stop()
    
    # Create SQL views on startup
    with st.spinner("Initializing database views..."):
        try:
            create_all_views()
            st.success("✅ Database views initialized")
        except Exception as e:
            st.error(f"❌ Failed to initialize database views: {e}")
            st.stop()
    
    # Four-tab interface
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏗️ Fundamentals", 
        "⚙️ Pipeline Status",
        "📊 Execution History",
        "📈 Analyze"
    ])
    
    with tab1:
        render_fundamentals_tab()  # Top-down: facets → canonicals → recipes → sessions → instructions
    
    with tab2:
        render_pipeline_status_tab()
    
    with tab3:
        render_results_tab()  # Top-down execution view: recipe_runs → session_runs → instruction_runs
    
    with tab4:
        render_analyze_tab()  # Bottom-up: instruction_runs → session_runs → recipe_runs for debugging

if __name__ == "__main__":
    main()