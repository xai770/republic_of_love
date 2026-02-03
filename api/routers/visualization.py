"""
Visualization routes — serve Clara skill matrix visualizations and market terrain.
"""
import subprocess
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import pandas as pd

from api.deps import get_db, get_current_user
from core.database import get_connection_raw

router = APIRouter(prefix="/viz", tags=["visualization"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = PROJECT_ROOT / "frontend" / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Cache for market data (loaded once)
_market_cache = None


@router.get("/match/{match_id}")
def get_match_visualization(
    match_id: int,
    request_user: dict = Depends(get_current_user),
    conn=Depends(get_db)
):
    """
    Get or generate Clara skill matrix visualization for a match.
    Returns HTML page with interactive Plotly chart.
    """
    if not request_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get match details
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.match_id, m.profile_id, m.posting_id, pr.user_id
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match['user_id'] != request_user['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    profile_id = match['profile_id']
    posting_id = match['posting_id']
    
    # Check if viz already exists
    viz_file = OUTPUT_DIR / f"clara_viz_p{profile_id}_j{posting_id}.html"
    
    if not viz_file.exists():
        # Generate it
        try:
            result = subprocess.run(
                ["python3", "tools/clara_visualizer.py", 
                 "--profile", str(profile_id), 
                 "--posting", str(posting_id)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Visualization generation failed: {result.stderr[:200]}"
                )
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Visualization timed out")
    
    if not viz_file.exists():
        raise HTTPException(status_code=500, detail="Visualization file not created")
    
    # Return HTML to display in browser (not download)
    return FileResponse(
        viz_file,
        media_type="text/html"
    )


@router.get("/embed/{match_id}")
def get_embedded_visualization(
    match_id: int,
    request_user: dict = Depends(get_current_user),
    conn=Depends(get_db)
):
    """
    Return just the Plotly div for embedding in an iframe.
    """
    if not request_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get match details
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.match_id, m.profile_id, m.posting_id, pr.user_id
            FROM profile_posting_matches m
            JOIN profiles pr ON m.profile_id = pr.profile_id
            WHERE m.match_id = %s
        """, (match_id,))
        match = cur.fetchone()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if match['user_id'] != request_user['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    profile_id = match['profile_id']
    posting_id = match['posting_id']
    
    viz_file = OUTPUT_DIR / f"clara_viz_p{profile_id}_j{posting_id}.html"
    
    if not viz_file.exists():
        # Generate it
        subprocess.run(
            ["python3", "tools/clara_visualizer.py", 
             "--profile", str(profile_id), 
             "--posting", str(posting_id)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=60
        )
    
    if viz_file.exists():
        return FileResponse(viz_file, media_type="text/html")
    
    return HTMLResponse("<p>Visualization not available</p>")


# --- Market Terrain Data API ---

@router.get("/market/data")
def get_market_data():
    """
    Get UMAP coordinates and metadata for all postings.
    Returns JSON optimized for Plotly.js.
    """
    global _market_cache
    
    umap_file = DATA_DIR / "umap_coords_postings.parquet"
    
    if not umap_file.exists():
        raise HTTPException(status_code=404, detail="Market data not computed yet. Run the notebook first.")
    
    # Use cache if available (parquet file hasn't changed)
    file_mtime = umap_file.stat().st_mtime
    if _market_cache and _market_cache.get('mtime') == file_mtime:
        return JSONResponse(_market_cache['data'])
    
    # Load and prepare data
    df = pd.read_parquet(umap_file)
    
    # Fetch fresh domain classifications from database
    try:
        conn = get_connection_raw()
        cur = conn.cursor()
        cur.execute("""
            SELECT posting_id, domain_gate->>'domain' as domain
            FROM postings
            WHERE domain_gate IS NOT NULL
        """)
        domain_df = pd.DataFrame([dict(row) for row in cur])
        conn.close()
        
        if len(domain_df) > 0:
            # Merge fresh domains into UMAP data
            df = df.drop(columns=['domain_clean'], errors='ignore')
            df = df.merge(domain_df, on='posting_id', how='left')
            df['domain'] = df['domain'].fillna('unclassified')
        else:
            df['domain'] = 'unclassified'
    except Exception as e:
        print(f"Warning: Could not fetch domains from DB: {e}")
        df['domain'] = df.get('domain_clean', 'unclassified')
    
    # For unknown/unclassified jobs, use auto-discovered clusters from embeddings
    if 'auto_cluster' in df.columns:
        unknown_mask = df['domain'].isin(['unknown', 'unclassified', None])
        df.loc[unknown_mask, 'domain'] = df.loc[unknown_mask, 'auto_cluster'].fillna('misc')
    
    # Remove garbage job titles (empty, too short, or nonsensical)
    df = df[df['job_title'].str.len() >= 5]  # Must have at least 5 chars
    df = df[df['job_title'].str.contains(' ', na=False)]  # Must have a space (real job title)
    
    # Remove marketing slogans masquerading as job titles
    spam_patterns = r'pflegst mit Herz|finden [Dd]einen|finden [Dd]en Job|wir finden Ihren'
    df = df[~df['job_title'].str.contains(spam_patterns, case=False, regex=True, na=False)]
    
    # Remove spatial outliers - points far from main cluster (2nd/98th percentile + IQR buffer)
    for coord in ['umap_x', 'umap_y']:
        q1 = df[coord].quantile(0.02)
        q3 = df[coord].quantile(0.98)
        iqr = q3 - q1
        lower = q1 - 1.0 * iqr
        upper = q3 + 1.0 * iqr
        df = df[(df[coord] >= lower) & (df[coord] <= upper)]
    
    # Convert date to string for JSON
    df['date_seen'] = df['date_seen'].astype(str)
    df['week'] = pd.to_datetime(df['date_seen']).dt.to_period('W').astype(str)
    
    # Compute stats
    stats = {
        'total_postings': len(df),
        'total_sources': df['source'].nunique(),
        'total_cities': df['location_city'].nunique(),
        'weeks_span': df['week'].nunique(),
        'total_domains': df['domain'].nunique()
    }
    
    # Prepare columnar data for efficient transfer
    data = {
        'stats': stats,
        'umap_x': df['umap_x'].tolist(),
        'umap_y': df['umap_y'].tolist(),
        'job_title': df['job_title'].tolist(),
        'source': df['source'].tolist(),
        'location_city': df['location_city'].fillna('').tolist(),
        'location_state': df['location_state'].fillna('').tolist(),
        'date_seen': df['date_seen'].tolist(),
        'week': df['week'].tolist(),
        'domain': df['domain'].tolist()
    }
    
    # Cache it
    _market_cache = {'mtime': file_mtime, 'data': data}
    
    return JSONResponse(data)

