#!/usr/bin/env python3
"""
Yogi BI Dashboard — Interactive Job Matching Interface

3-Panel + Postings Layout:
1. Timeline — Stacked bar by domain, click to drill down
2. Qualification — Pie chart with level toggles
3. Geography — State distribution, click to filter
4. Postings — Filtered job listings (bottom half)

This dashboard is the yogi's search criteria interface.
Filters here define what postings they want to see.

Usage:
    streamlit run tools/bi_app.py
    
    # Or with specific port:
    streamlit run tools/bi_app.py --server.port 8501

Author: Arden (Feb 5-6, 2026)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env so DB_PASSWORD is always current
load_dotenv(Path(__file__).parent.parent / '.env', override=True)

from core.database import get_connection_raw, return_connection
import psycopg2
import psycopg2.extras

# =============================================================================
# I18N — BILINGUAL SUPPORT (DE/EN)
# =============================================================================

BI_STRINGS = {
    'de': {
        # Panel headers
        'timeline_header': '📅 Zeitachse nach Berufsfeld',
        'qual_header': '🎓 Qualifikationsstufen',
        'geo_header': '🌍 Geografie',
        'postings_header': '📋 Stellenangebote',
        # Qualification levels
        'q_unclassified': 'Nicht klassifiziert',
        'q_helfer': 'Helfer',
        'q_fachkraft': 'Fachkraft',
        'q_spezialist': 'Spezialist',
        'q_experte': 'Experte',
        'q_unknown': 'Unbekannt',
        'q_desc_unclassified': 'Noch nicht klassifiziert',
        'q_desc_helfer': 'Einstieg/Ungelernt',
        'q_desc_fachkraft': 'Facharbeiter/Ausbildung',
        'q_desc_spezialist': 'Spezialist',
        'q_desc_experte': 'Experte/Akademiker',
        # Qualification summary
        'classified': 'klassifiziert',
        'unclassified': 'nicht klassifiziert',
        # Geography
        'postings_by_state': 'Stellenangebote nach Bundesland',
        'cities_in': 'Städte in',
        # Postings panel
        'matches': 'Treffer',
        'in_last_90_days': 'der letzten 90 Tage',
        'apply_filters': 'Filter setzen, um bestimmte Segmente anzuzeigen',
        'no_match': 'Keine Stellenangebote für diese Filter. Versuchen Sie weniger Filter.',
        'showing_of': 'Zeige 50 von {count} Stellenangeboten. Verfeinern Sie die Filter.',
        'sort_by': 'Sortieren nach',
        'sort_date': '📅 Datum (neueste zuerst)',
        'sort_qual': '🎓 Qualifikationsstufe',
        'sort_state': '🌍 Bundesland',
        'sort_ihl': '⭐ IHL-Score',
        'view': 'Ansehen →',
        # Search
        'select_profile': 'Profil auswählen...',
        'keywords': '🔍 Suchbegriffe',
        'keyword_placeholder': 'Jobtitel, Berufe, Städte suchen...',
        # Filters
        'no_filters': 'Keine Filter aktiv — alle Stellenangebote werden angezeigt',
        'clear_all': '🔄 Alle löschen',
        # Footer
        'footer': 'Yogi BI Dashboard • talent.yoga • Daten von Arbeitsagentur + Deutsche Bank',
        # Debug
        'postings_loaded': 'Stellenangebote geladen',
        'classified_label': 'Klassifiziert',
        'loading': 'Lade Arbeitsmarktdaten...',
    },
    'en': {
        'timeline_header': '📅 Timeline by Domain',
        'qual_header': '🎓 Qualification Levels',
        'geo_header': '🌍 Geography',
        'postings_header': '📋 Postings',
        'q_unclassified': 'Unclassified',
        'q_helfer': 'Helper',
        'q_fachkraft': 'Skilled Worker',
        'q_spezialist': 'Specialist',
        'q_experte': 'Expert',
        'q_unknown': 'Unknown',
        'q_desc_unclassified': 'Not yet classified',
        'q_desc_helfer': 'Entry/Unskilled',
        'q_desc_fachkraft': 'Skilled/Vocational',
        'q_desc_spezialist': 'Specialist',
        'q_desc_experte': 'Expert/Academic',
        'classified': 'classified',
        'unclassified': 'unclassified',
        'postings_by_state': 'Postings by State',
        'cities_in': 'Cities in',
        'matches': 'matches',
        'in_last_90_days': 'in last 90 days',
        'apply_filters': 'Apply filters to explore specific segments',
        'no_match': 'No postings match your current filters. Try relaxing some filters.',
        'showing_of': 'Showing 50 of {count} postings. Refine filters to see more specific results.',
        'sort_by': 'Sort by',
        'sort_date': '📅 Date (newest first)',
        'sort_qual': '🎓 Qualification Level',
        'sort_state': '🌍 State',
        'sort_ihl': '⭐ IHL Score',
        'view': 'View →',
        'select_profile': 'Select profile...',
        'keywords': '🔍 Keywords',
        'keyword_placeholder': 'Search job titles, professions, cities...',
        'no_filters': 'No filters active — showing all postings',
        'clear_all': '🔄 Clear All',
        'footer': 'Yogi BI Dashboard • talent.yoga • Data from Arbeitsagentur + Deutsche Bank',
        'postings_loaded': 'Postings loaded',
        'classified_label': 'Classified',
        'loading': 'Loading job market data...',
    },
}

# Domain name translations (DB stores English names)
DOMAIN_DE = {
    'Technology & Engineering': 'Technik & Ingenieurwesen',
    'Manufacturing & Engineering': 'Produktion & Fertigung',
    'Healthcare & Medicine': 'Gesundheit & Medizin',
    'Transport & Logistics': 'Transport & Logistik',
    'Commerce & Retail': 'Handel & Einzelhandel',
    'Business & Management': 'Wirtschaft & Management',
    'Construction & Trades': 'Bau & Handwerk',
    'Finance & Banking': 'Finanzen & Bankwesen',
    'IT & Technology': 'IT & Technologie',
    'Education & Social Work': 'Bildung & Sozialarbeit',
    'Hospitality & Food': 'Gastgewerbe & Ernährung',
    'Hospitality & Tourism': 'Gastgewerbe & Tourismus',
    'Government & Law': 'Verwaltung & Recht',
    'Culture & Media': 'Kultur & Medien',
    'Science & Research': 'Wissenschaft & Forschung',
    'Security & Defense': 'Sicherheit & Verteidigung',
    'Agriculture & Nature': 'Landwirtschaft & Natur',
    'Unclassified': 'Nicht klassifiziert',
}


def get_lang() -> str:
    """Get current language from session state or query params."""
    # Check query params first (?lang=en)
    params = st.query_params
    if 'lang' in params:
        lang = params['lang']
        if lang in ('de', 'en'):
            return lang
    return st.session_state.get('bi_lang', 'de')


def t(key: str) -> str:
    """Translate a BI string key."""
    lang = get_lang()
    return BI_STRINGS.get(lang, BI_STRINGS['de']).get(key, key)


def domain_name(en_name: str) -> str:
    """Translate domain name to current language."""
    if get_lang() == 'de':
        return DOMAIN_DE.get(en_name, en_name)
    return en_name


# =============================================================================
# STREAMLIT-SPECIFIC DATABASE CONNECTION
# =============================================================================
# Streamlit's caching and multi-threading exhausts the shared pool.
# Use direct connections for BI queries instead.

def get_bi_connection():
    """Get a direct database connection for BI queries (bypasses pool)."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'base_yard'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD'),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Yogi BI — Job Market Dashboard",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stMetric {
        padding: 10px;
        border-radius: 5px;
    }
    .filter-badge {
        background-color: #4CAF50;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        margin: 2px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# PLOTLY DARK MODE TEMPLATE
# =============================================================================

# Create a dark-mode-friendly template
PLOTLY_TEMPLATE = {
    'layout': {
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'color': '#fafafa'},
        'xaxis': {
            'gridcolor': 'rgba(128,128,128,0.2)',
            'linecolor': 'rgba(128,128,128,0.3)',
            'tickfont': {'color': '#fafafa'},
            'title': {'font': {'color': '#fafafa'}}
        },
        'yaxis': {
            'gridcolor': 'rgba(128,128,128,0.2)',
            'linecolor': 'rgba(128,128,128,0.3)',
            'tickfont': {'color': '#fafafa'},
            'title': {'font': {'color': '#fafafa'}}
        },
        'title': {
            'font': {'color': '#fafafa'}
        }
    }
}

