#!/usr/bin/env python3
"""
Hybrid Skill Extraction - Option C Implementation

Phase 1: Extract RAW skills from job summaries (what's ACTUALLY in the text)
Phase 2: Map to taxonomy using fuzzy matching + LLM confirmation
Phase 3: Track unmapped skills for taxonomy expansion

Based on: Option C - Hybrid Approach
"""

import psycopg2
import requests
import json
import time
import argparse
from datetime import datetime
from difflib import SequenceMatcher

# Database connection
DB_CONFIG = {
    'dbname': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025',
    'host': 'localhost'
}

# LLM settings
LLM_MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"

def ask_llm(prompt, temperature=0.3, max_tokens=2000):
    """Call LLM with prompt"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            return None
    except Exception as e:
        print(f"    ⚠️  LLM error: {e}")
        return None

def extract_raw_skills(job_summary):
    """Phase 1: Extract raw skills from job summary (no taxonomy constraint)"""
    
    prompt = f"""Extract ALL skills, technologies, and competencies mentioned in this job posting.

JOB SUMMARY:
{job_summary}

TASK:
- List EVERY skill, tool, technology, or competency mentioned
- Include technical skills (Python, SQL, AWS, etc.)
- Include soft skills (leadership, communication, etc.)
- Include domain knowledge (finance, healthcare, etc.)
- Keep skills SHORT and ATOMIC (e.g., "SQL" not "Fundierte SQL Kenntnisse")
- Extract the core skill name, not full descriptions
- If text is in German, extract German skill names

Return a simple JSON array of skills found:
["skill_1", "skill_2", "skill_3"]

Return ONLY the JSON array, no other text."""

    response = ask_llm(prompt)
    if not response:
        return []
    
    # Parse JSON array
    try:
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            skills = json.loads(json_str)
            return [s.strip() for s in skills if isinstance(s, str) and s.strip()]
        else:
            return []
    except json.JSONDecodeError:
        return []

def translate_skill_to_english(raw_skill):
    """Translate a skill from German (or other language) to English"""
    
    prompt = f"""Translate this skill/competency to English.

Skill: "{raw_skill}"

RULES:
- If already in English, return as-is
- If German, translate to standard English skill name
- Use professional terminology
- Keep it SHORT and ATOMIC (e.g., "SQL" not "SQL knowledge")
- Return ONLY the English skill name, nothing else

Examples:
- "Programmierkenntnisse" → "Programming"
- "SQL" → "SQL"
- "Führungserfahrung" → "Leadership"
- "Datenanalyse" → "Data Analysis"

English skill name:"""

    response = ask_llm(prompt, temperature=0.1)
    if response:
        # Clean up the response
        english = response.strip().strip('"').strip("'").strip()
        return english
    return raw_skill  # fallback to original

def load_taxonomy(conn):
    """Load complete taxonomy: skills and their domains"""
    cur = conn.cursor()
    
    # Get all skills from taxonomy
    cur.execute("""
        SELECT DISTINCT skill
        FROM skill_aliases
        ORDER BY skill
    """)
    
    taxonomy_skills = {row[0].lower(): row[0] for row in cur.fetchall()}
    
    cur.close()
    return taxonomy_skills

def load_synonyms(conn):
    """Load existing synonym mappings"""
    cur = conn.cursor()
    
    # skill_synonyms has canonical_skill_id (integer)
    # skill_aliases doesn't have skill_id, just skill (text)
    # For now, return empty dict - we'll build synonyms dynamically
    
    # TODO: Fix schema mismatch or query differently
    cur.close()
    return {}

def string_similarity(a, b):
    """Calculate string similarity (0.0 to 1.0)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_best_match(raw_skill, taxonomy_skills, threshold=0.85):
    """Find best matching taxonomy skill using fuzzy matching"""
    raw_lower = raw_skill.lower()
    
    # Exact match
    if raw_lower in taxonomy_skills:
        return taxonomy_skills[raw_lower], 1.0
    
    # Fuzzy match
    best_match = None
    best_score = 0.0
    
    for tax_skill_lower, tax_skill_canonical in taxonomy_skills.items():
        score = string_similarity(raw_skill, tax_skill_canonical)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = tax_skill_canonical
    
    return best_match, best_score

