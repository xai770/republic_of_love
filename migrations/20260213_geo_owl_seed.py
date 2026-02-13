#!/usr/bin/env python3
"""
Migration: Seed OWL with German geography data from GeoNames

Creates:
  - 1 country entity (Deutschland)
  - 16 Bundesland entities (child_of Deutschland)
  - ~2,600 city entities (child_of Bundesland)  -- only cities in our postings
  - owl_names synonyms for all (GeoNames English variants, comma-qualifier variants)
  - metadata: lat/lng from GeoNames (averaged per city)

Data source: data/DE/DE.txt (GeoNames, CC-BY 4.0)

Run: python3 migrations/20260213_geo_owl_seed.py [--dry-run]
Idempotent: skips entities that already exist (checked by canonical_name + owl_type).
"""

import argparse
import sys
import os
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.database import get_connection

GEONAMES_FILE = Path(__file__).resolve().parent.parent / "data" / "DE" / "DE.txt"

# Map GeoNames state names → our canonical German names (as used in postings.location_state)
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

# English names for the canonical states (become owl_names synonyms)
STATE_ENGLISH = {
    "Baden-Württemberg": "Baden-Württemberg",  # same in English
    "Bayern": "Bavaria",
    "Berlin": "Berlin",
    "Brandenburg": "Brandenburg",
    "Bremen": "Bremen",
    "Hamburg": "Hamburg",
    "Hessen": "Hesse",
    "Niedersachsen": "Lower Saxony",
    "Mecklenburg-Vorpommern": "Mecklenburg-Western Pomerania",
    "Nordrhein-Westfalen": "North Rhine-Westphalia",
    "Rheinland-Pfalz": "Rhineland-Palatinate",
    "Saarland": "Saarland",
    "Sachsen": "Saxony",
    "Sachsen-Anhalt": "Saxony-Anhalt",
    "Schleswig-Holstein": "Schleswig-Holstein",
    "Thüringen": "Thuringia",
}


def parse_geonames(filepath):
    """Parse DE.txt into city→state mapping with lat/lng."""
    city_data = defaultdict(lambda: {"states": set(), "lats": [], "lngs": [], "geonames_names": set()})

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 10:
                continue
            place_name = parts[2].strip()
            raw_state = parts[3].strip()
            lat = parts[9].strip()
            lng = parts[10].strip()

            if not place_name or not raw_state:
                continue

            canonical_state = STATE_CANONICAL.get(raw_state)
            if not canonical_state:
                continue  # Unknown state name

            # Skip obvious non-city entries (companies, institutions)
            skip_words = ["AG", "GmbH", "Krankenkasse", "gericht", "verwaltung",
                          "Finanzamt", "anwaltschaft", "BARMER", "HUK-", "Karstadt",
                          "Siemens", "Marketing", "Commerzbank", "Bank ", "UniCredit",
                          "Techniker ", "Post ", "DAK-", "IKK ", "Justizvollzug",
                          "Universität", "Landratsamt", "Versicherung", "Ordinariat",
                          "Bundesknappschaft", "BKK", "Volksfürsorge", "Bibliothek",
                          "Deutsche Rentenversicherung", "AOK", "Justizbehörden"]
            if any(w in place_name for w in skip_words):
                continue

            city_data[place_name]["states"].add(canonical_state)
            city_data[place_name]["geonames_names"].add(place_name)
            try:
                city_data[place_name]["lats"].append(float(lat))
                city_data[place_name]["lngs"].append(float(lng))
            except ValueError:
                pass

    return city_data


def get_posting_cities(conn):
    """Get all distinct city names from postings (our actual universe)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT location_city
        FROM postings
        WHERE location_city IS NOT NULL
          AND TRIM(location_city) != ''
          AND COALESCE(invalidated, false) = false
    """)
    return {row["location_city"].strip() for row in cur.fetchall()}


def create_owl_entity(cur, owl_type, canonical_name, metadata=None, created_by="arden"):
    """Insert into owl, return owl_id. Skip if exists."""
    cur.execute(
        "SELECT owl_id FROM owl WHERE owl_type = %s AND canonical_name = %s",
        (owl_type, canonical_name),
    )
    row = cur.fetchone()
    if row:
        return row["owl_id"], False  # Already exists

    cur.execute(
        """INSERT INTO owl (owl_type, canonical_name, status, created_by, metadata)
           VALUES (%s, %s, 'active', %s, %s)
           RETURNING owl_id""",
        (owl_type, canonical_name, created_by, json.dumps(metadata) if metadata else None),
    )
    return cur.fetchone()["owl_id"], True


