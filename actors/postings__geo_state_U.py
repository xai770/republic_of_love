#!/usr/bin/env python3
"""
postings__geo_state_U.py - Resolve location_state from city name via OWL geography

PURPOSE:
Postings from Arbeitsagentur often arrive with location_city but no location_state.
This actor resolves the Bundesland by looking up the city name in OWL's geography
hierarchy: city → child_of → bundesland.

Input:  postings.location_city (via work_query: WHERE location_state IS NULL AND location_city IS NOT NULL)
Output: postings.location_state

Output Fields:
    - success: bool
    - location_state: str - The resolved Bundesland name
    - method: str - How it was resolved (direct/comma_strip/city_state/already_set)
    - skip_reason: str - Why it was skipped (ambiguous/no_match/empty_city)

Flow:
    1. Look up city in owl_names → find city entity → walk child_of → get bundesland
    2. If no match and city has comma, strip qualifier and retry
    3. Skip ambiguous cities (Neustadt, Buchholz — multiple Bundesländer)
    4. Skip international cities (no German Bundesland in OWL)

PIPELINE POSITION:
    fetch → berufenet → domain_gate → **geo_state** → enrichment
    Runs after domain classification, before description backfill.

Usage:
    # Batch mode (for turing_fetch pipeline):
    python3 actors/postings__geo_state_U.py --batch 10000

    # Single posting:
    python3 actors/postings__geo_state_U.py 12345

    # Dry run (show what would change):
    python3 actors/postings__geo_state_U.py --batch 10000 --dry-run

Author: Arden
Date: 2026-02-13
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import get_connection_raw, return_connection
from core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# WORK QUERY — must match the actor registration in task_types
# ============================================================================
WORK_QUERY = """
    SELECT posting_id, location_city
    FROM postings
    WHERE location_state IS NULL
      AND location_city IS NOT NULL
      AND TRIM(location_city) != ''
      AND COALESCE(invalidated, false) = false
