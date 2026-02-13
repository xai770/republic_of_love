#!/usr/bin/env python3
"""
Migration: Complete OWL geography — load ALL GeoNames places + postal codes

Previous migration (20260213_geo_owl_seed.py) loaded only cities that appear
in postings (~4,815).  This migration:

  1. Fixes Deutschland child_of geography (was missing)
  2. Loads ALL 13,660 unambiguous places from DE.txt (8,845 new)
  3. Adds postal_codes array to metadata for every city (new + existing)
  4. Adds lat/lng metadata for any city missing it
  5. Idempotent: safe to re-run

Data source: data/DE/DE.txt (GeoNames, CC-BY 4.0)
Run: python3 migrations/20260213_geo_owl_complete.py [--dry-run]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.database import get_connection

GEONAMES_FILE = Path(__file__).resolve().parent.parent / "data" / "DE" / "DE.txt"

STATE_CANONICAL = {
    "Baden-Württemberg": "Baden-Württemberg",
    "Bavaria": "Bayern",
    "Bayern": "Bayern",
    "Berlin": "Berlin",
    "Land Berlin": "Berlin",
    "Brandenburg": "Brandenburg",
    "Bremen": "Bremen",
    "Hamburg": "Hamburg",
    "Hessen": "Hessen",
    "Lower Saxony": "Niedersachsen",
    "Niedersachsen": "Niedersachsen",
    "Mecklenburg-Vorpommern": "Mecklenburg-Vorpommern",
    "Mecklenburg-Western Pomerania": "Mecklenburg-Vorpommern",
    "Nordrhein-Westfalen": "Nordrhein-Westfalen",
    "Rheinland-Pfalz": "Rheinland-Pfalz",
    "Saarland": "Saarland",
    "Sachsen": "Sachsen",
    "Saxony": "Sachsen",
    "Sachsen-Anhalt": "Sachsen-Anhalt",
    "Saxony-Anhalt": "Sachsen-Anhalt",
    "Schleswig-Holstein": "Schleswig-Holstein",
    "Thuringia": "Thüringen",
    "Thüringen": "Thüringen",
}

# Company/institution skip patterns in GeoNames
SKIP_WORDS = [
    "AG", "GmbH", "Krankenkasse", "gericht", "verwaltung",
    "Finanzamt", "anwaltschaft", "BARMER", "HUK-", "Karstadt",
    "Siemens", "Marketing", "Commerzbank", "Bank ", "UniCredit",
    "Techniker ", "Post ", "DAK-", "IKK ", "Justizvollzug",
    "Universität", "Landratsamt", "Versicherung", "Ordinariat",
    "Bundesknappschaft", "BKK", "Volksfürsorge", "Bibliothek",
    "Deutsche Rentenversicherung", "AOK", "Justizbehörden",
    "Postfach", "Großkunde",
]


def parse_geonames(filepath):
    """Parse DE.txt into city data with postal codes, lat/lng, state."""
    city_data = defaultdict(lambda: {
        "states": set(),
        "lats": [],
        "lngs": [],
        "postal_codes": set(),
    })

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 10:
                continue
            postal_code = parts[1].strip()
            place_name = parts[2].strip()
            raw_state = parts[3].strip()
            lat = parts[9].strip()
            lng = parts[10].strip() if len(parts) > 10 else ""

            if not place_name or not raw_state:
                continue

            canonical_state = STATE_CANONICAL.get(raw_state)
            if not canonical_state:
                continue

            if any(w in place_name for w in SKIP_WORDS):
                continue

            city_data[place_name]["states"].add(canonical_state)
            if postal_code:
                city_data[place_name]["postal_codes"].add(postal_code)
            try:
                city_data[place_name]["lats"].append(float(lat))
            except ValueError:
                pass
            try:
                city_data[place_name]["lngs"].append(float(lng))
            except ValueError:
                pass

    return city_data


def main():
    parser = argparse.ArgumentParser(description="Complete OWL geography")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("OWL Geography Completion")
    print("=" * 60)

    print("\nParsing GeoNames DE.txt...")
    city_data = parse_geonames(GEONAMES_FILE)
    print(f"  {len(city_data):,} place names parsed")

    # Only load unambiguous cities (appear in exactly 1 state)
    unambiguous = {}
    ambiguous_count = 0
    for place, data in city_data.items():
        if len(data["states"]) == 1:
            state = list(data["states"])[0]
            avg_lat = sum(data["lats"]) / len(data["lats"]) if data["lats"] else None
            avg_lng = sum(data["lngs"]) / len(data["lngs"]) if data["lngs"] else None
            unambiguous[place] = {
                "state": state,
                "lat": round(avg_lat, 4) if avg_lat else None,
                "lng": round(avg_lng, 4) if avg_lng else None,
                "postal_codes": sorted(data["postal_codes"]),
            }
        else:
            ambiguous_count += 1

    print(f"  {len(unambiguous):,} unambiguous (1 state)")
    print(f"  {ambiguous_count:,} ambiguous (multi-state, skipped)")

    if args.dry_run:
        print("\n  DRY RUN — no changes made.")
        return

    with get_connection() as conn:
        cur = conn.cursor()

        stats = {
            "link_fixed": 0,
            "cities_created": 0,
            "cities_updated": 0,
            "names_added": 0,
            "rels_added": 0,
        }

        # ================================================================
        # 1. Fix: Deutschland child_of geography
        # ================================================================
        print("\n[1/4] Fixing Deutschland → geography link...")
        cur.execute("SELECT owl_id FROM owl WHERE owl_type='taxonomy_root' AND canonical_name='geography'")
        geo_root = cur.fetchone()
        cur.execute("SELECT owl_id FROM owl WHERE owl_type='country' AND canonical_name='Deutschland'")
        deutschland = cur.fetchone()

        if geo_root and deutschland:
            cur.execute(
                "SELECT 1 FROM owl_relationships WHERE owl_id=%s AND related_owl_id=%s AND relationship='child_of'",
                (deutschland["owl_id"], geo_root["owl_id"])
            )
            if not cur.fetchone():
                cur.execute(
                    """INSERT INTO owl_relationships (owl_id, related_owl_id, relationship, strength, created_by, notes)
                       VALUES (%s, %s, 'child_of', 1.0, 'arden', 'geography')""",
                    (deutschland["owl_id"], geo_root["owl_id"])
                )
                stats["link_fixed"] = 1
                print(f"  ✓ Deutschland (#{deutschland['owl_id']}) → geography (#{geo_root['owl_id']})")
            else:
                print("  Already linked.")
        else:
            print("  ✗ Could not find geography root or Deutschland entity!")

        # ================================================================
        # 2. Load existing bundesland owl_ids
        # ================================================================
        print("\n[2/4] Loading Bundesland IDs...")
        cur.execute("SELECT owl_id, canonical_name FROM owl WHERE owl_type='bundesland'")
        state_owl_ids = {row["canonical_name"]: row["owl_id"] for row in cur.fetchall()}
        print(f"  {len(state_owl_ids)} Bundesländer found")

        # ================================================================
        # 3. Load existing cities for fast lookup
        # ================================================================
        print("\n[3/4] Loading existing OWL cities...")
        cur.execute("SELECT owl_id, canonical_name, metadata FROM owl WHERE owl_type='city'")
        existing_cities = {}
        for row in cur.fetchall():
            existing_cities[row["canonical_name"]] = {
                "owl_id": row["owl_id"],
                "metadata": row["metadata"] if isinstance(row["metadata"], dict) else
                            (json.loads(row["metadata"]) if row["metadata"] else {}),
            }
        print(f"  {len(existing_cities):,} existing cities")

        # ================================================================
        # 4. Upsert all unambiguous cities
        # ================================================================
        print(f"\n[4/4] Processing {len(unambiguous):,} cities...")
        batch_count = 0

        for place_name, geo in sorted(unambiguous.items()):
            state_id = state_owl_ids.get(geo["state"])
            if not state_id:
                continue

            metadata = {
                "country": "DE",
                "bundesland": geo["state"],
            }
            if geo["lat"] is not None:
                metadata["latitude"] = geo["lat"]
            if geo["lng"] is not None:
                metadata["longitude"] = geo["lng"]
            if geo["postal_codes"]:
                metadata["postal_codes"] = geo["postal_codes"]

            if place_name in existing_cities:
                # UPDATE existing: merge postal_codes + fill missing lat/lng
                existing = existing_cities[place_name]
                owl_id = existing["owl_id"]
                old_meta = existing["metadata"] or {}

                changed = False

                # Add postal codes if missing
                if "postal_codes" not in old_meta and geo["postal_codes"]:
                    old_meta["postal_codes"] = geo["postal_codes"]
                    changed = True

                # Add lat/lng if missing
                if "latitude" not in old_meta and geo["lat"] is not None:
                    old_meta["latitude"] = geo["lat"]
                    old_meta["longitude"] = geo["lng"]
                    changed = True

                if changed:
                    cur.execute(
                        "UPDATE owl SET metadata = %s WHERE owl_id = %s",
                        (json.dumps(old_meta), owl_id)
                    )
                    stats["cities_updated"] += 1
            else:
                # INSERT new city
                cur.execute(
                    """INSERT INTO owl (owl_type, canonical_name, status, created_by, metadata)
                       VALUES ('city', %s, 'active', 'arden', %s)
                       RETURNING owl_id""",
                    (place_name, json.dumps(metadata))
                )
                owl_id = cur.fetchone()["owl_id"]
                stats["cities_created"] += 1

                # Primary name
                cur.execute(
                    """INSERT INTO owl_names (owl_id, display_name, language, is_primary, name_type,
                                              confidence, created_by, confidence_source)
                       VALUES (%s, %s, 'de', true, 'canonical', 1.0, 'arden', 'geonames_import')
                       ON CONFLICT DO NOTHING""",
                    (owl_id, place_name)
                )
                stats["names_added"] += 1

                # child_of Bundesland
                cur.execute(
                    """INSERT INTO owl_relationships (owl_id, related_owl_id, relationship,
                                                      strength, created_by, notes)
                       VALUES (%s, %s, 'child_of', 1.0, 'arden', 'geography')
                       ON CONFLICT DO NOTHING""",
                    (owl_id, state_id)
                )
                stats["rels_added"] += 1

            batch_count += 1
            if batch_count % 2000 == 0:
                conn.commit()
                print(f"  ... {batch_count:,} processed")

        conn.commit()

        print(f"\n{'=' * 60}")
        print(f"Summary:")
        print(f"  Deutschland→geography link:  {'fixed' if stats['link_fixed'] else 'already ok'}")
        print(f"  New cities created:          {stats['cities_created']:,}")
        print(f"  Existing cities updated:     {stats['cities_updated']:,}")
        print(f"  Names added:                 {stats['names_added']:,}")
        print(f"  Relationships added:         {stats['rels_added']:,}")
        print(f"  Total OWL cities now:        {len(existing_cities) + stats['cities_created']:,}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
