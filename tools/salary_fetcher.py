import os
#!/usr/bin/env python3
"""
Entgeltatlas Salary Data Fetcher
=================================

Fetches salary data from the Bundesagentur für Arbeit's Entgeltatlas
for berufenet professions and stores it in the database.

The Entgeltatlas provides:
- Median monthly gross salary
- 25th percentile (lower quartile)
- 75th percentile (upper quartile)
- Sample size (Fallzahl)

Data source: https://web.arbeitsagentur.de/entgeltatlas/
Data vintage: Entgeltatlas 2024

Usage:
    python3 tools/salary_fetcher.py                # Fetch top 50 professions
    python3 tools/salary_fetcher.py --limit 100    # Fetch top 100
    python3 tools/salary_fetcher.py --all          # Fetch all with postings (slow!)
    python3 tools/salary_fetcher.py --test         # Test mode - 3 professions

Author: Claude (Feb 2026)
"""

import argparse
import json
import re
import time
import sys
from datetime import datetime
from typing import Optional, Tuple

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Installing playwright...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection using standard credentials."""
    return psycopg2.connect(
        dbname='turing',
        user='base_admin',
        password=os.getenv('DB_PASSWORD', ''),
        host='localhost'
    )


def parse_salary(text: str) -> Optional[int]:
    """Parse salary string like '6.097 €' to integer 6097."""
    if not text:
        return None
    # Handle "> X.XXX €" (upper bound exceeded)
    text = text.replace('>', '').strip()
    # Remove € and whitespace
    text = text.replace('€', '').strip()
    # Remove thousand separator (German uses . as thousand separator)
    text = text.replace('.', '').replace(',', '')
    try:
        return int(text)
    except ValueError:
        return None


def extract_salary_from_page(page) -> dict:
    """Extract salary data from the current Entgeltatlas page.
    
    Returns dict with keys: median, q25, q75, sample_size
    """
    result = {
        'median': None,
        'q25': None,
        'q75': None,
        'sample_size': None
    }
    
    try:
        # Wait for page to load
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        
        # Get the full page text content for debugging
        page_text = page.content()
        
        # Try to find the hint paragraphs that contain the salary data
        # The structure is:
        # - "Das Medianentgelt ... beträgt X.XXX €."
        # - "Das untere Quartil liegt bei X.XXX € und das obere Quartil beträgt X.XXX €."
        
        # Method 1: Find in page text using regex (most reliable)
        median_match = re.search(r'Medianentgelt[^€]*beträgt\s*([\d.]+)\s*€', page_text)
        if median_match:
            result['median'] = parse_salary(median_match.group(1) + ' €')
        
        quartile_match = re.search(r'untere Quartil liegt bei\s*([\d.]+)\s*€[^€]*obere Quartil beträgt\s*([\d.]+)\s*€', page_text)
        if quartile_match:
            result['q25'] = parse_salary(quartile_match.group(1) + ' €')
            result['q75'] = parse_salary(quartile_match.group(2) + ' €')
        
        # Method 2: If not found, try DOM selectors
        if not result['median']:
            try:
                # Look for paragraph containing median text
                paragraphs = page.locator('p').all()
                for p in paragraphs:
                    text = p.text_content()
                    if 'Medianentgelt' in text and 'beträgt' in text:
                        m = re.search(r'beträgt\s*([\d.]+)\s*€', text)
                        if m:
                            result['median'] = parse_salary(m.group(1) + ' €')
                    if 'untere Quartil' in text:
                        m = re.search(r'liegt bei\s*([\d.>]+)\s*€', text)
                        if m:
                            result['q25'] = parse_salary(m.group(1) + ' €')
                        m = re.search(r'obere Quartil beträgt\s*([\d.>]+)\s*€', text)
                        if m:
                            result['q75'] = parse_salary(m.group(1) + ' €')
            except Exception as e:
                print(f"    DOM selector error: {e}")
                
    except PlaywrightTimeout:
        print("    Timeout waiting for page")
    except Exception as e:
        print(f"    Error extracting: {e}")
    
    # If graphic extraction failed, try table view
    if not result['median']:
        try:
            # Switch to table view
            table_button = page.locator('text=Tabelle').first
            if table_button.is_visible():
                table_button.click()
                page.wait_for_load_state('networkidle')
                time.sleep(1.5)
            
            # Find the Deutschland row in the table
            rows = page.locator('table tbody tr')
            count = rows.count()
            for i in range(count):
                row = rows.nth(i)
                cells = row.locator('td')
                if cells.count() >= 5:
                    region = cells.nth(0).text_content().strip()
                    if region == 'Deutschland':
                        result['q25'] = parse_salary(cells.nth(1).text_content())
                        result['median'] = parse_salary(cells.nth(2).text_content())
                        result['q75'] = parse_salary(cells.nth(3).text_content())
                        sample_text = cells.nth(4).text_content().strip().replace('.', '')
                        try:
                            result['sample_size'] = int(sample_text)
                        except ValueError:
                            pass
                        break
        except Exception as e:
            print(f"    Table extraction error: {e}")
    
    return result


def fetch_salary_for_profession(page, profession_name: str) -> dict:
    """Fetch salary data for a single profession by name.
    
    Returns dict with salary data or empty dict if not found.
    """
    result = {}
    
    try:
        # Navigate to Entgeltatlas
        page.goto('https://web.arbeitsagentur.de/entgeltatlas/')
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        
        # Find the search input and type profession name
        search_input = page.locator('input[role="combobox"], [role="combobox"]').first
        search_input.click()
        
        # Clear any existing text and type new search
        search_input.fill('')
        time.sleep(0.3)
        
        # Use a shortened, clean version of the name for search
        search_term = profession_name.split('(')[0].strip()[:40]
        search_input.fill(search_term)
        
        # Wait for autocomplete suggestions
        time.sleep(2)
        
        # Try to find and click on a suggestion
        try:
            suggestions = page.locator('[role="option"]')
            count = suggestions.count()
            if count > 0:
                # Click the first suggestion
                suggestions.first.click()
                page.wait_for_load_state('networkidle')
                time.sleep(1.5)
                
                # Check if we landed on a results page
                if '/beruf/' in page.url or '/tabelle' in page.url:
                    result = extract_salary_from_page(page)
                    return result
        except Exception as e:
            print(f"    Suggestion click error: {e}")
        
        # Fallback: Try pressing Enter to search
        if not result.get('median'):
            try:
                search_input.press('Enter')
                page.wait_for_load_state('networkidle')
                time.sleep(1.5)
                if '/beruf/' in page.url or '/tabelle' in page.url:
                    result = extract_salary_from_page(page)
            except Exception:
                pass
            
    except PlaywrightTimeout:
        print(f"    Timeout searching for: {profession_name}")
    except Exception as e:
        print(f"    Search error: {e}")
    
    return result


def get_professions_to_fetch(conn, limit: int = None) -> list:
    """Get list of professions that need salary data.
    
    Returns professions with the most postings first, excluding those
    that already have salary data fetched.
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT b.berufenet_id, b.name, b.kldb, b.qualification_level, 
               COUNT(*) as posting_count
        FROM berufenet b
        JOIN postings p ON p.berufenet_id = b.berufenet_id
        WHERE b.salary_median IS NULL  -- Only unfetched
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
    parser = argparse.ArgumentParser(description='Fetch Entgeltatlas salary data')
    parser.add_argument('--limit', type=int, default=50, help='Number of professions to fetch')
    parser.add_argument('--all', action='store_true', help='Fetch all professions with postings')
    parser.add_argument('--test', action='store_true', help='Test mode - only 3 professions')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    args = parser.parse_args()
    
    if args.test:
        args.limit = 3
    elif args.all:
        args.limit = None
    
    conn = get_db_connection()
    professions = get_professions_to_fetch(conn, args.limit)
    
    if not professions:
        print("No professions to fetch (all have salary data or no postings)")
        return
    
    total = len(professions)
    print(f"Fetching salary data for {total} professions...")
    print(f"Estimated time: ~{format_eta(total * 8)} (based on ~8s per profession)")
    print("=" * 70)
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    times = []  # Track time per profession for better ETA
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='de-DE'
        )
        page = context.new_page()
        
        for i, prof in enumerate(professions, 1):
            prof_start = time.time()
            
            # Progress header with ETA
            elapsed = time.time() - start_time
            if times:
                avg_time = sum(times) / len(times)
                remaining = (total - i + 1) * avg_time
                eta_str = f"ETA: {format_eta(remaining)}"
            else:
                eta_str = "ETA: calculating..."
            
            pct = 100 * i / total
            progress_bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"\n[{progress_bar}] {pct:5.1f}% | {i}/{total} | {eta_str} | Elapsed: {format_eta(elapsed)}")
            print(f"  → {prof['name'][:55]}")
            
            salary = fetch_salary_for_profession(page, prof['name'])
            
            prof_time = time.time() - prof_start
            times.append(prof_time)
            
            if salary.get('median'):
                print(f"    ✓ €{salary['median']:,} (Q25: {salary.get('q25')}, Q75: {salary.get('q75')}) [{prof_time:.1f}s]")
                update_salary_data(conn, prof['berufenet_id'], salary)
                success_count += 1
            else:
                print(f"    ✗ No data [{prof_time:.1f}s]")
                update_salary_data(conn, prof['berufenet_id'], {
                    'median': None, 'q25': None, 'q75': None, 'sample_size': None
                })
                fail_count += 1
            
            # Small delay to be nice to the server
            time.sleep(0.5)
        
        browser.close()
    
    conn.close()
    
    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"DONE! ✓ {success_count} succeeded | ✗ {fail_count} failed | {format_eta(total_time)} total")
    print(f"Success rate: {100*success_count/(success_count+fail_count):.0f}%")


if __name__ == '__main__':
    main()
