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
        # Auto-create with yogi_name (never store real names)
        yogi_name = user.get('yogi_name') or 'New Yogi'
        email = user.get('email')
        cur.execute("""
            INSERT INTO profiles (full_name, email, user_id, profile_source)
            VALUES (%s, %s, %s, 'self')
            RETURNING profile_id
        """, (yogi_name, email, user['user_id']))
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
    # Preference fields for form pre-population
    desired_roles: Optional[List[str]] = None
    desired_locations: Optional[List[str]] = None
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    min_seniority: Optional[str] = None


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
    entry_type: str = 'work'  # work, education, project


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
    entry_type: str = 'work'


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Get the current user's profile.
    Returns profile linked to authenticated user.
    """
    # Auto-create profile if missing
    _ensure_profile(user, conn)

    with conn.cursor() as cur:
        # Get profile — use yogi_name for display (never expose real name)
        cur.execute("""
            SELECT p.profile_id, u.yogi_name as display_name, p.email,
                   p.current_title as title, p.desired_locations[1] as location,
                   p.desired_roles, p.desired_locations, p.skill_keywords,
                   p.expected_salary_min, p.expected_salary_max, p.min_seniority
            FROM profiles p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s
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
            completeness=completeness,
            desired_roles=profile['desired_roles'],
            desired_locations=profile['desired_locations'],
            expected_salary_min=profile['expected_salary_min'],
            expected_salary_max=profile['expected_salary_max'],
            min_seniority=profile['min_seniority']
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


