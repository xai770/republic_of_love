#!/usr/bin/env python3
"""
Domain Gate Detector - Classifies job postings by domain and restriction level

PURPOSE:
Detects whether a job posting requires regulated credentials (Approbation, Staatsexamen, etc.)
and gates matches accordingly. Uses embedding similarity to classify domain, then pattern
matching to detect restriction evidence.

PREREQUISITE: job_description must exist (via postings_for_matching view)
This actor uses match_text from postings_for_matching because:
  - AA jobs: match_text = job_description (concise, no summary needed)
  - DB jobs: match_text = extracted_summary (strips corporate boilerplate)
  - Single source of truth for "what we match against"

Input:  postings_for_matching.match_text (via work_query where domain_gate IS NULL)
Output: postings.domain_gate (jsonb)

Output Fields:
    - success: bool - Whether processing completed successfully
    - domain: str - Detected domain (healthcare, legal, etc.)
    - gate_decision: str - 'hard' | 'soft' | 'allow'
    - restricted_role: bool - Whether role requires specific credential
    - skip_reason: str - Reason for skipping if not processed
    - error: str - Error message if failed

Flow Diagram (Mermaid):
```mermaid
flowchart TD
    A[📋 Posting] --> B{Has match_text?}
    B -->|No| Z1[⏭️ SKIP: NO_DESCRIPTION]
    B -->|Yes| C[🔄 Stage A: Domain Classification]
    C --> D[🔄 Stage B: Restriction Detection]
    D --> E{Evidence found?}
    E -->|Hard evidence| F[🚫 HARD gate]
    E -->|Soft evidence| G[⚠️ SOFT gate]
    E -->|No evidence| H[✅ ALLOW]
    F --> I[💾 Save domain_gate]
    G --> I
    H --> I
    I --> J[✅ SUCCESS]
```

PIPELINE POSITION:
```
job_description → [extracted_summary] → domain_gate → embeddings → matching
                  (DB only)            [THIS ACTOR]
```

RAQ Config:
- state_tables: postings.domain_gate
- compare_output_field: output->>'gate_decision'

Usage:
    # Via daemon (automatic):
    # Daemon runs work_query: SELECT posting_id FROM postings_for_matching WHERE domain_gate IS NULL
    
    # Manual backfill:
    python3 scripts/domain_gate_batch.py --limit 5000
    
    # Direct test:
    ./tools/turing/turing-harness run postings__domain_gate_U --input '{"posting_id": 123}'
    
    # Standalone:
    python3 actors/postings__domain_gate_U.py 12345
    python3 actors/postings__domain_gate_U.py --test

Author: Arden
Date: 2026-01-28
Task Type ID: 1298
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

import numpy as np
import requests
import psycopg2.extras

# ============================================================================
# SETUP - Standard boilerplate
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection, get_connection_raw, return_connection
from core.constants import Status

# ============================================================================
# CONFIGURATION
# ============================================================================
TASK_TYPE_ID = 1298

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "snowflake-arctic-embed2:latest"

# Classification thresholds
MIN_CONFIDENCE = 0.35  # Below this, domain is "unknown"
MIN_GAP = 0.03         # Gap between 1st and 2nd candidate must be at least this

# Cache for config loaded from OWL (module-level for reuse across instances)
_DOMAIN_CONFIG_CACHE = None


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DetectionResult:
    """Result of domain/restriction detection."""
    domain: str
    domain_confidence: float
    domain_gap: float
    restricted_role: bool
    restriction_evidence: List[str]
    negative_evidence: List[str]
    gate_decision: str  # 'hard', 'soft', 'allow'
    explanation: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# OWL CONFIG LOADER
# ============================================================================

def load_domain_config_from_owl(conn) -> Dict:
    """
    Load domain gate configuration from OWL.
    
    Returns dict with:
      - domain_keywords: {domain: "keyword1 keyword2 ..."}
      - restriction_evidence: {domain: {patterns: [...], negative_patterns: [...], soft_patterns: [...]}}
      - gated_domains: set of domains with gate_type='hard'
    """
    global _DOMAIN_CONFIG_CACHE
    if _DOMAIN_CONFIG_CACHE is not None:
        return _DOMAIN_CONFIG_CACHE
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("""
        SELECT o.canonical_name, o.metadata,
               array_agg(DISTINCT n.display_name) FILTER (WHERE n.display_name IS NOT NULL) as keywords
        FROM owl o
        LEFT JOIN owl_names n ON o.owl_id = n.owl_id AND n.name_type = 'alias'
        WHERE o.owl_type = 'domain_gate' AND o.status = 'active'
        GROUP BY o.owl_id, o.canonical_name, o.metadata
    """)
    
    domain_keywords = {}
    restriction_evidence = {}
    gated_domains = set()
    
    for row in cur.fetchall():
        domain = row['canonical_name']
        metadata = row['metadata'] or {}
        keywords = row['keywords'] or []
        
        domain_keywords[domain] = " ".join(keywords)
        
        if metadata.get('evidence_patterns') or metadata.get('negative_patterns') or metadata.get('soft_patterns'):
            restriction_evidence[domain] = {
                'patterns': metadata.get('evidence_patterns', []),
                'negative_patterns': metadata.get('negative_patterns', []),
                'soft_patterns': metadata.get('soft_patterns', []),
            }
        
        if metadata.get('gate_type') == 'hard':
            gated_domains.add(domain)
    
    _DOMAIN_CONFIG_CACHE = {
        'domain_keywords': domain_keywords,
        'restriction_evidence': restriction_evidence,
        'gated_domains': gated_domains,
    }
    
    return _DOMAIN_CONFIG_CACHE


# ============================================================================
# EMBEDDING HELPERS
# ============================================================================

def get_embedding(text: str) -> Optional[np.ndarray]:
    """Get embedding for text via Ollama."""
    try:
        resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": text}, timeout=60)
        resp.raise_for_status()
        return np.array(resp.json()["embeddings"][0])
    except Exception as e:
        print(f"Embedding error: {e}", file=sys.stderr)
        return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def build_domain_centroids(conn) -> Dict[str, np.ndarray]:
    """Build embedding centroids for each domain (expensive, cache result)."""
    centroids = {}
    config = load_domain_config_from_owl(conn)
    
    for domain, keywords in config['domain_keywords'].items():
        emb = get_embedding(keywords)
        if emb is not None:
            centroids[domain] = emb / np.linalg.norm(emb)
    
    return centroids


# ============================================================================
# DETECTION LOGIC
# ============================================================================

def detect_domain(text: str, centroids: Dict[str, np.ndarray], title: str = None) -> Tuple[str, float, float]:
    """
    Stage A: Detect domain using embedding similarity.
    Title-weighted (60% title, 40% text) per Nate's advice.
    """
    emb_text = get_embedding(text)
    if emb_text is None:
        return "unknown", 0.0, 0.0
    
    if title and len(title.strip()) > 5:
        emb_title = get_embedding(title)
        if emb_title is not None:
            scores_text = [(d, cosine_similarity(emb_text, c)) for d, c in centroids.items()]
            scores_title = [(d, cosine_similarity(emb_title, c)) for d, c in centroids.items()]
            
            scores = []
            for d in centroids.keys():
                text_score = next(s for dom, s in scores_text if dom == d)
                title_score = next(s for dom, s in scores_title if dom == d)
                combined = 0.6 * title_score + 0.4 * text_score
                scores.append((d, combined))
            
            scores.sort(key=lambda x: -x[1])
            best_domain, best_conf = scores[0]
            gap = scores[0][1] - scores[1][1] if len(scores) > 1 else 0.0
            
            if best_conf < MIN_CONFIDENCE or gap < MIN_GAP:
                return "unknown", best_conf, gap
            return best_domain, best_conf, gap
    
    # Fallback: text only
    scores = [(d, cosine_similarity(emb_text, c)) for d, c in centroids.items()]
    scores.sort(key=lambda x: -x[1])
    
    best_domain, best_conf = scores[0]
    gap = scores[0][1] - scores[1][1] if len(scores) > 1 else 0.0
    
    if best_conf < MIN_CONFIDENCE or gap < MIN_GAP:
        return "unknown", best_conf, gap
    return best_domain, best_conf, gap


def detect_restriction_evidence(text: str, domain: str, conn) -> Tuple[List[str], List[str], List[str]]:
    """
    Stage B: Detect restriction evidence using patterns from OWL.
    Returns: (hard_evidence, negative_evidence, soft_evidence)
    """
    text_lower = text.lower()
    config = load_domain_config_from_owl(conn)
    restriction_evidence = config['restriction_evidence']
    
    hard, negative, soft = [], [], []
    
    def check_patterns(patterns_dict: dict, text: str) -> Tuple[List[str], List[str], List[str]]:
        h, n, s = [], [], []
        for pattern in patterns_dict.get("patterns", []):
            if pattern.lower() in text:
                h.append(pattern)
        for pattern in patterns_dict.get("negative_patterns", []):
            if pattern.lower() in text:
                n.append(pattern)
        for pattern in patterns_dict.get("soft_patterns", []):
            if pattern.lower() in text:
                s.append(pattern)
        return h, n, s
    
    if domain in restriction_evidence:
        h, n, s = check_patterns(restriction_evidence[domain], text_lower)
        hard.extend(h)
        negative.extend(n)
        soft.extend(s)
    
    # Safety net: always check healthcare/legal
    for safety_domain in ["healthcare", "legal"]:
        if safety_domain != domain and safety_domain in restriction_evidence:
            h, _, s = check_patterns(restriction_evidence[safety_domain], text_lower)
            hard.extend(h)
            soft.extend(s)
    
    return list(set(hard)), list(set(negative)), list(set(soft))


def classify_posting(text: str, title: str, centroids: Dict[str, np.ndarray], conn) -> DetectionResult:
    """
    Main classification: Domain + Restriction detection.
    
    Decision logic:
    - HARD: hard evidence found, no negative evidence
    - SOFT: gated domain with soft evidence OR unclear role
    - ALLOW: non-gated domain or negative evidence
    """
    domain, confidence, gap = detect_domain(text, centroids, title=title)
    hard_evidence, negative_evidence, soft_evidence = detect_restriction_evidence(text, domain, conn)
    
    config = load_domain_config_from_owl(conn)
    gated_domains = config['gated_domains']
    
    # Decision tree
    if len(hard_evidence) > 0 and len(negative_evidence) == 0:
        gate_decision = "hard"
        explanation = f"Restricted role: {hard_evidence[:3]}"
        restricted_role = True
    elif len(negative_evidence) > 0:
        if domain in gated_domains:
            gate_decision = "soft"
            explanation = f"Domain regulated, role excluded: {negative_evidence[:3]}"
        else:
            gate_decision = "allow"
            explanation = f"Role excluded: {negative_evidence[:3]}"
        restricted_role = False
    elif len(soft_evidence) > 0:
        gate_decision = "soft"
        explanation = f"Vocational role: {soft_evidence[:3]}"
        restricted_role = False
    elif domain in gated_domains:
        gate_decision = "soft"
        explanation = f"Domain '{domain}' regulated - verify credentials"
        restricted_role = False
    else:
        gate_decision = "allow"
        explanation = f"Domain '{domain}' not gated"
        restricted_role = False
    
    all_evidence = hard_evidence + soft_evidence
    
    return DetectionResult(
        domain=domain,
        domain_confidence=round(confidence, 3),
        domain_gap=round(gap, 3),
        restricted_role=restricted_role,
        restriction_evidence=all_evidence[:5],
        negative_evidence=negative_evidence[:5],
        gate_decision=gate_decision,
        explanation=explanation,
    )


# ============================================================================
# ACTOR CLASS
# ============================================================================

class DomainGateDetector:
    """
    Actor for detecting domain gates on job postings.
    
    Three-Phase Structure (per TEMPLATE_actor.py):
    1. PREFLIGHT: Validate input, skip bad data early
    2. PROCESS: Classify domain + detect restriction evidence
    3. QA: Validate output (minimal for deterministic embedding-based classification)
    
    Writes to: postings.domain_gate (jsonb)
    """
    
    def __init__(self, db_conn=None):
        """Initialize with database connection."""
        self.conn = db_conn or get_connection_raw()
        self._owns_conn = db_conn is None  # Track if we need to return it
        self.input_data: Dict[str, Any] = {}
        self._centroids = None  # Lazy-loaded, can be injected for batch processing
    
    def _get_centroids(self):
        """Lazy-load centroids (expensive, so cache them)."""
        if self._centroids is None:
            self._centroids = build_domain_centroids(self.conn)
        return self._centroids
    
    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================
    
    def process(self) -> Dict[str, Any]:
        """
        Main entry point. Called by pull_daemon.
        """
        posting_id = self.input_data.get('posting_id') or self.input_data.get('subject_id')
        
        if not posting_id:
            return {'success': False, 'error': 'No posting_id in input'}
        
        try:
            # ----------------------------------------------------------------
            # PHASE 1: PREFLIGHT
            # ----------------------------------------------------------------
            preflight = self._preflight(posting_id)
            if not preflight['ok']:
                return {
                    'success': False,
                    'skip_reason': preflight['reason'],
                    'error': preflight.get('message', preflight['reason']),
                    'posting_id': posting_id,
                }
            
            data = preflight['data']
            
            # ----------------------------------------------------------------
            # PHASE 2: PROCESS
            # ----------------------------------------------------------------
            title = data['job_title'] or ''
            match_text = data['match_text']
            text = f"{title}\n\n{match_text}"
            
            result = classify_posting(text, title, self._get_centroids(), self.conn)
            
            # ----------------------------------------------------------------
            # PHASE 3: SAVE (no QA needed - deterministic classification)
            # ----------------------------------------------------------------
            gate_data = result.to_dict()
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE postings
                SET domain_gate = %s, updated_at = NOW()
                WHERE posting_id = %s
            """, (json.dumps(gate_data), posting_id))
            self.conn.commit()
            
            return {
                'success': True,
                '_consistency': '1/1',
                'posting_id': posting_id,
                'domain': result.domain,
                'gate_decision': result.gate_decision,
                'restricted_role': result.restricted_role,
            }
            
        except Exception as e:
            self.conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'posting_id': posting_id,
            }
    
    # ========================================================================
    # PHASE 1: PREFLIGHT
    # ========================================================================
    
    def _preflight(self, posting_id: int) -> Dict:
        """Validate input data before processing."""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Use the view that provides match_text
        cur.execute("""
            SELECT posting_id, job_title, match_text, domain_gate
            FROM postings_for_matching
            WHERE posting_id = %s
        """, (posting_id,))
        row = cur.fetchone()
        
        if not row:
            return {'ok': False, 'reason': 'NOT_IN_VIEW', 'message': f'Posting {posting_id} not in postings_for_matching (missing description?)'}
        
        # Idempotency check
        if row['domain_gate'] is not None:
            return {'ok': False, 'reason': 'ALREADY_PROCESSED', 'message': f'Posting {posting_id} already has domain_gate'}
        
        # match_text is guaranteed by view, but double-check
        if not row['match_text'] or len(row['match_text'].strip()) < 50:
            return {'ok': False, 'reason': 'NO_DESCRIPTION', 'message': f'Insufficient match_text'}
        
        return {'ok': True, 'data': row}


