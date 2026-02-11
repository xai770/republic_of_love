#!/usr/bin/env python3
"""
Enrichment Daemon - Work-query-driven enrichment cascade.

Replaces the sequential steps 3-6 of nightly_fetch.sh with a pull-based
architecture where each enrichment step declares its own work_query and 
the daemon exhausts work for each step in dependency order.

Why this is better than sequential batch scripts:
  1. Self-healing: If step 3 fails mid-run, step 4 still processes what's ready
  2. Continuous: Can run as a daemon (--watch) beyond the nightly window
  3. Observable: Each step reports its own backlog
  4. Composable: Add new enrichment steps without editing nightly_fetch.sh

Usage:
    python3 scripts/enrichment_daemon.py --once      # One pass, exhaust all work
    python3 scripts/enrichment_daemon.py --watch      # Continuous daemon (5s poll)
    python3 scripts/enrichment_daemon.py --status     # Show backlog per step
    python3 scripts/enrichment_daemon.py --step 3     # Run only step 3
    python3 scripts/enrichment_daemon.py --dry-run    # Show what would run

Architecture:
    Each enrichment step defines:
      - work_query: SQL that returns subject_ids needing work
      - run(): function that processes a batch
      - depends_on: list of step numbers that must produce data first
    
    The daemon loops through steps in dependency order, running each until
    its work_query returns 0 rows, then moves to the next.

Coexistence with nightly_fetch.sh:
    nightly_fetch.sh handles steps 1-2 (network fetches from AA/DB APIs).
    This daemon handles steps 3-6 (enrichment/transformation).
    They can run independently — nightly_fetch.sh populates raw postings,
    this daemon processes them whenever they appear.
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('enrichment_daemon')

# ntfy.sh topic for notifications (same as nightly_fetch.sh)
NTFY_TOPIC = "ty-pipeline"


def notify(title: str, message: str, priority: str = "default"):
    """Send push notification via ntfy.sh."""
    try:
        subprocess.run(
            ["curl", "-s", "-H", f"Title: {title}", "-H", f"Priority: {priority}",
             "-d", message, f"https://ntfy.sh/{NTFY_TOPIC}"],
            capture_output=True, timeout=10
        )
    except Exception:
        pass


@dataclass
class EnrichmentStep:
    """Definition of an enrichment step."""
    number: int
    name: str
    description: str
    work_query: str  # SQL returning count of pending items
    command: list     # Command to run (subprocess), including batch size
    depends_on: tuple = ()  # Step numbers this depends on
    enabled: bool = True


# ============================================================================
# ENRICHMENT STEPS - Define the cascade
# ============================================================================
# These mirror nightly_fetch.sh steps 3-6 but are self-describing

STEPS = [
    EnrichmentStep(
        number=3,
        name="job_description_backfill",
        description="Backfill missing job descriptions from AA pages (Playwright)",
        work_query="""
            SELECT COUNT(*) as cnt 
            FROM postings 
            WHERE source = 'arbeitsagentur' 
              AND (job_description IS NULL OR LENGTH(COALESCE(job_description,'')) < 100)
              AND job_description != '[EXTERNAL_PARTNER]'
              AND COALESCE(invalidated, false) = false
        """,
        command=["python3", "actors/postings__job_description_U.py", "--batch", "50000"],
        depends_on=(),
    ),
    EnrichmentStep(
        number=3.5,
        name="external_partner_scrape",
        description="Scrape partner sites for job descriptions (HTTP-based scrapers)",
        work_query="""
            SELECT COUNT(*) as cnt
            FROM postings p
            WHERE p.source = 'arbeitsagentur'
              AND (p.job_description IS NULL OR LENGTH(COALESCE(p.job_description,'')) < 100)
              AND p.job_description != '[EXTERNAL_PARTNER]'
              AND COALESCE(p.invalidated, false) = false
              AND p.source_metadata->'raw_api_response'->>'externeUrl' IS NOT NULL
              AND p.source_metadata->'raw_api_response'->>'externeUrl' NOT LIKE '%%arbeitsagentur.de%%'
        """,
        command=["python3", "actors/postings__external_partners_U.py", "--batch", "1000"],
        depends_on=(),
    ),
    EnrichmentStep(
        number=4,
        name="extracted_summary",
        description="Extract summaries from Deutsche Bank postings (LLM)",
        work_query="""
            SELECT COUNT(*) as cnt
            FROM postings 
            WHERE source = 'deutsche_bank'
              AND extracted_summary IS NULL
              AND job_description IS NOT NULL
              AND LENGTH(job_description) > 100
        """,
        command=["python3", "actors/postings__extracted_summary_U.py", "--batch", "5000", "--source", "deutsche_bank"],
        depends_on=(3,),
    ),
    EnrichmentStep(
        number=5,
        name="embedding",
        description="Generate embeddings for match-eligible postings",
        work_query="""
            SELECT COUNT(*) as cnt 
            FROM postings_for_matching p 
            WHERE NOT EXISTS (
                SELECT 1 FROM embeddings e 
                WHERE e.text = p.match_text
            )
        """,
        command=["python3", "actors/postings__embedding_U.py", "--batch", "100000"],
        depends_on=(3, 4),
    ),
    EnrichmentStep(
        number=6,
        name="domain_classification",
        description="Classify posting domains from Berufenet KldB codes",
        work_query="""
            SELECT COUNT(*) as cnt
            FROM postings p
            WHERE p.job_description IS NOT NULL
              AND LENGTH(p.job_description) > 100
              AND (p.domain_gate IS NULL OR p.domain_gate->>'primary_domain' IS NULL)
              AND p.source_metadata->'raw_api_response'->>'berufenetKldbCode' IS NOT NULL
        """,
        command=["python3", "tools/populate_domain_gate.py", "--apply"],
        depends_on=(3,),
    ),
]


def get_backlog(step: EnrichmentStep) -> int:
    """Run work_query to get pending item count."""
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(step.work_query)
            return cur.fetchone()['cnt']
    except Exception as e:
        logger.error(f"Work query failed for {step.name}: {e}")
        return -1


def run_step(step: EnrichmentStep, dry_run: bool = False) -> bool:
    """Execute one enrichment step. Returns True if work was done."""
    backlog = get_backlog(step)
    
    if backlog <= 0:
        logger.debug(f"  {step.name}: no work (backlog={backlog})")
        return False
    
    logger.info(f"📋 Step {step.number} [{step.name}]: {backlog:,} items pending")
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would run: {' '.join(step.command)}")
        return True
    
    cmd = list(step.command)
    
    logger.info(f"  Running: {' '.join(cmd)}")
    start = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=False,  # Let output flow to our stdout
            timeout=7200,  # 2 hour max per step
        )
        elapsed = time.time() - start
        
        if result.returncode != 0:
            logger.error(f"  ❌ {step.name} failed (exit code {result.returncode}) after {elapsed:.0f}s")
            return False
        
        logger.info(f"  ✅ {step.name} completed in {elapsed:.0f}s")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"  ⏰ {step.name} timed out after 2 hours")
        return False
    except Exception as e:
        logger.error(f"  ❌ {step.name} error: {e}")
        return False


def show_status():
    """Show backlog for each enrichment step."""
    print("=" * 65)
    print("ENRICHMENT PIPELINE STATUS")
    print("=" * 65)
    print()
    
    for step in STEPS:
        if not step.enabled:
            status = "DISABLED"
            backlog = 0
        else:
            backlog = get_backlog(step)
            status = f"{backlog:,} pending" if backlog > 0 else "✅ clear"
        
        deps = f" (needs: {','.join(str(d) for d in step.depends_on)})" if step.depends_on else ""
        print(f"  Step {step.number:>4} | {step.name:<30} | {status}{deps}")
        print(f"         | {step.description}")
        print()
    
    print("=" * 65)


def run_once(steps: list, dry_run: bool = False) -> int:
    """Run all steps once in dependency order. Returns total items processed."""
    completed_steps = set()
    total_processed = 0
    
    for step in steps:
        if not step.enabled:
            continue
        
        # Check dependencies
        unmet = [d for d in step.depends_on if d not in completed_steps]
        if unmet:
            # Dependencies not completed this cycle, but that's OK —
            # the work_query ensures we only process what's ready
            logger.debug(f"  {step.name}: dependencies {unmet} not run this cycle (OK, work_query filters)")
        
        worked = run_step(step, dry_run)
        if worked:
            total_processed += 1
        completed_steps.add(step.number)
    
    return total_processed


def run_watch(steps: list, poll_interval: int = 30, dry_run: bool = False):
    """Continuous daemon mode — keep polling for work."""
    logger.info("=" * 60)
    logger.info("ENRICHMENT DAEMON STARTED (watch mode)")
    logger.info(f"  Poll interval: {poll_interval}s")
    logger.info(f"  Steps: {', '.join(str(s.number) for s in steps if s.enabled)}")
    logger.info("=" * 60)
    
    try:
        while True:
            cycle_start = time.time()
            processed = run_once(steps, dry_run)
            
            if processed > 0:
                logger.info(f"Cycle complete: {processed} steps had work")
            else:
                logger.debug("Cycle complete: no work found")
            
            # Sleep until next poll
            elapsed = time.time() - cycle_start
            sleep_time = max(0, poll_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    except KeyboardInterrupt:
        logger.info("Shutting down (Ctrl+C)")


def main():
    parser = argparse.ArgumentParser(
        description="Enrichment Daemon — work-query-driven enrichment cascade"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run all steps once, then exit")
    mode.add_argument("--watch", action="store_true", help="Continuous daemon mode")
    mode.add_argument("--status", action="store_true", help="Show backlog per step")
    
    parser.add_argument("--step", type=float, help="Run only this step number")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run")
    parser.add_argument("--poll-interval", type=int, default=30, help="Seconds between polls (watch mode)")
    
    args = parser.parse_args()
    
    # Filter steps
    steps = STEPS
    if args.step is not None:
        steps = [s for s in STEPS if s.number == args.step]
        if not steps:
            print(f"Unknown step {args.step}. Available: {', '.join(str(s.number) for s in STEPS)}")
            return 1
    
    if args.status:
        show_status()
        return 0
    
    if args.watch:
        run_watch(steps, poll_interval=args.poll_interval, dry_run=args.dry_run)
        return 0
    
    # Default: --once
    total = run_once(steps, dry_run=args.dry_run)
    logger.info(f"Done. {total} steps had work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
