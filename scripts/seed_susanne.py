#!/usr/bin/env python3
"""
scripts/seed_susanne.py — Create Susanne Mustermann, the demo yogi.

PURPOSE:
    Creates a fictional yogi account with a realistic 3-month job-search
    history. Used to populate the home page (activity log + Yogi-meter)
    for demos and UI development, before real users accumulate enough data.

    Pulls REAL posting IDs from the DB so all hotlinks work.

SAFE BY DESIGN:
    - Idempotent: run multiple times, same result (looks up by marker)
    - Never touches users with is_protected = TRUE
    - All data is marked is_test_profile = TRUE
    - Clearly fake email: susanne.demo@talent.yoga.local (no MX record)

AFTER RUNNING:
    Login at: http://localhost:8000/auth/test-login/{printed user_id}

USAGE:
    python3 scripts/seed_susanne.py              # create / update
    python3 scripts/seed_susanne.py --wipe       # delete and recreate
    python3 scripts/seed_susanne.py --show       # print user_id only
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.database import get_connection_raw, return_connection

# ── Constants ──────────────────────────────────────────────────────────────────

MARKER_EMAIL = "susanne.demo@talent.yoga.local"
DISPLAY_NAME = "Susanne M."
YOGI_NAME    = "Susanne"
LANGUAGE     = "de"
FORMALITY    = "Sie"

PROFILE_SUMMARY = """
Kauffrau für Büromanagement mit 5 Jahren Berufserfahrung in einem Berliner
Tech-Startup. Versiert in Büroorganisation, Korrespondenz, Terminmanagement,
Buchhaltungsvorbereitung und der Koordination interdisziplinärer Teams.
Mein letzter Arbeitgeber wurde übernommen; meine Stelle wurde im Rahmen der
Restrukturierung abgebaut. Ich suche jetzt eine neue Festanstellung, bevorzugt
in Berlin, gerne auch remote.
""".strip()

SKILLS = [
    "MS Office", "SAP Basics", "Büroorganisation", "Terminmanagement",
    "Korrespondenz", "Buchhaltungsvorbereitung", "DATEV Basics",
    "Reisekostenabrechnung", "Projektkoordination", "CRM-Systeme",
]

# Berufenet patterns that match Susanne's background
MATCH_BERUFENET_PATTERNS = [
    "%kaufm%", "%büro%", "%assisten%", "%sekret%",
    "%sachbearbeit%", "%verwalt%", "%office%", "%koordinat%",
]

# How many postings to pull from the DB
N_POSTINGS_TO_MATCH = 28

# ── Event timeline: simulate 3 months of activity ─────────────────────────────
# Each dict: (days_ago, event_type, note_de, outcome)
# outcome = user_decision for the match ("apply"|"skip"|None)

EVENT_SCRIPT = [
    # Week 1 — cautious start, lots of viewing
    (90, "viewed",  None, None),
    (89, "viewed",  None, None),
    (89, "viewed",  None, None),
    (88, "dismissed", "Gehalt zu niedrig angegeben, passt nicht.", "skip"),
    (88, "viewed",  None, None),
    (87, "saved",   "Interessant — Teilzeit möglich, gute Lage.", None),
    (87, "viewed",  None, None),
    (86, "dismissed", "Vollständig auf Englisch — nicht mein Schwerpunkt.", "skip"),
    (85, "saved",   "Genau mein Profil. Warte noch auf mehr Infos.", None),
    # Week 2
    (82, "viewed",  None, None),
    (81, "viewed",  None, None),
    (81, "dismissed", "Homeoffice ausgeschlossen, Fahrweg zu lang.", "skip"),
    (80, "saved",   "Gutes Unternehmen, kenne jemanden dort.", None),
    (79, "viewed",  None, None),
    (78, "apply_intent", "Ich möchte mich bewerben. Unterlagen vorbereiten.", None),
    (77, "applied", "Bewerbung abgeschickt. Anschreiben auf Ratschlag von Mira überarbeitet.", "apply"),
    # Week 3
    (74, "viewed",  None, None),
    (73, "viewed",  None, None),
    (72, "saved",   "Remote-Option vorhanden. Merken.", None),
    (71, "dismissed", "Stelle bereits besetzt laut Unternehmensite.", "skip"),
    (70, "viewed",  None, None),
    (69, "apply_intent", "Scheint gut zu passen. Morgen bewerben.", None),
    # Week 4
    (66, "applied", "Bewerbung über das Unternehmensportal eingereicht.", "apply"),
    (65, "viewed",  None, None),
    (64, "saved",   "Auf Wiedervorlage für nächste Woche.", None),
    (63, "dismissed", "Quereinsteiger gesucht — passt nicht zu meiner Erfahrung.", "skip"),
    # Month 2 — more decisive, mix of apply/not apply
    (55, "viewed",  None, None),
    (54, "saved",   "Interessante Branche, die ich noch nicht kenne.", None),
    (53, "apply_intent", "Unterlagen aktualisiert.", None),
    (52, "applied", "Direkte Bewerbung per E-Mail.", "apply"),
    (50, "viewed",  None, None),
    (49, "viewed",  None, None),
    (48, "dismissed", "Befristung nur 6 Monate, zu unsicher.", "skip"),
    (45, "apply_intent", "Stelle klingt gut, prüfe noch das Unternehmen.", None),
    (44, "not_applied", "Nach Recherche: Unternehmen hat schlechte Bewertungen auf Kununu. Kein Interesse.", "skip"),
    # Rejection — emotionally real
    (40, "outcome_received", "Absage erhalten. Begründung: intern besetzt. Enttäuschend, aber verständlich.", "apply"),
    # Month 3 — resilient, continuing
    (35, "viewed",  None, None),
    (34, "saved",   "Sehr gute Übereinstimmung laut talent.yoga. Gut ansehen.", None),
    (33, "viewed",  None, None),
    (32, "apply_intent", "Alles vorbereitet.", None),
    (31, "applied", "Bewerbung eingereicht. Bin gespannt.", "apply"),
    (28, "viewed",  None, None),
    (27, "viewed",  None, None),
    (25, "dismissed", "Nur auf Englisch, kein Deutsch — nicht passend.", "skip"),
    (20, "viewed",  None, None),
    (18, "saved",   "Könnte interessant sein. Erst mehr lesen.", None),
    (15, "viewed",  None, None),
    (14, "apply_intent", "Mira hat Anschreiben geprüft. Morgen abschicken.", None),
    (10, "not_applied", "Stelle wurde zurückgezogen. Schade.", "skip"),
    ( 7, "viewed",  None, None),
    ( 5, "saved",   "Klingt vielversprechend. In die engere Wahl.", None),
    ( 3, "viewed",  None, None),
    ( 2, "viewed",  None, None),
    ( 1, "viewed",  None, None),
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def ago(days: int, hour: int = 10, minute: int = 0) -> datetime:
    """Return a timezone-aware datetime N days ago."""
    base = datetime.now(timezone.utc) - timedelta(days=days)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def fetch_matching_postings(cur, n: int) -> list[dict]:
    """Pull N active postings with office/admin berufenet classification."""
    patterns = " OR ".join(
        f"p.berufenet_name ILIKE %s" for _ in MATCH_BERUFENET_PATTERNS
    )
    query = f"""
        SELECT p.posting_id, p.job_title, p.location_city,
               p.berufenet_name, p.external_url, p.extracted_summary
        FROM postings p
        WHERE p.enabled = TRUE
          AND p.invalidated = FALSE
          AND p.berufenet_name IS NOT NULL
          AND ({patterns})
        ORDER BY RANDOM()
        LIMIT %s
    """
    cur.execute(query, (*MATCH_BERUFENET_PATTERNS, n))
    return cur.fetchall()


def make_match_score(posting: dict, idx: int) -> dict:
    """
    Generate a plausible match score for a posting.
    Uses idx to ensure variety across the dataset.
    """
    seed = posting["posting_id"] + idx
    r = random.Random(seed)

    skill_score   = round(r.uniform(0.45, 0.95), 2)
    match_rate    = round(r.uniform(0.40, 0.92), 2)
    confidence    = round(r.uniform(0.55, 0.90), 2)

    if match_rate >= 0.75:
        recommendation = "APPLY"
        go_reasons = [
            "Berufliche Qualifikation passt gut",
            "Standort und Arbeitszeiten kompatibel",
        ]
        nogo_reasons = []
    elif match_rate >= 0.55:
        recommendation = "CONSIDER"
        go_reasons   = ["Grundqualifikation vorhanden"]
        nogo_reasons = ["Spezifische Anforderungen teilweise nicht erfüllt"]
    else:
        recommendation = "SKIP"
        go_reasons   = []
        nogo_reasons = ["Qualifikationslücke im Kernbereich", "Anforderungsprofil abweichend"]

    return {
        "skill_match_score": skill_score,
        "match_rate":        match_rate,
        "recommendation":    recommendation,
        "confidence":        confidence,
        "go_reasons":        json.dumps(go_reasons),
        "nogo_reasons":      json.dumps(nogo_reasons),
        "model_version":     "seed-v1",
        "computed_at":       ago(random.randint(5, 95)).isoformat(),
    }


# ── Core functions ─────────────────────────────────────────────────────────────

def find_susanne(cur) -> dict | None:
    cur.execute("SELECT * FROM users WHERE email LIKE %s", (f"%{MARKER_EMAIL}%",))
    return cur.fetchone()


def delete_susanne(conn, cur) -> None:
    print("⚠️  Wiping Susanne's account...")
    cur.execute("""
        DELETE FROM yogi_posting_events WHERE profile_id IN (
            SELECT profile_id FROM profiles WHERE user_id IN (
                SELECT user_id FROM users WHERE email LIKE %s
            )
        )
    """, (f"%{MARKER_EMAIL}%",))
    cur.execute("""
        DELETE FROM profile_posting_matches WHERE profile_id IN (
            SELECT profile_id FROM profiles WHERE user_id IN (
                SELECT user_id FROM users WHERE email LIKE %s
            )
        )
    """, (f"%{MARKER_EMAIL}%",))
    cur.execute("""
        DELETE FROM profiles WHERE user_id IN (
            SELECT user_id FROM users WHERE email LIKE %s
        )
    """, (f"%{MARKER_EMAIL}%",))
    cur.execute("DELETE FROM users WHERE email LIKE %s", (f"%{MARKER_EMAIL}%",))
    conn.commit()
    print("   Done.")


def create_user(cur) -> int:
    print("👤 Creating user Susanne Mustermann...")
    cur.execute("""
        INSERT INTO users (
            email, display_name, yogi_name, language, formality,
            subscription_status, onboarding_completed_at,
            terms_accepted_at, trial_ends_at, trial_budget_cents, is_protected
        ) VALUES (
            %s, %s, %s, %s, %s,
            'active',
            NOW() - INTERVAL '89 days',
            NOW() - INTERVAL '90 days',
            NOW() + INTERVAL '1 year',
            500,
            FALSE
        )
        RETURNING user_id
    """, (MARKER_EMAIL, DISPLAY_NAME, YOGI_NAME, LANGUAGE, FORMALITY))
    user_id = cur.fetchone()["user_id"]
    print(f"   user_id = {user_id}")
    return user_id


def create_profile(cur, user_id: int) -> int:
    print("📋 Creating profile...")
    cur.execute("""
        INSERT INTO profiles (
            user_id, full_name, profile_summary, current_title,
            skills_extraction_status, experience_level, years_of_experience,
            location, language, skill_keywords,
            is_test_profile, matching_enabled, enabled
        ) VALUES (
            %s, %s, %s,
            'Kauffrau für Büromanagement',
            'completed',
            'mid',
            5,
            'Berlin',
            'de',
            %s,
            TRUE,
            TRUE,
            TRUE
        )
        RETURNING profile_id
    """, (user_id, "Susanne Mustermann", PROFILE_SUMMARY, json.dumps(SKILLS)))
    profile_id = cur.fetchone()["profile_id"]
    print(f"   profile_id = {profile_id}")
    return profile_id


def create_matches(cur, profile_id: int, postings: list[dict]) -> dict[int, int]:
    """
    Insert profile_posting_matches.
    Returns {posting_id: match_id}.
    """
    print(f"🔗 Creating {len(postings)} matches...")
    mapping = {}
    for i, p in enumerate(postings):
        scores = make_match_score(p, i)
        cur.execute("""
            INSERT INTO profile_posting_matches (
                profile_id, posting_id,
                skill_match_score, match_rate, recommendation,
                confidence, go_reasons, nogo_reasons,
                model_version, computed_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT DO NOTHING
            RETURNING match_id
        """, (
            profile_id, p["posting_id"],
            scores["skill_match_score"], scores["match_rate"],
            scores["recommendation"], scores["confidence"],
            scores["go_reasons"], scores["nogo_reasons"],
            scores["model_version"], scores["computed_at"],
        ))
        row = cur.fetchone()
        if row:
            mapping[p["posting_id"]] = row["match_id"]
    print(f"   Created {len(mapping)} matches")
    return mapping


def seed_events(cur, profile_id: int, postings: list[dict],
                match_map: dict[int, int]) -> None:
    """
    Walk EVENT_SCRIPT, assigning a posting to each event in a round-robin
    pattern so every event references a real posting_id.
    """
    print(f"📅 Seeding {len(EVENT_SCRIPT)} events...")
    posting_ids = [p["posting_id"] for p in postings]

    # Track user_decision updates needed on matches
    decision_updates: list[tuple[str, int]] = []

    for i, (days_ago, event_type, note, user_decision) in enumerate(EVENT_SCRIPT):
        pid = posting_ids[i % len(posting_ids)]
        match_id = match_map.get(pid)

        ts = ago(days_ago, hour=random.randint(8, 18), minute=random.randint(0, 59))

        cur.execute("""
            INSERT INTO yogi_posting_events (
                profile_id, posting_id, match_id, event_type, note, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (profile_id, pid, match_id, event_type, note, ts))

        # Track view counts on profile_posting_matches
        if event_type == "viewed" and match_id:
            cur.execute("""
                UPDATE profile_posting_matches
                SET first_viewed_at = LEAST(COALESCE(first_viewed_at, %s), %s),
                    last_viewed_at  = GREATEST(COALESCE(last_viewed_at, %s), %s),
                    view_count      = view_count + 1
                WHERE match_id = %s
            """, (ts, ts, ts, ts, match_id))

        # Apply user_decision to match row (last one wins if multiple events on same posting)
        if user_decision and match_id:
            decision_updates.append((user_decision, match_id))

    # Apply user decisions
    for decision, match_id in decision_updates:
        cur.execute("""
            UPDATE profile_posting_matches
            SET user_decision = %s,
                user_applied  = %s,
                applied_at    = CASE WHEN %s = 'apply' THEN NOW() - INTERVAL '30 days' ELSE NULL END
            WHERE match_id = %s
        """, (decision, decision == "apply", decision, match_id))

    print(f"   Done.")


def print_summary(user_id: int, profile_id: int) -> None:
    print()
    print("=" * 60)
    print("✅  Susanne Mustermann is ready.")
    print(f"   user_id    = {user_id}")
    print(f"   profile_id = {profile_id}")
    print()
    print("   Login URL (dev server):")
    print(f"   http://localhost:8000/auth/test-login/{user_id}")
    print()
    print("   To log in as Susanne and see the home page:")
    print(f"   python3 scripts/login_as.py {user_id}")
    print("=" * 60)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed Susanne Mustermann demo account")
    parser.add_argument("--wipe",  action="store_true", help="Delete and recreate from scratch")
    parser.add_argument("--show",  action="store_true", help="Print user_id and exit (no changes)")
    args = parser.parse_args()

    conn = get_connection_raw()
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            existing = find_susanne(cur)

            if args.show:
                if existing:
                    print(existing["user_id"])
                else:
                    print("Susanne does not exist yet. Run without --show to create her.")
                return

            if existing:
                if args.wipe:
                    delete_susanne(conn, cur)
                else:
                    print(f"Susanne already exists (user_id={existing['user_id']}).")
                    print("Use --wipe to delete and recreate, or --show to get her user_id.")
                    print(f"\nLogin URL: http://localhost:8000/auth/test-login/{existing['user_id']}")
                    return

            # Fetch real postings
            print("🔍 Fetching real postings from DB...")
            postings = fetch_matching_postings(cur, N_POSTINGS_TO_MATCH)
            if len(postings) < 5:
                print(f"ERROR: Only found {len(postings)} matching postings. Need at least 5.")
                sys.exit(1)
            print(f"   Found {len(postings)} postings")

            # Create user + profile + matches + events
            user_id    = create_user(cur)
            profile_id = create_profile(cur, user_id)
            match_map  = create_matches(cur, profile_id, postings)
            seed_events(cur, profile_id, postings, match_map)

            conn.commit()
            print_summary(user_id, profile_id)

    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    finally:
        return_connection(conn)


if __name__ == "__main__":
    main()
