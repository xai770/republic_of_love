#!/usr/bin/env python3
"""
One-time migration: Import Berufenet professions into OWL.

Step 1 of the Berufenet → OWL integration plan (2026-02-11).

Creates:
- 3,562 owl entities (owl_type='berufenet')
- owl_names entries: primary name + stripped variants per entity

Idempotent: skips existing entries via ON CONFLICT DO NOTHING.

Usage:
    python3 scripts/import_berufenet_to_owl.py              # Full run
    python3 scripts/import_berufenet_to_owl.py --dry-run     # Preview only
    python3 scripts/import_berufenet_to_owl.py --verify      # Check results
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.database import get_connection


def generate_name_variants(name: str) -> list[str]:
    """
    Generate lookup-friendly variants of a Berufenet profession name.
    
    Examples:
        "Koch/Köchin"
            → ["Koch", "Köchin"]
        "Landwirt/in"
            → ["Landwirt", "Landwirtin"]
        "Metallbauer/in - Konstruktionstechnik"
            → ["Metallbauer - Konstruktionstechnik", "Metallbauerin - Konstruktionstechnik",
               "Metallbauer Konstruktionstechnik"]
        "Medizinisch-technische/r Laboratoriumsassistent/in"
            → ["Medizinisch-technischer Laboratoriumsassistent",
               "Medizinisch-technische Laboratoriumsassistentin"]
    """
    variants = set()
    
    # Pattern 1: "Koch/Köchin" — slash separates male/female full forms
    # Detect: slash where the right side starts with uppercase
    slash_full = re.match(r'^(.+)/([A-ZÄÖÜ].+)$', name)
    if slash_full:
        variants.add(slash_full.group(1).strip())
        variants.add(slash_full.group(2).strip())
    
    # Pattern 1b: "Pflegefachmann/-frau" — slash-hyphen separates genders
    slash_hyph = re.match(r'^(.+?)/(-.+?)(?:\s*\(.*\))?$', name)
    if slash_hyph:
        variants.add(slash_hyph.group(1).strip())  # Pflegefachmann
        # Also strip any parenthetical from the full name
        base_no_parens = re.sub(r'\s*\(.*\)', '', name).strip()
        variants.add(base_no_parens)
    
    # Pattern 1c: "Krankenschwester/-pfleger" — slash-hyphen other direction
    slash_hyph2 = re.match(r'^(.+?)/(-.+)$', name)
    if slash_hyph2:
        variants.add(slash_hyph2.group(1).strip())  # Krankenschwester
    
    # Pattern 2: "/in" suffix — "Landwirt/in" → "Landwirt", "Landwirtin"
    if '/in' in name and not slash_full:
        # Strip "/in" for masculine
        masculine = name.replace('/in', '')
        variants.add(masculine.strip())
        # Build feminine: replace "/in" with "in"
        feminine = name.replace('/in', 'in')
        variants.add(feminine.strip())
    
    # Pattern 3: "/r " — "technische/r " → "technischer" / "technische"
    if '/r ' in name:
        variants.add(name.replace('/r ', 'r ').strip())
        variants.add(name.replace('/r ', ' ').strip())
    
    # Pattern 4: Strip specialization after " - "
    # "Tierwirt/in - Rinderhaltung" → also "Tierwirt Rinderhaltung"
    if ' - ' in name:
        base = name.split(' - ')[0].strip()
        spec = name.split(' - ', 1)[1].strip()
        # Base without gender
        base_clean = re.sub(r'/in\b', '', base).strip()
        variants.add(f"{base_clean} {spec}")
        # Just the base (without specialization)
        variants.add(base_clean)
    
    # Remove the original name from variants (it's stored as canonical)
    variants.discard(name)
    
    # Filter out empty strings and very short strings
    variants = {v for v in variants if v and len(v) > 2}
    
    return sorted(variants)


def import_berufenet_to_owl(dry_run: bool = False):
    """Import all berufenet professions as OWL entities with name variants."""
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # Load all berufenet professions
        cur.execute("""
            SELECT berufenet_id, name, kldb, qualification_level
            FROM berufenet
            ORDER BY berufenet_id
        """)
        professions = cur.fetchall()
        print(f"Loaded {len(professions)} Berufenet professions")
        
        # Check how many already exist in OWL
        cur.execute("SELECT COUNT(*) FROM owl WHERE owl_type = 'berufenet'")
        existing = cur.fetchone()['count']
        print(f"Existing OWL berufenet entities: {existing}")
        
        if existing > 0 and not dry_run:
            print(f"  ⚠️  {existing} entities already exist — will skip duplicates (ON CONFLICT)")
        
        owl_created = 0
        names_created = 0
        total_variants = 0
        
        for prof in professions:
            berufenet_id = prof['berufenet_id']
            name = prof['name']
            kldb = prof['kldb']
            qual_level = prof['qualification_level']
            
            variants = generate_name_variants(name)
            total_variants += len(variants)
            
            if dry_run:
                if variants:
                    print(f"  {name}")
                    for v in variants:
                        print(f"    → {v}")
                continue
            
            # Insert OWL entity
            cur.execute("""
                INSERT INTO owl (owl_type, canonical_name, metadata, created_by, description)
                VALUES (
                    'berufenet',
                    %s,
                    jsonb_build_object(
                        'berufenet_id', %s,
                        'kldb', %s,
                        'qualification_level', %s
                    ),
                    'arden',
                    %s
                )
                ON CONFLICT (owl_type, canonical_name) DO NOTHING
                RETURNING owl_id
            """, (
                name,
                berufenet_id,
                kldb,
                qual_level,
                f"Berufenet profession: {name} (KLDB: {kldb}, Level: {qual_level})"
            ))
            
            result = cur.fetchone()
            if result is None:
                # Already existed — get the owl_id
                cur.execute("""
                    SELECT owl_id FROM owl
                    WHERE owl_type = 'berufenet' AND canonical_name = %s
                """, (name,))
                owl_id = cur.fetchone()['owl_id']
            else:
                owl_id = result['owl_id']
                owl_created += 1
            
            # Insert primary name (canonical)
            cur.execute("""
                INSERT INTO owl_names (owl_id, language, display_name, is_primary, name_type, created_by, confidence)
                VALUES (%s, 'de', %s, true, 'canonical', 'arden', 1.0)
                ON CONFLICT (owl_id, language, display_name) DO NOTHING
            """, (owl_id, name))
            if cur.rowcount > 0:
                names_created += 1
            
            # Insert variants
            for variant in variants:
                cur.execute("""
                    INSERT INTO owl_names (owl_id, language, display_name, is_primary, name_type, created_by, confidence)
                    VALUES (%s, 'de', %s, false, 'alias', 'arden', 1.0)
                    ON CONFLICT (owl_id, language, display_name) DO NOTHING
                """, (owl_id, variant))
                if cur.rowcount > 0:
                    names_created += 1
        
        if not dry_run:
            conn.commit()
        
        print(f"\n{'='*60}")
        if dry_run:
            print(f"DRY RUN — would create:")
            print(f"  OWL entities:  {len(professions)}")
            print(f"  Name variants: {total_variants} (+ {len(professions)} canonical)")
        else:
            print(f"IMPORT COMPLETE")
            print(f"  OWL entities created:  {owl_created}")
            print(f"  OWL names created:     {names_created}")
            print(f"  Skipped (existing):    {len(professions) - owl_created}")
        print(f"{'='*60}")


def migrate_synonyms(dry_run: bool = False):
    """
    Migrate berufenet_synonyms (DB table) and OWL_SYNONYMS (Python dict)
    into owl_names as aliases.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        
        # --- Part A: DB berufenet_synonyms table ---
        cur.execute("""
            SELECT s.aa_beruf, s.berufenet_id, s.source, b.name AS berufenet_name
            FROM berufenet_synonyms s
            JOIN berufenet b ON s.berufenet_id = b.berufenet_id
        """)
        db_synonyms = cur.fetchall()
        print(f"\nDB berufenet_synonyms: {len(db_synonyms)} entries")
        
        db_migrated = 0
        for syn in db_synonyms:
            # Find the OWL entity for this berufenet profession
            cur.execute("""
                SELECT owl_id FROM owl
                WHERE owl_type = 'berufenet' AND canonical_name = %s
            """, (syn['berufenet_name'],))
            owl_row = cur.fetchone()
            
            if not owl_row:
                if not dry_run:
                    print(f"  ⚠️  No OWL entity for: {syn['berufenet_name']} (berufenet_id={syn['berufenet_id']})")
                continue
            
            owl_id = owl_row['owl_id']
            
            if dry_run:
                print(f"  {syn['aa_beruf']:<50} → {syn['berufenet_name']} (source: {syn['source']})")
                db_migrated += 1
                continue
            
            cur.execute("""
                INSERT INTO owl_names (owl_id, language, display_name, is_primary, name_type, created_by, confidence,
                                       provenance)
                VALUES (%s, 'de', %s, false, 'alias', 'arden_migration', 0.9,
                        jsonb_build_object('source', %s, 'migrated_from', 'berufenet_synonyms'))
                ON CONFLICT (owl_id, language, display_name) DO NOTHING
            """, (owl_id, syn['aa_beruf'], syn['source']))
            if cur.rowcount > 0:
                db_migrated += 1
        
        # --- Part B: Python dict OWL_SYNONYMS from lib/berufenet_matching.py ---
        # Import and migrate the hardcoded dict
        try:
            from lib.berufenet_matching import OWL_SYNONYMS
        except ImportError:
            print("  ⚠️  Could not import OWL_SYNONYMS from lib/berufenet_matching.py")
            OWL_SYNONYMS = {}
        
        print(f"Python OWL_SYNONYMS dict: {len(OWL_SYNONYMS)} entries")
        
        py_migrated = 0
        for colloquial, formal in OWL_SYNONYMS.items():
            # Find the OWL entity for the formal name
            # Try: exact canonical, exact alias, then fuzzy (canonical starts with formal)
            cur.execute("""
                SELECT o.owl_id, o.canonical_name
                FROM owl o
                WHERE o.owl_type = 'berufenet'
                  AND (o.canonical_name = %s
                       OR EXISTS (
                           SELECT 1 FROM owl_names n
                           WHERE n.owl_id = o.owl_id AND n.display_name = %s
                       )
                       OR o.canonical_name ILIKE %s || '%%'
                  )
                ORDER BY
                    CASE WHEN o.canonical_name = %s THEN 0
                         WHEN EXISTS (SELECT 1 FROM owl_names n WHERE n.owl_id = o.owl_id AND n.display_name = %s) THEN 1
                         ELSE 2
                    END
                LIMIT 1
            """, (formal, formal, formal, formal, formal))
            owl_row = cur.fetchone()
            
            if not owl_row:
                print(f"  ⚠️  No OWL entity for formal name: '{formal}' (colloquial: '{colloquial}')")
                continue
            
            owl_id = owl_row['owl_id']
            
            if dry_run:
                print(f"  {colloquial:<50} → {owl_row['canonical_name']}")
                py_migrated += 1
                continue
            
            cur.execute("""
                INSERT INTO owl_names (owl_id, language, display_name, is_primary, name_type, created_by, confidence,
                                       provenance)
                VALUES (%s, 'de', %s, false, 'alias', 'arden_migration', 0.9,
                        jsonb_build_object('source', 'python_owl_synonyms', 'migrated_from', 'lib/berufenet_matching.py'))
                ON CONFLICT (owl_id, language, display_name) DO NOTHING
            """, (owl_id, colloquial))
            if cur.rowcount > 0:
                py_migrated += 1
        
        if not dry_run:
            conn.commit()
        
        print(f"\n{'='*60}")
        label = "DRY RUN — would migrate:" if dry_run else "SYNONYM MIGRATION COMPLETE"
        print(label)
        print(f"  From DB berufenet_synonyms: {db_migrated}")
        print(f"  From Python OWL_SYNONYMS:   {py_migrated}")
        print(f"{'='*60}")