# =============================================================================
# DATA LOADING (Cached)
# =============================================================================

DATA_LIMIT = 50000  # Max rows to load for performance

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_postings_data():
    """Load postings with all fields needed for filtering."""
    conn = get_bi_connection()  # Direct connection, bypasses pool
    try:
        cur = conn.cursor()
        
        # First get total count
        cur.execute("""
            SELECT COUNT(*) as cnt FROM postings 
            WHERE first_seen_at >= NOW() - INTERVAL '90 days'
              AND invalidated IS NOT TRUE
        """)
        total_count = cur.fetchone()['cnt']
        
        query = f"""
            SELECT 
                p.posting_id,
                p.job_title,
                p.location_city,
                p.location_state,
                p.location_country,
                p.location_postal_code,
                p.first_seen_at::date as date_seen,
                p.source,
                p.domain_gate->>'primary_domain' as domain,
                p.domain_gate->>'sub_domain' as sub_domain,
                p.qualification_level,
                p.berufenet_name,
                p.berufenet_kldb,
                p.external_url,
                p.ihl_score,
                pc.latitude,
                pc.longitude
            FROM postings p
            LEFT JOIN plz_centroid pc ON p.location_postal_code = pc.plz
            WHERE p.first_seen_at >= NOW() - INTERVAL '90 days'
              AND p.invalidated IS NOT TRUE
            ORDER BY p.first_seen_at DESC
            LIMIT {DATA_LIMIT}
        """
        
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        cur.close()
        # Convert RealDictRow to regular dicts for pandas
        data = [dict(row) for row in rows]
        df = pd.DataFrame(data, columns=columns)
    finally:
        conn.close()  # Direct connection - just close it
    
    if len(df) == 0:
        return df, 0
    
    # Clean up
    df['domain'] = df['domain'].fillna('Unclassified')
    df['date_seen'] = pd.to_datetime(df['date_seen'], errors='coerce')
    df['qualification_level'] = df['qualification_level'].fillna(0).astype(int)
    
    return df, total_count