@router.put("/me/yogi-name")
def update_yogi_name(
    payload: dict,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Update the user's yogi_name (public alias).

    Uses Taro's layered validation (A+B+C+D):
    - Hard-block: email, phone, address → 400
    - Reserved names → 400
    - Generic "looks real" heuristic → warning (user can confirm)
    - Real-name guard (transient OAuth data, never stored) → 400
    - Uniqueness → 400

    Privacy: real_name from OAuth/profile is read transiently for
    comparison only. It is NEVER stored, logged, or returned.
    """
    from core.taro import validate_yogi_name

    new_name = (payload.get("yogi_name") or "").strip()
    confirmed = payload.get("confirmed", False)  # user confirmed a warning

    if not new_name:
        raise HTTPException(status_code=400, detail="Yogi-Name darf nicht leer sein.")

    # ── Gather transient identity fragments (NEVER stored) ────
    # Google OAuth display_name — read from session, not persisted
    display_name = user.get("display_name") or ""
    email = user.get("email") or ""

    # profiles.full_name may hold OAuth name from initial import
    with conn.cursor() as cur:
        cur.execute(
            "SELECT full_name FROM profiles WHERE user_id = %s",
            (user["user_id"],)
        )
        row = cur.fetchone()
        profile_name = ""
        if row and row["full_name"] and row["full_name"] not in ("New Yogi",):
            profile_name = row["full_name"]

    # Combine all transient identity data for Taro
    real_name = display_name or profile_name or None

    # ── Validate via Taro ────────────────────────────────
    ok, msg, severity = validate_yogi_name(
        new_name,
        real_name=real_name,
        email=email,
        conn=conn,
        current_user_id=user["user_id"]
    )

    if severity == "error":
        # Map Taro keys to user-facing messages
        error_messages = {
            "contains_email": "Yogi-Name darf keine E-Mail-Adresse enthalten.",
            "contains_phone": "Yogi-Name darf keine Telefonnummer enthalten.",
            "contains_address": "Yogi-Name darf keine Adresse enthalten.",
            "reserved": "Dieser Name ist reserviert.",
            "matches_real_name": "Dein Yogi-Name darf nicht dein echter Name sein. Wähle ein Pseudonym!",
            "contains_real_name": "Dein Yogi-Name enthält deinen echten Namen. Wähle ein Pseudonym!",
            "subset_of_real_name": "Dein Yogi-Name ist zu ähnlich zu deinem echten Namen. Wähle ein Pseudonym!",
            "already_taken": "Dieser Yogi-Name ist bereits vergeben.",
        }
        detail = error_messages.get(msg, msg)
        raise HTTPException(status_code=400, detail=detail)

    if severity == "warning" and not confirmed:
        # Soft warning — return 200 with warning, let user confirm
        warning_messages = {
            "looks_like_full_name": "Das sieht wie ein echter Name aus. Möchtest du stattdessen ein Pseudonym wählen?",
            "contains_title": "Titel wie Dr./Prof. deuten auf einen echten Namen hin. Bist du sicher?",
            "contains_particle": "Namenspartikel (von, van, de…) deuten auf einen echten Namen hin. Bist du sicher?",
            "common_first_name": "Das ist ein häufiger Vorname. Wähle lieber ein kreatives Pseudonym!",
        }
        return {
            "status": "warning",
            "warning": warning_messages.get(msg, msg),
            "warning_key": msg,
            "yogi_name": new_name
        }

    # ── Save ─────────────────────────────────────────────
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET yogi_name = %s WHERE user_id = %s",
            (new_name, user["user_id"])
        )
        conn.commit()

    return {"status": "ok", "yogi_name": new_name}


@router.get("/me/yogi-name/suggest")
def suggest_yogi_names(
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Generate yogi name suggestions via Taro.
    Returns 6 fresh, unique, non-taken names.
    """
    from core.taro import suggest_names

    names = suggest_names(conn, count=6)
    return {"suggestions": names}


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: int, user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Get a specific profile by ID.
    Users can only view their own profile.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.profile_id, u.yogi_name as display_name, p.email, p.user_id
            FROM profiles p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.profile_id = %s
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
                   location, is_current, duration_months, entry_type
            FROM profile_work_history
            WHERE profile_id = %s
            ORDER BY entry_type, COALESCE(end_date, CURRENT_DATE) DESC, start_date DESC
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
        
        entry_type = entry.entry_type if entry.entry_type in ('work', 'education', 'project') else 'work'
        cur.execute("""
            INSERT INTO profile_work_history 
                (profile_id, company_name, job_title, start_date, end_date, 
                 job_description, location, is_current, extraction_status, entry_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
            RETURNING work_history_id, company_name as company, job_title as title,
                      start_date, end_date, job_description as description,
                      location, is_current, duration_months, entry_type
        """, (
            profile_id, entry.company, entry.title,
            entry.start_date, entry.end_date, entry.description,
            entry.location, entry.is_current, entry_type
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
        
        entry_type = entry.entry_type if entry.entry_type in ('work', 'education', 'project') else 'work'
        cur.execute("""
            UPDATE profile_work_history SET
                company_name = %s, job_title = %s, start_date = %s, end_date = %s,
                job_description = %s, location = %s, is_current = %s,
                extraction_status = 'pending', entry_type = %s,
                updated_at = NOW()
            WHERE work_history_id = %s
            RETURNING work_history_id, company_name as company, job_title as title,
                      start_date, end_date, job_description as description,
                      location, is_current, duration_months, entry_type
        """, (
            entry.company, entry.title, entry.start_date, entry.end_date,
            entry.description, entry.location, entry.is_current, entry_type,
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
    Parse uploaded CV (PDF/DOCX/TXT/MD) and extract ANONYMIZED career data.
    
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
            
        elif filename.endswith('.txt') or filename.endswith('.md'):
            text = content.decode('utf-8', errors='ignore')
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, TXT, or MD.")
        
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
    start_year: Optional[int] = None
    start_month: Optional[int] = None
    end_year: Optional[int] = None
    end_month: Optional[int] = None
    is_current: Optional[bool] = None
    industry: Optional[str] = None
    key_responsibilities: List[str] = []
    technologies_used: List[str] = []


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

            # Build start_date / end_date from year+month
            start_date = None
            if entry.start_year:
                start_date = f"{entry.start_year}-{entry.start_month or 1:02d}-01"
            end_date = None
            if entry.end_year:
                end_date = f"{entry.end_year}-{entry.end_month or 1:02d}-01"

            cur.execute("""
                INSERT INTO profile_work_history
                    (profile_id, company_name, job_title, duration_months,
                     job_description, extraction_status,
                     start_date, end_date, is_current, technologies_used)
                VALUES (%s, %s, %s, %s, %s, 'imported', %s, %s, %s, %s)
            """, (
                profile_id,
                entry.employer_description,
                entry.role,
                duration_months,
                description,
                start_date,
                end_date,
                entry.is_current or False,
                entry.technologies_used or None
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


# ─────────────────────────────────────────────────────────
# Profile-as-Markdown + Activity Log  (split-pane profile page)
# ─────────────────────────────────────────────────────────

@router.get("/me/markdown")
def get_profile_markdown(user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Render the current user's profile as a Markdown document.
    Used by the split-pane profile builder's right-side preview.
    """
    with conn.cursor() as cur:
        # Profile basics
        cur.execute("""
            SELECT p.profile_id, u.yogi_name, p.current_title, p.location,
                   p.profile_summary, p.skill_keywords, p.years_of_experience,
                   p.experience_level, p.desired_roles, p.desired_locations,
                   p.expected_salary_min, p.expected_salary_max, p.min_seniority
            FROM profiles p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s
        """, (user['user_id'],))
        profile = cur.fetchone()

        if not profile:
            return {"markdown": "_Noch kein Profil vorhanden. Sprich mit Adele, lade deinen Lebenslauf hoch, oder fülle das Formular aus._", "completeness": 0}

        # Work history (includes education and projects via entry_type)
        cur.execute("""
            SELECT company_name, job_title, department, start_date, end_date,
                   is_current, duration_months, job_description, location,
                   technologies_used, entry_type
            FROM profile_work_history
            WHERE profile_id = %s
            ORDER BY entry_type, COALESCE(end_date, '2099-01-01') DESC, start_date DESC
        """, (profile['profile_id'],))
        all_entries = cur.fetchall()

    # Split by entry_type
    work_history = [e for e in all_entries if e.get('entry_type', 'work') == 'work']
    education = [e for e in all_entries if e.get('entry_type') == 'education']
    projects = [e for e in all_entries if e.get('entry_type') == 'project']

    # Build markdown
    lines = []

    # Header
    name = profile['yogi_name'] or 'Yogi'
    lines.append(f"# {name}")
    subtitle_parts = []
    if profile['current_title']:
        subtitle_parts.append(profile['current_title'])
    if profile['location']:
        subtitle_parts.append(profile['location'])
    if subtitle_parts:
        lines.append(' · '.join(subtitle_parts))
    lines.append('')

    # Summary
    if profile['profile_summary']:
        lines.append(f"> {profile['profile_summary']}")
        lines.append('')

    # ── Helper: render a list of entries ──
    def _render_entries(entries, lines):
        for job in entries:
            title = job['job_title'] or 'Position'
            company = job['company_name'] or ''
            loc = f" — {job['location']}" if job.get('location') else ''

            # Date range
            if job.get('start_date'):
                start = job['start_date'].strftime('%m/%Y')
                if job.get('is_current'):
                    end = 'heute'
                elif job.get('end_date'):
                    end = job['end_date'].strftime('%m/%Y')
                else:
                    end = '?'
                date_range = f"{start} – {end}"
            elif job.get('duration_months'):
                years = job['duration_months'] / 12
                date_range = f"~{years:.0f} Jahre" if years >= 1 else f"~{job['duration_months']} Monate"
            else:
                date_range = ''

            lines.append(f"### {title}")
            meta_parts = [p for p in [company, date_range, loc.lstrip(' — ')] if p]
            if meta_parts:
                lines.append('*' + ' · '.join(meta_parts) + '*')
            if job.get('job_description'):
                lines.append('')
                lines.append(job['job_description'])
            if job.get('technologies_used'):
                techs = job['technologies_used']
                if isinstance(techs, list) and techs:
                    lines.append('')
                    lines.append('`' + '` · `'.join(techs) + '`')
            lines.append('')

    # Work History
    if work_history:
        lines.append('## Berufserfahrung')
        lines.append('')
        _render_entries(work_history, lines)

    # Education
    if education:
        lines.append('## Ausbildung')
        lines.append('')
        _render_entries(education, lines)

    # Projects
    if projects:
        lines.append('## Projekte')
        lines.append('')
        _render_entries(projects, lines)

    # Skills
    skills = []
    if profile['skill_keywords']:
        kw = profile['skill_keywords']
        if isinstance(kw, str):
            import json
            kw = json.loads(kw)
        skills = sorted(set(kw)) if kw else []

    if skills:
        lines.append('## Skills')
        lines.append('')
        lines.append(', '.join(f"**{s}**" for s in skills))
        lines.append('')

    # Preferences
    prefs_parts = []
    if profile.get('desired_roles'):
        prefs_parts.append(f"**Wunschrollen:** {', '.join(profile['desired_roles'])}")
    if profile.get('desired_locations'):
        prefs_parts.append(f"**Wunschorte:** {', '.join(profile['desired_locations'])}")
    sal_parts = []
    if profile.get('expected_salary_min'):
        sal_parts.append(f"{profile['expected_salary_min']:,}€")
    if profile.get('expected_salary_max'):
        sal_parts.append(f"{profile['expected_salary_max']:,}€")
    if sal_parts:
        prefs_parts.append(f"**Gehaltsvorstellung:** {' – '.join(sal_parts)}")
    if profile.get('min_seniority'):
        prefs_parts.append(f"**Mindestlevel:** {profile['min_seniority']}")

    if prefs_parts:
        lines.append('## Suchpräferenzen')
        lines.append('')
        for p in prefs_parts:
            lines.append(f"- {p}")
        lines.append('')

    # Completeness calculation
    completeness = 0
    if profile['yogi_name']: completeness += 10
    if profile['current_title']: completeness += 10
    if profile['location']: completeness += 10
    if work_history: completeness += 20
    if education: completeness += 10
    if projects: completeness += 10
    if skills: completeness += 20
    if profile.get('desired_roles') or profile.get('desired_locations'): completeness += 10

    return {"markdown": '\n'.join(lines), "completeness": completeness}


@router.get("/me/activity-log")
def get_activity_log(user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Return the profile-building activity log: Adele chat messages,
    CV upload events, form edit events. Chronological order.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT message_id, sender_type, message_type, body,
                   recipient_type, created_at
            FROM yogi_messages
            WHERE user_id = %s
              AND (
                  recipient_type = 'adele'
                  OR sender_type = 'adele'
                  OR (sender_type = 'system' AND message_type IN ('cv_upload', 'form_edit', 'cv_import'))
              )
            ORDER BY created_at ASC
            LIMIT 200
        """, (user['user_id'],))
        rows = cur.fetchall()

    return [
        {
            "id": r['message_id'],
            "sender": r['sender_type'],
            "type": r['message_type'],
            "body": r['body'],
            "recipient": r['recipient_type'],
            "at": r['created_at'].isoformat() if r['created_at'] else None,
        }
        for r in rows
    ]