def add_owl_name(cur, owl_id, display_name, language="de", is_primary=False,
                 name_type="alias", confidence=1.0, created_by="arden",
                 confidence_source="geonames_import"):
    """Insert into owl_names. Skip if exact duplicate exists."""
    cur.execute(
        "SELECT 1 FROM owl_names WHERE owl_id = %s AND display_name = %s AND language = %s",
        (owl_id, display_name, language),
    )
    if cur.fetchone():
        return False

    cur.execute(
        """INSERT INTO owl_names (owl_id, display_name, language, is_primary, name_type,
                                  confidence, created_by, confidence_source)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (owl_id, display_name, language, is_primary, name_type, confidence,
         created_by, confidence_source),
    )
    return True


def add_owl_relationship(cur, owl_id, related_owl_id, relationship="child_of",
                         strength=1.0, created_by="arden", notes=None):
    """Insert into owl_relationships. Skip if exists."""
    cur.execute(
        """SELECT 1 FROM owl_relationships
           WHERE owl_id = %s AND related_owl_id = %s AND relationship = %s""",
        (owl_id, related_owl_id, relationship),
    )
    if cur.fetchone():
        return False

    cur.execute(
        """INSERT INTO owl_relationships (owl_id, related_owl_id, relationship,
                                          strength, created_by, notes)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (owl_id, related_owl_id, relationship, strength, created_by, notes),
    )
    return True


import json


