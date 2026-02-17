"""
Profile endpoints — CRUD for user profiles.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import json as _json
import tempfile
import os

from psycopg2.extras import Json

from api.deps import get_db, require_user

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _ensure_profile(user: dict, conn) -> int:
    """Return existing profile_id or create a new profile row for this user."""
    with conn.cursor() as cur:
        cur.execute("SELECT profile_id FROM profiles WHERE user_id = %s", (user['user_id'],))
        row = cur.fetchone()
        if row:
            return row['profile_id']
        # Auto-create with display_name as initial full_name
        display = user.get('display_name') or user.get('yogi_name') or 'New Yogi'
        email = user.get('email')
        cur.execute("""
            INSERT INTO profiles (full_name, email, user_id, profile_source)
            VALUES (%s, %s, %s, 'self')
            RETURNING profile_id
        """, (display, email, user['user_id']))
        conn.commit()
        return cur.fetchone()['profile_id']


class ProfileSkill(BaseModel):
    skill: str
    years: Optional[int] = None


class ProfileResponse(BaseModel):
    profile_id: int
    display_name: Optional[str]
    email: Optional[str]
    title: Optional[str]
    location: Optional[str]
    skills: List[str]
    skill_count: int
    # T010: Added fields for completeness calculation
    has_work_history: bool = False
    has_preferences: bool = False
    completeness: int = 0  # 0-100%


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None


class PreferencesUpdate(BaseModel):
    desired_roles: Optional[List[str]] = None
    desired_locations: Optional[List[str]] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    min_seniority: Optional[str] = None


class WorkHistoryCreate(BaseModel):
    company: str
    title: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_current: bool = False


class WorkHistoryResponse(BaseModel):
    work_history_id: int
    company: str
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    description: Optional[str]
    location: Optional[str]
    is_current: bool
    duration_months: Optional[int]


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Get the current user's profile.
    Returns profile linked to authenticated user.
    """
    # Auto-create profile if missing
    _ensure_profile(user, conn)

    with conn.cursor() as cur:
        # Get profile linked to this user (including preferences)
        cur.execute("""
            SELECT profile_id, full_name as display_name, email, 
                   current_title as title, desired_locations[1] as location,
                   desired_roles, desired_locations, skill_keywords
            FROM profiles
            WHERE user_id = %s
        """, (user['user_id'],))
        profile = cur.fetchone()
        
        # Parse skills from JSON array
        import json
        skill_keywords = profile['skill_keywords']
        skills = []
        if skill_keywords:
            if isinstance(skill_keywords, str):
                skill_keywords = json.loads(skill_keywords)
            skills = sorted(set(skill_keywords)) if skill_keywords else []
        
        # Check for work history
        cur.execute("""
            SELECT COUNT(*) as cnt FROM profile_work_history WHERE profile_id = %s
        """, (profile['profile_id'],))
        work_history_count = cur.fetchone()['cnt']
        has_work_history = work_history_count > 0
        
        # Check for preferences
        has_preferences = bool(profile['desired_roles'] or profile['desired_locations'])
        
        # T010: Calculate completeness
        # - Name: +10%
        # - Title: +10%  
        # - Location: +10%
        # - Work history (1+ entries): +30%
        # - Skills extracted: +20%
        # - Job preferences set: +20%
        completeness = 0
        if profile['display_name']:
            completeness += 10
        if profile['title']:
            completeness += 10
        if profile['location']:
            completeness += 10
        if has_work_history:
            completeness += 30
        if len(skills) > 0:
            completeness += 20
        if has_preferences:
            completeness += 20
        
        return ProfileResponse(
            profile_id=profile['profile_id'],
            display_name=profile['display_name'],
            email=profile['email'],
            title=profile['title'],
            location=profile['location'],
            skills=skills,
            skill_count=len(skills),
            has_work_history=has_work_history,
            has_preferences=has_preferences,
            completeness=completeness
        )


