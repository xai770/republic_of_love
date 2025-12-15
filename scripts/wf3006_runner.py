#!/usr/bin/env python3
"""
WF3006 Daemon Runner - Entity Classification

Runs the full classification pipeline continuously:
1. Fetch batch of orphan skills
2. Classify with gemma3:4b  
3. Debate low-confidence with challenger/defender/judge
4. Save decisions and reasoning
5. Apply approved decisions
6. Loop if more orphans exist

Can be run as daemon or one-shot.

Usage:
    python3 scripts/wf3006_runner.py           # One batch
    python3 scripts/wf3006_runner.py --daemon  # Continuous until all done
    python3 scripts/wf3006_runner.py --daemon --interval 60  # Every 60 seconds

Author: Arden
Date: December 15, 2025
"""

import argparse
import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.wave_runner.actors.orphan_fetcher_v2 import execute as fetch_orphans
from core.wave_runner.actors.classification_saver import execute as save_classification
from core.wave_runner.actors.classification_applier import execute as apply_classification
from core.wave_runner.actors.debate_panel import run_debate
from core.wave_runner.actors.domain_split_grader import execute as grade_proposal
from core.wave_runner.actors.domain_proposal_applier import execute as apply_proposals

# Configuration
BATCH_SIZE = 10
CLASSIFIER_MODEL = "gemma3:4b"
DEBATE_CONFIDENCE_THRESHOLD = 0.80

# Stats
stats = {
    "batches_processed": 0,
    "skills_classified": 0,
    "debates_held": 0,
    "debates_overturned": 0,
    "domains_created": 0,
    "proposals_graded": 0,
    "proposals_approved": 0,
    "errors": 0,
    "start_time": None
}


