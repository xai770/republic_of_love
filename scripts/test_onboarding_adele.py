#!/usr/bin/env python3
"""
End-to-end test: full onboarding (Mira) → profile build (Adele).

Uses user_id=2 (test@talent.yoga). Resets the user to fresh state first.
Talks to the live FastAPI server via HTTP at localhost:8000.

Usage:
    python scripts/test_onboarding_adele.py           # run full flow
    python scripts/test_onboarding_adele.py --reset    # reset only (no conversation)
"""
import argparse
import requests
import jwt
import time
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
USER_ID = 2
SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"
DB_DSN = "postgresql://base_admin:A40ytN2UEGc_tDliTLtMF-WyKOV_VslrULoLxmUZl38@localhost:5432/turing"

# ── Helpers ─────────────────────────────────────────────────────────────

def make_session_cookie():
    """Generate a valid JWT session cookie for the test user."""
    payload = {
        "user_id": USER_ID,
        "exp": (datetime.utcnow() + timedelta(hours=24)).timestamp(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return {"session": token}


def reset_user():
    """Reset user_id=2 to a completely fresh state — no profile, no name, no sessions."""
    conn = psycopg2.connect(DB_DSN, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            # Clear yogi_name and onboarding
            cur.execute("""
                UPDATE users
                SET yogi_name = NULL,
                    onboarding_completed_at = NULL,
                    notification_email = NULL,
                    notification_consent_at = NULL
                WHERE user_id = %s
            """, (USER_ID,))

            # Delete Adele sessions
            cur.execute("DELETE FROM adele_sessions WHERE user_id = %s", (USER_ID,))

            # Delete messages (both Mira and Adele)
            cur.execute("DELETE FROM yogi_messages WHERE user_id = %s", (USER_ID,))

            # Delete work history
            cur.execute("""
                DELETE FROM profile_work_history
                WHERE profile_id IN (SELECT profile_id FROM profiles WHERE user_id = %s)
            """, (USER_ID,))

            # Delete profile
            cur.execute("DELETE FROM profiles WHERE user_id = %s", (USER_ID,))

            conn.commit()
            print("✓ User reset: yogi_name=NULL, onboarding=NULL, profile deleted, messages cleared")
    finally:
        conn.close()


def chat_mira(message, cookies):
    """Send a message to Mira and return her reply."""
    r = requests.post(
        f"{BASE_URL}/api/mira/chat",
        json={"message": message},
        cookies=cookies,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data


def chat_adele(message, cookies):
    """Send a message to Adele and return her reply."""
    r = requests.post(
        f"{BASE_URL}/api/adele/chat",
        json={"message": message},
        cookies=cookies,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data


def get_adele_session(cookies):
    """Get Adele session progress."""
    r = requests.get(f"{BASE_URL}/api/adele/session", cookies=cookies, timeout=10)
    r.raise_for_status()
    return r.json()


def verify_profile():
    """Check the DB for the profile created by Adele."""
    conn = psycopg2.connect(DB_DSN, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.profile_id, p.full_name, p.current_title, p.profile_source,
                       p.skill_keywords, p.experience_level, p.desired_locations,
                       p.desired_roles, p.expected_salary_min, p.expected_salary_max
                FROM profiles p WHERE p.user_id = %s
            """, (USER_ID,))
            profile = cur.fetchone()
            if not profile:
                print("\n✗ No profile found for user_id=%d" % USER_ID)
                return False

            print(f"\n═══ Profile Created ═══")
            print(f"  ID:       {profile['profile_id']}")
            print(f"  Name:     {profile['full_name']}")
            print(f"  Title:    {profile['current_title']}")
            print(f"  Source:   {profile['profile_source']}")
            print(f"  Skills:   {profile['skill_keywords']}")
            print(f"  Level:    {profile['experience_level']}")
            print(f"  Location: {profile['desired_locations']}")
            print(f"  Roles:    {profile['desired_roles']}")
            print(f"  Salary:   {profile['expected_salary_min']}-{profile['expected_salary_max']}")

            cur.execute("""
                SELECT company_name, job_title, duration_months, job_description,
                       technologies_used, is_current
                FROM profile_work_history
                WHERE profile_id = %s
                ORDER BY start_date DESC NULLS LAST
            """, (profile['profile_id'],))
            work = cur.fetchall()
            print(f"\n  Work history ({len(work)} entries):")
            for w in work:
                dur = f"{w['duration_months']}mo" if w['duration_months'] else "?"
                current = " (current)" if w['is_current'] else ""
                print(f"    • {w['job_title']} at {w['company_name']} ({dur}{current})")
                if w['job_description']:
                    print(f"      {w['job_description'][:100]}")
                if w['technologies_used']:
                    print(f"      tech: {w['technologies_used']}")

            return True
    finally:
        conn.close()


def pr(role, text, phase=None):
    """Pretty-print a chat line."""
    color = "\033[36m" if role == "Mira" else "\033[35m" if role == "Adele" else "\033[33m"
    reset = "\033[0m"
    phase_tag = f" [{phase}]" if phase else ""
    # Truncate long replies for readability
    display = text if len(text) < 200 else text[:200] + "..."
    print(f"{color}{role}{phase_tag}:{reset} {display}")


# ── Conversation scripts ────────────────────────────────────────────────

MIRA_ONBOARDING = [
    ("Hi!", "Mira should ask for yogi_name"),
    ("Call me Sparrow", "Mira should set yogi_name=Sparrow and ask about notifications"),
    ("No thanks", "Mira should accept decline and complete onboarding"),
]

ADELE_INTERVIEW = [
    ("Hi Adele!", "Adele intro — should ask about current role"),
    ("I'm a backend engineer at Siemens, building microservices for IoT platforms. I've been here for 3 years.",
     "current_role → should ask for more details or move to work history"),
    ("Before that I was at BMW for 2 years as a software developer, working on the connected car platform.",
     "work_history entry 1"),
    ("No, that's all my work experience.",
     "should move to skills"),
    ("Python, Go, Docker, Kubernetes, PostgreSQL, Redis, gRPC, CI/CD, Terraform, AWS",
     "skills phase"),
    ("I have a Master's in Computer Science from TU Munich, graduated 2019.",
     "education phase"),
    ("I'd like to stay in Munich, remote is fine too. Looking for senior roles, 85-100k range. I want to work with distributed systems.",
     "preferences phase"),
    ("Yes, save it!",
     "should confirm and save profile"),
]


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test onboarding + Adele flow")
    parser.add_argument("--reset", action="store_true", help="Reset user only, don't run conversations")
    parser.add_argument("--skip-mira", action="store_true", help="Skip Mira onboarding (if already done)")
    parser.add_argument("--skip-adele", action="store_true", help="Skip Adele interview")
    args = parser.parse_args()

    print("═══ Test: Onboarding + Adele Profile Build ═══")
    print(f"  User: test@talent.yoga (user_id={USER_ID})")
    print()

    # Reset
    reset_user()
    if args.reset:
        print("Reset complete. Exiting.")
        return

    cookies = make_session_cookie()

    # ── Step 1: Mira Onboarding ──
    if not args.skip_mira:
        print("\n── Step 1: Mira Onboarding ──")
        for msg, expect in MIRA_ONBOARDING:
            pr("You", msg)
            resp = chat_mira(msg, cookies)
            pr("Mira", resp['reply'])
            actions = resp.get('actions')
            if actions:
                print(f"  → actions: {actions}")
            time.sleep(0.5)

        # Verify onboarding
        conn = psycopg2.connect(DB_DSN, cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT yogi_name, onboarding_completed_at FROM users WHERE user_id = %s", (USER_ID,))
            u = cur.fetchone()
            if u['yogi_name']:
                print(f"\n✓ Yogi name set: {u['yogi_name']}")
            else:
                print("\n✗ Yogi name NOT set!")
            if u['onboarding_completed_at']:
                print(f"✓ Onboarding completed: {u['onboarding_completed_at']}")
            else:
                print("✗ Onboarding NOT completed!")
        conn.close()
    else:
        print("── Skipping Mira onboarding ──")

    # ── Step 2: Adele Interview ──
    if not args.skip_adele:
        print("\n── Step 2: Adele Interview ──")
        for msg, expect in ADELE_INTERVIEW:
            pr("You", msg)
            resp = chat_adele(msg, cookies)
            pr("Adele", resp['reply'], phase=resp.get('phase'))
            time.sleep(0.5)

        # Check session progress
        session = get_adele_session(cookies)
        print(f"\n  Session: phase={session['phase']}, progress={session['progress']}%, "
              f"work_entries={session['work_history_count']}, turns={session['turn_count']}")

        # Verify profile
        verify_profile()
    else:
        print("── Skipping Adele interview ──")

    print("\n═══ Done ═══")


if __name__ == "__main__":
    main()
