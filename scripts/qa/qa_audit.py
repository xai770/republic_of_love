#!/usr/bin/env python3
"""
QA Audit Tool - Unified Quality Assurance for Turing
=====================================================

Implements the 6-dimension sampling strategy:
1. Longest outputs (catch verbosity, hallucination loops)
2. Shortest outputs (catch truncation, failures)
3. Slowest processing (catch performance issues)
4. Fastest processing (catch shortcuts)
5. Most similar pairs (catch copy-paste, templates)
6. Random sample (baseline quality)

All runs are RAQ-compliant:
- Recorded: Creates workflow_run + interactions
- Auditable: Full lineage from finding to source
- Queryable: qa_findings table for easy analysis

Usage:
    # Discovery QA (sample and flag for review)
    python scripts/qa_audit.py discover --target summary --samples 5
    
    # Review pending findings
    python scripts/qa_audit.py review
    
    # Check status
    python scripts/qa_audit.py status
    
    # Re-run checks on specific postings
    python scripts/qa_audit.py check --posting-ids 123,456,789

Author: Arden
Date: December 10, 2025
"""

import sys
import os
import argparse
import hashlib
import json
import random
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from core.text_utils import sanitize_for_storage


class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

load_dotenv()

# Version of the check logic - bump when patterns change
CHECK_VERSION = "2025-12-10-v1"


def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        database=os.getenv('DB_NAME', 'turing'),
        user=os.getenv('DB_USER', 'base_admin'),
        password=os.getenv('DB_PASSWORD', '')
    )


