#!/usr/bin/env python3
"""
doug__newsletter_C.py - Doug's daily newsletter generator

PURPOSE:
Doug creates a daily newsletter for job seekers with:
1. Job market trends
2. Interview tips
3. Industry news
4. Salary insights
5. Skills in demand

This runs daily (cron) and stores newsletters for Mira to share.

Input:  Topics config + DDG searches
Output: yogi_newsletters table

Usage:
    # Generate today's newsletter:
    python3 actors/doug__newsletter_C.py
    
    # Generate for specific date:
    python3 actors/doug__newsletter_C.py --date 2026-02-05
    
    # Preview only (don't save):
    python3 actors/doug__newsletter_C.py --preview

Author: Arden
Date: 2026-02-05
"""

import json
import sys
import re
import subprocess
import argparse
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, date

import psycopg2.extras
import requests

# ============================================================================
# SETUP
# ============================================================================

import os
from core.database import get_connection_raw, return_connection
from core.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
LLM_MODEL = "qwen2.5:7b"

# Newsletter topics to search
NEWSLETTER_TOPICS = [
    {
        'id': 'job_market',
        'name_de': 'Arbeitsmarkt-Trends',
        'name_en': 'Job Market Trends',
        'queries': [
            'Arbeitsmarkt Deutschland 2026 Trends',
            'Stellenmarkt aktuelle Entwicklung',
            'Fachkräftemangel Deutschland aktuell'
        ]
    },
    {
        'id': 'tech_jobs',
        'name_de': 'Tech & IT Karriere',
        'name_en': 'Tech & IT Careers',
        'queries': [
            'IT Jobs Deutschland Gehalt 2026',
            'Software Entwickler gefragt Branchen',
            'KI Künstliche Intelligenz Jobs Deutschland'
        ]
    },
    {
        'id': 'interview_tips',
        'name_de': 'Bewerbungstipps',
        'name_en': 'Interview Tips',
        'queries': [
            'Vorstellungsgespräch Tipps 2026',
            'Bewerbung Fehler vermeiden',
            'Gehaltsverhandlung Strategie'
        ]
    },
    {
        'id': 'skills_demand',
        'name_de': 'Gefragte Skills',
        'name_en': 'Skills in Demand',
        'queries': [
            'gefragte Fähigkeiten Arbeitsmarkt 2026',
            'Weiterbildung Karriere Deutschland',
            'Zukunftssichere Berufe'
        ]
    },
    {
        'id': 'work_culture',
        'name_de': 'Arbeitskultur',
        'name_en': 'Work Culture',
        'queries': [
            'Remote Work Deutschland Trend',
            'Work-Life-Balance Unternehmen',
            'New Work Konzepte Arbeitgeber'
        ]
    }
]

# Doug's newsletter personality - German
DOUG_NEWSLETTER_SYSTEM_DE = """Du bist Doug, der Karriere-Assistent bei talent.yoga.
Du schreibst einen täglichen Newsletter für Jobsuchende in Deutschland.

Dein Stil:
- Freundlich und motivierend
- Informativ aber nicht trocken
- Mit praktischen Tipps
- Gelegentlich humorvoll

Strukturiere den Newsletter mit klaren Abschnitten.
Verwende Emojis sparsam aber passend.
Halte jeden Abschnitt prägnant (2-3 Absätze).
Antworte IMMER auf Deutsch."""

# Doug's newsletter personality - English
DOUG_NEWSLETTER_SYSTEM_EN = """You are Doug, the career assistant at talent.yoga.
You write a daily newsletter for job seekers in Germany.

Your style:
- Friendly and motivating
- Informative but not dry
- With practical tips
- Occasionally humorous

Structure the newsletter with clear sections.
Use emojis sparingly but appropriately.
Keep each section concise (2-3 paragraphs).
Always respond in English."""