def log(msg: str, level: str = "INFO"):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def save_debate_reasoning(entity_id: int, debate_result: dict):
    """Save debate reasoning to classification_reasoning table."""
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        dbname=os.environ.get('DB_NAME', 'turing'),
        user=os.environ.get('DB_USER', 'base_admin'),
        password=os.environ.get('DB_PASSWORD', 'base_yoga_secure_2025')
    )
    
    try:
        cur = conn.cursor()
        
        # Save challenger reasoning
        challenge = debate_result.get("challenge", {})
        if challenge and not challenge.get("error"):
            cur.execute("""
                INSERT INTO classification_reasoning 
                    (entity_id, model, role, reasoning, confidence, suggested_domain)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                entity_id,
                "qwen2.5:7b",
                "challenger",
                challenge.get("challenge_reasoning", ""),
                challenge.get("strength", 0.5),
                challenge.get("alternative_domain")
            ))
        
        # Save defender reasoning
        defense = debate_result.get("defense", {})
        if defense and not defense.get("error"):
            cur.execute("""
                INSERT INTO classification_reasoning 
                    (entity_id, model, role, reasoning, confidence, suggested_domain)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                entity_id,
                "gemma3:4b",
                "defender",
                defense.get("defense", ""),
                defense.get("revised_confidence", 0.7),
                debate_result.get("initial", {}).get("domain")
            ))
        
        # Save judge ruling
        ruling = debate_result.get("ruling", {})
        if ruling and not ruling.get("error"):
            cur.execute("""
                INSERT INTO classification_reasoning 
                    (entity_id, model, role, reasoning, confidence, suggested_domain,
                     was_overturned, overturn_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                entity_id,
                "gemma3:4b",
                "judge",
                ruling.get("reasoning", ""),
                ruling.get("final_confidence", 0.7),
                ruling.get("final_domain"),
                debate_result.get("overturned", False),
                ruling.get("reasoning") if debate_result.get("overturned") else None
            ))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


def call_llm(prompt: str, model: str = CLASSIFIER_MODEL) -> dict:
    """Call Ollama LLM."""
    try:
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return {"error": result.stderr, "success": False}
        
        return {"response": result.stdout.strip(), "success": True}
        
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def build_classification_prompt(skills_text: str, domains_text: str) -> str:
    """Build classification prompt."""
    return f"""You are a skill classification expert. Classify each skill into EXACTLY ONE domain.

{domains_text}

For each skill, respond with a JSON object on its own line:
{{"entity_id": <id>, "action": "CLASSIFY", "domain": "<domain_name>", "confidence": 0.XX, "reasoning": "brief reason"}}

If no domain fits well, use:
{{"entity_id": <id>, "action": "NEW_DOMAIN", "suggested_domain_name": "<name>", "confidence": 0.XX, "reasoning": "why new domain needed"}}

SKILLS TO CLASSIFY:
{skills_text}

Respond with one JSON object per skill, one per line. No markdown, no extra text."""


def parse_classifications(response_text: str) -> list:
    """Parse classification response into list of decisions."""
    import re
    decisions = []
    
    for line in response_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Try to extract JSON from line
        try:
            json_match = re.search(r'\{[^{}]*\}', line, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                decisions.append(decision)
        except json.JSONDecodeError:
            pass
    
    return decisions


def process_pending_proposals() -> dict:
    """Grade and apply any pending domain proposals."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    result = {
        "graded": 0,
        "approved": 0,
        "rejected": 0,
        "applied": 0
    }
    
    # Load .env if exists
    env_file = PROJECT_ROOT / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)
    
    # Check for pending proposals
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        dbname=os.environ.get('DB_NAME', 'turing'),
        user=os.environ.get('DB_USER', 'base_admin'),
        password=os.environ.get('DB_PASSWORD', 'base_yoga_secure_2025')
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("""
            SELECT proposal_id, proposal_type, suggested_name 
            FROM domain_split_proposals 
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT 5
        """)
        pending = cur.fetchall()
        
        if not pending:
            return result
        
        log(f"Found {len(pending)} pending proposals to grade")
        
        # Grade each proposal
        for proposal in pending:
            log(f"  Grading proposal {proposal['proposal_id']}: {proposal['suggested_name']}")
            
            grade_result = grade_proposal({"proposal_id": proposal['proposal_id']})
            result["graded"] += 1
            stats["proposals_graded"] += 1
            
            # Check results array for the grading outcome
            results = grade_result.get("results", [])
            if results and results[0].get("grader_approved"):
                result["approved"] += 1
                stats["proposals_approved"] += 1
                log(f"    ✅ APPROVED (conf: {results[0].get('grader_confidence', 'N/A')})")
            elif grade_result.get("approved", 0) > 0:
                # Batch grading returned approved count
                result["approved"] += grade_result.get("approved", 0)
                stats["proposals_approved"] += grade_result.get("approved", 0)
                log(f"    ✅ APPROVED")
            else:
                result["rejected"] += 1
                reasoning = (results[0].get('grader_reasoning', 'No reason') if results 
                           else grade_result.get('message', 'No reason'))
                log(f"    ❌ REJECTED: {str(reasoning)[:50]}...")
        
        # Apply approved proposals
        if result["approved"] > 0:
            log("  Applying approved proposals...")
            apply_result = apply_proposals({})
            result["applied"] = apply_result.get("applied", 0)
            log(f"    Applied {result['applied']} domain proposals")
        
    finally:
        cur.close()
        conn.close()
    
    return result


