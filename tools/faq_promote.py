#!/usr/bin/env python3
"""
FAQ Promotion Script

Takes a promoted FAQ candidate and generates the Markdown entry
for config/mira_faq.md, then optionally appends it.

Usage:
    python tools/faq_promote.py <candidate_id>                    # Show entry
    python tools/faq_promote.py <candidate_id> --apply            # Append to faq file
    python tools/faq_promote.py <candidate_id> --category pricing # Specify category

Author: Arden
Date: 2026-02-09
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

FAQ_FILE = Path(__file__).parent.parent / "config" / "mira_faq.md"


def generate_faq_entry(
    faq_id: str,
    category: str,
    user_message: str,
    mira_response: str,
    answer_en: str = None
) -> str:
    """Generate Markdown FAQ entry."""
    
    # Clean up message for variants
    question = user_message.strip().rstrip('?') + '?'
    
    entry = f"""
### {faq_id}
**category:** {category}
**question_variants:**
- {question}

**answer_de:**
{mira_response.strip()}

**answer_en:**
{answer_en or '(TODO: translate)'}

---
"""
    return entry


def promote_candidate(candidate_id: int, category: str = None, apply: bool = False) -> None:
    """Promote a candidate to FAQ corpus."""
    from core.database import get_connection
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM mira_faq_candidates 
                WHERE id = %s
            """, (candidate_id,))
            row = cur.fetchone()
            
            if not row:
                print(f"❌ Candidate #{candidate_id} not found.")
                return
            
            if row['review_decision'] != 'promote':
                print(f"⚠️  Candidate #{candidate_id} is not marked for promotion.")
                print(f"   Current status: {row['review_decision'] or 'pending'}")
                print(f"   Use 'faq_review.py promote {candidate_id}' first.")
                return
            
            # Use stored FAQ ID or generate one
            faq_id = row['promoted_faq_id'] or f"faq_promoted_{candidate_id:04d}"
            
            # Guess category from content
            if not category:
                msg_lower = row['user_message'].lower()
                if any(w in msg_lower for w in ['kost', 'preis', 'bezahl', 'price', 'cost', 'pay']):
                    category = 'pricing'
                elif any(w in msg_lower for w in ['daten', 'privat', 'data', 'privacy', 'gdpr']):
                    category = 'privacy'
                elif any(w in msg_lower for w in ['match', 'job', 'stelle', 'arbeit']):
                    category = 'matching'
                elif any(w in msg_lower for w in ['profil', 'profile', 'lebenslauf', 'resume']):
                    category = 'profile'
                else:
                    category = 'general'
            
            entry = generate_faq_entry(
                faq_id=faq_id,
                category=category,
                user_message=row['user_message'],
                mira_response=row['mira_response']
            )
            
            print(f"\n📝 Generated FAQ entry for candidate #{candidate_id}:")
            print("=" * 60)
            print(entry)
            print("=" * 60)
            
            if apply:
                # Append to FAQ file
                with open(FAQ_FILE, 'a', encoding='utf-8') as f:
                    f.write(entry)
                print(f"\n✅ Appended to {FAQ_FILE}")
                print("   Don't forget to run embedding regeneration!")
            else:
                print(f"\nTo append to {FAQ_FILE.name}, run:")
                print(f"  python tools/faq_promote.py {candidate_id} --category {category} --apply")


def main():
    parser = argparse.ArgumentParser(description="Promote FAQ candidate to corpus")
    parser.add_argument('id', type=int, help='Candidate ID to promote')
    parser.add_argument('--category', '-c', help='FAQ category (pricing, privacy, matching, profile, general)')
    parser.add_argument('--apply', '-a', action='store_true', help='Actually append to FAQ file')
    
    args = parser.parse_args()
    
    promote_candidate(args.id, category=args.category, apply=args.apply)


if __name__ == '__main__':
    main()