"""

# City-states: these cities ARE their own Bundesland
CITY_STATES = {"Berlin", "Hamburg", "Bremen"}

# GeoNames data file (cleaned, company rows removed)
GEONAMES_FILE = Path(__file__).resolve().parent.parent / "data" / "DE" / "DE.txt"


def _load_geonames() -> Dict[str, str]:
    """
    Load city→state from GeoNames DE.txt (cleaned of company rows).
    
    Skips ambiguous place names (same name in multiple Bundesländer).
    Returns dict mapping place_name (original case) → Bundesland.
    """
    if not GEONAMES_FILE.exists():
        return {}
    
    geo = {}
    ambiguous = set()
    with open(GEONAMES_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 4 or not parts[3].strip():
                continue
            place = parts[2].strip()
            state = parts[3].strip()
            if not place or not state:
                continue
            key = place.lower()
            if key in geo and geo[key] != state:
                ambiguous.add(key)
            else:
                geo[key] = state
    
    for k in ambiguous:
        del geo[k]
    
    return geo


def _load_self_learned(cur) -> Dict[str, str]:
    """
    Build city→state from postings that already have location_state populated.
    
    Picks the state with the most rows per city. Skips 'Sonstiges'.
    Returns dict mapping location_city (original case) → Bundesland.
    """
    cur.execute("""
        SELECT location_city, location_state, COUNT(*) as cnt
        FROM postings
        WHERE location_state IS NOT NULL
          AND location_state != ''
          AND location_state != 'Sonstiges'
          AND location_city IS NOT NULL
          AND location_city != ''
        GROUP BY 1, 2
        ORDER BY 3 DESC
    """)
    
    db_map = {}
    for row in cur.fetchall():
        city = row["location_city"]
        state = row["location_state"]
        cnt = row["cnt"]
        key = city.lower()
        if key not in db_map or cnt > db_map[key][1]:
            db_map[key] = (state, cnt)
    
    return {k: v[0] for k, v in db_map.items()}


def build_city_state_lookup(cur) -> Dict[str, str]:
    """
    Build a city_name → bundesland lookup from three sources (layered):
    
    1. OWL geography hierarchy (most authoritative)
    2. GeoNames DE.txt (13K+ unambiguous German places)
    3. Self-learned from existing postings (matches AA naming conventions)
    
    Later layers override earlier ones, so self-learned (which matches the actual
    AA city naming like "Nürnberg, Mittelfranken") takes priority.
    
    Returns dict mapping city name (lowered) → bundesland canonical_name.
    """
    # Layer 1: OWL
    cur.execute("""
        SELECT n.display_name, state.canonical_name as bundesland
        FROM owl_names n
        JOIN owl city ON city.owl_id = n.owl_id AND city.owl_type = 'city'
        JOIN owl_relationships r ON r.owl_id = city.owl_id AND r.relationship = 'child_of'
        JOIN owl state ON state.owl_id = r.related_owl_id AND state.owl_type = 'bundesland'
        WHERE city.status = 'active'
    """)
    
    from collections import defaultdict
    name_states = defaultdict(set)
    for row in cur.fetchall():
        name_states[row["display_name"].strip().lower()].add(row["bundesland"])
    
    # Only unambiguous OWL mappings
    lookup = {name: list(states)[0] for name, states in name_states.items() if len(states) == 1}
    owl_count = len(lookup)
    
    # Layer 2: GeoNames (fills gaps — especially small towns not in OWL)
    geo = _load_geonames()
    for name, state in geo.items():
        if name not in lookup:
            lookup[name] = state
    geo_added = len(lookup) - owl_count
    
    # Layer 3: Self-learned (overrides — matches actual AA city naming)
    db = _load_self_learned(cur)
    for name, state in db.items():
        lookup[name] = state  # override: DB-learned uses AA naming conventions
    
    logger.info(
        "City→Bundesland lookup: %d OWL + %d GeoNames + %d self-learned = %d total",
        owl_count, geo_added, len(db), len(lookup),
    )
    
    return lookup


def resolve_state(city: str, lookup: Dict[str, str]) -> Tuple[Optional[str], str]:
    """
    Resolve a city name to its Bundesland.
    
    Returns (bundesland, method) where method is one of:
        'direct'      - exact match in OWL
        'comma_strip' - matched after stripping comma qualifier
        'city_state'  - Berlin/Hamburg/Bremen
        None          - no match found (method = 'no_match')
    """
    city_clean = city.strip()
    city_lower = city_clean.lower()
    
    if not city_clean:
        return None, "empty_city"
    
    # Strategy 1: Direct match
    if city_lower in lookup:
        return lookup[city_lower], "direct"
    
    # Strategy 2: City-states
    if city_clean in CITY_STATES:
        return city_clean, "city_state"
    
    # Strategy 3: Comma-strip ("Nürnberg, Mittelfranken" → "Nürnberg")
    if "," in city_clean:
        base = city_clean.split(",")[0].strip().lower()
        if base in lookup:
            return lookup[base], "comma_strip"
    
    return None, "no_match"


def process_batch(batch_size: int = 10000, dry_run: bool = False) -> Dict[str, Any]:
    """Process a batch of postings with NULL location_state."""
    conn = get_connection_raw()
    try:
        cur = conn.cursor()
        
        # Build lookup once (logged inside build_city_state_lookup)
        lookup = build_city_state_lookup(cur)
        
        # Get pending rows
        cur.execute(WORK_QUERY + " LIMIT %s", (batch_size,))
        rows = cur.fetchall()
        
        if not rows:
            print("No postings with NULL location_state remaining")
            return {"success": True, "processed": 0, "message": "No work remaining"}
        
        stats = {"direct": 0, "comma_strip": 0, "city_state": 0, "no_match": 0, "empty_city": 0}
        updates = []
        
        for row in rows:
            posting_id = row["posting_id"]
            city = row["location_city"]
            
            state, method = resolve_state(city, lookup)
            stats[method] += 1
            
            if state:
                updates.append((state, posting_id))
        
        if dry_run:
            print(f"DRY RUN: {len(rows):,} rows checked")
            print(f"  Would update: {len(updates):,}")
            for method, count in sorted(stats.items(), key=lambda x: -x[1]):
                if count > 0:
                    print(f"  {method}: {count:,}")
            return {"success": True, "dry_run": True, "would_update": len(updates), "stats": stats}
        
        # Batch update
        if updates:
            psycopg2.extras.execute_batch(
                cur,
                "UPDATE postings SET location_state = %s WHERE posting_id = %s",
                updates,
                page_size=1000,
            )
            conn.commit()
        
        resolved = len(updates)
        total = len(rows)
        print(f"Geo state resolution: {resolved:,}/{total:,} resolved "
              f"(direct={stats['direct']}, comma={stats['comma_strip']}, "
              f"city_state={stats['city_state']}, no_match={stats['no_match']})")
        
        return {
            "success": True,
            "processed": total,
            "resolved": resolved,
            "no_match": stats["no_match"],
            "stats": stats,
        }
    
    except Exception as e:
        conn.rollback()
        logger.error("Geo state resolution failed: %s", e)
        raise
    finally:
        return_connection(conn)


def process_single(posting_id: int) -> Dict[str, Any]:
    """Process a single posting."""
    conn = get_connection_raw()
    try:
        cur = conn.cursor()
        
        cur.execute(
            "SELECT posting_id, location_city, location_state FROM postings WHERE posting_id = %s",
            (posting_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"Posting {posting_id} not found"}
        
        if row["location_state"]:
            return {"success": True, "method": "already_set",
                    "location_state": row["location_state"]}
        
        if not row["location_city"]:
            return {"success": False, "skip_reason": "no_city"}
        
        lookup = build_city_state_lookup(cur)
        state, method = resolve_state(row["location_city"], lookup)
        
        if state:
            cur.execute(
                "UPDATE postings SET location_state = %s WHERE posting_id = %s",
                (state, posting_id),
            )
            conn.commit()
            return {"success": True, "location_state": state, "method": method}
        else:
            return {"success": False, "skip_reason": method,
                    "city": row["location_city"]}
    
    except Exception as e:
        conn.rollback()
        logger.error("Geo state resolution failed for posting %s: %s", posting_id, e)
        raise
    finally:
        return_connection(conn)


# ============================================================================
# THICK ACTOR CLASS (for turing_daemon compatibility)
# ============================================================================
class GeoStateResolver:
    """Thick actor interface for turing_daemon."""
    
    def __init__(self, db_conn=None):
        self.conn = db_conn or get_connection_raw()
        self._owns_conn = db_conn is None
        self.input_data: Dict[str, Any] = {}
        self._lookup = None
    
    def _get_lookup(self):
        if self._lookup is None:
            cur = self.conn.cursor()
            self._lookup = build_city_state_lookup(cur)
        return self._lookup
    
    def process(self) -> Dict[str, Any]:
        posting_id = self.input_data.get("subject_id") or self.input_data.get("posting_id")
        if not posting_id:
            return {"success": False, "error": "No subject_id in input"}
        
        cur = self.conn.cursor()
        cur.execute(
            "SELECT location_city, location_state FROM postings WHERE posting_id = %s",
            (posting_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"Posting {posting_id} not found"}
        
        if row["location_state"]:
            return {"success": True, "method": "already_set",
                    "location_state": row["location_state"]}
        
        if not row["location_city"] or not row["location_city"].strip():
            return {"success": False, "skip_reason": "empty_city"}
        
        lookup = self._get_lookup()
        state, method = resolve_state(row["location_city"], lookup)
        
        if state:
            cur.execute(
                "UPDATE postings SET location_state = %s WHERE posting_id = %s",
                (state, posting_id),
            )
            self.conn.commit()
            return {"success": True, "location_state": state, "method": method}
        else:
            return {"success": False, "skip_reason": method,
                    "city": row["location_city"]}


# ============================================================================
# CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Resolve location_state from city via OWL")
    parser.add_argument("posting_id", nargs="?", type=int, help="Single posting ID")
    parser.add_argument("--batch", type=int, default=0, help="Batch size (0 = single mode)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    args = parser.parse_args()
    
    if args.batch > 0:
        result = process_batch(args.batch, dry_run=args.dry_run)
    elif args.posting_id:
        result = process_single(args.posting_id)
        print(result)
    else:
        # Default: run full batch
        result = process_batch(50000, dry_run=args.dry_run)
    
    if not result.get("success", False) and not result.get("dry_run"):
        sys.exit(1)


if __name__ == "__main__":
    main()