@st.cache_data(ttl=300)
def load_profiles():
    """Load profiles with skills."""
    conn = get_bi_connection()  # Direct connection
    try:
        cur = conn.cursor()
        
        query = """
            SELECT 
                profile_id,
                full_name,
                current_title,
                skill_keywords,
                location,
                desired_locations,
                desired_roles
            FROM profiles
            WHERE enabled = true
        """
        
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        cur.close()
        # Convert RealDictRow to regular dicts for pandas
        data = [dict(row) for row in rows]
        return pd.DataFrame(data, columns=columns)
    finally:
        conn.close()  # Direct connection - just close it


@st.cache_data(ttl=3600)
def get_plz_coordinates(plz: str) -> tuple:
    """Get lat/lon for a German postal code."""
    conn = get_bi_connection()  # Direct connection
    cur = conn.cursor()
    try:
        cur.execute("SELECT latitude, longitude FROM plz_centroid WHERE plz = %s", (plz,))
        row = cur.fetchone()
        cur.close()
    finally:
        conn.close()  # Direct connection - just close it
    if row:
        return (float(row[0]), float(row[1]))
    return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate haversine distance in km between two points."""
    R = 6371  # Earth's radius in km
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c


@st.cache_data(ttl=3600)
def load_umap_data():
    """Load pre-computed UMAP coordinates if available."""
    umap_path = Path('/home/xai/Documents/ty_learn/data/umap_coords_postings.parquet')
    if umap_path.exists():
        return pd.read_parquet(umap_path)
    return None


@st.cache_data(ttl=3600)
def get_cluster_centroids():
    """Get centroids for each auto_cluster in the UMAP space."""
    umap_df = load_umap_data()
    if umap_df is None:
        return {}
    
    centroids = umap_df.groupby('auto_cluster').agg({
        'umap_x': 'mean', 
        'umap_y': 'mean', 
        'posting_id': 'count'
    }).reset_index()
    
    return {
        row['auto_cluster']: {'x': row['umap_x'], 'y': row['umap_y'], 'count': row['posting_id']}
        for _, row in centroids.iterrows()
    }


# Skill-to-cluster mapping keywords
SKILL_CLUSTER_MAP = {
    # Tech/Engineering
    'elektroniker_mechatroniker': ['elektronik', 'mechatronik', 'elektro', 'schaltung', 'steuerung', 'elektriker', 'automation'],
    'engineer_analyst': ['engineer', 'analyst', 'developer', 'software', 'python', 'java', 'programming', 'data', 'machine learning', 'ai', 'analytics'],
    'consultant_zerspanungsmechaniker': ['consultant', 'beratung', 'cnc', 'zerspanung', 'fräsen', 'drehen'],
    
    # Management/Business
    'manager_mitarbeiter': ['manager', 'management', 'leitung', 'führung', 'team', 'koordination'],
    'manager_senior': ['senior', 'director', 'head', 'vp', 'chief', 'executive'],
    'manager_chef': ['chief', 'ceo', 'cto', 'cfo', 'geschäftsführ', 'vorstand'],
    'services_business': ['business', 'service', 'kundenservice', 'support', 'vertrieb', 'sales'],
    
    # Office/Admin
    'sachbearbeiter_mitarbeiter': ['sachbearbeiter', 'verwaltung', 'büro', 'office', 'administration', 'buchhaltung', 'accounting', 'excel', 'word'],
    'führungskraft_filiale': ['filiale', 'store', 'retail', 'einzelhandel', 'verkauf'],
    
    # Healthcare
    'pflegefachkraft_erzieher': ['pflege', 'erzieher', 'sozial', 'pädagogik', 'betreuung', 'kinder', 'altenpflege', 'kranken'],
    'facharzt_oberarzt': ['arzt', 'medizin', 'klinik', 'krankenhaus', 'therapie', 'diagnostik', 'pharma', 'gesundheit'],
    
    # Logistics/Production
    'lager_stapler': ['lager', 'logistik', 'stapler', 'kommission', 'versand', 'warehouse', 'supply chain'],
    'produktion_helfer': ['produktion', 'fertigung', 'montage', 'helfer', 'arbeiter', 'manufacturing'],
    'gewerblich_sonstig': ['handwerk', 'gewerbe', 'installation', 'wartung', 'reparatur', 'technik'],
    
    # Food/Hospitality
    'koch_köchin': ['koch', 'küche', 'gastronomie', 'restaurant', 'catering', 'food'],
    
    # IT specific
    'inhouse_teilzeit': ['teilzeit', 'inhouse', 'intern', 'support', 'helpdesk'],
    
    # Cleaning/Facility
    'reinigung_facility': ['reinigung', 'facility', 'gebäude', 'hausmeister', 'cleaning'],
    
    # Students/Entry
    'student_einzelhandel': ['student', 'werkstudent', 'praktikum', 'ausbildung', 'trainee', 'junior'],
    'student_basis': ['minijob', 'aushilfe', 'nebenjob', 'basis'],
}


def project_skill_to_umap(skill: str, centroids: dict, jitter: float = 0.5) -> tuple:
    """
    Project a skill to UMAP coordinates based on keyword matching to clusters.
    Returns (x, y) coordinates.
    """
    skill_lower = skill.lower()
    
    # Find matching cluster
    best_cluster = None
    best_score = 0
    
    for cluster, keywords in SKILL_CLUSTER_MAP.items():
        score = sum(1 for kw in keywords if kw in skill_lower)
        if score > best_score and cluster in centroids:
            best_score = score
            best_cluster = cluster
    
    if best_cluster and best_cluster in centroids:
        centroid = centroids[best_cluster]
        # Add small jitter to avoid overlap
        np.random.seed(hash(skill) % 2**32)
        x = centroid['x'] + np.random.uniform(-jitter, jitter)
        y = centroid['y'] + np.random.uniform(-jitter, jitter)
        return x, y
    
    # Default: center of the map with jitter
    np.random.seed(hash(skill) % 2**32)
    return 7.0 + np.random.uniform(-2, 2), 4.0 + np.random.uniform(-2, 2)

def extract_skills_from_profile(skill_keywords):
    """Extract skill list from various profile formats."""
    if not skill_keywords:
        return []
    
    skills = []
    if isinstance(skill_keywords, list):
        for item in skill_keywords:
            if isinstance(item, str):
                skills.append(item)
            elif isinstance(item, dict) and 'skill' in item:
                skills.append(item['skill'])
    return skills

# =============================================================================
# QUALIFICATION LEVEL HELPERS
# =============================================================================

QUAL_EMOJIS = {0: '⚪', 1: '🟢', 2: '🔵', 3: '🟡', 4: '🔴'}
QUAL_KEYS = {0: 'q_unclassified', 1: 'q_helfer', 2: 'q_fachkraft', 3: 'q_spezialist', 4: 'q_experte'}
QUAL_DESC_KEYS = {0: 'q_desc_unclassified', 1: 'q_desc_helfer', 2: 'q_desc_fachkraft', 3: 'q_desc_spezialist', 4: 'q_desc_experte'}


def get_qual_levels() -> dict:
    """Return qualification levels dict translated to current language."""
    return {
        level: (QUAL_EMOJIS[level], t(QUAL_KEYS[level]), t(QUAL_DESC_KEYS[level]))
        for level in range(5)
    }


def qual_label(level: int) -> str:
    """Return emoji + name for qualification level."""
    ql = get_qual_levels()
    if level in ql:
        emoji, name, _ = ql[level]
        return f"{emoji} {name}"
    return f"❓ {t('q_unknown')}"

def qual_emoji(level: int) -> str:
    """Return just emoji for qualification level."""
    return QUAL_EMOJIS.get(level, '❓')

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize all filter states."""
    if 'bi_lang' not in st.session_state:
        # Check query param, default to German
        params = st.query_params
        st.session_state.bi_lang = params.get('lang', 'de') if 'lang' in params else 'de'
    if 'selected_domain' not in st.session_state:
        st.session_state.selected_domain = None
    if 'selected_subdomain' not in st.session_state:
        st.session_state.selected_subdomain = None
    if 'selected_quals' not in st.session_state:
        st.session_state.selected_quals = [0, 1, 2, 3, 4]  # All selected by default including unclassified
    if 'selected_state' not in st.session_state:
        st.session_state.selected_state = None
    if 'selected_city' not in st.session_state:
        st.session_state.selected_city = None
    if 'date_range' not in st.session_state:
        st.session_state.date_range = None
    if 'selected_profile_id' not in st.session_state:
        st.session_state.selected_profile_id = None
    if 'selected_skills' not in st.session_state:
        st.session_state.selected_skills = []
    if 'search_plz' not in st.session_state:
        st.session_state.search_plz = None
    if 'keyword_search' not in st.session_state:
        st.session_state.keyword_search = ''
    if 'search_radius' not in st.session_state:
        st.session_state.search_radius = 25

