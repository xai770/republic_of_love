#!/usr/bin/env python3
"""
Orphan Skill Classifier - Option C: Simple Script

This script directly classifies orphan skills without using the Turing workflow system.
Use this for immediate results while we design a proper workflow.

Author: Arden
Date: December 15, 2025

Usage:
    python scripts/classify_orphans.py [--batch-size 25] [--max-batches 10] [--dry-run]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import psycopg2
import psycopg2.extras
import requests

# Database connection config
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'turing'),
    'user': os.getenv('DB_USER', 'base_admin'),
    'password': os.getenv('DB_PASSWORD', 'base_yoga_secure_2025'),
}

# Ollama config
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
CLASSIFY_MODEL = 'gemma3:4b'  # Fast, good for classification

# Domain mapping - from entities table
DOMAINS = {
    'technology': 8452,
    'data_and_analytics': 8453,
    'business_operations': 8454,
    'people_and_communication': 8455,
    'compliance_and_risk': 8456,
    'project_and_product': 8457,
    'corporate_culture': 8458,
    'specialized_knowledge': 8459,
}

DOMAIN_DESCRIPTIONS = {
    'technology': 'Software, hardware, infrastructure, programming languages, databases, cloud',
    'data_and_analytics': 'Data science, analytics, statistics, visualization, reporting',
    'business_operations': 'Operations, supply chain, logistics, procurement, facilities',
    'people_and_communication': 'HR, training, communication, marketing, writing, presentation',
    'compliance_and_risk': 'Legal, regulatory, audit, risk management, security, privacy',
    'project_and_product': 'Project management, product management, agile, scrum, planning',
    'corporate_culture': 'Values, mission, diversity, inclusion, workplace culture',
    'specialized_knowledge': 'Industry-specific knowledge, domain expertise, certifications',
}


def get_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)


def fetch_orphan_batch(cursor, batch_size=25):
    """
    Fetch orphan skills that have no domain assignment and no pending decision.
    """
    cursor.execute("""
        SELECT e.entity_id, e.canonical_name, e.description
        FROM entities e
        WHERE e.entity_type = 'skill'
          AND e.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er
              JOIN entities domain ON er.related_entity_id = domain.entity_id
              WHERE er.entity_id = e.entity_id
                AND er.relationship = 'is_a'
                AND domain.entity_type = 'skill_domain'
          )
          AND NOT EXISTS (
              SELECT 1 FROM registry_decisions rd
              WHERE rd.subject_entity_id = e.entity_id
                AND rd.decision_type = 'skill_domain_mapping'
                AND rd.review_status IN ('pending', 'approved', 'auto_approved')
          )
        ORDER BY e.entity_id
        LIMIT %s
    """, (batch_size,))
    
    return cursor.fetchall()


def count_remaining_orphans(cursor):
    """Count how many orphans remain."""
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM entities e
        WHERE e.entity_type = 'skill'
          AND e.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM entity_relationships er
              JOIN entities domain ON er.related_entity_id = domain.entity_id
              WHERE er.entity_id = e.entity_id
                AND er.relationship = 'is_a'
                AND domain.entity_type = 'skill_domain'
          )
          AND NOT EXISTS (
              SELECT 1 FROM registry_decisions rd
              WHERE rd.subject_entity_id = e.entity_id
                AND rd.decision_type = 'skill_domain_mapping'
                AND rd.review_status IN ('pending', 'approved', 'auto_approved')
          )
    """)
    return cursor.fetchone()['count']


def check_existing_alias(cursor, skill_name):
    """
    Check if this skill already exists in entity_names (as an alias).
    Returns the canonical entity_id if found, None otherwise.
    """
    cursor.execute("""
        SELECT entity_id, is_primary 
        FROM entity_names 
        WHERE LOWER(display_name) = LOWER(%s)
    """, (skill_name,))
    row = cursor.fetchone()
    return row['entity_id'] if row else None