def verify():
    """Show current OWL berufenet state."""
    with get_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM owl WHERE owl_type = 'berufenet'")
        entities = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM owl_names n
            JOIN owl o ON n.owl_id = o.owl_id
            WHERE o.owl_type = 'berufenet'
        """)
        names = cur.fetchone()['count']
        
        cur.execute("""
            SELECT n.name_type, COUNT(*) AS cnt
            FROM owl_names n
            JOIN owl o ON n.owl_id = o.owl_id
            WHERE o.owl_type = 'berufenet'
            GROUP BY n.name_type
            ORDER BY cnt DESC
        """)
        by_type = cur.fetchall()
        
        cur.execute("""
            SELECT n.created_by, COUNT(*) AS cnt
            FROM owl_names n
            JOIN owl o ON n.owl_id = o.owl_id
            WHERE o.owl_type = 'berufenet'
            GROUP BY n.created_by
            ORDER BY cnt DESC
        """)
        by_creator = cur.fetchall()
        
        print(f"\n📊 OWL BERUFENET STATUS")
        print(f"{'='*60}")
        print(f"  Entities (owl_type='berufenet'): {entities}")
        print(f"  Total names:                     {names}")
        print(f"\n  By name_type:")
        for row in by_type:
            print(f"    {row['name_type']:<20} {row['cnt']:>6}")
        print(f"\n  By created_by:")
        for row in by_creator:
            print(f"    {row['created_by']:<20} {row['cnt']:>6}")
        
        # Sample: show a few entities with their names
        cur.execute("""
            SELECT o.canonical_name, 
                   array_agg(n.display_name ORDER BY n.is_primary DESC, n.display_name) AS names
            FROM owl o
            JOIN owl_names n ON o.owl_id = n.owl_id
            WHERE o.owl_type = 'berufenet'
            GROUP BY o.owl_id, o.canonical_name
            HAVING COUNT(*) > 2
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        samples = cur.fetchall()
        
        if samples:
            print(f"\n  Sample entities (most names):")
            for row in samples:
                print(f"    {row['canonical_name']}")
                for nm in row['names']:
                    if nm != row['canonical_name']:
                        print(f"      → {nm}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import Berufenet into OWL')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--verify', action='store_true', help='Show current OWL berufenet state')
    parser.add_argument('--synonyms', action='store_true', help='Migrate synonyms (Step 2+3)')
    parser.add_argument('--all', action='store_true', help='Run full import + synonym migration')
    
    args = parser.parse_args()
    
    if args.verify:
        verify()
    elif args.all:
        import_berufenet_to_owl(dry_run=args.dry_run)
        migrate_synonyms(dry_run=args.dry_run)
        if not args.dry_run:
            verify()
    elif args.synonyms:
        migrate_synonyms(dry_run=args.dry_run)
    else:
        import_berufenet_to_owl(dry_run=args.dry_run)
