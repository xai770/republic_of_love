import os
#!/usr/bin/env python3
"""
Entgeltatlas Salary API Fetcher (Fast Version)
================================================

Fetches salary data directly from the Entgeltatlas REST API using KLDB codes.
Much faster than browser-based scraping (~0.2s per profession vs ~8s).

API Endpoint: https://rest.arbeitsagentur.de/infosysbub/entgeltatlas/pc/v1/entgelte/{kldb}
Required Header: X-API-Key: infosysbub-ega

Parameters:
- l: qualification level (1=Helfer, 2=Fachkraft, 3=Spezialist, 4=Experte)
- r=1: Deutschland (all regions)
- a=1: All age groups
- b=1: All genders

Usage:
    python3 tools/salary_api_fetcher.py                # Fetch top 50 professions
    python3 tools/salary_api_fetcher.py --limit 500    # Fetch top 500
    python3 tools/salary_api_fetcher.py --all          # Fetch all with postings

Author: Claude (Feb 2026)
"""

import argparse
import requests
import time
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


API_BASE = "https://rest.arbeitsagentur.de/infosysbub/entgeltatlas/pc/v1/entgelte"
API_KEY = "infosysbub-ega"

HEADERS = {
    "X-API-Key": API_KEY,
    "Accept": "application/json"
}


def get_db_connection():
    """Get database connection using standard credentials."""
    return psycopg2.connect(
        dbname='turing',
        user='base_admin',
        password=os.getenv('DB_PASSWORD', ''),
        host='localhost'
    )


def fetch_salary_from_api(kldb: str, level: int) -> dict:
    """Fetch salary data from Entgeltatlas API.
    
    Args:
        kldb: KLDB code like "43414" (without the "B " prefix)
        level: qualification level (1-4)
        
    Returns:
        dict with median, q25, q75, sample_size or empty dict if no data
    """
    # Clean KLDB code - remove "B " prefix if present
    kldb_clean = kldb.replace("B ", "").replace(" ", "")
    
    url = f"{API_BASE}/{kldb_clean}?l={level}&r=1&a=1&b=1"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                # First result is the "Gesamt" (all genders, all ages) entry
                entry = data[0]
                return {
                    'median': entry.get('entgelt'),
                    'q25': entry.get('entgeltQ25'),
                    'q75': entry.get('entgeltQ75'),
                    'sample_size': entry.get('besetzung')
                }
        elif response.status_code == 404:
            return {}  # No data for this KLDB
        else:
            print(f"    API error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"    Request error: {e}")
        return {}
    
    return {}


def get_professions_to_fetch(conn, limit: int = None, retry_failed: bool = False) -> list:
    """Get list of professions that need salary data.
    
    Args:
        conn: database connection
        limit: max number to return
        retry_failed: if True, also include previously attempted (no data found)
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if retry_failed:
        # Include previously attempted professions
        where_clause = "WHERE b.salary_median IS NULL AND b.kldb IS NOT NULL"
    else:
        # Only unfetched (salary_updated_at is NULL)
        where_clause = "WHERE b.salary_updated_at IS NULL AND b.kldb IS NOT NULL"
    
    query = f"""
        SELECT b.berufenet_id, b.name, b.kldb, b.qualification_level, 
               COUNT(*) as posting_count
        FROM berufenet b
        LEFT JOIN postings p ON p.berufenet_id = b.berufenet_id
        {where_clause}
        GROUP BY b.berufenet_id, b.name, b.kldb, b.qualification_level
        ORDER BY COUNT(*) DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    cur.execute(query)
    return cur.fetchall()


def update_salary_data(conn, berufenet_id: int, salary_data: dict):
    """Update berufenet table with fetched salary data."""
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE berufenet
        SET salary_median = %s,
            salary_q25 = %s,
            salary_q75 = %s,
            salary_sample_size = %s,
            salary_updated_at = %s
        WHERE berufenet_id = %s
    """, (
        salary_data.get('median'),
        salary_data.get('q25'),
        salary_data.get('q75'),
        salary_data.get('sample_size'),
        datetime.now(),
        berufenet_id
    ))
    
    conn.commit()


def format_eta(seconds: float) -> str:
    """Format seconds into human readable time."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def main():
    parser = argparse.ArgumentParser(description='Fetch Entgeltatlas salary data via API')
    parser.add_argument('--limit', type=int, default=50, help='Number of professions to fetch')
    parser.add_argument('--all', action='store_true', help='Fetch all professions with KLDB codes')
    parser.add_argument('--retry', action='store_true', help='Retry previously failed fetches')
    parser.add_argument('--test', action='store_true', help='Test mode - only 5 professions')
    args = parser.parse_args()
    
    if args.test:
        args.limit = 5
    elif args.all:
        args.limit = None
    
    conn = get_db_connection()
    professions = get_professions_to_fetch(conn, args.limit, args.retry)
    
    if not professions:
        print("No professions to fetch (all have salary data or no KLDB codes)")
        return
    
    total = len(professions)
    est_time = total * 0.3  # ~0.3s per API call
    print(f"Fetching salary data for {total} professions via API...")
    print(f"Estimated time: ~{format_eta(est_time)} (based on ~0.3s per profession)")
    print("=" * 70)
    
    success_count = 0
    fail_count = 0
    no_kldb_count = 0
    start_time = time.time()
    
    for i, prof in enumerate(professions, 1):
        # Progress
        elapsed = time.time() - start_time
        if i > 1:
            avg_time = elapsed / (i - 1)
            remaining = (total - i + 1) * avg_time
            eta_str = f"ETA: {format_eta(remaining)}"
        else:
            eta_str = "ETA: calculating..."
        
        pct = 100 * i / total
        progress_bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        
        # Skip if no KLDB code
        if not prof['kldb']:
            no_kldb_count += 1
            continue
        
        # Determine qualification level (default to 2 if not specified)
        level = prof.get('qualification_level') or 2
        
        # Fetch salary via API
        salary = fetch_salary_from_api(prof['kldb'], level)
        
        if salary.get('median'):
            print(f"[{progress_bar}] {pct:5.1f}% | {i}/{total} | {eta_str}")
            print(f"  ✓ {prof['name'][:50]}: €{salary['median']:,} (Q25: {salary.get('q25')}, Q75: {salary.get('q75')})")
            update_salary_data(conn, prof['berufenet_id'], salary)
            success_count += 1
        else:
            # No data - still mark as attempted
            update_salary_data(conn, prof['berufenet_id'], {
                'median': None, 'q25': None, 'q75': None, 'sample_size': None
            })
            fail_count += 1
        
        # Small delay to be nice to the server
        time.sleep(0.1)
    
    conn.close()
    
    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"DONE! ✓ {success_count} succeeded | ✗ {fail_count} no data | {no_kldb_count} no KLDB | {format_eta(total_time)} total")
    if success_count + fail_count > 0:
        print(f"Success rate: {100*success_count/(success_count+fail_count):.0f}%")


if __name__ == '__main__':
    main()