def process_batch() -> dict:
    """Process one batch of orphan skills."""
    batch_stats = {
        "fetched": 0,
        "classified": 0,
        "debated": 0,
        "saved": 0,
        "applied": 0,
        "remaining": 0,
        "errors": []
    }
    
    # Step 1: Fetch orphans
    log("Fetching orphan skills...")
    fetch_result = fetch_orphans({
        "batch_size": BATCH_SIZE,
        "include_history": True,
        "include_similar": True
    })
    
    if fetch_result.get("status") == "NO_ORPHANS":
        log("No orphans remaining!", "SUCCESS")
        return {"status": "complete", "remaining": 0}
    
    if fetch_result.get("status") == "error":
        log(f"Fetch error: {fetch_result.get('error')}", "ERROR")
        batch_stats["errors"].append(f"Fetch: {fetch_result.get('error')}")
        return {"status": "error", **batch_stats}
    
    skills = fetch_result.get("skills", [])
    batch_stats["fetched"] = len(skills)
    batch_stats["remaining"] = fetch_result.get("remaining", 0)
    
    log(f"Fetched {len(skills)} skills, {batch_stats['remaining']} remaining")
    
    # Step 2: Classify
    log(f"Classifying with {CLASSIFIER_MODEL}...")
    prompt = build_classification_prompt(
        fetch_result.get("skills_text", ""),
        fetch_result.get("domains_text", "")
    )
    
    llm_result = call_llm(prompt)
    
    if not llm_result.get("success"):
        log(f"LLM error: {llm_result.get('error')}", "ERROR")
        batch_stats["errors"].append(f"LLM: {llm_result.get('error')}")
        return {"status": "error", **batch_stats}
    
    response_text = llm_result.get("response", "")
    decisions = parse_classifications(response_text)
    batch_stats["classified"] = len(decisions)
    
    log(f"Classified {len(decisions)} skills")
    
    # Step 3: Debate low-confidence classifications
    debated_decisions = []
    skill_ids_in_batch = {s["entity_id"]: s for s in skills}
    
    for decision in decisions:
        confidence = decision.get("confidence", 0.85)
        skill_id = decision.get("entity_id")
        
        # Convert entity_id to int for lookup (LLM sometimes returns it as string)
        try:
            skill_id_int = int(skill_id) if skill_id is not None else None
        except (ValueError, TypeError):
            skill_id_int = None
        
        # Debug: log confidence being evaluated
        if confidence < DEBATE_CONFIDENCE_THRESHOLD:
            log(f"  Low confidence detected: entity_id={skill_id}, conf={confidence}")
            skill_info = skill_ids_in_batch.get(skill_id_int)
            
            if skill_info:
                log(f"  Debating {skill_info['name']} (conf: {confidence})...")
                batch_stats["debated"] += 1
                stats["debates_held"] += 1
                
                debate_result = run_debate(
                    skill=skill_info,
                    initial_classification={
                        "domain": decision.get("domain"),
                        "confidence": confidence,
                        "reasoning": decision.get("reasoning", "")
                    },
                    available_domains=fetch_result.get("domains", []),
                    similar_skills=skill_info.get("similar", [])
                )
                
                # Save debate reasoning to DB
                try:
                    save_debate_reasoning(skill_id_int, debate_result)
                except Exception as e:
                    log(f"  Warning: Failed to save debate reasoning: {e}", "WARN")
                
                if debate_result.get("overturned"):
                    log(f"    ⚡ OVERTURNED → {debate_result.get('final_domain')}")
                    stats["debates_overturned"] += 1
                    decision["domain"] = debate_result.get("final_domain")
                    decision["confidence"] = debate_result.get("final_confidence")
                    decision["reasoning"] += f" [DEBATED: {debate_result.get('ruling', {}).get('reasoning', '')}]"
        
        debated_decisions.append(decision)
    
    # Step 4: Save decisions
    log("Saving decisions...")
    
    # Convert to response format for saver
    response_for_saver = "\n".join([json.dumps(d) for d in debated_decisions])
    
    save_result = save_classification({
        "response": response_for_saver,
        "model": CLASSIFIER_MODEL
    })
    
    batch_stats["saved"] = save_result.get("saved", 0)
    
    if save_result.get("domains_created", 0) > 0:
        stats["domains_created"] += save_result.get("domains_created")
        log(f"  Created {save_result.get('domains_created')} new domain(s)")
    
    log(f"Saved {batch_stats['saved']} decisions")
    
    # Step 5: Apply approved decisions
    log("Applying approved decisions...")
    apply_result = apply_classification({})
    
    batch_stats["applied"] = apply_result.get("applied", 0)
    log(f"Applied {batch_stats['applied']} relationships")
    
    # Step 6: Grade and apply pending domain proposals
    log("Processing pending domain proposals...")
    proposal_result = process_pending_proposals()
    if proposal_result.get("graded", 0) > 0:
        log(f"Graded {proposal_result['graded']} proposals, approved {proposal_result['approved']}, applied {proposal_result['applied']}")
    
    # Update global stats
    stats["batches_processed"] += 1
    stats["skills_classified"] += batch_stats["classified"]
    
    return {"status": "success", **batch_stats}


