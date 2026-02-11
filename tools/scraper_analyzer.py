#!/usr/bin/env python3
"""
Scraper Analyzer - Test extraction patterns against job posting URLs.

PURPOSE:
Automates the "try every key" approach to scraper development.
Given a URL, tests all known extraction patterns and reports what works.

USAGE:
    # Analyze a specific URL
    python3 tools/scraper_analyzer.py "https://example.com/job/123"
    
    # Find next biggest unscraped domain
    python3 tools/scraper_analyzer.py --find-next
    
    # Analyze top N unscraped domains
    python3 tools/scraper_analyzer.py --find-next --top 5

Author: Arden
Date: 2026-02-10
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================================
# EXTRACTION PATTERNS
# ============================================================================

class PatternResult:
    """Result of trying an extraction pattern."""
    def __init__(self, name: str, success: bool, content: str = "", error: str = ""):
        self.name = name
        self.success = success
        self.content = content
        self.error = error
        self.text_length = len(BeautifulSoup(content, 'html.parser').get_text()) if content else 0


def try_json_ld(html: str) -> PatternResult:
    """
    Pattern: JSON-LD schema.org/JobPosting
    Used by: helixjobs, jobboersedirekt, hogapage, europersonal, jobvector
    """
    try:
        match = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return PatternResult("json_ld", False, error="No JSON-LD script tag found")
        
        data = json.loads(match.group(1))
        
        # Handle array of schemas
        if isinstance(data, list):
            for item in data:
                if item.get('@type') == 'JobPosting':
                    data = item
                    break
            else:
                return PatternResult("json_ld", False, error="No JobPosting in JSON-LD array")
        
        if data.get('@type') != 'JobPosting':
            return PatternResult("json_ld", False, error=f"Wrong @type: {data.get('@type')}")
        
        description = data.get('description', '')
        if not description:
            return PatternResult("json_ld", False, error="JSON-LD JobPosting has empty description")
        
        return PatternResult("json_ld", True, content=description)
        
    except json.JSONDecodeError as e:
        return PatternResult("json_ld", False, error=f"JSON parse error: {e}")
    except Exception as e:
        return PatternResult("json_ld", False, error=str(e))


def try_html_description_wrapper(html: str) -> PatternResult:
    """
    Pattern: HTML class containing 'DescriptionWrapper' (styled-components)
    Used by: persyjobs (XING)
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        el = soup.find(class_=re.compile(r'DescriptionWrapper', re.I))
        if el:
            return PatternResult("html_description_wrapper", True, content=str(el))
        return PatternResult("html_description_wrapper", False, error="No DescriptionWrapper class found")
    except Exception as e:
        return PatternResult("html_description_wrapper", False, error=str(e))


def try_html_whitebox(html: str) -> PatternResult:
    """
    Pattern: HTML .whitebox container (first one with substantial content)
    Used by: jobexport
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        whiteboxes = soup.find_all(class_='whitebox')
        for wb in whiteboxes:
            text = wb.get_text(strip=True)
            if len(text) > 200:  # Substantial content
                return PatternResult("html_whitebox", True, content=str(wb))
        return PatternResult("html_whitebox", False, error="No whitebox with >200 chars found")
    except Exception as e:
        return PatternResult("html_whitebox", False, error=str(e))


def try_html_job_description_class(html: str) -> PatternResult:
    """
    Pattern: HTML with common job description class names
    Tries: job-description, jobDescription, stellenbeschreibung, job-details, job-content
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try common class patterns
        patterns = [
            r'job-?description',
            r'job-?details',
            r'job-?content', 
            r'stellenbeschreibung',
            r'vacancy-?description',
            r'posting-?description',
        ]
        
        for pattern in patterns:
            el = soup.find(class_=re.compile(pattern, re.I))
            if el:
                text = el.get_text(strip=True)
                if len(text) > 100:
                    return PatternResult("html_job_description_class", True, content=str(el))
        
        return PatternResult("html_job_description_class", False, error="No common job-description class found")
    except Exception as e:
        return PatternResult("html_job_description_class", False, error=str(e))