@router.put("/me", response_model=ProfileResponse)
def update_my_profile(
    update: ProfileUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Update the current user's profile.
    """
    with conn.cursor() as cur:
        # Ensure profile exists (auto-create for new users)
        profile_id = _ensure_profile(user, conn)
        
        # Build update query dynamically
        updates = []
        values = []
        if update.name is not None:
            updates.append("full_name = %s")
            values.append(update.name)
        if update.title is not None:
            updates.append("current_title = %s")
            values.append(update.title)
        if update.location is not None:
            updates.append("desired_locations = ARRAY[%s]")
            values.append(update.location)
        
        if updates:
            updates.append("updated_at = NOW()")
            values.append(profile_id)
            cur.execute(f"""
                UPDATE profiles SET {', '.join(updates)}
                WHERE profile_id = %s
            """, values)
            conn.commit()
        
    # Return updated profile
    return get_my_profile(user, conn)


@router.put("/me/preferences")
def update_my_preferences(
    prefs: PreferencesUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Update job search preferences (target roles, locations, salary, seniority).
    """
    with conn.cursor() as cur:
        profile_id = _ensure_profile(user, conn)
        
        # Build update query
        updates = []
        values = []
        
        if prefs.desired_roles is not None:
            updates.append("desired_roles = %s")
            values.append(prefs.desired_roles)
        if prefs.desired_locations is not None:
            updates.append("desired_locations = %s")
            values.append(prefs.desired_locations)
        if prefs.expected_salary_min is not None:
            updates.append("expected_salary_min = %s")
            values.append(prefs.expected_salary_min)
        if prefs.expected_salary_max is not None:
            updates.append("expected_salary_max = %s")
            values.append(prefs.expected_salary_max)
        if prefs.min_seniority is not None:
            updates.append("min_seniority = %s")
            values.append(prefs.min_seniority)
        
        if updates:
            updates.append("updated_at = NOW()")
            values.append(profile_id)
            cur.execute(f"""
                UPDATE profiles SET {', '.join(updates)}
                WHERE profile_id = %s
            """, values)
            conn.commit()
        
        return {"status": "ok", "message": "Preferences updated"}


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Get a specific profile by ID.
    Users can only view their own profile.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT profile_id, full_name as display_name, email, user_id
            FROM profiles
            WHERE profile_id = %s
        """, (profile_id,))
        profile = cur.fetchone()
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check ownership
        if profile['user_id'] != user['user_id']:
            raise HTTPException(status_code=403, detail="Cannot view other users' profiles")
        
        # Get skills from profiles.skill_keywords
        cur.execute("SELECT skill_keywords FROM profiles WHERE profile_id = %s", (profile_id,))
        row = cur.fetchone()
        skill_keywords = row['skill_keywords'] if row else None
        
        skills = []
        if skill_keywords:
            import json
            if isinstance(skill_keywords, str):
                skill_keywords = json.loads(skill_keywords)
            skills = sorted(set(skill_keywords)) if skill_keywords else []
        
        return ProfileResponse(
            profile_id=profile['profile_id'],
            display_name=profile['display_name'],
            email=profile['email'],
            title=None,
            location=None,
            skills=skills,
            skill_count=len(skills)
        )


# --- Work History Endpoints ---

@router.get("/me/work-history", response_model=List[WorkHistoryResponse])
def get_my_work_history(user: dict = Depends(require_user), conn=Depends(get_db)):
    """Get all work history entries for current user's profile."""
    with conn.cursor() as cur:
        cur.execute("SELECT profile_id FROM profiles WHERE user_id = %s", (user['user_id'],))
        profile = cur.fetchone()
        if not profile:
            return []  # No profile yet — return empty list
        
        cur.execute("""
            SELECT work_history_id, company_name as company, job_title as title,
                   start_date, end_date, job_description as description,
                   location, is_current, duration_months
            FROM profile_work_history
            WHERE profile_id = %s
            ORDER BY COALESCE(end_date, CURRENT_DATE) DESC, start_date DESC
        """, (profile['profile_id'],))
        
        return [WorkHistoryResponse(**row) for row in cur.fetchall()]


@router.post("/me/work-history", response_model=WorkHistoryResponse, status_code=201)
def add_work_history(
    entry: WorkHistoryCreate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Add a new work history entry."""
    with conn.cursor() as cur:
        profile_id = _ensure_profile(user, conn)
        
        cur.execute("""
            INSERT INTO profile_work_history 
                (profile_id, company_name, job_title, start_date, end_date, 
                 job_description, location, is_current, extraction_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING work_history_id, company_name as company, job_title as title,
                      start_date, end_date, job_description as description,
                      location, is_current, duration_months
        """, (
            profile_id, entry.company, entry.title,
            entry.start_date, entry.end_date, entry.description,
            entry.location, entry.is_current
        ))
        result = cur.fetchone()
        conn.commit()
        
        # TODO: Trigger Clara extraction async (P1.3 notes)
        
        return WorkHistoryResponse(**result)


@router.put("/me/work-history/{work_history_id}", response_model=WorkHistoryResponse)
def update_work_history(
    work_history_id: int,
    entry: WorkHistoryCreate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Update an existing work history entry."""
    with conn.cursor() as cur:
        # Verify ownership
        cur.execute("""
            SELECT wh.work_history_id 
            FROM profile_work_history wh
            JOIN profiles p ON wh.profile_id = p.profile_id
            WHERE wh.work_history_id = %s AND p.user_id = %s
        """, (work_history_id, user['user_id']))
        
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Work history entry not found")
        
        cur.execute("""
            UPDATE profile_work_history SET
                company_name = %s, job_title = %s, start_date = %s, end_date = %s,
                job_description = %s, location = %s, is_current = %s,
                extraction_status = 'pending',
                updated_at = NOW()
            WHERE work_history_id = %s
            RETURNING work_history_id, company_name as company, job_title as title,
                      start_date, end_date, job_description as description,
                      location, is_current, duration_months
        """, (
            entry.company, entry.title, entry.start_date, entry.end_date,
            entry.description, entry.location, entry.is_current,
            work_history_id
        ))
        result = cur.fetchone()
        conn.commit()
        
        # Clara extraction triggered via extraction_status='pending'
        # Run: python tools/run_pending_extractions.py
        
        return WorkHistoryResponse(**result)


@router.delete("/me/work-history/{work_history_id}", status_code=204)
def delete_work_history(
    work_history_id: int,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """Delete a work history entry."""
    with conn.cursor() as cur:
        # Verify ownership and delete
        cur.execute("""
            DELETE FROM profile_work_history wh
            USING profiles p
            WHERE wh.profile_id = p.profile_id
              AND wh.work_history_id = %s
              AND p.user_id = %s
            RETURNING wh.work_history_id
        """, (work_history_id, user['user_id']))
        
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Work history entry not found")
        
        conn.commit()
    
    return None


# --- CV Parsing ---

def parse_cv_text(text: str) -> List[dict]:
    """
    Parse CV text to extract work history using LLM.
    Returns list of work history entries.
    """
    import requests
    
    prompt = f"""Extract work history from this CV. Return a JSON array of jobs.

CV TEXT:
{text[:8000]}

Return ONLY a JSON array with this structure (no other text):
[
  {{
    "company": "Company Name",
    "title": "Job Title",
    "start_date": "YYYY-MM-DD or YYYY-MM",
    "end_date": "YYYY-MM-DD or YYYY-MM or null if current",
    "description": "Job description/responsibilities",
    "location": "City, Country or null",
    "is_current": true/false
  }}
]

Extract all work experiences. Use null for missing dates. Order by most recent first."""

    try:
        response = requests.post(
            os.getenv('OLLAMA_URL', 'http://localhost:11434') + '/api/generate',
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()["response"]
        
        # Extract JSON from response
        import json
        import re
        
        # Find JSON array in response
        match = re.search(r'\[[\s\S]*\]', result)
        if match:
            jobs = json.loads(match.group())
            # Normalize dates
            for job in jobs:
                if job.get('start_date') and len(job['start_date']) == 7:
                    job['start_date'] += '-01'
                if job.get('end_date') and len(job['end_date']) == 7:
                    job['end_date'] += '-01'
            return jobs
        return []
    except Exception as e:
        print(f"CV parse error: {e}")
        return []


@router.post("/me/parse-cv")
async def parse_cv(
    file: UploadFile = File(...),
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Parse uploaded CV (PDF/DOCX) and extract ANONYMIZED career data.
    
    Privacy-first:
    - File is processed in memory only (never written to disk permanently)
    - LLM extracts + anonymizes: real name → yogi_name, companies → generalized
    - PII safety net validates output before returning
    - Raw text is discarded after processing
    
    Returns anonymized structured profile for yogi confirmation.
    """
    filename = file.filename.lower()
    content = await file.read()
    
    text = ""
    
    try:
        if filename.endswith('.pdf'):
            import pymupdf
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            doc = pymupdf.open(tmp_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            os.unlink(tmp_path)
            
        elif filename.endswith(('.docx', '.doc')):
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            text = "\n".join(para.text for para in doc.paragraphs)
            
        elif filename.endswith('.txt'):
            text = content.decode('utf-8', errors='ignore')
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        
        # Get yogi_name for anonymization
        with conn.cursor() as cur:
            cur.execute("SELECT yogi_name FROM users WHERE user_id = %s", (user['user_id'],))
            row = cur.fetchone()
            yogi_name = row['yogi_name'] if row else None
        
        if not yogi_name:
            raise HTTPException(status_code=400, detail="Please set your yogi name first (chat with Mira)")
        
        # Anonymize with LLM + PII safety check
        from core.cv_anonymizer import extract_and_anonymize
        result = await extract_and_anonymize(
            cv_text=text,
            yogi_name=yogi_name,
            conn=conn
        )
        
        # Explicitly discard raw text
        del text
        del content
        
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


# --- CV Import (save anonymized data to profile) ---

class CVWorkEntry(BaseModel):
    employer_description: str = "a company"
    role: str = "unknown role"
    duration_years: Optional[float] = None
    industry: Optional[str] = None
    key_responsibilities: List[str] = []


class CVEducationEntry(BaseModel):
    level: str = "unknown"
    field: Optional[str] = None
    duration_years: Optional[float] = None


class CVImportRequest(BaseModel):
    """Anonymized CV data from parse-cv, reviewed/edited by the yogi."""
    current_title: Optional[str] = None
    career_level: Optional[str] = None
    years_experience: Optional[int] = None
    skills: List[str] = []
    languages: List[str] = []
    certifications: List[str] = []
    profile_summary: Optional[str] = None
    work_history: List[CVWorkEntry] = []
    education: List[CVEducationEntry] = []


@router.post("/me/import-cv")
def import_cv(
    data: CVImportRequest,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Save anonymized CV data to profile after yogi review.

    Flow: parse-cv → yogi reviews/edits → import-cv saves to DB.
    Writes profile fields + work history + skill_keywords in one transaction.
    Replaces existing work history from previous CV imports (idempotent).
    """
    profile_id = _ensure_profile(user, conn)

    with conn.cursor() as cur:
        # Merge all keyword-type data into skill_keywords
        all_keywords = list(dict.fromkeys(
            data.skills + data.languages + data.certifications
        ))  # dedupe, preserve order

        # Update profile fields
        cur.execute("""
            UPDATE profiles SET
                current_title = COALESCE(%s, current_title),
                experience_level = COALESCE(%s, experience_level),
                years_of_experience = COALESCE(%s, years_of_experience),
                skill_keywords = %s,
                profile_summary = COALESCE(%s, profile_summary),
                profile_source = 'cv_import',
                skills_extraction_status = 'imported',
                updated_at = NOW()
            WHERE profile_id = %s
        """, (
            data.current_title,
            data.career_level,
            data.years_experience,
            Json(all_keywords),
            data.profile_summary,
            profile_id
        ))

        # Remove previous CV-imported work history (keep manually added ones)
        cur.execute("""
            DELETE FROM profile_work_history
            WHERE profile_id = %s AND extraction_status = 'imported'
        """, (profile_id,))

        # Insert work history entries
        imported_count = 0
        for entry in data.work_history:
            duration_months = None
            if entry.duration_years is not None:
                duration_months = int(entry.duration_years * 12)

            description = '; '.join(entry.key_responsibilities) if entry.key_responsibilities else None

            cur.execute("""
                INSERT INTO profile_work_history
                    (profile_id, company_name, job_title, duration_months,
                     job_description, extraction_status)
                VALUES (%s, %s, %s, %s, %s, 'imported')
            """, (
                profile_id,
                entry.employer_description,
                entry.role,
                duration_months,
                description
            ))
            imported_count += 1

        conn.commit()

    return {
        "status": "ok",
        "profile_id": profile_id,
        "skills_imported": len(all_keywords),
        "work_entries_imported": imported_count,
        "message": f"Profile updated: {len(all_keywords)} skills, {imported_count} work entries imported"
    }


# --- Skills Endpoint ---
# Note: profile_facets table is deprecated. Skills come from profiles.skill_keywords.
# This endpoint remains for backwards compatibility but returns skill_keywords data.

class SkillResponse(BaseModel):
    skill: str


@router.get("/me/skills", response_model=List[SkillResponse])
def get_my_skills(user: dict = Depends(require_user), conn=Depends(get_db)):
    """Get skills for current user's profile."""
    with conn.cursor() as cur:
        cur.execute("SELECT profile_id, skill_keywords FROM profiles WHERE user_id = %s", (user['user_id'],))
        profile = cur.fetchone()
        if not profile:
            return []
        
        skill_keywords = profile['skill_keywords']
        if not skill_keywords:
            return []
            
        import json
        if isinstance(skill_keywords, str):
            skill_keywords = json.loads(skill_keywords)
        
        return [SkillResponse(skill=s) for s in sorted(set(skill_keywords))]


# Note: /me/reextract endpoint removed (2026-02-03)
# Clara/Diego profile facet extraction pipeline was deprecated.
# Skills now come from profiles.skill_keywords which is populated during profile import.
