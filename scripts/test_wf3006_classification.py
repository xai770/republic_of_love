#!/usr/bin/env python3
"""
WF3006 Classification Test - Phase 2 Validation

Tests the core classification pipeline:
1. Fetch orphan skills with orphan_fetcher_v2
2. Classify using gemma3:4b via llm_chat.py
3. Save decisions with classification_saver
4. Apply decisions with classification_applier

Run: python3 scripts/test_wf3006_classification.py

Author: Arden
Date: December 15, 2025
"""

import json
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.wave_runner.actors.orphan_fetcher_v2 import execute as fetch_orphans
from core.wave_runner.actors.classification_saver import execute as save_classification
from core.wave_runner.actors.classification_applier import execute as apply_classification

# Configuration
MODEL = "gemma3:4b"
BATCH_SIZE = 10

def call_llm(prompt: str, model: str = MODEL) -> dict:
    """Call LLM via Ollama directly."""
    try:
        result = subprocess.run(
            ['ollama', 'run', model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes
        )
        
        if result.returncode != 0:
            return {"error": result.stderr, "success": False}
        
        return {"response": result.stdout.strip(), "success": True}
        
    except subprocess.TimeoutExpired:
        return {"error": "Timeout - model took too long", "success": False}
    except FileNotFoundError:
        return {"error": "Ollama not installed or not in PATH", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def build_classification_prompt(skills_text: str, domains_text: str) -> str:
    """Build the classification prompt from fetched data."""
    return f"""You are a skill classification expert. Classify each skill into EXACTLY ONE domain.

{domains_text}

For each skill, respond with a JSON object on its own line:
{{"entity_id": <id>, "action": "CLASSIFY", "domain": "<domain_name>", "confidence": 0.XX, "reasoning": "brief reason"}}

If no domain fits well, use:
{{"entity_id": <id>, "action": "NEW_DOMAIN", "suggested_domain_name": "<name>", "confidence": 0.XX, "reasoning": "why new domain needed"}}

SKILLS TO CLASSIFY:
{skills_text}

Respond with one JSON object per skill, one per line. No markdown, no extra text."""


def main():
    print("=" * 60)
    print("WF3006 Classification Test - Phase 2")
    print("=" * 60)
    
    # Step 1: Fetch orphans
    print("\n[Step 1] Fetching orphan skills...")
    fetch_result = fetch_orphans({
        "batch_size": BATCH_SIZE,
        "include_history": True,
        "include_similar": True
    })
    
    if fetch_result.get("status") == "NO_ORPHANS":
        print("✓ No orphans to process!")
        return
    
    if fetch_result.get("status") == "error":
        print(f"✗ Error fetching orphans: {fetch_result.get('error')}")
        return
    
    skills = fetch_result.get("skills", [])
    print(f"✓ Fetched {len(skills)} orphan skills")
    print(f"  Remaining orphans: {fetch_result.get('remaining')}")
    
    for s in skills:
        history_note = f" (attempt #{s['attempt_count']+1})" if s['has_history'] else ""
        print(f"  - {s['entity_id']}: {s['name']}{history_note}")
    
    # Step 2: Build prompt and call LLM
    print(f"\n[Step 2] Classifying with {MODEL}...")
    prompt = build_classification_prompt(
        fetch_result.get("skills_text", ""),
        fetch_result.get("domains_text", "")
    )
    
    llm_result = call_llm(prompt)
    
    if llm_result.get("error"):
        print(f"✗ LLM error: {llm_result.get('error')}")
        return
    
    response_text = llm_result.get("response", "")
    print(f"✓ Got LLM response ({len(response_text)} chars)")
    print("\n--- LLM Response ---")
    print(response_text[:1000])
    if len(response_text) > 1000:
        print("...")
    print("--- End Response ---\n")
    
    # Step 3: Save decisions
    print("\n[Step 3] Saving decisions...")
    save_result = save_classification({
        "response": response_text,
        "model": MODEL
    })
    
    print(f"  Status: {save_result.get('status')}")
    print(f"  Total processed: {save_result.get('total_processed', 0)}")
    print(f"  Saved: {save_result.get('saved', 0)}")
    print(f"  Domains created: {save_result.get('domains_created', 0)}")
    print(f"  Proposals: {save_result.get('proposals_created', 0)}")
    print(f"  Skipped: {save_result.get('skipped', 0)}")
    print(f"  Errors: {save_result.get('errors', 0)}")
    
    if save_result.get("results"):
        print("\n  Decision details:")
        for r in save_result["results"][:5]:
            status_emoji = "✓" if r.get("status") == "saved" else "⚠"
            print(f"    {status_emoji} {r.get('entity_id')}: {r.get('action')} → {r.get('domain', r.get('message', ''))}")
    
    # Step 4: Apply decisions
    print("\n[Step 4] Applying approved decisions...")
    apply_result = apply_classification({})
    
    print(f"  Status: {apply_result.get('status')}")
    print(f"  Applied: {apply_result.get('applied', 0)}")
    print(f"  Skipped: {apply_result.get('skipped', 0)}")
    print(f"  Remaining: {apply_result.get('remaining', 0)}")
    
    if apply_result.get("applied_details"):
        print("\n  Applied relationships:")
        for d in apply_result["applied_details"]:
            print(f"    ✓ {d['skill']} → {d['domain']} (conf: {d['confidence']})")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Skills fetched: {len(skills)}")
    print(f"Decisions saved: {save_result.get('saved', 0)}")
    print(f"Relationships created: {apply_result.get('applied', 0)}")
    print(f"Remaining orphans: {fetch_result.get('remaining', 0) - apply_result.get('applied', 0)}")
    
    if apply_result.get("applied", 0) > 0:
        print("\n✅ Phase 2 validation PASSED - core pipeline working!")
    else:
        print("\n⚠️ No relationships created - check decision confidence levels")


if __name__ == "__main__":
    main()