def run_daemon(interval: int = 30, max_batches: int = None):
    """Run continuously until no orphans remain or max_batches hit."""
    stats["start_time"] = datetime.now()
    batch_count = 0
    
    log("=" * 60)
    log("WF3006 Entity Classification Daemon Starting")
    log(f"Batch size: {BATCH_SIZE}, Interval: {interval}s")
    log("=" * 60)
    
    while True:
        batch_count += 1
        
        if max_batches and batch_count > max_batches:
            log(f"Reached max batches ({max_batches}), stopping")
            break
        
        log(f"\n--- BATCH {batch_count} ---")
        result = process_batch()
        
        if result.get("status") == "complete":
            log("🎉 All orphans classified!", "SUCCESS")
            break
        
        if result.get("status") == "error":
            stats["errors"] += 1
            if stats["errors"] > 5:
                log("Too many consecutive errors, stopping", "ERROR")
                break
        else:
            stats["errors"] = 0  # Reset on success
        
        remaining = result.get("remaining", 0)
        if remaining == 0:
            log("No more orphans!", "SUCCESS")
            break
        
        log(f"Sleeping {interval}s... ({remaining} orphans remaining)")
        time.sleep(interval)
    
    # Print summary
    elapsed = (datetime.now() - stats["start_time"]).total_seconds()
    
    log("\n" + "=" * 60)
    log("DAEMON SUMMARY")
    log("=" * 60)
    log(f"Runtime: {elapsed:.1f} seconds")
    log(f"Batches processed: {stats['batches_processed']}")
    log(f"Skills classified: {stats['skills_classified']}")
    log(f"Debates held: {stats['debates_held']}")
    log(f"Debates overturned: {stats['debates_overturned']}")
    log(f"Domains created: {stats['domains_created']}")
    log(f"Proposals graded: {stats['proposals_graded']}")
    log(f"Proposals approved: {stats['proposals_approved']}")


def run_single_batch():
    """Run a single batch."""
    log("=" * 60)
    log("WF3006 Single Batch Run")
    log("=" * 60)
    
    result = process_batch()
    
    log("\n" + "=" * 60)
    log("BATCH RESULT")
    log("=" * 60)
    log(f"Status: {result.get('status')}")
    log(f"Fetched: {result.get('fetched', 0)}")
    log(f"Classified: {result.get('classified', 0)}")
    log(f"Debated: {result.get('debated', 0)}")
    log(f"Saved: {result.get('saved', 0)}")
    log(f"Applied: {result.get('applied', 0)}")
    log(f"Remaining: {result.get('remaining', 0)}")


def main():
    parser = argparse.ArgumentParser(description="WF3006 Entity Classification Runner")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between batches (daemon mode)")
    parser.add_argument("--max-batches", type=int, help="Max batches before stopping (daemon mode)")
    parser.add_argument("--batch-size", type=int, default=10, help="Skills per batch")
    
    args = parser.parse_args()
    
    global BATCH_SIZE
    BATCH_SIZE = args.batch_size
    
    if args.daemon:
        run_daemon(interval=args.interval, max_batches=args.max_batches)
    else:
        run_single_batch()


if __name__ == "__main__":
    main()