def compute_hash(text: str) -> str:
    """Compute MD5 hash of text for change detection."""
    if not text:
        return None
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute Jaccard similarity between two texts.
    Returns value between 0 (completely different) and 1 (identical).
    """
    if not text1 or not text2:
        return 0.0
    
    # Tokenize into words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


class QAAudit:
    """Main QA Audit class."""
    
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.run_id = None
        self.workflow_run_id = None
        
    def create_run(self, run_type: str, target_type: str) -> int:
        """Create a new QA run with RAQ compliance."""
        # Create workflow_run for traceability
        self.cur.execute("""
            INSERT INTO workflow_runs (workflow_id, status, started_at)
            VALUES (9999, 'running', NOW())
            RETURNING workflow_run_id
        """)
        self.workflow_run_id = self.cur.fetchone()['workflow_run_id']
        
        # Create qa_run linked to workflow_run
        self.cur.execute("""
            INSERT INTO qa_runs (run_type, check_version, target_type, workflow_run_id, status)
            VALUES (%s, %s, %s, %s, 'running')
            RETURNING run_id
        """, (run_type, CHECK_VERSION, target_type, self.workflow_run_id))
        self.run_id = self.cur.fetchone()['run_id']
        
        self.conn.commit()
        return self.run_id
    
    def create_interaction(self, input_data: dict, output_data: dict, posting_id: int = None) -> int:
        """Create an interaction for RAQ audit trail."""
        self.cur.execute("""
            INSERT INTO interactions (
                workflow_run_id,
                conversation_id,
                actor_id,
                actor_type,
                execution_order,
                input,
                output,
                status,
                created_at,
                completed_at
            ) VALUES (
                %s,
                9999,  -- QA conversation placeholder
                152,   -- QA Auditor actor
                'script',
                1,
                %s,
                %s,
                'completed',
                NOW(),
                NOW()
            )
            RETURNING interaction_id
        """, (
            self.workflow_run_id,
            json.dumps(input_data, cls=DecimalEncoder),
            json.dumps(output_data, cls=DecimalEncoder)
        ))
        interaction_id = self.cur.fetchone()['interaction_id']
        self.conn.commit()
        return interaction_id
    
    def add_finding(self, posting_id: int, check_type: str, severity: str,
                    description: str, evidence: str, field_checked: str,
                    data_hash: str, source_interaction_id: int,
                    pattern_matched: str = None, metric_value: float = None):
        """Add a QA finding with full traceability."""
        self.cur.execute("""
            INSERT INTO qa_findings (
                posting_id, check_type, severity, description, evidence,
                field_checked, field_length, data_hash, check_version,
                qa_run_id, source_interaction_id, pattern_matched, metric_value,
                status, detected_by
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                'open', 'qa_audit.py'
            )
            RETURNING finding_id
        """, (
            posting_id, check_type, severity, description, evidence[:1000] if evidence else None,
            field_checked, len(evidence) if evidence else 0, data_hash, CHECK_VERSION,
            self.run_id, source_interaction_id, pattern_matched, metric_value
        ))
        finding_id = self.cur.fetchone()['finding_id']
        self.conn.commit()
        return finding_id
    
    def complete_run(self, items_checked: int, samples_generated: int, findings_count: int):
        """Mark run as completed."""
        self.cur.execute("""
            UPDATE qa_runs 
            SET status = 'completed', 
                completed_at = NOW(),
                items_checked = %s,
                samples_generated = %s,
                findings_count = %s
            WHERE run_id = %s
        """, (items_checked, samples_generated, findings_count, self.run_id))
        
        self.cur.execute("""
            UPDATE workflow_runs 
            SET status = 'completed', 
                completed_at = NOW()
            WHERE workflow_run_id = %s
        """, (self.workflow_run_id,))
        
        self.conn.commit()

    def discover_summaries(self, n_samples: int = 5):
        """
        Run discovery QA on job summaries using 6-dimension sampling.
        
        Samples:
        - n longest summaries
        - n shortest summaries  
        - n slowest processing times
        - n fastest processing times
        - n most similar pairs
        - n random
        """
        print(f"\n{'='*60}")
        print(f"QA DISCOVERY: Job Summaries")
        print(f"Check version: {CHECK_VERSION}")
        print(f"Samples per dimension: {n_samples}")
        print(f"{'='*60}\n")
        
        self.create_run('discovery', 'summary')
        
        # Get all summaries with processing time (compute from completed_at - started_at)
        # Only include non-invalidated postings
        self.cur.execute("""
            SELECT 
                p.posting_id,
                p.job_title,
                p.extracted_summary,
                LENGTH(p.extracted_summary) as summary_length,
                EXTRACT(EPOCH FROM (i.completed_at - i.started_at)) * 1000 as latency_ms
            FROM postings p
            LEFT JOIN interactions i ON i.input->>'posting_id' = p.posting_id::text
                AND i.conversation_id IN (SELECT conversation_id FROM conversations WHERE conversation_name LIKE '%Summary%')
                AND i.status = 'completed'
            WHERE p.extracted_summary IS NOT NULL
              AND (p.invalidated = FALSE OR p.invalidated IS NULL)
            ORDER BY p.posting_id
        """)
        postings = self.cur.fetchall()
        
        if not postings:
            print("❌ No postings with summaries found")
            return
        
        print(f"📊 Total postings with summaries: {len(postings)}")
        
        samples = set()
        findings_count = 0
        
        # 1. LONGEST summaries
        print(f"\n🔍 Sampling {n_samples} LONGEST summaries...")
        longest = sorted(postings, key=lambda x: x['summary_length'] or 0, reverse=True)[:n_samples]
        for p in longest:
            samples.add(p['posting_id'])
            data_hash = compute_hash(p['extracted_summary'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'longest'},
                {'summary_length': p['summary_length'], 'check': 'length_outlier'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='info',
                description=f"LONGEST: {p['summary_length']} chars - {p['job_title'][:50]}",
                evidence=p['extracted_summary'][:500],
                field_checked='extracted_summary',
                data_hash=data_hash,
                source_interaction_id=interaction_id,
                pattern_matched='sample_longest',
                metric_value=p['summary_length']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: {p['summary_length']} chars")
        
        # 2. SHORTEST summaries
        print(f"\n🔍 Sampling {n_samples} SHORTEST summaries...")
        shortest = sorted(postings, key=lambda x: x['summary_length'] or 999999)[:n_samples]
        for p in shortest:
            samples.add(p['posting_id'])
            data_hash = compute_hash(p['extracted_summary'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'shortest'},
                {'summary_length': p['summary_length'], 'check': 'length_outlier'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='medium' if p['summary_length'] < 200 else 'info',
                description=f"SHORTEST: {p['summary_length']} chars - {p['job_title'][:50]}",
                evidence=p['extracted_summary'][:500],
                field_checked='extracted_summary',
                data_hash=data_hash,
                source_interaction_id=interaction_id,
                pattern_matched='sample_shortest',
                metric_value=p['summary_length']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: {p['summary_length']} chars")
        
        # 3. SLOWEST processing
        print(f"\n🔍 Sampling {n_samples} SLOWEST processing times...")
        with_latency = [p for p in postings if p['latency_ms']]
        if with_latency:
            slowest = sorted(with_latency, key=lambda x: x['latency_ms'], reverse=True)[:n_samples]
            for p in slowest:
                samples.add(p['posting_id'])
                data_hash = compute_hash(p['extracted_summary'])
                interaction_id = self.create_interaction(
                    {'posting_id': p['posting_id'], 'sample_type': 'slowest'},
                    {'latency_ms': p['latency_ms'], 'check': 'processing_time'}
                )
                self.add_finding(
                    posting_id=p['posting_id'],
                    check_type='processing_time_outlier',
                    severity='info',
                    description=f"SLOWEST: {p['latency_ms']}ms - {p['job_title'][:50]}",
                    evidence=p['extracted_summary'][:500],
                    field_checked='extracted_summary',
                    data_hash=data_hash,
                    source_interaction_id=interaction_id,
                    pattern_matched='sample_slowest',
                    metric_value=p['latency_ms']
                )
                findings_count += 1
                print(f"   #{p['posting_id']}: {p['latency_ms']}ms")
        else:
            print("   (no latency data available)")
        
        # 4. FASTEST processing
        print(f"\n🔍 Sampling {n_samples} FASTEST processing times...")
        if with_latency:
            fastest = sorted(with_latency, key=lambda x: x['latency_ms'])[:n_samples]
            for p in fastest:
                samples.add(p['posting_id'])
                data_hash = compute_hash(p['extracted_summary'])
                interaction_id = self.create_interaction(
                    {'posting_id': p['posting_id'], 'sample_type': 'fastest'},
                    {'latency_ms': p['latency_ms'], 'check': 'processing_time'}
                )
                self.add_finding(
                    posting_id=p['posting_id'],
                    check_type='processing_time_outlier',
                    severity='info',
                    description=f"FASTEST: {p['latency_ms']}ms - {p['job_title'][:50]}",
                    evidence=p['extracted_summary'][:500],
                    field_checked='extracted_summary',
                    data_hash=data_hash,
                    source_interaction_id=interaction_id,
                    pattern_matched='sample_fastest',
                    metric_value=p['latency_ms']
                )
                findings_count += 1
                print(f"   #{p['posting_id']}: {p['latency_ms']}ms")
        else:
            print("   (no latency data available)")
        
        # 5. MOST SIMILAR pairs
        print(f"\n🔍 Finding {n_samples} MOST SIMILAR pairs...")
        # Sample subset for similarity (full O(n²) too expensive)
        sample_for_sim = random.sample(postings, min(200, len(postings)))
        similarities = []
        
        for i, p1 in enumerate(sample_for_sim):
            for p2 in sample_for_sim[i+1:]:
                sim = compute_similarity(p1['extracted_summary'], p2['extracted_summary'])
                if sim > 0.5:  # Only track high similarity
                    similarities.append((p1, p2, sim))
        
        similarities.sort(key=lambda x: x[2], reverse=True)
        
        for p1, p2, sim in similarities[:n_samples]:
            samples.add(p1['posting_id'])
            samples.add(p2['posting_id'])
            
            interaction_id = self.create_interaction(
                {'posting_ids': [p1['posting_id'], p2['posting_id']], 'sample_type': 'similar'},
                {'similarity': sim, 'check': 'duplicate_detection'}
            )
            
            self.add_finding(
                posting_id=p1['posting_id'],
                check_type='manual_review',
                severity='high' if sim > 0.8 else 'medium',
                description=f"SIMILAR ({sim:.0%}): #{p1['posting_id']} ↔ #{p2['posting_id']}",
                evidence=f"Job 1: {p1['job_title']}\nJob 2: {p2['job_title']}\n\nSummary 1:\n{p1['extracted_summary'][:300]}",
                field_checked='extracted_summary',
                data_hash=compute_hash(p1['extracted_summary']),
                source_interaction_id=interaction_id,
                pattern_matched='sample_similar',
                metric_value=sim
            )
            findings_count += 1
            print(f"   #{p1['posting_id']} ↔ #{p2['posting_id']}: {sim:.0%} similar")
        
        if not similarities:
            print("   (no high-similarity pairs found)")
        
        # 6. RANDOM sample
        print(f"\n🔍 Sampling {n_samples} RANDOM postings...")
        remaining = [p for p in postings if p['posting_id'] not in samples]
        random_sample = random.sample(remaining, min(n_samples, len(remaining)))
        
        for p in random_sample:
            samples.add(p['posting_id'])
            data_hash = compute_hash(p['extracted_summary'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'random'},
                {'summary_length': p['summary_length'], 'check': 'baseline'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='info',
                description=f"RANDOM: {p['summary_length']} chars - {p['job_title'][:50]}",
                evidence=p['extracted_summary'][:500],
                field_checked='extracted_summary',
                data_hash=data_hash,
                source_interaction_id=interaction_id,
                pattern_matched='sample_random',
                metric_value=p['summary_length']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: {p['job_title'][:40]}")
        
        # Complete the run
        self.complete_run(
            items_checked=len(postings),
            samples_generated=len(samples),
            findings_count=findings_count
        )
        
        print(f"\n{'='*60}")
        print(f"✅ QA Run #{self.run_id} completed")
        print(f"   Items checked: {len(postings)}")
        print(f"   Unique samples: {len(samples)}")
        print(f"   Findings created: {findings_count}")
        print(f"   Workflow run: {self.workflow_run_id}")
        
        # Auto-generate report
        report_path = self.generate_report(run_id=self.run_id)
        
        print(f"\n   Next: python scripts/qa_audit.py review --run {self.run_id}")
        print(f"{'='*60}\n")
        
        return report_path
    
    def discover_skills(self, n_samples: int = 5):
        """
        Run discovery QA on skill_keywords using 6-dimension sampling.
        
        Samples:
        - n with most skills
        - n with fewest skills
        - n with highest average weight
        - n with lowest average weight
        - n most similar skill sets
        - n random
        """
        print(f"\n{'='*60}")
        print(f"QA DISCOVERY: Skills Keywords")
        print(f"Check version: {CHECK_VERSION}")
        print(f"Samples per dimension: {n_samples}")
        print(f"{'='*60}\n")
        
        self.create_run('discovery', 'skills')
        
        # Get all postings with skills
        self.cur.execute("""
            SELECT 
                p.posting_id,
                p.job_title,
                p.skill_keywords,
                jsonb_array_length(p.skill_keywords) as skill_count
            FROM postings p
            WHERE p.skill_keywords IS NOT NULL
              AND jsonb_array_length(p.skill_keywords) > 0
              AND (p.invalidated = FALSE OR p.invalidated IS NULL)
            ORDER BY p.posting_id
        """)
        postings = self.cur.fetchall()
        
        if not postings:
            print("❌ No postings with skills found")
            return
        
        print(f"📊 Total postings with skills: {len(postings)}")
        
        # Calculate average weight for each posting
        for p in postings:
            skills = p['skill_keywords']
            if skills:
                weights = [s.get('weight', 0) for s in skills if isinstance(s, dict)]
                p['avg_weight'] = sum(weights) / len(weights) if weights else 0
                p['skill_names'] = [s.get('name', 'unknown') for s in skills if isinstance(s, dict)]
            else:
                p['avg_weight'] = 0
                p['skill_names'] = []
        
        samples = set()
        findings_count = 0
        
        # 1. MOST skills
        print(f"\n🔍 Sampling {n_samples} with MOST skills...")
        most = sorted(postings, key=lambda x: x['skill_count'] or 0, reverse=True)[:n_samples]
        for p in most:
            samples.add(p['posting_id'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'most_skills'},
                {'skill_count': p['skill_count'], 'check': 'skill_count_outlier'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='info',
                description=f"MOST SKILLS: {p['skill_count']} skills - {p['job_title'][:50]}",
                evidence=json.dumps(p['skill_names'][:10], indent=2),
                field_checked='skill_keywords',
                data_hash=compute_hash(json.dumps(p['skill_keywords'])),
                source_interaction_id=interaction_id,
                pattern_matched='sample_most_skills',
                metric_value=p['skill_count']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: {p['skill_count']} skills")
        
        # 2. FEWEST skills
        print(f"\n🔍 Sampling {n_samples} with FEWEST skills...")
        fewest = sorted(postings, key=lambda x: x['skill_count'] or 999)[:n_samples]
        for p in fewest:
            samples.add(p['posting_id'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'fewest_skills'},
                {'skill_count': p['skill_count'], 'check': 'skill_count_outlier'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='medium' if p['skill_count'] < 3 else 'info',
                description=f"FEWEST SKILLS: {p['skill_count']} skills - {p['job_title'][:50]}",
                evidence=json.dumps(p['skill_names'], indent=2),
                field_checked='skill_keywords',
                data_hash=compute_hash(json.dumps(p['skill_keywords'])),
                source_interaction_id=interaction_id,
                pattern_matched='sample_fewest_skills',
                metric_value=p['skill_count']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: {p['skill_count']} skills")
        
        # 3. HIGHEST average weight
        print(f"\n🔍 Sampling {n_samples} with HIGHEST average weight...")
        highest_weight = sorted(postings, key=lambda x: x['avg_weight'], reverse=True)[:n_samples]
        for p in highest_weight:
            samples.add(p['posting_id'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'highest_weight'},
                {'avg_weight': p['avg_weight'], 'check': 'weight_outlier'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='info',
                description=f"HIGHEST WEIGHT: avg {p['avg_weight']:.1f} - {p['job_title'][:50]}",
                evidence=json.dumps(p['skill_keywords'][:5], indent=2, cls=DecimalEncoder),
                field_checked='skill_keywords',
                data_hash=compute_hash(json.dumps(p['skill_keywords'])),
                source_interaction_id=interaction_id,
                pattern_matched='sample_highest_weight',
                metric_value=p['avg_weight']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: avg weight {p['avg_weight']:.1f}")
        
        # 4. LOWEST average weight
        print(f"\n🔍 Sampling {n_samples} with LOWEST average weight...")
        lowest_weight = sorted(postings, key=lambda x: x['avg_weight'] if x['avg_weight'] > 0 else 999)[:n_samples]
        for p in lowest_weight:
            samples.add(p['posting_id'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'lowest_weight'},
                {'avg_weight': p['avg_weight'], 'check': 'weight_outlier'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='medium' if p['avg_weight'] < 30 else 'info',
                description=f"LOWEST WEIGHT: avg {p['avg_weight']:.1f} - {p['job_title'][:50]}",
                evidence=json.dumps(p['skill_keywords'][:5], indent=2, cls=DecimalEncoder),
                field_checked='skill_keywords',
                data_hash=compute_hash(json.dumps(p['skill_keywords'])),
                source_interaction_id=interaction_id,
                pattern_matched='sample_lowest_weight',
                metric_value=p['avg_weight']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: avg weight {p['avg_weight']:.1f}")
        
        # 5. MOST SIMILAR skill sets (by skill name overlap)
        print(f"\n🔍 Finding {n_samples} MOST SIMILAR skill sets...")
        sample_for_sim = random.sample(postings, min(200, len(postings)))
        similarities = []
        
        for i, p1 in enumerate(sample_for_sim):
            for p2 in sample_for_sim[i+1:]:
                # Jaccard similarity on skill names
                set1 = set(p1['skill_names'])
                set2 = set(p2['skill_names'])
                if set1 and set2:
                    intersection = len(set1 & set2)
                    union = len(set1 | set2)
                    sim = intersection / union if union > 0 else 0
                    if sim > 0.5:
                        similarities.append((p1, p2, sim))
        
        similarities.sort(key=lambda x: x[2], reverse=True)
        
        for p1, p2, sim in similarities[:n_samples]:
            samples.add(p1['posting_id'])
            samples.add(p2['posting_id'])
            
            interaction_id = self.create_interaction(
                {'posting_ids': [p1['posting_id'], p2['posting_id']], 'sample_type': 'similar_skills'},
                {'similarity': sim, 'check': 'duplicate_skills'}
            )
            
            common_skills = list(set(p1['skill_names']) & set(p2['skill_names']))
            self.add_finding(
                posting_id=p1['posting_id'],
                check_type='manual_review',
                severity='high' if sim > 0.8 else 'medium',
                description=f"SIMILAR SKILLS ({sim:.0%}): #{p1['posting_id']} ↔ #{p2['posting_id']}",
                evidence=f"Job 1: {p1['job_title']}\nJob 2: {p2['job_title']}\n\nCommon skills: {common_skills}",
                field_checked='skill_keywords',
                data_hash=compute_hash(json.dumps(p1['skill_keywords'])),
                source_interaction_id=interaction_id,
                pattern_matched='sample_similar_skills',
                metric_value=sim
            )
            findings_count += 1
            print(f"   #{p1['posting_id']} ↔ #{p2['posting_id']}: {sim:.0%} similar ({len(common_skills)} common)")
        
        if not similarities:
            print("   (no high-similarity pairs found)")
        
        # 6. RANDOM sample
        print(f"\n🔍 Sampling {n_samples} RANDOM postings...")
        remaining = [p for p in postings if p['posting_id'] not in samples]
        random_sample = random.sample(remaining, min(n_samples, len(remaining)))
        
        for p in random_sample:
            samples.add(p['posting_id'])
            interaction_id = self.create_interaction(
                {'posting_id': p['posting_id'], 'sample_type': 'random'},
                {'skill_count': p['skill_count'], 'check': 'baseline'}
            )
            self.add_finding(
                posting_id=p['posting_id'],
                check_type='manual_review',
                severity='info',
                description=f"RANDOM: {p['skill_count']} skills - {p['job_title'][:50]}",
                evidence=json.dumps(p['skill_names'], indent=2),
                field_checked='skill_keywords',
                data_hash=compute_hash(json.dumps(p['skill_keywords'])),
                source_interaction_id=interaction_id,
                pattern_matched='sample_random',
                metric_value=p['skill_count']
            )
            findings_count += 1
            print(f"   #{p['posting_id']}: {p['job_title'][:40]}")
        
        # Complete the run
        self.complete_run(
            items_checked=len(postings),
            samples_generated=len(samples),
            findings_count=findings_count
        )
        
        print(f"\n{'='*60}")
        print(f"✅ QA Run #{self.run_id} completed")
        print(f"   Items checked: {len(postings)}")
        print(f"   Unique samples: {len(samples)}")
        print(f"   Findings created: {findings_count}")
        print(f"   Workflow run: {self.workflow_run_id}")
        
        # Auto-generate report
        report_path = self.generate_report(run_id=self.run_id)
        
        print(f"\n   Next: python scripts/qa_audit.py review --run {self.run_id}")
        print(f"{'='*60}\n")
        
        return report_path

    def show_status(self):
        """Show QA status summary."""
        print(f"\n{'='*60}")
        print("QA STATUS")
        print(f"{'='*60}\n")
        
        # Recent runs
        self.cur.execute("""
            SELECT run_id, run_type, target_type, status, 
                   items_checked, findings_count, started_at::date
            FROM qa_runs
            ORDER BY run_id DESC
            LIMIT 10
        """)
        runs = self.cur.fetchall()
        
        print("📋 Recent QA Runs:")
        if runs:
            for r in runs:
                print(f"   #{r['run_id']}: {r['run_type']}/{r['target_type']} - {r['status']} "
                      f"({r['findings_count']} findings) - {r['started_at']}")
        else:
            print("   (no runs yet)")
        
        # Open findings by type
        self.cur.execute("""
            SELECT check_type, severity, COUNT(*) as count
            FROM qa_findings
            WHERE status = 'open'
            GROUP BY check_type, severity
            ORDER BY count DESC
        """)
        findings = self.cur.fetchall()
        
        print(f"\n📊 Open Findings:")
        if findings:
            for f in findings:
                print(f"   {f['check_type']}/{f['severity']}: {f['count']}")
        else:
            print("   (no open findings)")
        
        # Total counts
        self.cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM qa_findings WHERE status = 'open') as open,
                (SELECT COUNT(*) FROM qa_findings WHERE status = 'reviewed_valid') as reviewed_valid,
                (SELECT COUNT(*) FROM qa_findings WHERE status IN ('remediation_queued', 'remediation_applied', 'reprocessing')) as in_remediation,
                (SELECT COUNT(*) FROM qa_findings WHERE status = 'archived_stale') as stale
        """)
        counts = self.cur.fetchone()
        
        print(f"\n📈 Totals:")
        print(f"   Open: {counts['open']}")
        print(f"   Reviewed (valid): {counts['reviewed_valid']}")
        print(f"   In remediation: {counts['in_remediation']}")
        print(f"   Archived (stale): {counts['stale']}")
        print()
    
    def review_findings(self, run_id: int = None, limit: int = 10):
        """Interactive review of findings."""
        query = """
            SELECT f.finding_id, f.posting_id, f.check_type, f.severity,
                   f.description, f.evidence, f.pattern_matched, f.metric_value,
                   p.job_title
            FROM qa_findings f
            JOIN postings p ON f.posting_id = p.posting_id
            WHERE f.status = 'open'
        """
        params = []
        
        if run_id:
            query += " AND f.qa_run_id = %s"
            params.append(run_id)
        
        query += " ORDER BY f.severity DESC, f.finding_id LIMIT %s"
        params.append(limit)
        
        self.cur.execute(query, params)
        findings = self.cur.fetchall()
        
        print(f"\n{'='*60}")
        print(f"QA REVIEW - {len(findings)} findings")
        print(f"{'='*60}\n")
        
        for f in findings:
            print(f"{'─'*60}")
            print(f"Finding #{f['finding_id']} [{f['severity'].upper()}]")
            print(f"Posting: #{f['posting_id']} - {f['job_title'][:50]}")
            print(f"Type: {f['check_type']} / {f['pattern_matched']}")
            print(f"Description: {f['description']}")
            if f['metric_value']:
                print(f"Metric: {f['metric_value']}")
            print(f"\nEvidence:\n{f['evidence'][:400]}...")
            print()

    def remediate_findings(self, finding_id: int = None, run_id: int = None, action: str = 'classify'):
        """
        Remediate findings via proper workflow.
        
        Actions:
        - classify: Analyze and classify each finding's root cause
        - fix: Queue fixes via appropriate workflows
        - dismiss: Mark false positives as reviewed_valid
        """
        # Create remediation workflow run
        self.cur.execute("""
            INSERT INTO workflow_runs (workflow_id, status, started_at)
            VALUES (9000, 'running', NOW())
            RETURNING workflow_run_id
        """)
        rem_workflow_run_id = self.cur.fetchone()['workflow_run_id']
        self.conn.commit()
        
        # Get findings to remediate
        query = """
            SELECT f.finding_id, f.posting_id, f.check_type, f.severity,
                   f.description, f.pattern_matched, f.metric_value,
                   p.job_title, p.extracted_summary, p.job_description
            FROM qa_findings f
            JOIN postings p ON f.posting_id = p.posting_id
            WHERE f.status = 'open'
        """
        params = []
        
        if finding_id:
            query += " AND f.finding_id = %s"
            params.append(finding_id)
        elif run_id:
            query += " AND f.qa_run_id = %s"
            params.append(run_id)
        
        self.cur.execute(query, params)
        findings = self.cur.fetchall()
        
        print(f"\n{'='*60}")
        print(f"QA REMEDIATION - {len(findings)} findings")
        print(f"Workflow Run: {rem_workflow_run_id}")
        print(f"Action: {action}")
        print(f"{'='*60}\n")
        
        classified = {'encoding': [], 'hallucination': [], 'false_positive': [], 'needs_review': []}
        
        for f in findings:
            # Classify the finding
            classification = self._classify_finding(f)
            classified[classification].append(f)
            
            # Record classification interaction
            self.cur.execute("""
                INSERT INTO interactions (
                    workflow_run_id, conversation_id, actor_id, actor_type,
                    execution_order, input, output, status, created_at, completed_at
                ) VALUES (
                    %s, 9999, 152, 'script', 1,
                    %s, %s, 'completed', NOW(), NOW()
                )
            """, (
                rem_workflow_run_id,
                json.dumps({'finding_id': f['finding_id'], 'action': 'classify'}, cls=DecimalEncoder),
                json.dumps({'classification': classification, 'reason': self._get_classification_reason(f, classification)}, cls=DecimalEncoder)
            ))
        
        self.conn.commit()
        
        # Report
        print("📊 Classification Results:")
        for cls, items in classified.items():
            if items:
                print(f"\n   {cls.upper()} ({len(items)}):")
                for item in items[:5]:
                    print(f"      #{item['finding_id']}: {item['job_title'][:40]}")
        
        if action == 'fix':
            self._apply_fixes(classified, rem_workflow_run_id)
        elif action == 'dismiss':
            self._dismiss_false_positives(classified['false_positive'], rem_workflow_run_id)
        
        # Complete workflow run
        self.cur.execute("""
            UPDATE workflow_runs SET status = 'completed', completed_at = NOW()
            WHERE workflow_run_id = %s
        """, (rem_workflow_run_id,))
        self.conn.commit()
        
        print(f"\n✅ Remediation complete. Workflow run: {rem_workflow_run_id}")
    
    def _classify_finding(self, finding: dict) -> str:
        """Classify a finding into remediation categories."""
        desc = finding['description'] or ''
        pattern = finding['pattern_matched'] or ''
        summary = finding['extracted_summary'] or ''
        job_desc = finding['job_description'] or ''
        
        # Check for encoding issues
        if 'Ã' in summary or '\\u00' in summary:
            return 'encoding'
        
        # Check for hallucination (expansion ratio > 200%)
        if job_desc and summary:
            expansion = len(summary) / max(len(job_desc), 1) * 100
            if expansion > 200:
                return 'hallucination'
        
        # Similar postings with different external IDs are usually false positives
        if 'SIMILAR' in desc:
            # These are often legitimate - same role, different openings
            return 'false_positive'
        
        # Processing time outliers are usually just informational
        if 'processing_time' in finding['check_type']:
            return 'false_positive'
        
        return 'needs_review'
    
    def _get_classification_reason(self, finding: dict, classification: str) -> str:
        """Get reason for classification."""
        if classification == 'encoding':
            return 'UTF-8 encoding issue detected in summary (mojibake characters)'
        elif classification == 'hallucination':
            summary = finding['extracted_summary'] or ''
            job_desc = finding['job_description'] or ''
            ratio = len(summary) / max(len(job_desc), 1) * 100
            return f'Expansion ratio {ratio:.0f}% exceeds 200% threshold'
        elif classification == 'false_positive':
            if 'SIMILAR' in (finding['description'] or ''):
                return 'Similar postings are distinct job openings (different external IDs)'
            return 'Processing time variance is within acceptable bounds'
        return 'Requires manual review'
    
    def _apply_fixes(self, classified: dict, workflow_run_id: int):
        """Apply fixes for classified issues."""
        print("\n🔧 Applying fixes...")
        
        # For hallucinations: queue re-summarization
        for f in classified['hallucination']:
            self.cur.execute("""
                UPDATE qa_findings 
                SET status = 'remediation_queued',
                    resolution_notes = 'Queued for re-summarization via WF3001'
                WHERE finding_id = %s
            """, (f['finding_id'],))
            print(f"   #{f['finding_id']}: Queued for re-summarization")
            
            # Clear the bad summary so it gets re-processed
            self.cur.execute("""
                UPDATE postings 
                SET extracted_summary = NULL
                WHERE posting_id = %s
            """, (f['posting_id'],))
        
        # For encoding: fix in place using shared utility and queue re-summarization
        for f in classified['encoding']:
            # Get current job_description, fix it with shared utility, save back
            self.cur.execute("SELECT job_description FROM postings WHERE posting_id = %s", (f['posting_id'],))
            row = self.cur.fetchone()
            if row and row['job_description']:
                fixed_desc = sanitize_for_storage(row['job_description'])
                self.cur.execute("""
                    UPDATE postings 
                    SET job_description = %s,
                        extracted_summary = NULL
                    WHERE posting_id = %s
                """, (fixed_desc, f['posting_id']))
            
            self.cur.execute("""
                UPDATE qa_findings 
                SET status = 'remediation_applied',
                    resolution_notes = 'Encoding fixed in job_description, summary cleared for re-processing',
                    resolved_at = NOW()
                WHERE finding_id = %s
            """, (f['finding_id'],))
            print(f"   #{f['finding_id']}: Encoding fixed, queued for re-summarization")
        
        self.conn.commit()
    
    def _dismiss_false_positives(self, findings: list, workflow_run_id: int):
        """Dismiss false positive findings."""
        print("\n✓ Dismissing false positives...")
        
        for f in findings:
            self.cur.execute("""
                UPDATE qa_findings 
                SET status = 'reviewed_valid',
                    resolution_notes = 'Dismissed as false positive via remediation workflow',
                    resolved_at = NOW()
                WHERE finding_id = %s
            """, (f['finding_id'],))
            print(f"   #{f['finding_id']}: Marked as reviewed_valid")
        
        self.conn.commit()
    
    def generate_report(self, run_id: int = None, output_path: str = None) -> str:
        """
        Generate a markdown report for a QA run.
        
        Similar to trace reports - shows all selected records with full details.
        """
        # Get run info
        if not run_id:
            self.cur.execute("""
                SELECT run_id FROM qa_runs 
                ORDER BY run_id DESC LIMIT 1
            """)
            row = self.cur.fetchone()
            if not row:
                print("❌ No QA runs found")
                return None
            run_id = row['run_id']
        
        self.cur.execute("""
            SELECT r.*, wr.workflow_run_id, wr.started_at as wf_started, wr.completed_at as wf_completed
            FROM qa_runs r
            LEFT JOIN workflow_runs wr ON r.workflow_run_id = wr.workflow_run_id
            WHERE r.run_id = %s
        """, (run_id,))
        run = self.cur.fetchone()
        
        if not run:
            print(f"❌ Run #{run_id} not found")
            return None
        
        # Get all findings for this run with full posting data
        # Only include non-invalidated postings
        self.cur.execute("""
            SELECT 
                f.finding_id, f.posting_id, f.check_type, f.severity,
                f.description, f.evidence, f.pattern_matched, f.metric_value,
                f.status, f.data_hash, f.detected_at,
                p.posting_name, p.enabled, p.job_title, p.job_description,
                p.location_city, p.location_country,
                p.source, p.ihl_score, p.external_job_id, p.external_url,
                p.posting_status, p.extracted_summary,
                LENGTH(p.job_description) as desc_length,
                LENGTH(p.extracted_summary) as summary_length
            FROM qa_findings f
            JOIN postings p ON f.posting_id = p.posting_id
            WHERE f.qa_run_id = %s
              AND (p.invalidated = FALSE OR p.invalidated IS NULL)
            ORDER BY f.pattern_matched, f.metric_value DESC NULLS LAST
        """, (run_id,))
        findings = self.cur.fetchall()
        
        # Build report
        now = datetime.now()
        report_lines = []
        
        report_lines.append("# QA Discovery Report\n")
        report_lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        report_lines.append("\n## Run Context\n")
        report_lines.append(f"**Run ID:** {run['run_id']}")
        report_lines.append(f"**Run Type:** {run['run_type']}")
        report_lines.append(f"**Target Type:** {run['target_type']}")
        report_lines.append(f"**Check Version:** {run['check_version']}")
        report_lines.append(f"**Status:** {run['status']}")
        report_lines.append(f"**Started:** {run['started_at']}")
        report_lines.append(f"**Completed:** {run.get('completed_at', 'N/A')}")
        report_lines.append(f"**Workflow Run ID:** {run.get('workflow_run_id', 'N/A')}")
        report_lines.append(f"**Items Checked:** {run['items_checked']}")
        report_lines.append(f"**Findings Created:** {run['findings_count']}")
        
        # Stats summary
        report_lines.append("\n---\n")
        report_lines.append("\n## Sampling Statistics\n")
        
        by_pattern = {}
        by_severity = {}
        for f in findings:
            pat = f['pattern_matched'] or 'unknown'
            by_pattern[pat] = by_pattern.get(pat, 0) + 1
            sev = f['severity']
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        report_lines.append("\n### By Sample Type\n")
        report_lines.append("| Sample Type | Count |")
        report_lines.append("|-------------|-------|")
        for pat, count in sorted(by_pattern.items()):
            report_lines.append(f"| {pat} | {count} |")
        
        report_lines.append("\n### By Severity\n")
        report_lines.append("| Severity | Count |")
        report_lines.append("|----------|-------|")
        for sev, count in sorted(by_severity.items()):
            report_lines.append(f"| {sev} | {count} |")
        
        report_lines.append("\n---\n")
        
        # Group findings by pattern for organized display
        grouped = {}
        for f in findings:
            pat = f['pattern_matched'] or 'unknown'
            if pat not in grouped:
                grouped[pat] = []
            grouped[pat].append(f)
        
        sample_type_titles = {
            'sample_longest': '📏 LONGEST Summaries',
            'sample_shortest': '📐 SHORTEST Summaries', 
            'sample_slowest': '🐢 SLOWEST Processing',
            'sample_fastest': '⚡ FASTEST Processing',
            'sample_similar': '🔄 MOST SIMILAR Pairs',
            'sample_random': '🎲 RANDOM Samples'
        }
        
        for pattern in ['sample_longest', 'sample_shortest', 'sample_slowest', 
                        'sample_fastest', 'sample_similar', 'sample_random']:
            if pattern not in grouped:
                continue
                
            title = sample_type_titles.get(pattern, pattern)
            report_lines.append(f"\n## {title}\n")
            
            for f in grouped[pattern]:
                report_lines.append(f"\n### Finding #{f['finding_id']} - Posting #{f['posting_id']}\n")
                report_lines.append(f"**Severity:** {f['severity'].upper()}")
                report_lines.append(f"**Status:** {f['status']}")
                if f['metric_value']:
                    metric_name = 'chars' if 'length' in pattern or 'longest' in pattern or 'shortest' in pattern else \
                                  'ms' if 'slow' in pattern or 'fast' in pattern else \
                                  '%' if 'similar' in pattern else ''
                    report_lines.append(f"**Metric:** {f['metric_value']:.1f} {metric_name}")
                
                # Full posting metadata
                report_lines.append("\n#### Posting Metadata\n")
                report_lines.append("| Field | Value |")
                report_lines.append("|-------|-------|")
                report_lines.append(f"| posting_id | {f['posting_id']} |")
                report_lines.append(f"| posting_name | {f['posting_name'] or 'N/A'} |")
                report_lines.append(f"| job_title | {f['job_title'] or 'N/A'} |")
                report_lines.append(f"| enabled | {f['enabled']} |")
                location = f"{f['location_city'] or ''}, {f['location_country'] or ''}".strip(', ')
                report_lines.append(f"| location | {location or 'N/A'} |")
                report_lines.append(f"| source_id | {f['source_id'] or 'N/A'} |")
                report_lines.append(f"| external_job_id | {f['external_job_id'] or 'N/A'} |")
                report_lines.append(f"| external_url | {f['external_url'] or 'N/A'} |")
                report_lines.append(f"| posting_status | {f['posting_status'] or 'N/A'} |")
                report_lines.append(f"| ihl_score | {f['ihl_score'] or 'N/A'} |")
                report_lines.append(f"| skill_keywords | {f['skill_keywords'] or 'N/A'} |")
                report_lines.append(f"| created_by_interaction_id | {f['created_by_interaction_id'] or 'N/A'} |")
                report_lines.append(f"| updated_by_interaction_id | {f['updated_by_interaction_id'] or 'N/A'} |")
                report_lines.append(f"| job_description length | {f['desc_length'] or 0} chars |")
                report_lines.append(f"| extracted_summary length | {f['summary_length'] or 0} chars |")
                
                if f['desc_length'] and f['summary_length']:
                    ratio = (f['summary_length'] / f['desc_length']) * 100
                    report_lines.append(f"| summary/description ratio | {ratio:.1f}% |")
                
                # Job Description (FULL)
                report_lines.append("\n#### Job Description (Full)\n")
                job_desc = f['job_description'] or '(none)'
                report_lines.append("```")
                report_lines.append(job_desc)
                report_lines.append("```")
                
                # Extracted Summary (full)
                report_lines.append("\n#### Extracted Summary\n")
                summary = f['extracted_summary'] or '(none)'
                report_lines.append("```")
                report_lines.append(summary)
                report_lines.append("```")
                
                # Quality indicators
                report_lines.append("\n#### Quality Indicators\n")
                indicators = []
                
                # Check for encoding issues
                if 'Ã' in (summary or '') or 'Ã' in (job_desc or ''):
                    indicators.append("⚠️ **ENCODING ISSUE**: Mojibake characters detected (Ã)")
                
                # Check for hallucination
                if f['desc_length'] and f['summary_length'] and f['summary_length'] > f['desc_length'] * 2:
                    indicators.append(f"⚠️ **POSSIBLE HALLUCINATION**: Summary ({f['summary_length']}) > 2x description ({f['desc_length']})")
                
                # Check for truncation
                if f['summary_length'] and f['summary_length'] < 200:
                    indicators.append(f"⚠️ **POSSIBLY TRUNCATED**: Summary only {f['summary_length']} chars")
                
                # Check for template markers
                if summary and ('===OUTPUT TEMPLATE===' in summary or '[Not specified' in summary):
                    indicators.append("⚠️ **TEMPLATE RESIDUE**: Output template markers present")
                
                if not indicators:
                    indicators.append("✅ No obvious quality issues detected")
                
                for ind in indicators:
                    report_lines.append(f"- {ind}")
                
                report_lines.append("\n---\n")
        
        # Final summary
        report_lines.append("\n## Summary\n")
        report_lines.append(f"- **Total findings:** {len(findings)}")
        report_lines.append(f"- **Unique postings sampled:** {len(set(f['posting_id'] for f in findings))}")
        
        issues = sum(1 for f in findings if f['severity'] in ('high', 'medium'))
        report_lines.append(f"- **High/Medium severity:** {issues}")
        
        report_lines.append(f"\n**Next Steps:**")
        report_lines.append(f"1. Review findings above for quality issues")
        report_lines.append(f"2. Run `python scripts/qa_audit.py remediate --run {run_id} --action classify` to classify issues")
        report_lines.append(f"3. Run `python scripts/qa_audit.py remediate --run {run_id} --action fix` to apply fixes")
        
        report_content = '\n'.join(report_lines)
        
        # Save report
        if not output_path:
            output_path = f"/home/xai/Documents/ty_learn/reports/qa_run_{run_id}.md"
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report_content)
        
        print(f"\n✅ Report generated: {output_path}")
        return output_path
    
    def reprocess_remediated(self, limit: int = 10, dry_run: bool = False):
        """
        Trigger re-processing for postings that had QA issues fixed.
        
        These are postings where:
        - extracted_summary was cleared due to hallucination/encoding fix
        - job_description exists and is valid
        """
        print(f"\n{'='*60}")
        print(f"QA REPROCESS - Postings with cleared summaries")
        print(f"{'='*60}\n")
        
        # Find postings ready for reprocessing
        self.cur.execute("""
            SELECT DISTINCT p.posting_id, p.job_title, 
                   f.finding_id, f.check_type, f.resolution_notes
            FROM postings p
            JOIN qa_findings f ON f.posting_id = p.posting_id
            WHERE p.extracted_summary IS NULL
              AND p.job_description IS NOT NULL
              AND LENGTH(p.job_description) > 100
              AND f.status IN ('remediation_queued', 'remediation_applied')
              AND p.enabled = true
            ORDER BY p.posting_id
            LIMIT %s
        """, (limit,))
        
        postings = self.cur.fetchall()
        
        if not postings:
            print("✅ No postings need reprocessing")
            return
        
        print(f"Found {len(postings)} postings ready for reprocessing:\n")
        
        for p in postings:
            print(f"  #{p['posting_id']}: {p['job_title'][:50]}")
            print(f"     Finding #{p['finding_id']}: {p['check_type']}")
            print(f"     Notes: {(p['resolution_notes'] or '')[:60]}")
            print()
        
        if dry_run:
            print("DRY RUN - no changes made")
            return
        
        # Create workflow runs for each posting
        print(f"\n🔄 Triggering WF3001 re-processing...")
        
        for p in postings:
            # Create a workflow run for this posting
            self.cur.execute("""
                INSERT INTO workflow_runs (workflow_id, posting_id, status, started_at, metadata, environment)
                VALUES (3001, %s, 'running', NOW(), %s, 'prod')
                RETURNING workflow_run_id
            """, (p['posting_id'], json.dumps({'trigger': 'qa_reprocess', 'finding_id': p['finding_id']})))
            
            wf_run_id = self.cur.fetchone()['workflow_run_id']
            
            # Update finding status
            self.cur.execute("""
                UPDATE qa_findings 
                SET status = 'reprocessing',
                    resolution_notes = resolution_notes || E'\nTriggered WF3001 run ' || %s
                WHERE finding_id = %s
            """, (wf_run_id, p['finding_id']))
            
            print(f"  #{p['posting_id']}: Created workflow_run {wf_run_id}")
        
        self.conn.commit()
        
        print(f"\n✅ {len(postings)} workflow runs created")
        print(f"\nNext: Run batch processor to execute pending workflow runs:")
        print(f"  python tools/batch/batch_summary_extractor.py --limit {len(postings)}")
        print(f"\nOr monitor progress:")
        print(f"  python tools/monitoring/_show_3001.py")


