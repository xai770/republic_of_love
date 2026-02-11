#!/usr/bin/env python3
"""
mira_job_tools.py - Job Search Tools for Mira
==============================================

Provides job search and exploration capabilities for Mira.
Unlike Navigator (which is for taxonomy classification), this is 
designed for conversational job discovery.

Tools available:
    - search_jobs: Semantic search for jobs
    - get_job_details: Get full details of a specific job
    - explain_match: Explain why a job matches a yogi's profile

Author: Arden
Date: 2026-02-05
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """A job search result."""
    posting_id: int
    job_title: str
    company: str
    location: str
    beruf: Optional[str]
    qualification_level: Optional[int]  # 1-4 from berufenet
    match_score: Optional[float]  # 0-100 if comparing to profile
    summary_preview: str  # First ~200 chars of summary


@dataclass
class JobSearchResults:
    """Results from a job search."""
    query: str
    total_found: int
    jobs: List[JobResult]
    search_type: str  # 'semantic', 'keyword', 'location'


# =============================================================================
# INTENT DETECTION
# =============================================================================

def detect_job_search_intent(message: str) -> Optional[Dict[str, Any]]:
    """
    Detect if user is asking to search for jobs.
    
    Returns dict with search parameters if detected:
        {
            'query': str,  # The search query
            'location': Optional[str],  # Location filter if mentioned
            'qualification_level': Optional[int],  # If they mention experience level
            'intent_type': 'search' | 'browse' | 'specific'
        }
    
    Returns None if not a job search request.
    """
    message_lower = message.lower()
    
    # Not a job search if just chatting
    chat_phrases = ['how are you', 'wie geht', 'hello', 'hallo', 'hi', 'thanks', 'danke']
    if any(phrase in message_lower for phrase in chat_phrases) and len(message_lower) < 20:
        return None
    
    # Job search patterns - German
    de_patterns = [
        (r'(?:suche|such|finde|zeig).*?(?:jobs?|stellen?|arbeit)', 'search'),
        (r'(?:gibt es|hast du|habt ihr).*?(?:jobs?|stellen?)', 'browse'),
        (r'(?:jobs?|stellen?|arbeit).*?(?:als|für|in|bei)', 'search'),
        (r'(?:was|welche).*?(?:jobs?|stellen?).*?(?:gibt es|hast du)', 'browse'),
        (r'(?:ich möchte|ich will|ich suche).*?(?:job|stelle|arbeit)', 'search'),
        (r'(?:developer|entwickler|ingenieur|mechaniker|pfleger|kaufmann).*?(?:job|stelle)', 'search'),
    ]
    
    # Job search patterns - English
    en_patterns = [
        (r'(?:find|search|show|look for).*?jobs?', 'search'),
        (r'(?:are there|do you have|any).*?jobs?', 'browse'),
        (r'jobs?\s+(?:as|for|in|at)', 'search'),
        (r'(?:what|which).*?jobs?\s+(?:are|do)', 'browse'),
        (r'(?:i want|i need|i\'m looking for).*?(?:job|work|position)', 'search'),
        (r'(?:developer|engineer|nurse|mechanic).*?(?:job|position)', 'search'),
    ]
    
    all_patterns = de_patterns + en_patterns
    
    for pattern, intent_type in all_patterns:
        if re.search(pattern, message_lower, re.IGNORECASE):
            # Extract the search query
            query = extract_search_query(message)
            location = extract_location(message)
            qual_level = extract_qualification_level(message)
            
            return {
                'query': query,
                'location': location,
                'qualification_level': qual_level,
                'intent_type': intent_type,
                'raw_message': message
            }
    
    return None


def extract_search_query(message: str) -> str:
    """Extract the core job search query from a message."""
    # Remove common filler words
    query = message.lower()
    
    # Remove request phrases
    removals = [
        r'^(?:ich suche|ich möchte|kannst du|zeig mir|finde|such)\s*',
        r'^(?:i want|i need|i\'m looking for|find me|show me|search for)\s*',
        r'\s*(?:jobs?|stellen?|positions?|arbeit)\s*$',
        r'\s*(?:bitte|please)\s*$',
        r'\s*(?:für mich|for me)\s*$',
    ]
    
    for pattern in removals:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE)
    
    # Remove location if present (we extract it separately)
    query = re.sub(r'\s+(?:in|bei|near|nahe)\s+[a-zäöüß]+$', '', query, flags=re.IGNORECASE)
    
    return query.strip() or message.strip()


def extract_location(message: str) -> Optional[str]:
    """Extract location from a job search message."""
    message_lower = message.lower()
    
    # Common German cities
    cities = [
        'berlin', 'münchen', 'munich', 'hamburg', 'köln', 'cologne',
        'frankfurt', 'stuttgart', 'düsseldorf', 'dortmund', 'essen',
        'leipzig', 'bremen', 'dresden', 'hannover', 'nürnberg', 'nuremberg',
        'duisburg', 'bochum', 'wuppertal', 'bielefeld', 'bonn', 'münster',
        'karlsruhe', 'mannheim', 'augsburg', 'wiesbaden', 'aachen',
    ]
    
    # Check for "in <city>" pattern
    loc_match = re.search(r'(?:in|bei|near|nahe)\s+([a-zäöüß]+)', message_lower)
    if loc_match:
        loc = loc_match.group(1)
        # Capitalize properly
        return loc.title()
    
    # Check if any city is mentioned
    for city in cities:
        if city in message_lower:
            return city.title()
    
    return None


def extract_qualification_level(message: str) -> Optional[int]:
    """Extract qualification/experience level from message."""
    message_lower = message.lower()
    
    # Level 1: Unskilled / Helper
    if any(w in message_lower for w in ['helper', 'helfer', 'ungelernt', 'ohne ausbildung', 'entry']):
        return 1
    
    # Level 2: Vocational training
    if any(w in message_lower for w in ['ausbildung', 'apprentice', 'fachkraft', 'facharbeiter']):
        return 2
    
    # Level 3: Professional / Technical
    if any(w in message_lower for w in ['techniker', 'meister', 'bachelor', 'professional']):
        return 3
    
    # Level 4: Expert / Master
    if any(w in message_lower for w in ['master', 'senior', 'expert', 'lead', 'architect', 'director']):
        return 4
    
    return None


# =============================================================================
# JOB SEARCH FUNCTIONS
# =============================================================================

async def search_jobs(
    conn, 
    query: str,
    location: Optional[str] = None,
    qualification_level: Optional[int] = None,
    profile_id: Optional[int] = None,
    limit: int = 5
) -> JobSearchResults:
    """
    Search for jobs using semantic similarity.
    
    Args:
        conn: Database connection
        query: Search query (job title, skills, etc.)
        location: Optional location filter
        qualification_level: Optional berufenet qualification level (1-4)
        profile_id: Optional profile ID to calculate match scores
        limit: Max results to return
    
    Returns:
        JobSearchResults with matching jobs
    """
    try:
        # First, try to get embedding for the query
        query_embedding = await get_query_embedding(query)
        
        with conn.cursor() as cur:
            if query_embedding:
                # Semantic search using embeddings
                results = await semantic_job_search(
                    cur, query_embedding, location, qualification_level, profile_id, limit
                )
                search_type = 'semantic'
            else:
                # Fallback to keyword search
                results = keyword_job_search(
                    cur, query, location, qualification_level, limit
                )
                search_type = 'keyword'
            
            return JobSearchResults(
                query=query,
                total_found=len(results),
                jobs=results,
                search_type=search_type
            )
    
    except Exception as e:
        logger.error(f"Job search error: {e}")
        return JobSearchResults(
            query=query,
            total_found=0,
            jobs=[],
            search_type='error'
        )


async def get_query_embedding(query: str) -> Optional[List[float]]:
    """Get embedding for a search query using Ollama."""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/embeddings',
                json={"model": "bge-m3:567m", "prompt": query}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
    except Exception as e:
        logger.warning(f"Embedding failed for query: {e}")
    
    return None


async def semantic_job_search(
    cur,
    query_embedding: List[float],
    location: Optional[str],
    qualification_level: Optional[int],
    profile_id: Optional[int],
    limit: int
) -> List[JobResult]:
    """Search jobs using vector similarity."""
    
    # Build the query with filters
    filters = ["p.status = 'active'"]
    params = []
    
    if location:
        filters.append("p.location ILIKE %s")
        params.append(f"%{location}%")
    
    if qualification_level:
        filters.append("b.qualification_level = %s")
        params.append(qualification_level)
    
    filter_clause = " AND ".join(filters)
    
    # Vector similarity search
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    sql = f"""
        SELECT 
            p.posting_id,
            p.job_title,
            COALESCE(p.posting_name, 'Unknown') as company,
            COALESCE(p.location, '') as location,
            p.beruf,
            b.qualification_level,
            LEFT(COALESCE(p.extracted_summary, p.job_description, ''), 200) as summary_preview,
            1 - (e.embedding <=> %s::vector) as similarity
        FROM postings p
        LEFT JOIN posting_embeddings e ON p.posting_id = e.posting_id
        LEFT JOIN berufenet b ON p.berufenet_id = b.berufenet_id
        WHERE {filter_clause}
          AND e.embedding IS NOT NULL
        ORDER BY e.embedding <=> %s::vector
        LIMIT %s
    """
    
    params = [embedding_str] + params + [embedding_str, limit]
    
    cur.execute(sql, params)
    
    results = []
    for row in cur.fetchall():
        results.append(JobResult(
            posting_id=row['posting_id'],
            job_title=row['job_title'],
            company=row['company'],
            location=row['location'],
            beruf=row['beruf'],
            qualification_level=row['qualification_level'],
            match_score=float(row['similarity']) * 100 if row['similarity'] else None,
            summary_preview=row['summary_preview']
        ))
    
    return results


def keyword_job_search(
    cur,
    query: str,
    location: Optional[str],
    qualification_level: Optional[int],
    limit: int
) -> List[JobResult]:
    """Fallback keyword-based search."""
    
    filters = ["p.status = 'active'"]
    params = []
    
    # Text search on job title and description
    filters.append("""(
        p.job_title ILIKE %s 
        OR p.extracted_summary ILIKE %s 
        OR p.beruf ILIKE %s
    )""")
    search_pattern = f"%{query}%"
    params.extend([search_pattern, search_pattern, search_pattern])
    
    if location:
        filters.append("p.location ILIKE %s")
        params.append(f"%{location}%")
    
    if qualification_level:
        filters.append("b.qualification_level = %s")
        params.append(qualification_level)
    
    filter_clause = " AND ".join(filters)
    
    sql = f"""
        SELECT 
            p.posting_id,
            p.job_title,
            COALESCE(p.posting_name, 'Unknown') as company,
            COALESCE(p.location, '') as location,
            p.beruf,
            b.qualification_level,
            LEFT(COALESCE(p.extracted_summary, p.job_description, ''), 200) as summary_preview
        FROM postings p
        LEFT JOIN berufenet b ON p.berufenet_id = b.berufenet_id
        WHERE {filter_clause}
        ORDER BY p.created_at DESC
        LIMIT %s
    """
    
    params.append(limit)
    cur.execute(sql, params)
    
    results = []
    for row in cur.fetchall():
        results.append(JobResult(
            posting_id=row['posting_id'],
            job_title=row['job_title'],
            company=row['company'],
            location=row['location'],
            beruf=row['beruf'],
            qualification_level=row['qualification_level'],
            match_score=None,  # No score for keyword search
            summary_preview=row['summary_preview']
        ))
    
    return results


# =============================================================================
# RESULT FORMATTING
# =============================================================================

def format_job_results_for_mira(
    results: JobSearchResults,
    language: str = 'de',
    uses_du: bool = True
) -> str:
    """
    Format job search results for Mira to include in her response.
    
    Returns a structured text that Mira can use conversationally.
    """
    if not results.jobs:
        if language == 'en':
            return f"I couldn't find any jobs matching '{results.query}'. Try different keywords or a broader search."
        else:
            if uses_du:
                return f"Ich konnte keine Jobs finden, die zu '{results.query}' passen. Versuch andere Stichwörter oder eine breitere Suche."
            else:
                return f"Ich konnte keine Stellen finden, die zu '{results.query}' passen. Versuchen Sie andere Stichwörter oder eine breitere Suche."
    
    # Build formatted result
    lines = []
    
    if language == 'en':
        lines.append(f"Found {results.total_found} jobs for '{results.query}':\n")
    else:
        lines.append(f"Ich habe {results.total_found} Stellen für '{results.query}' gefunden:\n")
    
    for i, job in enumerate(results.jobs, 1):
        qual_emoji = get_qualification_emoji(job.qualification_level)
        location_str = f" in {job.location}" if job.location else ""
        
        if job.match_score:
            lines.append(f"{i}. **{job.job_title}**{location_str} ({job.match_score:.0f}% match) {qual_emoji}")
        else:
            lines.append(f"{i}. **{job.job_title}**{location_str} {qual_emoji}")
        
        if job.summary_preview:
            preview = job.summary_preview[:100] + "..." if len(job.summary_preview) > 100 else job.summary_preview
            lines.append(f"   _{preview}_")
        
        lines.append("")
    
    if language == 'en':
        lines.append("Want details on any of these? Just ask!")
    else:
        if uses_du:
            lines.append("Möchtest du mehr Details zu einer davon? Frag einfach!")
        else:
            lines.append("Möchten Sie mehr Details zu einer davon? Fragen Sie einfach!")
    
    return "\n".join(lines)


def get_qualification_emoji(level: Optional[int]) -> str:
    """Get emoji indicator for qualification level."""
    if level is None:
        return ""
    
    emojis = {
        1: "🟢",  # Entry/Helper
        2: "🔵",  # Vocational
        3: "🟡",  # Professional
        4: "🔴",  # Expert
    }
    return emojis.get(level, "")


def get_qualification_label(level: Optional[int], language: str = 'de') -> str:
    """Get human-readable qualification level label."""
    if level is None:
        return ""
    
    if language == 'en':
        labels = {
            1: "Entry Level",
            2: "Vocational Training",
            3: "Professional/Technical",
            4: "Expert/Master",
        }
    else:
        labels = {
            1: "Einstieg/Helfer",
            2: "Ausbildung",
            3: "Fachkraft/Techniker",
            4: "Experte/Meister",
        }
    
    return labels.get(level, "")