def confirm_match_with_llm(raw_skill, suggested_skill):
    """Ask LLM to confirm if two skills are the same"""
    
    prompt = f"""Are these two skills the same thing?

Skill 1: "{raw_skill}"
Skill 2: "{suggested_skill}"

Consider:
- Are they synonyms? (e.g., "Python" and "python programming")
- Do they refer to the same competency?
- Would someone with Skill 2 be considered to have Skill 1?

Answer with just: YES or NO"""

    response = ask_llm(prompt, temperature=0.1)
    if response:
        return 'YES' in response.upper()
    return False

def suggest_taxonomy_placement(raw_skill, taxonomy_domains):
    """Ask LLM to suggest where new skill belongs in taxonomy"""
    
    domains_list = "\n".join(f"- {d}" for d in taxonomy_domains)
    
    prompt = f"""A new skill needs to be added to our taxonomy: "{raw_skill}"

Our taxonomy has these 13 functional domains:
{domains_list}

TASK:
1. Which domain does "{raw_skill}" belong to?
2. What should be the canonical name? (use underscores, like "Financial_Analysis")
3. Why does it belong there?

Return JSON:
{{
  "domain": "DOMAIN_NAME",
  "canonical_name": "Canonical_Skill_Name",
  "reasoning": "Brief explanation",
  "confidence": 0.95
}}

Return ONLY the JSON, no other text."""

    response = ask_llm(prompt, temperature=0.3)
    if not response:
        return None
    
    # Parse JSON
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return None

def map_skills_to_taxonomy(raw_skills, taxonomy_skills, synonyms, conn):
    """Phase 2: Map raw skills to taxonomy (with translation support)"""
    
    mapped = []
    unmapped = []
    
    for raw_skill in raw_skills:
        raw_lower = raw_skill.lower()
        
        # Check synonyms first
        if raw_lower in synonyms:
            canonical = synonyms[raw_lower]
            mapped.append(canonical)
            print(f"      ✓ {raw_skill} → {canonical} (synonym)")
            continue
        
        # Translate to English if needed
        print(f"      🔤 Translating: {raw_skill}...", end=" ")
        english_skill = translate_skill_to_english(raw_skill)
        print(f"→ {english_skill}")
        
        # Try exact match with English translation
        english_lower = english_skill.lower()
        if english_lower in taxonomy_skills:
            canonical = taxonomy_skills[english_lower]
            mapped.append(canonical)
            print(f"         ✓ Exact match: {canonical}")
            
            # Add to skill_aliases (German → English mapping)
            add_skill_alias(conn, raw_skill, canonical, 'de')
            continue
        
        # Try fuzzy matching with English
        best_match, score = find_best_match(english_skill, taxonomy_skills, threshold=0.85)
        
        if best_match and score >= 0.95:
            # High confidence match
            mapped.append(best_match)
            print(f"         ✓ Fuzzy match: {best_match} (score: {score:.2f})")
            add_skill_alias(conn, raw_skill, best_match, 'de')
        elif best_match and score >= 0.85:
            # Medium confidence - confirm with LLM
            print(f"         ? Maybe {best_match}? (score: {score:.2f}) - confirming...", end=" ")
            if confirm_match_with_llm(english_skill, best_match):
                mapped.append(best_match)
                print(f"✓ Confirmed")
                add_skill_alias(conn, raw_skill, best_match, 'de')
            else:
                unmapped.append((raw_skill, english_skill))
                print(f"✗ Rejected")
        else:
            # No good match found
            unmapped.append((raw_skill, english_skill))
            print(f"         ✗ No match found")
    
    return mapped, unmapped