def search_duckduckgo(query: str) -> str:
    """Search DuckDuckGo and return results."""
    try:
        result = subprocess.run(
            ['ddgr', '--json', '--num', '5', query],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0 and result.stdout:
            results = json.loads(result.stdout)
            output = []
            
            for i, item in enumerate(results[:5], 1):
                title = item.get('title', 'No title')
                url = item.get('url', '')
                abstract = item.get('abstract', '')
                output.append(f"{i}. {title}\n   {url}\n   {abstract}")
            
            return "\n\n".join(output)
        else:
            return ""
            
    except Exception as e:
        logger.warning(f"DDG search failed: {e}")
        return ""


def gather_topic_research(topics: List[Dict], max_topics: int = 4) -> Dict[str, str]:
    """Search for each topic and gather results."""
    research = {}
    
    for topic in topics[:max_topics]:
        topic_id = topic['id']
        logger.info(f"Searching topic: {topic['name_de']}")
        
        all_results = []
        for query in topic['queries'][:2]:  # Limit queries per topic
            result = search_duckduckgo(query)
            if result:
                all_results.append(result)
            time.sleep(1)  # Be nice to DDG
        
        research[topic_id] = {
            'name_de': topic['name_de'],
            'name_en': topic['name_en'],
            'results': "\n\n---\n\n".join(all_results)
        }
    
    return research


def generate_newsletter(
    research: Dict[str, Any],
    for_date: date,
    language: str = 'de'
) -> str:
    """Use LLM to generate Doug's newsletter."""
    
    # Build context from research
    context_parts = []
    for topic_id, data in research.items():
        topic_name = data['name_de'] if language == 'de' else data['name_en']
        if data['results']:
            context_parts.append(f"**{topic_name}:**\n{data['results']}")
    
    context = "\n\n=====\n\n".join(context_parts)
    
    # Select system prompt
    system_prompt = DOUG_NEWSLETTER_SYSTEM_DE if language == 'de' else DOUG_NEWSLETTER_SYSTEM_EN
    
    # Date formatting
    if language == 'de':
        months_de = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 
                     'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
        weekdays_de = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        date_str = f"{weekdays_de[for_date.weekday()]}, {for_date.day}. {months_de[for_date.month]} {for_date.year}"
        
        prompt = f"""Schreibe den talent.yoga Newsletter für {date_str}.

**Recherche-Ergebnisse von heute:**
{context}

Erstelle einen Newsletter mit diesen Abschnitten:
1. **Begrüßung** - Kurze, motivierende Einleitung
2. **Arbeitsmarkt aktuell** - Was gibt es Neues?
3. **Karriere-Tipp des Tages** - Ein praktischer Ratschlag
4. **Skill-Spotlight** - Eine gefragte Fähigkeit hervorheben
5. **Abschluss** - Ermutigung und Ausblick

Halte es unter 600 Wörtern. Verwende Markdown.
Wenn Infos fehlen, sei kreativ aber hilfreich."""

    else:
        date_str = for_date.strftime("%A, %B %d, %Y")
        
        prompt = f"""Write the talent.yoga newsletter for {date_str}.

**Today's research results:**
{context}

Create a newsletter with these sections:
1. **Greeting** - Short, motivating intro
2. **Job Market Update** - What's new?
3. **Career Tip of the Day** - One practical piece of advice
4. **Skill Spotlight** - Highlight an in-demand skill
5. **Closing** - Encouragement and outlook

Keep it under 600 words. Use Markdown.
If info is missing, be creative but helpful."""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                'model': LLM_MODEL,
                'prompt': prompt,
                'system': system_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.8,  # Slightly more creative for newsletter
                    'num_predict': 1500
                }
            },
            timeout=180
        )
        
        if resp.status_code == 200:
            response_text = resp.json().get('response', '')
            # Strip thinking tags if present
            response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
            return response_text
        else:
            logger.error(f"LLM error: {resp.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return None


# ============================================================================
# REVIEW CYCLE - QA for newsletter content
# ============================================================================

GRADER_SYSTEM = """Du bist ein strenger Qualitätsprüfer für deutsche Newsletter.
Prüfe den Newsletter auf:
1. Grammatik und Rechtschreibung
2. Logische Fehler oder Unsinn
3. Falsche Anreden - WICHTIG: "Lieferanten" statt "Leser" ist ein KRITISCHER FEHLER!
4. Unprofessionelle oder unpassende Formulierungen
5. Fehlende oder unvollständige Abschnitte

KRITISCHE FEHLER (immer [FAIL]):
- "Lieferanten" in einer Begrüßung (sollte "Leser/innen" oder "Leserinnen und Leser" sein)
- Chinesische oder andere fremde Zeichen im deutschen Text
- Komplett fehlende Abschnitte

Sei kritisch! Bei kritischen Fehlern IMMER [FAIL].
Antworte IMMER auf Deutsch."""

IMPROVER_SYSTEM = """Du bist ein erfahrener Redakteur für Karriere-Newsletter.
Deine Aufgabe ist es, den Newsletter basierend auf dem Feedback zu verbessern.
Behalte den Stil und die Struktur bei, korrigiere aber alle genannten Probleme.
Antworte IMMER auf Deutsch."""


def grade_newsletter(newsletter: str, language: str = 'de') -> dict:
    """
    Grade the newsletter using mistral model.
    
    Returns:
        {'passed': bool, 'feedback': str, 'issues': list}
    """
    if language == 'de':
        prompt = f"""Prüfe diesen Newsletter auf Qualität:

---NEWSLETTER START---
{newsletter}
---NEWSLETTER END---

Prüfe auf:
1. Grammatik- und Rechtschreibfehler
2. Falsche oder unsinnige Wörter (z.B. "Lieferanten" statt "Leser/innen")
3. Logische Fehler oder halluzinierte Fakten
4. Unprofessionelle Formulierungen
5. Fehlende Abschnitte (Begrüßung, Arbeitsmarkt, Tipp, Skill-Spotlight, Abschluss)

Antwortformat:
[PASS] wenn der Newsletter gut ist (kleinere Stilfragen ignorieren)
[FAIL] wenn es echte Probleme gibt

Nach [PASS] oder [FAIL]:
- Liste die gefundenen Probleme auf
- Gib konkretes Feedback zur Verbesserung

Beginne deine Antwort mit [PASS] oder [FAIL]."""
    else:
        prompt = f"""Review this newsletter for quality:

---NEWSLETTER START---
{newsletter}
---NEWSLETTER END---

Check for:
1. Grammar and spelling errors
2. Wrong or nonsensical words
3. Logical errors or hallucinated facts
4. Unprofessional phrasing
5. Missing sections (Greeting, Market Update, Tip, Skill Spotlight, Closing)

Response format:
[PASS] if newsletter is good (ignore minor style issues)
[FAIL] if there are real problems

After [PASS] or [FAIL]:
- List found issues
- Give concrete improvement feedback

Start your response with [PASS] or [FAIL]."""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                'model': 'mistral:latest',  # Use different model for grading
                'prompt': prompt,
                'system': GRADER_SYSTEM,
                'stream': False,
                'options': {
                    'temperature': 0.3,  # More deterministic for grading
                    'num_predict': 800
                }
            },
            timeout=120
        )
        
        if resp.status_code == 200:
            response_text = resp.json().get('response', '')
            response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
            
            passed = response_text.strip().startswith('[PASS]')
            
            return {
                'passed': passed,
                'feedback': response_text,
                'raw_response': response_text
            }
        else:
            logger.error(f"Grader LLM error: {resp.status_code}")
            return {'passed': True, 'feedback': 'Grading failed, auto-pass', 'raw_response': ''}
            
    except Exception as e:
        logger.error(f"Grader request failed: {e}")
        return {'passed': True, 'feedback': f'Grading error: {e}', 'raw_response': ''}