def try_html_scheme_text(html: str) -> PatternResult:
    """
    Pattern: HTML .scheme-text or .jobDescriptionSchemeContent
    Used by: finestjobs
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        container = soup.find(class_='jobDescriptionSchemeContent')
        if container:
            return PatternResult("html_scheme_text", True, content=str(container))
        
        scheme_texts = soup.find_all(class_='scheme-text')
        if scheme_texts:
            content = '\n'.join(str(st) for st in scheme_texts)
            return PatternResult("html_scheme_text", True, content=content)
        
        return PatternResult("html_scheme_text", False, error="No scheme-text or jobDescriptionSchemeContent found")
    except Exception as e:
        return PatternResult("html_scheme_text", False, error=str(e))


def try_html_article_main(html: str) -> PatternResult:
    """
    Pattern: HTML <article> or <main> tag with substantial content
    Generic fallback for semantic HTML
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in ['article', 'main']:
            el = soup.find(tag)
            if el:
                text = el.get_text(strip=True)
                if len(text) > 300:
                    return PatternResult("html_article_main", True, content=str(el))
        
        return PatternResult("html_article_main", False, error="No article/main tag with >300 chars")
    except Exception as e:
        return PatternResult("html_article_main", False, error=str(e))


def try_elementor_config(html: str) -> PatternResult:
    """
    Pattern: Elementor frontend config JSON
    Used by: gutejobs
    """
    try:
        match = re.search(r'var\s+elementorFrontendConfig\s*=\s*({.*?});', html, re.DOTALL)
        if not match:
            return PatternResult("elementor_config", False, error="No elementorFrontendConfig found")
        
        # This is complex to parse properly - just detect presence
        return PatternResult("elementor_config", True, content="[Elementor config detected - needs custom extraction]")
    except Exception as e:
        return PatternResult("elementor_config", False, error=str(e))


# All patterns to try, in order of specificity
PATTERNS = [
    ("JSON-LD JobPosting", try_json_ld),
    ("HTML DescriptionWrapper", try_html_description_wrapper),
    ("HTML whitebox", try_html_whitebox),
    ("HTML scheme-text", try_html_scheme_text),
    ("HTML job-description class", try_html_job_description_class),
    ("Elementor config", try_elementor_config),
    ("HTML article/main", try_html_article_main),
]


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def analyze_url(url: str, verbose: bool = True) -> List[PatternResult]:
    """
    Fetch URL and test all extraction patterns against it.
    
    Returns list of PatternResults, sorted by success then content length.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
    }
    
    if verbose:
        print(f"\n🔍 Analyzing: {url}")
        print("=" * 60)
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch URL: {e}")
        return []
    
    if verbose:
        print(f"✅ Fetched ({len(resp.text)} bytes)")
        
        # Check for SPA indicators
        if '<div id="__nuxt"></div>' in resp.text or '<div id="root"></div>' in resp.text:
            print("⚠️  WARNING: Looks like an SPA (client-rendered). May need Playwright.")
    
    html = resp.text
    results = []
    
    for name, pattern_fn in PATTERNS:
        result = pattern_fn(html)
        results.append(result)
        
        if verbose:
            if result.success:
                print(f"\n✅ {name}: SUCCESS ({result.text_length} chars text)")
                # Show preview
                preview = BeautifulSoup(result.content, 'html.parser').get_text()[:200]
                print(f"   Preview: {preview}...")
            else:
                print(f"\n❌ {name}: {result.error}")
    
    # Sort: successful first, then by content length
    results.sort(key=lambda r: (not r.success, -r.text_length))
    
    return results


def find_next_domains(top: int = 10) -> List[Tuple[str, int]]:
    """
    Find the biggest external partner domains that don't have scrapers yet.
    """
    from core.database import get_connection
    from actors.postings__external_partners_U import detect_scraper_from_url
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT source_metadata->'raw_api_response'->>'externeUrl' as partner_url
            FROM postings
            WHERE job_description = '[EXTERNAL_PARTNER]'
              AND invalidated = false
              AND source_metadata->'raw_api_response'->>'externeUrl' IS NOT NULL
        """)
        
        domains = Counter()
        sample_urls = {}  # domain -> first URL seen
        
        for row in cur.fetchall():
            url = row['partner_url']
            if url:
                try:
                    domain = urlparse(url).netloc
                    # Check if we already have a scraper
                    if detect_scraper_from_url(url) is None:
                        domains[domain] += 1
                        if domain not in sample_urls:
                            sample_urls[domain] = url
                except (ValueError, AttributeError):
                    pass
        
        print(f"\n📊 Top {top} unscraped external partner domains:\n")
        print(f"{'Count':>6}  {'Domain':<40}  Sample URL")
        print("-" * 100)
        
        results = []
        for domain, count in domains.most_common(top):
            sample = sample_urls.get(domain, "")[:50]
            print(f"{count:>6}  {domain:<40}  {sample}...")
            results.append((domain, count, sample_urls.get(domain)))
        
        return results