def add_skill_alias(conn, german_term, english_canonical, language='de'):
    """Add German term as alias for English canonical skill"""
    
    cur = conn.cursor()
    
    try:
        # Check if already exists (either as alias or as canonical)
        cur.execute("""
            SELECT 1 FROM skill_aliases 
            WHERE skill_alias = %s
        """, (german_term,))
        
        if cur.fetchone():
            # Already exists as alias
            cur.close()
            return
        
        # Check if the canonical skill exists
        cur.execute("""
            SELECT 1 FROM skill_aliases 
            WHERE skill = %s
        """, (english_canonical,))
        
        if not cur.fetchone():
            # Canonical doesn't exist, skip
            cur.close()
            return
        
        # Add as alias (german_term points to english_canonical)
        cur.execute("""
            INSERT INTO skill_aliases 
                (skill_alias, skill, display_name, language, confidence, notes)
            VALUES (%s, %s, %s, %s, 1.0, 'Auto-added from job extraction')
            ON CONFLICT (skill_alias) DO NOTHING
        """, (
            german_term,
            english_canonical,
            german_term,  # Use German as display name
            language
        ))
        
        conn.commit()
        print(f"         📝 Added alias: {german_term} → {english_canonical}")
    except Exception as e:
        conn.rollback()
        # Silently ignore duplicate key errors
        if 'duplicate key' not in str(e).lower():
            print(f"         ⚠️  Error adding alias: {e}")
    finally:
        cur.close()

def track_unmapped_skills(unmapped_skills, job_id, taxonomy_domains, conn):
    """Phase 3: Track new skills for taxonomy expansion"""
    
    cur = conn.cursor()
    
    for raw_skill, english_skill in unmapped_skills:
        # Suggest taxonomy placement using English translation
        suggestion = suggest_taxonomy_placement(english_skill, taxonomy_domains)
        
        if suggestion:
            print(f"      💡 Suggestion for '{raw_skill}' (EN: {english_skill}):")
            print(f"         Domain: {suggestion.get('domain')}")
            print(f"         Canonical: {suggestion.get('canonical_name')}")
            print(f"         Reasoning: {suggestion.get('reasoning')[:80]}...")
            
            # Insert or update in pending table
            try:
                cur.execute("""
                    INSERT INTO skills_pending_taxonomy 
                        (raw_skill, occurrences, suggested_domain, suggested_canonical, 
                         suggested_confidence, found_in_jobs, llm_reasoning)
                    VALUES (%s, 1, %s, %s, %s, ARRAY[%s], %s)
                    ON CONFLICT (raw_skill) DO UPDATE SET
                        occurrences = skills_pending_taxonomy.occurrences + 1,
                        found_in_jobs = array_append(skills_pending_taxonomy.found_in_jobs, %s)
                """, (
                    f"{raw_skill} (EN: {english_skill})",
                    suggestion.get('domain'),
                    suggestion.get('canonical_name'),
                    suggestion.get('confidence', 0.8),
                    job_id,
                    suggestion.get('reasoning'),
                    job_id
                ))
                conn.commit()
            except Exception as e:
                print(f"         ⚠️  Error saving to pending: {e}")
                conn.rollback()
    
    cur.close()