def improve_newsletter(newsletter: str, feedback: str, language: str = 'de') -> str:
    """
    Improve the newsletter based on grader feedback.
    
    Returns improved newsletter text.
    """
    if language == 'de':
        prompt = f"""Verbessere diesen Newsletter basierend auf dem Feedback:

---ORIGINAL NEWSLETTER---
{newsletter}
---END ORIGINAL---

---FEEDBACK VOM PRÜFER---
{feedback}
---END FEEDBACK---

Aufgaben:
1. Korrigiere ALLE genannten Probleme
2. Behalte die Struktur und den Stil bei
3. Füge keine neuen Informationen hinzu
4. Gib NUR den verbesserten Newsletter zurück, keine Erklärungen

Verbesserter Newsletter:"""
    else:
        prompt = f"""Improve this newsletter based on feedback:

---ORIGINAL NEWSLETTER---
{newsletter}
---END ORIGINAL---

---GRADER FEEDBACK---
{feedback}
---END FEEDBACK---

Tasks:
1. Fix ALL mentioned issues
2. Keep structure and style
3. Don't add new information
4. Return ONLY the improved newsletter, no explanations

Improved newsletter:"""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                'model': LLM_MODEL,
                'prompt': prompt,
                'system': IMPROVER_SYSTEM,
                'stream': False,
                'options': {
                    'temperature': 0.5,
                    'num_predict': 1500
                }
            },
            timeout=180
        )
        
        if resp.status_code == 200:
            response_text = resp.json().get('response', '')
            response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
            return response_text
        else:
            logger.error(f"Improver LLM error: {resp.status_code}")
            return newsletter  # Return original if improvement fails
            
    except Exception as e:
        logger.error(f"Improver request failed: {e}")
        return newsletter