def main():
    parser = argparse.ArgumentParser(description="Seed OWL with German geography")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    print("Parsing GeoNames DE.txt...")
    city_data = parse_geonames(GEONAMES_FILE)
    print(f"  {len(city_data):,} places parsed from GeoNames")

    with get_connection() as conn:
        cur = conn.cursor()
        posting_cities = get_posting_cities(conn)
        print(f"  {len(posting_cities):,} distinct cities in postings")

        if args.dry_run:
            # Just count what we'd do
            unambiguous = {c: d for c, d in city_data.items() if len(d["states"]) == 1}
            matchable = posting_cities & set(unambiguous.keys())
            # Also check comma-stripped versions
            extra = 0
            for pc in posting_cities:
                if pc in unambiguous:
                    continue
                if "," in pc:
                    base = pc.split(",")[0].strip()
                    if base in unambiguous:
                        extra += 1
            print(f"\n  DRY RUN:")
            print(f"  Would create: 1 country + 16 Bundesländer + {len(matchable) + extra:,} cities")
            print(f"  Direct matches: {len(matchable):,}")
            print(f"  Comma-strip matches: {extra:,}")
            return

        # ================================================================
        # 1. Create Deutschland (country)
        # ================================================================
        de_id, created = create_owl_entity(cur, "country", "Deutschland")
        add_owl_name(cur, de_id, "Deutschland", "de", is_primary=True, name_type="canonical")
        add_owl_name(cur, de_id, "Germany", "en")
        add_owl_name(cur, de_id, "DE", "de", name_type="abbreviation")
        status = "CREATED" if created else "exists"
        print(f"  Deutschland: owl_id={de_id} ({status})")

        # ================================================================
        # 2. Create 16 Bundesländer
        # ================================================================
        state_owl_ids = {}
        states_created = 0
        for canonical_name in sorted(set(STATE_CANONICAL.values())):
            state_id, created = create_owl_entity(
                cur, "bundesland", canonical_name,
                metadata={"country": "DE"}
            )
            state_owl_ids[canonical_name] = state_id
            if created:
                states_created += 1

            # Primary name (German)
            add_owl_name(cur, state_id, canonical_name, "de",
                         is_primary=True, name_type="canonical")

            # English synonym
            en_name = STATE_ENGLISH.get(canonical_name)
            if en_name and en_name != canonical_name:
                add_owl_name(cur, state_id, en_name, "en")

            # All GeoNames variant names as synonyms
            for raw, canon in STATE_CANONICAL.items():
                if canon == canonical_name and raw != canonical_name:
                    add_owl_name(cur, state_id, raw, "de")

            # child_of Deutschland
            add_owl_relationship(cur, state_id, de_id, "child_of",
                                 notes="geography")

        print(f"  Bundesländer: {states_created} created, {16 - states_created} existed")

        # ================================================================
        # 3. Create city entities (only cities that appear in our postings)
        # ================================================================
        # Build unambiguous city→state from GeoNames
        unambiguous = {}
        for place, data in city_data.items():
            if len(data["states"]) == 1:
                state = list(data["states"])[0]
                avg_lat = sum(data["lats"]) / len(data["lats"]) if data["lats"] else None
                avg_lng = sum(data["lngs"]) / len(data["lngs"]) if data["lngs"] else None
                unambiguous[place] = {
                    "state": state,
                    "lat": round(avg_lat, 4) if avg_lat else None,
                    "lng": round(avg_lng, 4) if avg_lng else None,
                }

        cities_created = 0
        names_added = 0
        rels_added = 0

        # Track which canonical cities we've created (to handle comma-strip synonyms)
        created_cities = {}  # canonical_name → owl_id

        for pc in sorted(posting_cities):
            if not pc.strip():
                continue

            # Match strategy 1: direct match
            match_key = pc
            geo = unambiguous.get(pc)

            # Match strategy 2: comma-strip (e.g. "Nürnberg, Mittelfranken" → "Nürnberg")
            if not geo and "," in pc:
                base = pc.split(",")[0].strip()
                geo = unambiguous.get(base)
                if geo:
                    match_key = base  # Canonical uses the base name

            if not geo:
                continue  # Ambiguous or international — skip

            state_name = geo["state"]
            state_id = state_owl_ids.get(state_name)
            if not state_id:
                continue

            # Use base city name as canonical
            canonical = match_key
            metadata = {"country": "DE", "bundesland": state_name}
            if geo["lat"]:
                metadata["latitude"] = geo["lat"]
            if geo["lng"]:
                metadata["longitude"] = geo["lng"]

            # Create city entity (or get existing)
            if canonical in created_cities:
                city_id = created_cities[canonical]
                was_created = False
            else:
                city_id, was_created = create_owl_entity(
                    cur, "city", canonical, metadata=metadata
                )
                created_cities[canonical] = city_id
                if was_created:
                    cities_created += 1

                    # Primary name
                    if add_owl_name(cur, city_id, canonical, "de",
                                    is_primary=True, name_type="canonical"):
                        names_added += 1

                    # child_of Bundesland
                    if add_owl_relationship(cur, city_id, state_id, "child_of",
                                            notes="geography"):
                        rels_added += 1

            # Add the posting's exact city name as a synonym (handles qualifier variants)
            if pc != canonical:
                if add_owl_name(cur, city_id, pc, "de", name_type="alias",
                                confidence_source="posting_city_name"):
                    names_added += 1

        # ================================================================
        # 4. Add city-state self-references (Berlin, Hamburg, Bremen)
        # ================================================================
        city_states = ["Berlin", "Hamburg", "Bremen"]
        for cs_name in city_states:
            state_id = state_owl_ids.get(cs_name)
            if not state_id:
                continue
            # The Bundesland entity IS also the city — add city-type alias
            if cs_name not in created_cities:
                # Create a city entity that's child_of the Bundesland
                city_id, was_created = create_owl_entity(
                    cur, "city", cs_name,
                    metadata={"country": "DE", "bundesland": cs_name, "is_city_state": True}
                )
                if was_created:
                    cities_created += 1
                    add_owl_name(cur, city_id, cs_name, "de",
                                 is_primary=True, name_type="canonical")
                    add_owl_relationship(cur, city_id, state_id, "child_of",
                                         notes="city-state geography")
                    names_added += 1
                    rels_added += 1
                created_cities[cs_name] = city_id

        conn.commit()

        print(f"\n  Summary:")
        print(f"    Cities created:       {cities_created:,}")
        print(f"    Names added:          {names_added:,}")
        print(f"    Relationships added:  {rels_added:,}")
        print(f"    Total OWL entities:   {cities_created + states_created + 1}")
        print(f"\n  Done. Committed.")


if __name__ == "__main__":
    main()
