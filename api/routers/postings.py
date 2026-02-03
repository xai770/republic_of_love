"""
Posting endpoints — job listings.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from api.deps import get_db, require_user

router = APIRouter(prefix="/postings", tags=["postings"])


class PostingStats(BaseModel):
    active_count: int
    total_count: int
    newest_date: Optional[datetime]


class PostingResponse(BaseModel):
    posting_id: int
    title: str
    company: Optional[str]
    location: Optional[str]
    source: Optional[str]
    url: Optional[str]
    created_at: Optional[datetime]
    
    
class PostingDetail(PostingResponse):
    job_description: Optional[str]
    extracted_summary: Optional[str]
    requirements: List[str]


@router.get("/stats", response_model=PostingStats)
def get_posting_stats(conn=Depends(get_db)):
    """
    Get posting statistics (no auth required for dashboard).
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE enabled = true) AS active_count,
                COUNT(*) AS total_count,
                MAX(first_seen_at) FILTER (WHERE enabled = true) AS newest_date
            FROM postings
        """)
        row = cur.fetchone()
        return PostingStats(
            active_count=row['active_count'] or 0,
            total_count=row['total_count'] or 0,
            newest_date=row['newest_date']
        )


@router.get("/", response_model=List[PostingResponse])
def list_postings(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    List active job postings.
    """
    with conn.cursor() as cur:
        if search:
            cur.execute("""
                SELECT posting_id, job_title as title, posting_name as company, 
                       location_city as location, source as source, 
                       external_url as url, created_at
                FROM postings
                WHERE enabled = true
                  AND (job_title ILIKE %s OR posting_name ILIKE %s)
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (f'%{search}%', f'%{search}%', limit, offset))
        else:
            cur.execute("""
                SELECT posting_id, job_title as title, posting_name as company,
                       location_city as location, source as source, 
                       external_url as url, created_at
                FROM postings
                WHERE enabled = true
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
        
        return [PostingResponse(**row) for row in cur.fetchall()]


@router.get("/{posting_id}", response_model=PostingDetail)
def get_posting(posting_id: int, user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Get a specific posting with full details.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT posting_id, job_title as title, posting_name as company,
                   location_city as location, source as source, 
                   external_url as url, created_at,
                   job_description, extracted_summary
            FROM postings
            WHERE posting_id = %s
        """, (posting_id,))
        posting = cur.fetchone()
        
        if not posting:
            raise HTTPException(status_code=404, detail="Posting not found")
        
        # Get requirements from posting_facets
        cur.execute("""
            SELECT DISTINCT skill
            FROM posting_facets
            WHERE posting_id = %s AND skill IS NOT NULL
            ORDER BY skill
        """, (posting_id,))
        requirements = [row['skill'] for row in cur.fetchall()]
        
        return PostingDetail(
            **{k: v for k, v in posting.items()},
            requirements=requirements
        )
