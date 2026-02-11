#!/usr/bin/env python3
"""
doug__research_C.py - Doug's company research actor

PURPOSE:
Doug researches companies and job postings for yogis who request it.
When a yogi's interaction state = 'researching', Doug kicks in:
1. Looks up the posting (company, title, URL)
2. Searches DDG for company info, reviews, culture
3. Writes a friendly research report to yogi_messages
4. Updates state to 'researched'

Input:  user_posting_interactions WHERE state = 'researching'
Output: yogi_messages (sender_type='doug', message_type='research_report')

Flow:
```
user_posting_interactions.state = 'researching'
    ↓
[Doug searches DDG]
    ↓
yogi_messages ← research report
    ↓
user_posting_interactions.state = 'researched'
```

Usage:
    # Batch mode (for daemon/cron):
    python3 actors/doug__research_C.py --batch 10
    
    # Single interaction:
    python3 actors/doug__research_C.py 123  # interaction_id

Author: Arden
Date: 2026-02-02
"""

import json
import sys
import re
import subprocess
import argparse
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import psycopg2.extras
import requests

# ============================================================================
# SETUP
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import os
from core.database import get_connection_raw, return_connection
from core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
LLM_MODEL = "qwen2.5:7b"  # For summarizing search results

# Doug's personality
DOUG_SYSTEM = """You are Doug, a friendly research assistant at talent.yoga.
You help job seekers by researching companies and positions.

Your tone is:
- Warm and supportive (but not sycophantic)
- Direct and honest (including about negatives)
- Practical and actionable

Write a research report that's helpful for someone considering this job.
Include: company overview, culture signals, red flags if any, and tips for applying.
Keep it under 800 words. Use markdown formatting."""