def generate_newsletter_with_review(
    research: Dict[str, Any],
    for_date: date,
    language: str = 'de',
    max_iterations: int = 3
) -> tuple:
    """
    Generate newsletter with review cycle.
    
    Returns:
        (newsletter_text, review_log)
    """
    review_log = []
    
    # Initial generation
    logger.info("Generating initial newsletter...")
    newsletter = generate_newsletter(research, for_date, language)
    
    if not newsletter:
        return None, [{'iteration': 0, 'error': 'Initial generation failed'}]
    
    review_log.append({
        'iteration': 0,
        'action': 'generate',
        'length': len(newsletter)
    })
    
    # Review cycle
    for i in range(max_iterations):
        logger.info(f"Review iteration {i+1}/{max_iterations}...")
        
        # Grade
        grade_result = grade_newsletter(newsletter, language)
        review_log.append({
            'iteration': i + 1,
            'action': 'grade',
            'passed': grade_result['passed'],
            'feedback_preview': grade_result['feedback'][:200] + '...' if len(grade_result['feedback']) > 200 else grade_result['feedback']
        })
        
        if grade_result['passed']:
            logger.info(f"✅ Newsletter passed review on iteration {i+1}")
            return newsletter, review_log
        
        # Improve if failed
        logger.info(f"❌ Newsletter failed review, improving...")
        newsletter = improve_newsletter(newsletter, grade_result['feedback'], language)
        review_log.append({
            'iteration': i + 1,
            'action': 'improve',
            'length': len(newsletter)
        })
    
    # Final grade after all iterations
    final_grade = grade_newsletter(newsletter, language)
    review_log.append({
        'iteration': max_iterations + 1,
        'action': 'final_grade',
        'passed': final_grade['passed'],
        'feedback_preview': final_grade['feedback'][:200] + '...'
    })
    
    if not final_grade['passed']:
        logger.warning("Newsletter still has issues after max iterations, publishing anyway")
    
    return newsletter, review_log