def classify_skill(skill_name, description=None):
    """
    Use LLM to classify a skill into a domain.
    Returns (domain_name, confidence).
    """
    domain_list = "\n".join([
        f"- {name}: {desc}" 
        for name, desc in DOMAIN_DESCRIPTIONS.items()
    ])
    
    desc_text = f" (Description: {description})" if description else ""
    
    prompt = f"""You are a skill classification expert. Classify the following skill into exactly ONE domain.

SKILL: {skill_name}{desc_text}

AVAILABLE DOMAINS:
{domain_list}

Respond in JSON format ONLY:
{{"domain": "domain_name", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

If you're uncertain, use confidence < 0.7 and we'll review manually.
Respond with JSON only, no other text."""

    try:
        response = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json={
                'model': CLASSIFY_MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.3}
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        
        # Parse JSON from response
        text = result.get('response', '').strip()
        # Handle markdown code blocks
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()
        
        data = json.loads(text)
        domain = data.get('domain', '').lower().strip()
        confidence = float(data.get('confidence', 0.5))
        reasoning = data.get('reasoning', '')
        
        # Normalize domain name
        domain = domain.replace(' ', '_').replace('-', '_')
        
        if domain not in DOMAINS:
            # Try fuzzy match
            for valid_domain in DOMAINS:
                if valid_domain in domain or domain in valid_domain:
                    domain = valid_domain
                    break
            else:
                return None, 0, f"Invalid domain: {domain}"
        
        return domain, confidence, reasoning
        
    except Exception as e:
        return None, 0, f"LLM error: {str(e)}"


def save_decision(cursor, skill_id, domain_name, confidence, reasoning, auto_approve=True):
    """
    Save classification decision to registry_decisions.
    """
    domain_id = DOMAINS.get(domain_name)
    if not domain_id:
        return False, f"Unknown domain: {domain_name}"
    
    review_status = 'auto_approved' if (auto_approve and confidence >= 0.8) else 'pending'
    
    cursor.execute("""
        INSERT INTO registry_decisions 
        (subject_entity_id, target_entity_id, decision_type, 
         reasoning, review_status, confidence, model, created_at)
        VALUES (%s, %s, 'skill_domain_mapping', 
                %s, %s, %s, %s, %s)
        RETURNING decision_id
    """, (
        skill_id,
        domain_id,
        f"Assign to {domain_name}: {reasoning}",
        review_status,
        confidence,
        CLASSIFY_MODEL,
        datetime.now()
    ))
    
    decision_id = cursor.fetchone()['decision_id']
    return True, decision_id


def apply_decision(cursor, skill_id, domain_id):
    """
    Create the is_a relationship for a skill -> domain mapping.
    """
    # Check if relationship already exists
    cursor.execute("""
        SELECT 1 FROM entity_relationships 
        WHERE entity_id = %s AND related_entity_id = %s AND relationship = 'is_a'
    """, (skill_id, domain_id))
    
    if cursor.fetchone():
        return True, "Already exists"
    
    cursor.execute("""
        INSERT INTO entity_relationships (entity_id, related_entity_id, relationship, created_at)
        VALUES (%s, %s, 'is_a', %s)
        RETURNING relationship_id
    """, (skill_id, domain_id, datetime.now()))
    
    rel_id = cursor.fetchone()['relationship_id']
    return True, rel_id