def search_duckduckgo(query: str) -> str:
    """Search DuckDuckGo and return results. (From tools/exec_agent.py)"""
    try:
        result = subprocess.run(
            ['ddgr', '--json', '--num', '5', query],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0 and result.stdout:
            results = json.loads(result.stdout)
            output = []
            
            for i, item in enumerate(results[:5], 1):
                title = item.get('title', 'No title')
                url = item.get('url', '')
                abstract = item.get('abstract', '')
                output.append(f"{i}. {title}\n   {url}\n   {abstract}")
            
            return "\n\n".join(output)
        else:
            return _search_ddg_fallback(query)
            
    except FileNotFoundError:
        return _search_ddg_fallback(query)
    except Exception as e:
        logger.warning(f"DDG search failed: {e}")
        return ""


def _search_ddg_fallback(query: str) -> str:
    """Fallback using DuckDuckGo Lite."""
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={query.replace(' ', '+')}"
        result = subprocess.run(
            ['curl', '-s', '-L', url],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            html = result.stdout
            links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            
            output = []
            for url, title in links[:5]:
                if url.startswith('http') and title.strip():
                    output.append(f"{title.strip()}\n   {url}")
            
            return "\n\n".join(output)
    except Exception as e:
        logger.warning(f"DDG fallback failed: {e}")
    
    return ""


def extract_company_from_summary(summary: str) -> Optional[str]:
    """Extract company name from extracted_summary."""
    if not summary:
        return None
    
    # Pattern: **Company:** Something
    match = re.search(r'\*\*Company:\*\*\s*([^\n*]+)', summary)
    if match:
        return match.group(1).strip()
    
    # Fallback: Company: Something
    match = re.search(r'Company:\s*([^\n]+)', summary)
    if match:
        return match.group(1).strip()
    
    return None


def generate_report(
    job_title: str,
    company: str,
    external_url: str,
    source: str,
    search_results: Dict[str, str]
) -> str:
    """Use LLM to generate Doug's research report."""
    
    # Build context from search results
    context_parts = []
    
    if search_results.get('company'):
        context_parts.append(f"**Company search results:**\n{search_results['company']}")
    
    if search_results.get('reviews'):
        context_parts.append(f"**Review/culture search results:**\n{search_results['reviews']}")
    
    if search_results.get('salary'):
        context_parts.append(f"**Salary/compensation search results:**\n{search_results['salary']}")
    
    context = "\n\n---\n\n".join(context_parts) if context_parts else "No search results found."
    
    prompt = f"""Write a research report for a job seeker about this position:

**Job Title:** {job_title}
**Company:** {company or 'Unknown'}
**Source:** {source}
**Job URL:** {external_url or 'Not available'}

**Search Results:**
{context}

Remember: Be helpful, honest, and practical. If info is limited, say so.
Format with markdown. Keep under 800 words."""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                'model': LLM_MODEL,
                'prompt': prompt,
                'system': DOUG_SYSTEM,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'num_predict': 1200
                }
            },
            timeout=120
        )
        
        if resp.status_code == 200:
            response_text = resp.json().get('response', '')
            # Strip thinking tags if present
            response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
            return response_text
        else:
            logger.error(f"LLM error: {resp.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return None


def process_interaction(conn, interaction: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single research request."""
    interaction_id = interaction['interaction_id']
    user_id = interaction['user_id']
    posting_id = interaction['posting_id']
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get posting details
    cur.execute("""
        SELECT posting_id, job_title, extracted_summary, external_url, source
        FROM postings
        WHERE posting_id = %s
    """, (posting_id,))
    
    posting = cur.fetchone()
    if not posting:
        return {'success': False, 'error': f'Posting {posting_id} not found'}
    
    job_title = posting['job_title'] or 'Unknown Position'
    company = extract_company_from_summary(posting['extracted_summary'])
    external_url = posting['external_url']
    source = posting['source']
    
    logger.info(f"Doug researching: {job_title} at {company or 'unknown company'}")
    
    # Conduct searches
    search_results = {}
    
    # Search 1: Company info
    if company:
        query = f"{company} company"
        search_results['company'] = search_duckduckgo(query)
        time.sleep(1)  # Be nice to DDG
    
    # Search 2: Company reviews/culture
    if company:
        query = f"{company} employee reviews culture glassdoor"
        search_results['reviews'] = search_duckduckgo(query)
        time.sleep(1)
    
    # Search 3: Salary info (optional)
    if company and job_title:
        query = f"{company} {job_title} salary"
        search_results['salary'] = search_duckduckgo(query)
    
    # Generate report
    report = generate_report(
        job_title=job_title,
        company=company,
        external_url=external_url,
        source=source,
        search_results=search_results
    )
    
    if not report:
        return {
            'success': False, 
            'error': 'Failed to generate research report',
            'interaction_id': interaction_id
        }
    
    # Insert message
    subject = f"Research: {job_title}" + (f" at {company}" if company else "")
    if len(subject) > 100:
        subject = subject[:97] + "..."
    
    cur.execute("""
        INSERT INTO yogi_messages (
            user_id, sender_type, posting_id, message_type, subject, body, created_at
        ) VALUES (%s, 'doug', %s, 'research_report', %s, %s, NOW())
        RETURNING message_id
    """, (user_id, posting_id, subject, report))
    
    message_id = cur.fetchone()['message_id']
    
    # Update interaction state: researching → informed
    cur.execute("""
        UPDATE user_posting_interactions
        SET state = 'informed', state_changed_at = NOW(), updated_at = NOW()
        WHERE interaction_id = %s
    """, (interaction_id,))
    
    conn.commit()
    
    return {
        'success': True,
        'interaction_id': interaction_id,
        'message_id': message_id,
        'user_id': user_id,
        'posting_id': posting_id,
        'company': company,
        'job_title': job_title
    }


def get_pending_research(conn, limit: int = 10) -> List[Dict]:
    """Get interactions waiting for research."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT interaction_id, user_id, posting_id, created_at
        FROM user_posting_interactions
        WHERE state = 'researching'
        ORDER BY state_changed_at ASC
        LIMIT %s
    """, (limit,))
    return [dict(row) for row in cur.fetchall()]


def process_batch(limit: int = 10):
    """Process a batch of research requests."""
    conn = get_connection_raw()
    
    try:
        pending = get_pending_research(conn, limit)
        
        if not pending:
            print("✅ No research requests pending")
            return
        
        print(f"📊 Doug has {len(pending)} research requests")
        
        success = 0
        failed = 0
        
        for interaction in pending:
            result = process_interaction(conn, interaction)
            
            if result['success']:
                print(f"  ✅ {result['job_title'][:40]} → message {result['message_id']}")
                success += 1
            else:
                print(f"  ❌ Interaction {interaction['interaction_id']}: {result.get('error', 'Unknown error')}")
                failed += 1
            
            # Rate limit between requests
            time.sleep(2)
        
        print(f"\n✅ Done: {success} reports written, {failed} failed")
        
    finally:
        return_connection(conn)


def process_single(interaction_id: int):
    """Process a single interaction by ID."""
    conn = get_connection_raw()
    
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT interaction_id, user_id, posting_id, state
            FROM user_posting_interactions
            WHERE interaction_id = %s
        """, (interaction_id,))
        
        interaction = cur.fetchone()
        if not interaction:
            print(f"❌ Interaction {interaction_id} not found")
            return
        
        if interaction['state'] != 'researching':
            print(f"⚠️ Interaction {interaction_id} is in state '{interaction['state']}', not 'researching'")
            print("  Run anyway? (override with --force)")
            return
        
        result = process_interaction(conn, dict(interaction))
        
        if result['success']:
            print(f"✅ Research complete: {result['job_title']}")
            print(f"   Message ID: {result['message_id']}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
    finally:
        return_connection(conn)


# ============================================================================
# ASYNC API — For Mira to call Doug directly
# ============================================================================

import asyncio
import threading

def _run_research_sync(interaction_id: int):
    """Sync wrapper for process_single — runs in thread."""
    conn = get_connection_raw()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT interaction_id, user_id, posting_id, state
            FROM user_posting_interactions
            WHERE interaction_id = %s
        """, (interaction_id,))
        interaction = cur.fetchone()
        
        if not interaction:
            logger.error(f"Doug: Interaction {interaction_id} not found")
            return
        
        if interaction['state'] != 'researching':
            logger.warning(f"Doug: Interaction {interaction_id} not in 'researching' state")
            return
        
        result = process_interaction(conn, dict(interaction))
        
        if result['success']:
            logger.info(f"Doug: Research complete for {result.get('company', 'unknown')} - {result.get('job_title', 'unknown')}")
        else:
            logger.error(f"Doug: Research failed - {result.get('error', 'Unknown')}")
            
    except Exception as e:
        logger.error(f"Doug: Exception during research - {e}")
    finally:
        return_connection(conn)


async def research_async(interaction_id: int) -> None:
    """
    Queue Doug research to run in background thread.
    Returns immediately — doesn't block Mira.
    
    Usage from Mira:
        from actors.doug__research_C import research_async
        asyncio.create_task(research_async(interaction_id))
    """
    loop = asyncio.get_event_loop()
    # Run in thread pool to not block async loop
    await loop.run_in_executor(None, _run_research_sync, interaction_id)


def research_fire_and_forget(interaction_id: int) -> None:
    """
    Fire-and-forget Doug research — starts thread and returns immediately.
    Use this when you don't want to await.
    
    Usage:
        from actors.doug__research_C import research_fire_and_forget
        research_fire_and_forget(interaction_id)
    """
    thread = threading.Thread(target=_run_research_sync, args=(interaction_id,), daemon=True)
    thread.start()
    logger.info(f"Doug: Research queued for interaction {interaction_id}")


def main():
    parser = argparse.ArgumentParser(description="Doug's company research actor")
    parser.add_argument('interaction_id', nargs='?', type=int, help='Single interaction ID')
    parser.add_argument('--batch', '-b', type=int, default=0, help='Batch size (0 = single mode)')
    parser.add_argument('--force', '-f', action='store_true', help='Force process even if not in researching state')
    
    args = parser.parse_args()
    
    if args.batch > 0:
        process_batch(args.batch)
    elif args.interaction_id:
        process_single(args.interaction_id)
    else:
        # Default: process up to 10
        process_batch(10)


if __name__ == '__main__':
    main()