def save_newsletter(conn, newsletter: str, for_date: date, language: str = 'de') -> int:
    """Save newsletter to database."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Check if newsletter already exists for this date
    cur.execute("""
        SELECT newsletter_id FROM yogi_newsletters
        WHERE newsletter_date = %s AND language = %s
    """, (for_date, language))
    
    existing = cur.fetchone()
    
    if existing:
        # Update existing
        cur.execute("""
            UPDATE yogi_newsletters
            SET content = %s, generated_at = NOW()
            WHERE newsletter_id = %s
            RETURNING newsletter_id
        """, (newsletter, existing['newsletter_id']))
        newsletter_id = existing['newsletter_id']
        logger.info(f"Updated existing newsletter {newsletter_id}")
    else:
        # Insert new
        cur.execute("""
            INSERT INTO yogi_newsletters (newsletter_date, language, content, generated_at)
            VALUES (%s, %s, %s, NOW())
            RETURNING newsletter_id
        """, (for_date, language, newsletter))
        newsletter_id = cur.fetchone()['newsletter_id']
        logger.info(f"Created new newsletter {newsletter_id}")
    
    conn.commit()
    return newsletter_id


def get_latest_newsletter(conn, language: str = 'de') -> Optional[Dict]:
    """Get the most recent newsletter."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT newsletter_id, newsletter_date, language, content, generated_at
        FROM yogi_newsletters
        WHERE language = %s
        ORDER BY newsletter_date DESC
        LIMIT 1
    """, (language,))
    result = cur.fetchone()
    return dict(result) if result else None


def get_newsletter_for_date(conn, for_date: date, language: str = 'de') -> Optional[Dict]:
    """Get newsletter for specific date."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT newsletter_id, newsletter_date, language, content, generated_at
        FROM yogi_newsletters
        WHERE newsletter_date = %s AND language = %s
    """, (for_date, language))
    result = cur.fetchone()
    return dict(result) if result else None


def ensure_table_exists(conn):
    """Create newsletter table if not exists."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS yogi_newsletters (
            newsletter_id SERIAL PRIMARY KEY,
            newsletter_date DATE NOT NULL,
            language VARCHAR(5) DEFAULT 'de',
            content TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(newsletter_date, language)
        )
    """)
    conn.commit()
    logger.info("Newsletter table ready")


def generate_daily_newsletter(
    for_date: Optional[date] = None,
    language: str = 'de',
    preview_only: bool = False,
    skip_review: bool = False
) -> Optional[str]:
    """Main function: generate and save daily newsletter.
    
    Args:
        for_date: Date for the newsletter (default: today)
        language: 'de' or 'en'
        preview_only: If True, don't save to database
        skip_review: If True, skip the QA review cycle
    """
    
    if for_date is None:
        for_date = date.today()
    
    logger.info("Doug is writing the newsletter for %s...", for_date)
    
    # Gather research
    logger.info("Researching topics...")
    research = gather_topic_research(NEWSLETTER_TOPICS, max_topics=4)
    
    topics_with_data = sum(1 for r in research.values() if r['results'])
    logger.info("Found data for %s topics", topics_with_data)
    
    # Generate newsletter (with or without review)
    if skip_review:
        logger.info("Writing newsletter (no review)...")
        newsletter = generate_newsletter(research, for_date, language)
        review_log = None
    else:
        logger.info("Writing newsletter with QA review...")
        newsletter, review_log = generate_newsletter_with_review(research, for_date, language, max_iterations=3)
        
        # Print review summary
        if review_log:
            grades = [r for r in review_log if r.get('action') == 'grade']
            improvements = [r for r in review_log if r.get('action') == 'improve']
            final_passed = grades[-1]['passed'] if grades else True
            
            logger.info("Review: %s grades,%s improvements", len(grades), len(improvements))
            if final_passed:
                logger.info("Passed QA review")
            else:
                logger.warning("Published with warnings (max iterations reached)")
    
    if not newsletter:
        logger.error("Failed to generate newsletter")
        return None
    
    logger.info("Newsletter generated (%s chars)", len(newsletter))
    
    if preview_only:
        logger.info("=" * 60)
        logger.info("%s", newsletter)
        logger.info("=" * 60)
        if review_log:
            logger.info("Review Log:")
            for entry in review_log:
                logger.info("%s", entry)
        return newsletter
    
    # Save to database
    conn = get_connection_raw()
    try:
        ensure_table_exists(conn)
        newsletter_id = save_newsletter(conn, newsletter, for_date, language)
        logger.info("Newsletter saved (ID: %s)", newsletter_id)
        return newsletter
    finally:
        return_connection(conn)


# ============================================================================
# API FUNCTIONS — For Mira to access newsletters
# ============================================================================

def get_todays_newsletter(language: str = 'de') -> Optional[str]:
    """Get today's newsletter content. Returns None if not generated yet."""
    conn = get_connection_raw()
    try:
        ensure_table_exists(conn)
        newsletter = get_newsletter_for_date(conn, date.today(), language)
        return newsletter['content'] if newsletter else None
    finally:
        return_connection(conn)


def get_latest_newsletter_content(language: str = 'de') -> Optional[Dict]:
    """Get the latest newsletter with metadata."""
    conn = get_connection_raw()
    try:
        ensure_table_exists(conn)
        return get_latest_newsletter(conn, language)
    finally:
        return_connection(conn)


def main():
    parser = argparse.ArgumentParser(description="Doug's daily newsletter generator")
    parser.add_argument('--date', '-d', type=str, help='Date for newsletter (YYYY-MM-DD)')
    parser.add_argument('--preview', '-p', action='store_true', help='Preview only, don\'t save')
    parser.add_argument('--language', '-l', type=str, default='de', choices=['de', 'en'],
                        help='Newsletter language (de or en)')
    parser.add_argument('--skip-review', '-s', action='store_true', 
                        help='Skip QA review cycle (faster but may have errors)')
    
    args = parser.parse_args()
    
    for_date = None
    if args.date:
        try:
            for_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logger.error("Invalid date format: %s. Use YYYY-MM-DD", args.date)
            sys.exit(1)
    
    generate_daily_newsletter(
        for_date=for_date,
        language=args.language,
        preview_only=args.preview,
        skip_review=args.skip_review
    )


if __name__ == '__main__':
    main()