def reset_filters():
    """Reset all filters to default."""
    st.session_state.selected_domain = None
    st.session_state.selected_subdomain = None
    st.session_state.selected_quals = [0, 1, 2, 3, 4]
    st.session_state.selected_state = None
    st.session_state.selected_city = None
    st.session_state.date_range = None
    st.session_state.selected_skills = []
    st.session_state.search_plz = None
    st.session_state.search_radius = 25
    st.session_state.keyword_search = ''
    st.session_state.selected_profile_id = None
    st.rerun()

# =============================================================================
# FILTER APPLICATION
# =============================================================================

def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all active filters to the dataframe."""
    filtered = df.copy()
    
    # Domain filter
    if st.session_state.selected_domain:
        filtered = filtered[filtered['domain'] == st.session_state.selected_domain]
    
    # Subdomain filter (profession within domain)
    if st.session_state.selected_subdomain:
        filtered = filtered[filtered['berufenet_name'] == st.session_state.selected_subdomain]
    
    # Qualification filter
    if st.session_state.selected_quals:
        filtered = filtered[filtered['qualification_level'].isin(st.session_state.selected_quals)]
    
    # State filter
    if st.session_state.selected_state:
        filtered = filtered[filtered['location_state'] == st.session_state.selected_state]
    
    # City filter
    if st.session_state.selected_city:
        filtered = filtered[filtered['location_city'] == st.session_state.selected_city]
    
    # Radius filter
    search_plz = st.session_state.get('search_plz')
    if search_plz:
        center_coords = get_plz_coordinates(search_plz)
        if center_coords:
            radius_km = st.session_state.get('search_radius', 25)
            center_lat, center_lon = center_coords
            
            # Only filter rows that have lat/lon
            has_coords = filtered['latitude'].notna() & filtered['longitude'].notna()
            
            if has_coords.any():
                # Calculate distance for rows with coordinates
                distances = filtered.loc[has_coords].apply(
                    lambda row: haversine_distance(center_lat, center_lon, row['latitude'], row['longitude']),
                    axis=1
                )
                within_radius = distances <= radius_km
                # Keep rows within radius (drop rows with coords outside radius)
                filtered = filtered.loc[has_coords][within_radius]
    
    # Date range filter
    if st.session_state.date_range:
        start_date, end_date = st.session_state.date_range
        filtered = filtered[
            (filtered['date_seen'] >= pd.to_datetime(start_date)) &
            (filtered['date_seen'] <= pd.to_datetime(end_date))
        ]
    
    # Keyword search filter
    keyword = st.session_state.get('keyword_search', '').strip().lower()
    if keyword:
        # Search in job_title, berufenet_name, and location
        mask = (
            filtered['job_title'].str.lower().str.contains(keyword, na=False) |
            filtered['berufenet_name'].str.lower().str.contains(keyword, na=False) |
            filtered['location_city'].str.lower().str.contains(keyword, na=False)
        )
        filtered = filtered[mask]
    
    return filtered

# =============================================================================
# PANEL 1: TIMELINE BY DOMAIN (Compact)
# =============================================================================

def render_date_domain_panel(df: pd.DataFrame, filtered_df: pd.DataFrame):
    """Render the timeline with stacked domain bars."""
    st.markdown(f"##### {t('timeline_header')}")
    
    # Aggregate by date and domain
    daily = filtered_df.groupby(['date_seen', 'domain']).size().reset_index(name='count')
    
    if len(daily) == 0:
        st.info("No postings match filters")
        return
    
    # Get top 10 domains for coloring, rest as "Other"
    top_domains = filtered_df['domain'].value_counts().head(10).index.tolist()
    daily['domain_display'] = daily['domain'].apply(
        lambda x: domain_name(x) if x in top_domains else ('Sonstige' if get_lang() == 'de' else 'Other')
    )
    
    # Create stacked bar chart
    fig = px.bar(
        daily,
        x='date_seen',
        y='count',
        color='domain_display',
        labels={'date_seen': '', 'count': '', 'domain_display': ''},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(color='#fafafa', size=9)
        ),
        barmode='stack',
        **PLOTLY_TEMPLATE['layout']
    )
    
    # Fix date formatting on x-axis
    fig.update_xaxes(tickformat="%b %d")
    
    # Render chart with click event
    event = st.plotly_chart(fig, use_container_width=True, key="domain_chart", on_select="rerun")
    
    # Handle click on domain
    if event and event.selection and event.selection.points:
        clicked_point = event.selection.points[0]
        if 'legendgroup' in clicked_point:
            clicked_domain = clicked_point['legendgroup']
            if clicked_domain != 'Other':
                st.session_state.selected_domain = clicked_domain
                st.rerun()
    
    # If domain is selected, show drill-down info
    if st.session_state.selected_domain:
        domain_count = len(filtered_df[filtered_df['domain'] == st.session_state.selected_domain])
        dn = domain_name(st.session_state.selected_domain)
        lbl = 'Stellenangebote' if get_lang() == 'de' else 'postings'
        st.caption(f"🔍 {dn}: {domain_count:,} {lbl}")

    # --- All domains horizontal bar, stacked by qualification ---
    QUAL_COLORS = {1: '#4CAF50', 2: '#2196F3', 3: '#FFC107', 4: '#F44336', 0: '#666666'}
    QUAL_NAMES = {level: t(QUAL_KEYS[level]) for level in range(5)}

    dq = filtered_df.groupby(['domain', 'qualification_level']).size().reset_index(name='count')
    dq['qual_name'] = dq['qualification_level'].map(QUAL_NAMES).fillna(t('q_unknown'))
    dq['domain_display'] = dq['domain'].apply(domain_name)

    # Sort domains by total count descending (but reversed for horizontal bar)
    domain_order_en = filtered_df['domain'].value_counts().index.tolist()[::-1]
    domain_order = [domain_name(d) for d in domain_order_en]

    qual_order = [QUAL_NAMES[i] for i in [1, 2, 3, 4, 0]]
    qual_color_map = {QUAL_NAMES[i]: c for i, c in QUAL_COLORS.items()}

    fig2 = px.bar(
        dq,
        x='count',
        y='domain_display',
        color='qual_name',
        orientation='h',
        labels={'domain_display': '', 'count': '', 'qual_name': ''},
        category_orders={
            'domain_display': domain_order,
            'qual_name': qual_order
        },
        color_discrete_map=qual_color_map
    )
    fig2.update_layout(
        height=max(340, len(domain_order) * 24),
        margin=dict(l=0, r=10, t=5, b=0),
        barmode='stack',
        legend=dict(
            orientation='h', yanchor='top', y=-0.05,
            xanchor='center', x=0.5,
            font=dict(color='#fafafa', size=9)
        ),
        **PLOTLY_TEMPLATE['layout']
    )
    fig2.update_yaxes(tickfont=dict(size=10))
    st.plotly_chart(fig2, use_container_width=True, key="domain_qual_chart")

# =============================================================================
# PANEL 2: QUALIFICATION LEVELS (Compact)
# =============================================================================

def render_qualification_panel(df: pd.DataFrame, filtered_df: pd.DataFrame):
    """Render qualification level toggles (chart is combined with domain panel)."""
    st.markdown(f"##### {t('qual_header')}")
    
    # Summary counts
    qual_counts_all = filtered_df['qualification_level'].value_counts().to_dict()
    total_classified = sum(v for k, v in qual_counts_all.items() if k > 0)
    total_unclassified = qual_counts_all.get(0, 0)
    st.caption(f"{total_classified:,} {t('classified')} · {total_unclassified:,} {t('unclassified')}")
    
    # Compact qualification toggles
    qual_counts = filtered_df['qualification_level'].value_counts().to_dict()
    ql = get_qual_levels()
    
    # Two rows of toggles for compactness
    col1, col2 = st.columns(2)
    new_quals = []
    
    for i, (level, (emoji, name, desc)) in enumerate(ql.items()):
        if level == 0:  # Skip unclassified in toggles
            if 0 in st.session_state.selected_quals:
                new_quals.append(0)
            continue
            
        count = qual_counts.get(level, 0)
        is_selected = level in st.session_state.selected_quals
        
        target_col = col1 if i % 2 == 1 else col2
        with target_col:
            if st.checkbox(f"{emoji} {count:,}", value=is_selected, key=f"qual_{level}", help=f"{name}: {desc}"):
                new_quals.append(level)
    
    # Update state if changed
    if set(new_quals) != set(st.session_state.selected_quals):
        st.session_state.selected_quals = new_quals if new_quals else [0, 1, 2, 3, 4]
        st.rerun()

# =============================================================================
# PANEL 3: GEOGRAPHY (Compact)
# =============================================================================

def render_geography_panel(df: pd.DataFrame, filtered_df: pd.DataFrame):
    """Render geography as a horizontal bar chart of states."""
    st.markdown(f"##### {t('geo_header')}")
    
    # Get state counts
    if st.session_state.selected_state:
        # Show cities within selected state
        state_df = filtered_df[filtered_df['location_state'] == st.session_state.selected_state]
        location_counts = state_df['location_city'].value_counts().head(8)
        title = f"{t('cities_in')} {st.session_state.selected_state}"
        click_key = "city_chart"
    else:
        # Show states
        location_counts = filtered_df['location_state'].value_counts().head(10)
        title = t('postings_by_state')
        click_key = "state_chart"
    
    if len(location_counts) > 0:
        fig = px.bar(
            x=location_counts.values,
            y=location_counts.index,
            orientation='h',
            labels={'x': '', 'y': ''},
            color_discrete_sequence=['steelblue']
        )
        fig.update_layout(
            height=180,
            margin=dict(l=0, r=0, t=0, b=0),
            **PLOTLY_TEMPLATE['layout']
        )
        fig.update_yaxes(tickfont=dict(size=9))
        
        event = st.plotly_chart(fig, use_container_width=True, key=click_key, on_select="rerun")
        
        # Handle click
        if event and event.selection and event.selection.points:
            clicked_point = event.selection.points[0]
            if 'y' in clicked_point:
                clicked_loc = clicked_point['y']
                if st.session_state.selected_state:
                    # Clicked on a city
                    st.session_state.selected_city = clicked_loc
                else:
                    # Clicked on a state
                    st.session_state.selected_state = clicked_loc
                st.rerun()
    
    # Show current filter and radius search in compact form
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.session_state.selected_state:
            filter_text = st.session_state.selected_state
            if st.session_state.selected_city:
                filter_text += f" → {st.session_state.selected_city}"
            st.caption(f"📍 {filter_text}")
    
    with col_b:
        # Compact radius input
        plz = st.text_input("PLZ", value=st.session_state.get('search_plz', ''), 
                           placeholder="PLZ", key="plz_input", label_visibility="collapsed")
        if plz and plz != st.session_state.get('search_plz'):
            st.session_state.search_plz = plz
            st.session_state.search_radius = 100  # Default 100km as per directive
            st.rerun()

# =============================================================================
# PANEL 4: SKILLS GRAPH
# =============================================================================

def render_skills_panel(df: pd.DataFrame, filtered_df: pd.DataFrame, profiles_df: pd.DataFrame):
    """Render skills overlay visualization."""
    st.subheader("✨ Skills Graph")
    
    # Profile selector
    profile_options = [
        (row['profile_id'], f"{row['full_name']} — {row['current_title']}")
        for _, row in profiles_df.iterrows()
    ]
    
    selected = st.selectbox(
        "Select Your Profile",
        options=[None] + profile_options,
        format_func=lambda x: "Select a profile..." if x is None else x[1],
        key="profile_select"
    )
    
    if selected:
        profile_id = selected[0]
        if profile_id != st.session_state.selected_profile_id:
            st.session_state.selected_profile_id = profile_id
            # Load skills for this profile
            profile = profiles_df[profiles_df['profile_id'] == profile_id].iloc[0]
            skills = extract_skills_from_profile(profile['skill_keywords'])
            st.session_state.selected_skills = skills
    
    # Show skills with toggle
    if st.session_state.selected_skills:
        st.markdown("**Your Skills** (toggle to include/exclude from matching)")
        
        # Create columns for skill chips
        skills = st.session_state.selected_skills[:20]  # Limit to 20 for display
        selected_skills = st.multiselect(
            "Skills to match",
            options=skills,
            default=skills[:10],  # Default select first 10
            key="skill_multiselect",
            label_visibility="collapsed"
        )
        
        # Load UMAP data for visualization
        umap_df = load_umap_data()
        
        if umap_df is not None and len(umap_df) > 0:
            # Create terrain + sparks visualization
            fig = go.Figure()
            
            # Background: density contour
            fig.add_trace(go.Histogram2dContour(
                x=umap_df['umap_x'],
                y=umap_df['umap_y'],
                colorscale='Blues',
                reversescale=True,
                showscale=False,
                contours=dict(showlines=False),
                opacity=0.5,
                name='Market Terrain',
                hoverinfo='skip'
            ))
            
            # Job postings as dots
            fig.add_trace(go.Scattergl(
                x=umap_df['umap_x'],
                y=umap_df['umap_y'],
                mode='markers',
                marker=dict(size=3, color='lightsteelblue', opacity=0.3),
                name=f'Jobs ({len(umap_df):,})',
                text=umap_df['job_title'],
                hovertemplate='<b>%{text}</b><extra></extra>'
            ))
            
            # Simulate skill positions (in real version, would compute from embeddings)
            if selected_skills:
                # Project skills to UMAP space using cluster centroids
                centroids = get_cluster_centroids()
                skill_coords = [project_skill_to_umap(skill, centroids) for skill in selected_skills]
                skill_x = [c[0] for c in skill_coords]
                skill_y = [c[1] for c in skill_coords]
                
                fig.add_trace(go.Scatter(
                    x=skill_x,
                    y=skill_y,
                    mode='markers+text',
                    marker=dict(
                        size=20,
                        color='gold',
                        symbol='star',
                        line=dict(width=2, color='darkorange')
                    ),
                    text=selected_skills,
                    textposition='top center',
                    textfont=dict(size=10, color='#fafafa'),
                    name='Your Skills',
                    hovertemplate='<b>%{text}</b><extra></extra>'
                ))
            
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=True,
                legend=dict(x=0.01, y=0.99, font=dict(color='#fafafa')),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("UMAP coordinates not computed yet. Run the market_visualization notebook first.")
    else:
        st.info("Select a profile to see your skills on the market terrain")

# =============================================================================
# PANEL 5: POSTINGS LIST
# =============================================================================

def render_postings_panel(filtered_df: pd.DataFrame):
    """Render filtered job postings."""
    total_available = st.session_state.get('total_available', 0)
    filtered_count = len(filtered_df)
    
    # Check if any real filters are applied (not counting profile which doesn't filter yet)
    has_filters = any([
        st.session_state.get('keyword_search'),
        st.session_state.selected_domain,
        st.session_state.selected_subdomain,
        st.session_state.selected_state,
        st.session_state.selected_city,
        st.session_state.get('search_plz'),
        len(st.session_state.selected_quals or []) < 5,  # Not all quals selected
    ])
    
    # Show header with context
    if has_filters:
        st.subheader(f"{t('postings_header')} ({filtered_count:,} {t('matches')})")
    else:
        st.subheader(f"{t('postings_header')} ({total_available:,} {t('in_last_90_days')})")
        st.caption(t('apply_filters'))
    
    if len(filtered_df) == 0:
        st.warning(t('no_match'))
        return
    
    # Sorting options
    sort_by = st.selectbox(
        t('sort_by'),
        options=['date_seen', 'qualification_level', 'location_state', 'ihl_score'],
        format_func=lambda x: {
            'date_seen': t('sort_date'),
            'qualification_level': t('sort_qual'),
            'location_state': t('sort_state'),
            'ihl_score': t('sort_ihl')
        }.get(x, x),
        key="sort_select"
    )
    
    ascending = sort_by not in ['date_seen', 'ihl_score']  # Descending for date and score
    sorted_df = filtered_df.sort_values(sort_by, ascending=ascending)
    
    # Display postings
    for idx, row in sorted_df.head(50).iterrows():
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                qual = qual_emoji(row['qualification_level'])
                title = row['job_title'] or 'Untitled'
                # Strip any existing markdown from title (some DB entries have **...** around title)
                title = title.strip().strip('*').strip()
                # Fix duplicate locations (e.g., "Sonneberg, Thüringen, Thüringen" -> "Sonneberg, Thüringen")
                city = row['location_city'] or ''
                state = row['location_state'] or ''
                # If city already ends with state (e.g., "Sonneberg, Thüringen" + "Thüringen"), don't add state
                if city and state:
                    if city.lower() == state.lower():
                        location = city
                    elif city.lower().endswith(', ' + state.lower()) or city.lower().endswith(',' + state.lower()):
                        location = city
                    else:
                        location = f"{city}, {state}"
                else:
                    location = city or state or ''
                
                st.markdown(f"**{qual} {title}**")
                st.caption(f"📍 {location} • 📅 {row['date_seen'].strftime('%b %d') if pd.notna(row['date_seen']) else 'N/A'} • {row['source']}")
                
                if row['berufenet_name']:
                    st.caption(f"🏷️ {row['berufenet_name']}")
            
            with col2:
                # Link to internal posting detail page (API on port 8000)
                st.link_button(t('view'), f"http://localhost:8000/posting/{row['posting_id']}", use_container_width=True)
                    
            st.divider()
    
    if len(filtered_df) > 50:
        st.info(t('showing_of').format(count=f'{len(filtered_df):,}'))

# =============================================================================
# SEARCH PANEL (Profile + Keywords)
# =============================================================================

def render_search_panel(profiles_df: pd.DataFrame):
    """Render the profile selector and keyword search box."""
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Profile selector
        profile_options = [
            (row['profile_id'], f"{row['full_name']}")
            for _, row in profiles_df.iterrows()
        ]
        
        current_idx = 0
        if st.session_state.selected_profile_id:
            for i, (pid, _) in enumerate(profile_options):
                if pid == st.session_state.selected_profile_id:
                    current_idx = i + 1
                    break
        
        selected = st.selectbox(
            "👤 Profile",
            options=[None] + profile_options,
            index=current_idx,
            format_func=lambda x: t('select_profile') if x is None else x[1],
            key="profile_select_main"
        )
        
        if selected:
            if selected[0] != st.session_state.selected_profile_id:
                st.session_state.selected_profile_id = selected[0]
                # Profile selected - filter will use skills for matching later
                st.rerun()
        elif st.session_state.selected_profile_id:
            st.session_state.selected_profile_id = None
            st.rerun()
    
    with col2:
        # Keyword search
        keyword = st.text_input(
            t('keywords'),
            value=st.session_state.get('keyword_search', ''),
            placeholder=t('keyword_placeholder'),
            key="keyword_input"
        )
        if keyword != st.session_state.get('keyword_search', ''):
            st.session_state.keyword_search = keyword
            st.rerun()

# =============================================================================
# ACTIVE FILTERS (Toggleable Badges)
# =============================================================================

def render_active_filters():
    """Render active filters as toggleable badges."""
    filters = []
    
    # Collect all active filters with their clear actions
    if st.session_state.get('keyword_search'):
        filters.append(('keyword', f"🔍 \"{st.session_state.keyword_search}\""))
    # Note: Profile filter is for future personalization, doesn't filter postings yet
    if st.session_state.selected_domain:
        filters.append(('domain', f"📊 {domain_name(st.session_state.selected_domain)}"))
    if st.session_state.selected_subdomain:
        filters.append(('subdomain', f"🏷️ {st.session_state.selected_subdomain}"))
    if st.session_state.selected_state:
        filters.append(('state', f"🗺️ {st.session_state.selected_state}"))
    if st.session_state.selected_city:
        filters.append(('city', f"📍 {st.session_state.selected_city}"))
    if st.session_state.get('search_plz'):
        filters.append(('plz', f"📍 {st.session_state.search_plz} ±{st.session_state.get('search_radius', 100)}km"))
    if st.session_state.selected_quals and len(st.session_state.selected_quals) < 5:
        ql = get_qual_levels()
        qual_names = [ql[q][1] for q in st.session_state.selected_quals if q in ql]
        filters.append(('quals', f"🎓 {', '.join(qual_names)}"))
    
    if not filters:
        st.caption(t('no_filters'))
        return
    
    # Render as clickable badges (buttons that remove the filter)
    cols = st.columns(len(filters) + 1)  # +1 for reset button
    
    for i, (filter_key, label) in enumerate(filters):
        with cols[i]:
            if st.button(f"{label} ✕", key=f"clear_{filter_key}", use_container_width=True):
                # Clear the specific filter
                if filter_key == 'keyword':
                    st.session_state.keyword_search = ''
                elif filter_key == 'profile':
                    st.session_state.selected_profile_id = None
                elif filter_key == 'domain':
                    st.session_state.selected_domain = None
                    st.session_state.selected_subdomain = None
                elif filter_key == 'subdomain':
                    st.session_state.selected_subdomain = None
                elif filter_key == 'state':
                    st.session_state.selected_state = None
                    st.session_state.selected_city = None
                elif filter_key == 'city':
                    st.session_state.selected_city = None
                elif filter_key == 'plz':
                    st.session_state.search_plz = None
                elif filter_key == 'quals':
                    st.session_state.selected_quals = [0, 1, 2, 3, 4]
                st.rerun()
    
    # Reset all button
    with cols[-1]:
        if st.button(t('clear_all'), key="reset_all", use_container_width=True):
            reset_filters()

# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main app entry point."""
    # Initialize state
    init_session_state()
    
    # Language toggle (top-right)
    lang_col1, lang_col2 = st.columns([20, 1])
    with lang_col2:
        lang_btn = '🇬🇧' if get_lang() == 'de' else '🇩🇪'
        if st.button(lang_btn, key='lang_toggle', help='Deutsch / English'):
            st.session_state.bi_lang = 'en' if get_lang() == 'de' else 'de'
            st.rerun()
    
    # Load data
    with st.spinner(t('loading')):
        df, total_available = load_postings_data()
        profiles_df = load_profiles()
    
    # Store total for use in postings panel
    st.session_state.total_available = total_available
    
    # DEBUG: Show data stats in collapsed expander
    with st.expander("Debug Info", expanded=False):
        st.markdown(f"**{t('postings_loaded')}:** {len(df):,} of {total_available:,}")
        st.markdown(f"**{t('classified_label')}:** {(df['domain'] != 'Unclassified').sum():,}")
    
    # =================
    # TOP: Search Panel (Profile + Keywords)
    # =================
    render_search_panel(profiles_df)
    
    # =================
    # ACTIVE FILTERS (Toggleable badges)
    # =================
    render_active_filters()
    
    st.markdown("---")
    
    # Apply filters
    filtered_df = apply_filters(df)
    
    # =================
    # ROW: 3 Equal Panels (Timeline | Qualification | Geography)
    # =================
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        render_date_domain_panel(df, filtered_df)
    
    with col2:
        render_qualification_panel(df, filtered_df)
    
    with col3:
        render_geography_panel(df, filtered_df)
    
    st.markdown("---")
    
    # =================
    # BOTTOM: Postings List
    # =================
    render_postings_panel(filtered_df)
    
    # Footer
    st.markdown("---")
    st.caption(t('footer'))

if __name__ == "__main__":
    main()