def analyze_domain(domain: str) -> None:
    """
    Find a sample URL for a domain and analyze it.
    """
    from core.database import get_connection
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT source_metadata->'raw_api_response'->>'externeUrl' as partner_url
            FROM postings
            WHERE job_description = '[EXTERNAL_PARTNER]'
              AND invalidated = false
              AND source_metadata->'raw_api_response'->>'externeUrl' LIKE %s
            LIMIT 1
        """, (f'%{domain}%',))
        
        row = cur.fetchone()
        if not row:
            print(f"❌ No URLs found for domain: {domain}")
            return
        
        analyze_url(row['partner_url'])


def recommend_scraper(results: List[PatternResult]) -> Optional[str]:
    """
    Based on analysis results, recommend which scraper pattern to use.
    """
    successful = [r for r in results if r.success and r.text_length > 100]
    
    if not successful:
        return None
    
    best = successful[0]
    
    recommendations = {
        "json_ld": "Use JSON-LD pattern (copy from helixjobs.py)",
        "html_description_wrapper": "Use DescriptionWrapper pattern (copy from persyjobs.py)",
        "html_whitebox": "Use whitebox pattern (copy from jobexport.py)",
        "html_scheme_text": "Use scheme-text pattern (copy from finestjobs.py)",
        "html_job_description_class": "Use standard HTML selector (new scraper needed)",
        "html_article_main": "Use generic article/main extraction (may need refinement)",
        "elementor_config": "Use Elementor config extraction (copy from gutejobs.py)",
    }
    
    return recommendations.get(best.name, f"Unknown pattern: {best.name}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze job posting URLs and find matching extraction patterns"
    )
    parser.add_argument('url', nargs='?', help='URL to analyze')
    parser.add_argument('--find-next', action='store_true', 
                        help='Find next biggest unscraped domains')
    parser.add_argument('--top', type=int, default=10,
                        help='Number of domains to show (default: 10)')
    parser.add_argument('--domain', type=str,
                        help='Analyze a specific domain (finds sample URL automatically)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Less verbose output')
    
    args = parser.parse_args()
    
    if args.find_next:
        domains = find_next_domains(args.top)
        
        if domains and not args.quiet:
            print("\n" + "=" * 60)
            print("💡 TIP: Analyze the top domain with:")
            top_domain = domains[0][0]
            print(f"   python3 tools/scraper_analyzer.py --domain {top_domain}")
        
    elif args.domain:
        analyze_domain(args.domain)
        
    elif args.url:
        results = analyze_url(args.url, verbose=not args.quiet)
        
        if results:
            print("\n" + "=" * 60)
            recommendation = recommend_scraper(results)
            if recommendation:
                print(f"💡 RECOMMENDATION: {recommendation}")
            else:
                print("❌ No working pattern found. May need Playwright or custom extraction.")
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
