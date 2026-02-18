"""
Documents router — user document library.

Documents are valuable artifacts created by TY actors:
- Doug reports, newsletters
- Match analysis documents
- Generated cover letters
- Resume optimizations

Unlike messages (transient), documents have lasting value.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime

from api.deps import get_db, require_user
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# ============================================================
# Models
# ============================================================

DocType = Literal["doug_report", "newsletter", "cover_letter", "match_analysis", "resume", "other"]

class Document(BaseModel):
    document_id: int
    doc_type: str
    title: str
    content: Optional[str]
    metadata: Optional[dict]
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DocumentSummary(BaseModel):
    """Lightweight document for list views."""
    document_id: int
    doc_type: str
    title: str
    created_by: str
    created_at: datetime
    preview: Optional[str]  # First 200 chars


class CreateDocumentRequest(BaseModel):
    doc_type: str
    title: str
    content: str
    metadata: Optional[dict] = None
    created_by: str = "system"


# ============================================================
# Endpoints
# ============================================================

@router.get("/")
async def list_documents(
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    created_by: Optional[str] = Query(None, description="Filter by creator (doug, mira, etc)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    List user's documents with optional filtering.
    Returns summaries (no full content) for performance.
    """
    user_id = user["user_id"]
    with conn.cursor() as cur:

        query = """
            SELECT document_id, doc_type, title, created_by, created_at,
                   LEFT(content, 200) as preview
            FROM yogi_documents
            WHERE user_id = %s
        """
        params = [user_id]

        if doc_type:
            query += " AND doc_type = %s"
            params.append(doc_type)

        if created_by:
            query += " AND created_by = %s"
            params.append(created_by)

        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()

        # Get total count
        count_query = "SELECT COUNT(*) FROM yogi_documents WHERE user_id = %s"
        count_params = [user_id]
        if doc_type:
            count_query += " AND doc_type = %s"
            count_params.append(doc_type)
        if created_by:
            count_query += " AND created_by = %s"
            count_params.append(created_by)

        cur.execute(count_query, count_params)
        total = cur.fetchone()["count"]

    return {
        "documents": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/types")
async def get_document_types(
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get document types with counts for the current user."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT doc_type, COUNT(*) as count
            FROM yogi_documents
            WHERE user_id = %s
            GROUP BY doc_type
            ORDER BY count DESC
        """, (user["user_id"],))
        return {"types": [dict(r) for r in cur.fetchall()]}


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Get full document by ID."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT document_id, doc_type, title, content, metadata,
                   created_by, created_at, updated_at
            FROM yogi_documents
            WHERE document_id = %s AND user_id = %s
        """, (document_id, user["user_id"]))
        doc = cur.fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(doc)


@router.post("/")
async def create_document(
    request: CreateDocumentRequest,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Create a new document for the user.
    Typically called by actors (Doug, Mira) not directly by users.
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO yogi_documents (user_id, doc_type, title, content, metadata, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING document_id, created_at
        """, (
            user["user_id"],
            request.doc_type,
            request.title,
            request.content,
            request.metadata or {},
            request.created_by
        ))
        result = cur.fetchone()
    conn.commit()

    logger.info(f"Document created: {result['document_id']} for user {user['user_id']}")
    return {
        "document_id": result["document_id"],
        "created_at": result["created_at"]
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """Delete a document."""
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM yogi_documents
            WHERE document_id = %s AND user_id = %s
            RETURNING document_id
        """, (document_id, user["user_id"]))
        deleted = cur.fetchone()
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    conn.commit()
    logger.info(f"Document deleted: {document_id}")
    return {"deleted": True, "document_id": document_id}


# ============================================================
# Actor helper: Create document for a user
# ============================================================

def create_document_for_user(
    conn,
    user_id: int,
    doc_type: str,
    title: str,
    content: str,
    created_by: str,
    metadata: dict = None
) -> int:
    """
    Helper for actors to create documents.
    Returns document_id.
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO yogi_documents (user_id, doc_type, title, content, metadata, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING document_id
        """, (user_id, doc_type, title, content, metadata or {}, created_by))
        doc_id = cur.fetchone()["document_id"]
    conn.commit()

    logger.info(f"Document created by {created_by}: {doc_id} for user {user_id}")
    return doc_id