def main():
    parser = argparse.ArgumentParser(description='QA Audit Tool for Turing')
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # discover command
    discover_parser = subparsers.add_parser('discover', help='Run discovery QA')
    discover_parser.add_argument('--target', choices=['summary', 'skills', 'ihl'], 
                                 default='summary', help='What to check')
    discover_parser.add_argument('--samples', type=int, default=5,
                                 help='Samples per dimension (default: 5)')
    
    # status command
    subparsers.add_parser('status', help='Show QA status')
    
    # review command
    review_parser = subparsers.add_parser('review', help='Review findings')
    review_parser.add_argument('--run', type=int, help='Specific run ID')
    review_parser.add_argument('--limit', type=int, default=10, help='Max findings to show')
    
    # remediate command
    remediate_parser = subparsers.add_parser('remediate', help='Remediate findings via workflow')
    remediate_parser.add_argument('--finding', type=int, help='Specific finding ID')
    remediate_parser.add_argument('--run', type=int, help='All findings from a run')
    remediate_parser.add_argument('--action', choices=['classify', 'fix', 'dismiss'], 
                                  default='classify', help='Action to take')
    
    # reprocess command - trigger WF3001 for postings with cleared summaries
    reprocess_parser = subparsers.add_parser('reprocess', help='Reprocess postings with remediated findings')
    reprocess_parser.add_argument('--limit', type=int, default=10, help='Max postings to reprocess')
    reprocess_parser.add_argument('--dry-run', action='store_true', help='Show what would be reprocessed')
    
    # report command - generate markdown report for a run
    report_parser = subparsers.add_parser('report', help='Generate markdown report for a QA run')
    report_parser.add_argument('--run', type=int, help='Specific run ID (default: latest)')
    report_parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    conn = get_connection()
    qa = QAAudit(conn)
    
    try:
        if args.command == 'discover':
            if args.target == 'summary':
                qa.discover_summaries(args.samples)
            elif args.target == 'skills':
                qa.discover_skills(args.samples)
            else:
                print(f"Target '{args.target}' not yet implemented")
        
        elif args.command == 'status':
            qa.show_status()
        
        elif args.command == 'review':
            qa.review_findings(run_id=args.run, limit=args.limit)
        
        elif args.command == 'remediate':
            qa.remediate_findings(
                finding_id=args.finding,
                run_id=args.run,
                action=args.action
            )
        
        elif args.command == 'reprocess':
            qa.reprocess_remediated(
                limit=args.limit,
                dry_run=args.dry_run
            )
        
        elif args.command == 'report':
            qa.generate_report(
                run_id=args.run,
                output_path=args.output
            )
    
    finally:
        conn.close()


if __name__ == '__main__':
    main()