def save_to_posting(conn, job_id, mapped_skills, raw_skills, unmapped_skills, processing_time):
    """Save results to postings table and log"""
    
    cur = conn.cursor()
    
    try:
        # Save mapped skills to postings.skill_keywords
        skills_json = json.dumps(mapped_skills)
        
        cur.execute("""
            UPDATE postings
            SET skill_keywords = %s::jsonb,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
        """, (skills_json, job_id))
        
        # Log extraction attempt
        cur.execute("""
            INSERT INTO skill_extraction_log
                (job_id, raw_skills_found, mapped_skills, unmapped_skills, 
                 extraction_method, llm_model, processing_time_seconds, success)
            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
        """, (
            job_id,
            raw_skills,
            mapped_skills,
            unmapped_skills,
            'hybrid_option_c',
            LLM_MODEL,
            processing_time
        ))
        
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        cur.close()
        print(f"    ⚠️  Database error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Hybrid skill extraction (Option C)')
    parser.add_argument('--job-id', type=str, help='Process specific job ID')
    parser.add_argument('--limit', type=int, help='Limit number of jobs')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    args = parser.parse_args()
    
    print("=" * 80)
    print("🔬 HYBRID SKILL EXTRACTION - OPTION C")
    print("=" * 80)
    print("Phase 1: Extract RAW skills from text")
    print("Phase 2: Map to taxonomy using fuzzy matching + LLM")
    print("Phase 3: Track unmapped skills for review")
    print()
    
    # Connect
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Load taxonomy
    print("📚 Loading taxonomy...")
    taxonomy_skills = load_taxonomy(conn)
    print(f"   Loaded {len(taxonomy_skills)} taxonomy skills")
    
    synonyms = load_synonyms(conn)
    print(f"   Loaded {len(synonyms)} synonym mappings")
    
    # Get taxonomy domains
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT parent_skill FROM skill_hierarchy WHERE parent_skill IS NOT NULL")
    taxonomy_domains = [row[0] for row in cur.fetchall()]
    cur.close()
    print(f"   Loaded {len(taxonomy_domains)} domains")
    
    # Clear existing skill_keywords
    if not args.dry_run:
        print("\n🗑️  Clearing existing skill_keywords...")
        cur = conn.cursor()
        cur.execute("UPDATE postings SET skill_keywords = NULL WHERE extracted_summary IS NOT NULL")
        cleared = cur.rowcount
        conn.commit()
        cur.close()
        print(f"   Cleared {cleared} postings")
    
    # Get postings to process
    print("\n📋 Finding postings to process...")
    cur = conn.cursor()
    
    if args.job_id:
        cur.execute("""
            SELECT job_id, job_title, extracted_summary
            FROM postings
            WHERE job_id = %s AND extracted_summary IS NOT NULL
        """, (args.job_id,))
    else:
        query = """
            SELECT job_id, job_title, extracted_summary
            FROM postings
            WHERE extracted_summary IS NOT NULL
            ORDER BY updated_at DESC
        """
        if args.limit:
            query += f" LIMIT {args.limit}"
        cur.execute(query)
    
    postings = cur.fetchall()
    cur.close()
    print(f"   Found {len(postings)} postings")
    
    if not postings:
        print("\n✅ No postings to process")
        conn.close()
        return
    
    # Process
    print("\n" + "=" * 80)
    print("PROCESSING")
    print("=" * 80)
    
    total_raw = 0
    total_mapped = 0
    total_unmapped = 0
    
    for i, (job_id, job_title, summary) in enumerate(postings, 1):
        print(f"\n[{i}/{len(postings)}] Job {job_id}: {job_title[:60]}...")
        start_time = time.time()
        
        if args.dry_run:
            print("  [DRY RUN]")
            continue
        
        # Phase 1: Extract raw skills
        print("  📝 Phase 1: Extracting raw skills...")
        raw_skills = extract_raw_skills(summary)
        print(f"     Found {len(raw_skills)} raw skills")
        total_raw += len(raw_skills)
        
        if not raw_skills:
            print("     ⚠️  No skills extracted")
            continue
        
        # Phase 2: Map to taxonomy
        print("  🗺️  Phase 2: Mapping to taxonomy...")
        mapped, unmapped = map_skills_to_taxonomy(raw_skills, taxonomy_skills, synonyms, conn)
        print(f"     ✓ Mapped: {len(mapped)}, ✗ Unmapped: {len(unmapped)}")
        total_mapped += len(mapped)
        total_unmapped += len(unmapped)
        
        # Phase 3: Track unmapped
        if unmapped:
            print("  💡 Phase 3: Suggesting taxonomy placement...")
            track_unmapped_skills(unmapped, job_id, taxonomy_domains, conn)
        
        # Save
        processing_time = time.time() - start_time
        if save_to_posting(conn, job_id, mapped, raw_skills, unmapped, processing_time):
            print(f"  ✓ Saved ({processing_time:.1f}s)")
        else:
            print(f"  ✗ Save failed")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Raw skills extracted: {total_raw}")
    print(f"✓ Mapped to taxonomy: {total_mapped} ({total_mapped/total_raw*100 if total_raw > 0 else 0:.1f}%)")
    print(f"✗ Unmapped (new skills): {total_unmapped} ({total_unmapped/total_raw*100 if total_raw > 0 else 0:.1f}%)")
    
    # Show pending review
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), SUM(occurrences)
        FROM skills_pending_taxonomy
        WHERE review_status = 'pending'
    """)
    pending_count, pending_occurrences = cur.fetchone()
    cur.close()
    
    if pending_count:
        print(f"\n💡 {pending_count} unique new skills need review ({pending_occurrences} total occurrences)")
        print("   Check: SELECT * FROM skills_pending_taxonomy ORDER BY occurrences DESC;")
    
    conn.close()

if __name__ == '__main__':
    main()