def check_domain_sizes(cursor):
    """
    Check if any domain has more than threshold skills.
    Returns domains that might need splitting.
    """
    cursor.execute("""
        SELECT d.canonical_name as domain, d.entity_id as domain_id, COUNT(er.entity_id) as skill_count
        FROM entities d
        LEFT JOIN entity_relationships er ON d.entity_id = er.related_entity_id AND er.relationship = 'is_a'
        WHERE d.entity_type = 'skill_domain'
        GROUP BY d.entity_id, d.canonical_name
        ORDER BY skill_count DESC
    """)
    
    return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description='Classify orphan skills')
    parser.add_argument('--batch-size', type=int, default=25, help='Skills per batch')
    parser.add_argument('--max-batches', type=int, default=0, help='Max batches (0=unlimited)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--apply', action='store_true', help='Also apply auto_approved decisions')
    parser.add_argument('--confidence-threshold', type=float, default=0.8, help='Min confidence for auto-approve')
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         Orphan Skill Classifier - Option C                  ║
╠══════════════════════════════════════════════════════════════╣
║  Batch Size: {args.batch_size:4}  Max Batches: {args.max_batches or 'unlimited':10}              ║
║  Dry Run: {str(args.dry_run):5}   Apply: {str(args.apply):5}                          ║
║  Confidence Threshold: {args.confidence_threshold:.2f}                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Count total orphans
    total_orphans = count_remaining_orphans(cursor)
    print(f"📊 Orphan skills remaining: {total_orphans}")
    
    if total_orphans == 0:
        print("✅ All skills classified!")
        return
    
    batch_num = 0
    total_classified = 0
    total_auto_approved = 0
    total_pending = 0
    total_errors = 0
    
    start_time = time.time()
    
    while True:
        batch_num += 1
        
        if args.max_batches and batch_num > args.max_batches:
            print(f"\n🛑 Reached max batches ({args.max_batches})")
            break
        
        orphans = fetch_orphan_batch(cursor, args.batch_size)
        
        if not orphans:
            print("\n✅ All orphan skills processed!")
            break
        
        print(f"\n═══ Batch {batch_num}: {len(orphans)} skills ═══")
        
        for skill in orphans:
            skill_id = skill['entity_id']
            skill_name = skill['canonical_name']
            description = skill.get('description')
            
            # Check for existing alias
            existing_id = check_existing_alias(cursor, skill_name)
            if existing_id and existing_id != skill_id:
                print(f"  🔗 {skill_name} → alias of {existing_id}")
                # Could handle alias merging here
                continue
            
            # Classify
            domain, confidence, reasoning = classify_skill(skill_name, description)
            
            if not domain:
                print(f"  ❌ {skill_name}: {reasoning}")
                total_errors += 1
                continue
            
            status = "AUTO" if confidence >= args.confidence_threshold else "PENDING"
            print(f"  {'✓' if status == 'AUTO' else '○'} {skill_name} → {domain} ({confidence:.0%}) [{status}]")
            
            if args.dry_run:
                total_classified += 1
                if status == "AUTO":
                    total_auto_approved += 1
                else:
                    total_pending += 1
                continue
            
            # Save decision
            success, result = save_decision(
                cursor, skill_id, domain, confidence, reasoning,
                auto_approve=(confidence >= args.confidence_threshold)
            )
            
            if success:
                total_classified += 1
                if status == "AUTO":
                    total_auto_approved += 1
                else:
                    total_pending += 1
                
                # Apply if auto-approved and --apply flag set
                if args.apply and status == "AUTO":
                    domain_id = DOMAINS[domain]
                    apply_decision(cursor, skill_id, domain_id)
            else:
                print(f"    ERROR saving: {result}")
                total_errors += 1
        
        # Commit batch
        if not args.dry_run:
            conn.commit()
        
        # Progress update
        remaining = count_remaining_orphans(cursor)
        elapsed = time.time() - start_time
        rate = total_classified / elapsed if elapsed > 0 else 0
        eta = remaining / rate / 60 if rate > 0 else 0
        
        print(f"  📈 Progress: {total_classified} done, {remaining} remaining (~{eta:.1f} min)")
    
    # Final summary
    elapsed = time.time() - start_time
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                      CLASSIFICATION COMPLETE                 ║
╠══════════════════════════════════════════════════════════════╣
║  Total Classified:     {total_classified:5}                                  ║
║  Auto-Approved:        {total_auto_approved:5}                                  ║
║  Pending Review:       {total_pending:5}                                  ║
║  Errors:               {total_errors:5}                                  ║
║  Time Elapsed:         {elapsed/60:5.1f} minutes                          ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Check domain sizes
    print("\n📊 Domain Sizes After Classification:")
    for domain_info in check_domain_sizes(cursor):
        name = domain_info['domain']
        count = domain_info['skill_count']
        flag = " ⚠️ NEEDS SPLITTING?" if count > 50 else ""
        print(f"  {name}: {count} skills{flag}")
    
    conn.close()


if __name__ == '__main__':
    main()