# ============================================================================
# STANDALONE CLI
# ============================================================================

def main():
    """
    Test the actor directly.
    
    Usage:
        python3 actors/postings__domain_gate_U.py              # random unprocessed
        python3 actors/postings__domain_gate_U.py 12345        # specific posting_id
        python3 actors/postings__domain_gate_U.py --test       # run test suite
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Domain Gate Detector')
    parser.add_argument('posting_id', nargs='?', type=int, help='Posting ID to process')
    parser.add_argument('--test', action='store_true', help='Run test suite')
    args = parser.parse_args()
    
    conn = get_connection_raw()
    
    if args.test:
        print("Building domain centroids...")
        centroids = build_domain_centroids(conn)
        print(f"Loaded {len(centroids)} domains")
        
        test_cases = [
            ("Facharzt für Kardiologie mit Approbation", "healthcare", "hard"),
            ("Rechtsanwalt (m/w/d) Arbeitsrecht", "legal", "hard"),
            ("Software Engineer Python/Django", "it_software", "allow"),
            ("Legal Secretary for law firm", "legal", "soft"),
        ]
        
        print(f"\n{'='*60}")
        for text, expected_domain, expected_gate in test_cases:
            result = classify_posting(text, text.split()[0], centroids, conn)
            status = "✓" if result.gate_decision == expected_gate else "✗"
            print(f"{status} [{result.gate_decision:5s}] {text[:50]}")
            if result.gate_decision != expected_gate:
                print(f"    Expected: {expected_gate}, Got: {result.gate_decision}")
        print(f"{'='*60}")
        return_connection(conn)
        return
    
    # Process mode
    posting_id = args.posting_id
    
    if not posting_id:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT posting_id FROM postings_for_matching
            WHERE domain_gate IS NULL
            ORDER BY RANDOM()
            LIMIT 1
        """)
        row = cur.fetchone()
        posting_id = row['posting_id'] if row else None
    
    if posting_id:
        actor = DomainGateDetector(conn)
        actor.input_data = {'posting_id': posting_id}
        result = actor.process()
        print(json.dumps(result, indent=2, default=str))
    else:
        print("No unprocessed postings found")
    
    return_connection(conn)


if __name__ == '__main__':
    main()
