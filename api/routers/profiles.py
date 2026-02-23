"""
Profile endpoints — CRUD for user profiles.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import json as _json
import logging
import tempfile
import os
import hashlib
import threading

import requests as _requests

from psycopg2.extras import Json

from api.deps import get_db, require_user, _get_pool
from config.settings import OLLAMA_EMBED_URL as _OLLAMA_EMBED_URL, EMBED_MODEL as _EMBED_MODEL

router = APIRouter(prefix="/profiles", tags=["profiles"])
logger = logging.getLogger(__name__)

# ── CV extraction job store ──────────────────────────────────────────────────
# Background tasks run in the FastAPI event loop; results are stored here so
# the browser can poll /me/parse-cv/status/{job_id} without keeping an HTTP
# connection open for the full (potentially 3+ min) extraction.
_cv_jobs: dict = {}
_cv_jobs_lock = threading.Lock()


def _job_update(job_id: str, **kwargs):
    with _cv_jobs_lock:
        if job_id in _cv_jobs:
            _cv_jobs[job_id].update(kwargs)


def _job_progress(job_id: str, msg: str):
    with _cv_jobs_lock:
        if job_id in _cv_jobs:
            _cv_jobs[job_id]['progress'].append(msg)


# Hard wall-clock budget for the entire CV extraction job (20 min)
_CV_JOB_TOTAL_TIMEOUT = 1200

async def _run_cv_extraction(job_id: str, text: str, yogi_name: str, user_id: int,
                              original_filename: str):
    """Background coroutine — runs extract_and_anonymize and stores the result."""
    import asyncio as _asyncio
    pool = _get_pool()
    conn = None
    try:
        conn = pool.getconn()
        _job_progress(job_id, f'🔍 Analysing structure…')
        from core.cv_anonymizer import extract_and_anonymize

        def _on_partial(data: dict):
            """Sync callback — invoked from inside extract_and_anonymize for each chunk/role."""
            kind = data.get('type', '')
            if kind == 'pass1_chunk':
                chunk, total, found = data['chunk'], data['total_chunks'], data['roles_found']
                _job_progress(job_id, f'🔍 Pass 1: {chunk}/{total} chunks — {found} roles so far…')
            elif kind == 'pass2_role':
                done, total = data['completed'], data['total']
                partial_wh = data.get('partial_work_history', [])
                _job_progress(job_id, f'🔒 Anonymizing: {done}/{total} roles…')
                _job_update(job_id, partial_result={'work_history': partial_wh})

        result = await _asyncio.wait_for(
            extract_and_anonymize(
                cv_text=text,
                yogi_name=yogi_name,
                conn=conn,
                on_partial=_on_partial,
            ),
            timeout=_CV_JOB_TOTAL_TIMEOUT
        )
        n_roles = len(result.get('work_history', []))
        n_skills = len(result.get('skills', []))
        _job_progress(job_id, f'✅ Found {n_roles} roles · {n_skills} skills')
        try:
            from lib.usage_tracker import log_event
            from lib.audit import log_audit_event
            log_event(conn, user_id, 'cv_extraction',
                      context={'filename': original_filename})
            log_audit_event(conn, user_id, actor='yogi', event_type='cv_upload',
                            detail={'filename': original_filename,
                                    'roles': len(result.get('work_history', [])),
                                    'skills': len(result.get('skills', []))})
        except Exception:
            pass
        _job_update(job_id, status='done', result=result)
    except _asyncio.TimeoutError:
        logger.error(f'CV extraction job {job_id} timed out after {_CV_JOB_TOTAL_TIMEOUT}s')
        with _cv_jobs_lock:
            partial = _cv_jobs.get(job_id, {}).get('partial_result')
        if partial and partial.get('work_history'):
            n = len(partial['work_history'])
            logger.warning(f'CV job {job_id}: saving partial result ({n} roles)')
            _job_progress(job_id, f'⚠ Timeout — partial import: {n} roles saved')
            _job_update(job_id, status='partial', result=partial,
                        error=f'Analysis timed out — {n} roles extracted so far')
        else:
            _job_update(job_id, status='failed',
                        error='CV analysis took too long — please try again with a shorter CV')
    except Exception as e:
        logger.error(f'CV extraction job {job_id} failed: {e}')
        _job_update(job_id, status='failed', error=str(e))
    finally:
        if conn:
            try:
                pool.putconn(conn)
            except Exception:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────────────────────
# Background task: translate free-text profile fields via local LLM
# ─────────────────────────────────────────────────────────────────────────────

async def _run_translation(job_id: str, user_id: int, target_lang: str):
    """
    Translate profile_summary and each work-history job_description in-place.
    Skips: job titles, company names, skill keywords — those stay as-is.
    """
    import asyncio as _asyncio
    from core.mira_llm import ask_llm

    pool = _get_pool()
    conn = None
    try:
        conn = pool.getconn()
        lang_name = {'de': 'German (Deutsch)', 'en': 'English'}.get(target_lang, target_lang)
        system_prompt = (
            f"You are a professional translator. Translate the following text to {lang_name}. "
            f"Rules: "
            f"Do NOT translate company names, job titles, technology names, programming languages or framework names. "
            f"Preserve all bullet points, semicolons, line breaks and paragraph structure exactly. "
            f"Use professional business language. "
            f"Reply with ONLY the translated text — no introduction, no explanation."
        )

        with conn.cursor() as cur:
            cur.execute(
                "SELECT profile_id, profile_summary FROM profiles WHERE user_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
        if not row:
            _job_update(job_id, status='failed', error='Profile not found')
            return

        profile_id = row['profile_id']

        with conn.cursor() as cur:
            cur.execute("""
                SELECT work_history_id, job_title, job_description
                FROM profile_work_history
                WHERE profile_id = %s
                  AND job_description IS NOT NULL AND TRIM(job_description) != ''
                ORDER BY COALESCE(end_date, CURRENT_DATE) DESC
            """, (profile_id,))
            entries = cur.fetchall()

        summary = row['profile_summary']
        total = len(entries) + (1 if summary else 0)
        if total == 0:
            _job_update(job_id, status='done',
                        result={'translated': 0, 'lang': target_lang})
            return

        done = 0

        # 1. Summary
        if summary and summary.strip():
            _job_progress(job_id, f'🌐 Übersetze Zusammenfassung…')
            translated = await _asyncio.wait_for(
                ask_llm(summary, system_prompt), timeout=120
            )
            if translated and translated.strip():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE profiles SET profile_summary = %s WHERE profile_id = %s",
                        (translated.strip(), profile_id)
                    )
                    conn.commit()
            done += 1
            _job_progress(job_id, f'🌐 Zusammenfassung fertig ({done}/{total})')

        # 2. Work-history descriptions
        for entry in entries:
            title = entry['job_title'] or '…'
            _job_progress(job_id, f'🌐 Übersetze „{title}"… ({done + 1}/{total})')
            translated = await _asyncio.wait_for(
                ask_llm(entry['job_description'], system_prompt), timeout=120
            )
            if translated and translated.strip():
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE profile_work_history SET job_description = %s "
                        "WHERE work_history_id = %s",
                        (translated.strip(), entry['work_history_id'])
                    )
                    conn.commit()
            done += 1
            _job_progress(job_id, f'🌐 {done}/{total} Abschnitte übersetzt…')

        _job_progress(job_id, f'✅ Übersetzung fertig — {done} Abschnitte')
        try:
            from lib.audit import log_audit_event
            import psycopg2.extras  # noqa – conn is already open
            log_audit_event(conn, user_id, actor='yogi',
                            event_type='profile_translate',
                            detail={'lang': target_lang, 'translated': done})
        except Exception:
            pass
        _job_update(job_id, status='done', result={'translated': done, 'lang': target_lang})

    except _asyncio.TimeoutError:
        logger.error(f'Translation job {job_id} timed out')
        _job_update(job_id, status='failed', error='Übersetzung hat zu lange gedauert — bitte erneut versuchen')
    except Exception as e:
        logger.error(f'Translation job {job_id} failed: {e}')
        _job_update(job_id, status='failed', error=str(e))
    finally:
        if conn:
            try:
                pool.putconn(conn)
            except Exception:
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────────────────────
# Background helper: compute & cache profile embedding after CV import
# ─────────────────────────────────────────────────────────────────────────────

def _build_profile_text(profile: dict) -> str:
    """Replicate the profile text convention used by search.py / Clara."""
    raw_skills = profile.get('skill_keywords') or []
    if isinstance(raw_skills, dict):
        raw_skills = raw_skills.get('keywords', [])
    skills = [str(s) for s in raw_skills]

    parts = [
        profile.get('current_title') or '',
        ' '.join(skills),
        (profile.get('profile_summary') or '')[:500],
        profile.get('experience_level') or '',
    ]
    return ' | '.join(p for p in parts if p).strip()


def _compute_profile_embedding_bg(user_id: int) -> None:
    """Run in a background thread: build profile text, call Ollama, cache result."""
    import logging
    log = logging.getLogger(__name__)
    conn = None
    pool = None
    try:
        pool = _get_pool()
        conn = pool.getconn()
        conn.autocommit = False

        with conn.cursor() as cur:
            cur.execute("""
                SELECT skill_keywords, current_title, profile_summary, experience_level
                FROM profiles
                WHERE user_id = %s
                ORDER BY updated_at DESC NULLS LAST
                LIMIT 1
            """, (user_id,))
            profile = cur.fetchone()

        if not profile:
            return

        text = _build_profile_text(profile)
        if not text:
            return

        text_clean = text.lower().strip()
        text_hash = hashlib.sha256(text_clean.encode()).hexdigest()[:32]

        # Already cached?
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM embeddings WHERE text_hash = %s", (text_hash,))
            if cur.fetchone():
                return

        # Compute via Ollama
        resp = _requests.post(
            _OLLAMA_EMBED_URL,
            json={'model': _EMBED_MODEL, 'prompt': text_clean},
            timeout=60
        )
        if resp.status_code != 200:
            log.warning("Ollama embedding error %s for user %s", resp.status_code, user_id)
            return

        embedding = resp.json().get('embedding')
        if not embedding:
            return

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO embeddings (text_hash, text, embedding, model)
                VALUES (%s, %s, %s::jsonb, %s)
                ON CONFLICT (text_hash) DO NOTHING
            """, (text_hash, text, _json.dumps(embedding), _EMBED_MODEL))
        conn.commit()
        log.info("Profile embedding cached for user %s (hash %s)", user_id, text_hash)

    except Exception as exc:
        log.error("_compute_profile_embedding_bg error for user %s: %s", user_id, exc)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn and pool:
            pool.putconn(conn)


def _schedule_profile_embedding(user_id: int) -> None:
    """Fire-and-forget: compute profile embedding in background thread."""
    t = threading.Thread(
        target=_compute_profile_embedding_bg,
        args=(user_id,),
        daemon=True
    )
    t.start()


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
    implied_skills: List[str] = []
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


class SkillUpdate(BaseModel):
    action: str          # "add" | "remove"
    skill: str
    source: str = "extracted"  # "extracted" | "implied"


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
                   p.implied_skills,
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
            skills = sorted(set(str(s) for s in skill_keywords)) if skill_keywords else []

        # Parse implied skills — JSONB [{name, category, confidence, evidence}]
        raw_implied = profile.get('implied_skills') or []
        if isinstance(raw_implied, str):
            raw_implied = json.loads(raw_implied)
        implied_names = sorted(set(
            e['name'] for e in raw_implied
            if isinstance(e, dict) and e.get('name')
        ))
        
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
            implied_skills=implied_names,
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
    request: Request,
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
    from api.i18n import get_language_from_request

    new_name = (payload.get("yogi_name") or "").strip()
    confirmed = payload.get("confirmed", False)  # user confirmed a warning
    dry_run = payload.get("dry_run", False)       # validate only, don't save
    lang = get_language_from_request(request)

    if not new_name:
        empty_msg = {"de": "Yogi-Name darf nicht leer sein.", "en": "Yogi name cannot be empty."}
        raise HTTPException(status_code=400, detail=empty_msg.get(lang, empty_msg["de"]))

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
        # Map Taro keys to user-facing messages (bilingual)
        error_messages = {
            "contains_email": {
                "de": "Yogi-Name darf keine E-Mail-Adresse enthalten.",
                "en": "Yogi name must not contain an email address.",
            },
            "contains_phone": {
                "de": "Yogi-Name darf keine Telefonnummer enthalten.",
                "en": "Yogi name must not contain a phone number.",
            },
            "contains_address": {
                "de": "Yogi-Name darf keine Adresse enthalten.",
                "en": "Yogi name must not contain an address.",
            },
            "reserved": {
                "de": "Dieser Name ist reserviert.",
                "en": "This name is reserved.",
            },
            "matches_real_name": {
                "de": "Dein Yogi-Name darf nicht dein echter Name sein. Wähle ein Pseudonym!",
                "en": "Your yogi name cannot be your real name. Choose a pseudonym!",
            },
            "contains_real_name": {
                "de": "Dein Yogi-Name enthält deinen echten Namen. Wähle ein Pseudonym!",
                "en": "Your yogi name contains your real name. Choose a pseudonym!",
            },
            "subset_of_real_name": {
                "de": "Dein Yogi-Name ist zu ähnlich zu deinem echten Namen. Wähle ein Pseudonym!",
                "en": "Your yogi name is too similar to your real name. Choose a pseudonym!",
            },
            "already_taken": {
                "de": "Dieser Yogi-Name ist bereits vergeben.",
                "en": "This yogi name is already taken.",
            },
        }
        msgs = error_messages.get(msg, {})
        detail = msgs.get(lang, msgs.get("de", msg))
        raise HTTPException(status_code=400, detail=detail)

    if severity == "warning" and not confirmed:
        # Soft warning — return 200 with warning, let user confirm
        warning_messages = {
            "looks_like_full_name": {
                "de": "Das sieht wie ein echter Name aus. Möchtest du stattdessen ein Pseudonym wählen?",
                "en": "That looks like a real name. Would you prefer to choose a pseudonym?",
            },
            "contains_title": {
                "de": "Titel wie Dr./Prof. deuten auf einen echten Namen hin. Bist du sicher?",
                "en": "Titles like Dr./Prof. suggest a real name. Are you sure?",
            },
            "contains_particle": {
                "de": "Namenspartikel (von, van, de…) deuten auf einen echten Namen hin. Bist du sicher?",
                "en": "Name particles (von, van, de…) suggest a real name. Are you sure?",
            },
            "common_first_name": {
                "de": "Das ist ein häufiger Vorname. Wähle lieber ein kreatives Pseudonym!",
                "en": "That's a common first name. Better pick a creative pseudonym!",
            },
        }
        msgs = warning_messages.get(msg, {})
        warning_text = msgs.get(lang, msgs.get("de", msg))
        return {
            "status": "warning",
            "warning": warning_text,
            "warning_key": msg,
            "yogi_name": new_name
        }

    # ── Save ─────────────────────────────────────────────
    if dry_run:
        return {"status": "ok", "yogi_name": new_name}

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET yogi_name = %s WHERE user_id = %s",
            (new_name, user["user_id"])
        )
        conn.commit()

    return {"status": "ok", "yogi_name": new_name}


@router.get("/me/yogi-name/suggest")
def suggest_yogi_names(
    gender: str = 'neutral',
    count: int = 6,
    language: str = 'en',
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Generate yogi name suggestions via Taro.
    Args:
        gender: 'masculine', 'feminine', or 'neutral'
        count: Number of suggestions (default 6, max 20)
        language: 'de' for German names, 'en' for English (default)
    """
    from core.taro import suggest_names

    if gender not in ('masculine', 'feminine', 'neutral'):
        gender = 'neutral'
    count = min(max(count, 1), 20)
    if language not in ('de', 'en'):
        language = 'en'

    names = suggest_names(conn, count=count, gender=gender, language=language)
    return {"suggestions": names}


@router.post("/me/yogi-name/suggest-from-keywords")
def suggest_yogi_names_llm(
    body: dict,
    gender: str = 'neutral',
    language: str = 'de',
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Generate yogi name suggestions using LLM, inspired by user-provided keywords.
    Args:
        body.keywords: Space/comma-separated inspiration words
        gender: 'masculine', 'feminine', or 'neutral'
        language: 'de' for German, 'en' for English
    """
    from core.taro import suggest_names_llm

    keywords = (body.get('keywords') or '').strip()
    if not keywords:
        # No keywords — ask LLM to freestyle, or fall back to algorithmic pool
        keywords = 'creative, unique, interesting'
    if len(keywords) > 200:
        keywords = keywords[:200]

    if gender not in ('masculine', 'feminine', 'neutral'):
        gender = 'neutral'
    if language not in ('de', 'en'):
        language = 'de'

    names = suggest_names_llm(
        keywords=keywords,
        conn=conn,
        count=8,
        gender=gender,
        language=language,
    )
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
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: dict = Depends(require_user),
    conn = Depends(get_db)
):
    """
    Parse uploaded CV — returns a job_id immediately.
    The LLM extraction runs as a background task (can take 1-3 minutes).
    Poll GET /me/parse-cv/status/{job_id} for progress and result.
    """
    import uuid
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
        elif filename.endswith(('.txt', '.md')):
            text = content.decode('utf-8', errors='ignore')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, TXT, or MD.")

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")

        # Get yogi_name now (while we still have a live connection)
        with conn.cursor() as cur:
            cur.execute("SELECT yogi_name FROM users WHERE user_id = %s", (user['user_id'],))
            row = cur.fetchone()
            yogi_name = row['yogi_name'] if row else None

        if not yogi_name:
            raise HTTPException(status_code=400, detail="Please set your yogi name first (chat with Mira)")

        # Create job entry and kick off background extraction
        job_id = str(uuid.uuid4())[:12]
        with _cv_jobs_lock:
            _cv_jobs[job_id] = {
                'status': 'running',
                'progress': [f'📂 "{file.filename}" read ({len(text):,} chars)'],
                'result': None,
                'partial_result': None,
                'error': None,
            }

        background_tasks.add_task(
            _run_cv_extraction, job_id, text, yogi_name, user['user_id'], file.filename
        )

        return {'job_id': job_id, 'status': 'running'}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.get("/me/parse-cv/status/{job_id}")
async def parse_cv_status(job_id: str, user: dict = Depends(require_user)):
    """Poll CV extraction job status. Returns progress list and result when done."""
    with _cv_jobs_lock:
        job = dict(_cv_jobs.get(job_id, {}))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/me/translate")
async def translate_profile(
    request: Request,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Translate free-text profile fields (summary + work descriptions) to the
    user's chosen language (read from the 'lang' cookie).
    Returns a job_id — poll /me/parse-cv/status/{job_id} for progress.
    """
    import uuid
    from api.i18n import get_language_from_request

    target_lang = get_language_from_request(request) or 'de'

    # Ensure profile exists
    with conn.cursor() as cur:
        cur.execute("SELECT profile_id FROM profiles WHERE user_id = %s", (user['user_id'],))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="No profile found — build one first")

    job_id = str(uuid.uuid4())[:12]
    target_label = 'Deutsch' if target_lang == 'de' else target_lang.upper()
    with _cv_jobs_lock:
        _cv_jobs[job_id] = {
            'status': 'running',
            'progress': [f'🌐 Starte Übersetzung nach {target_label}…'],
            'result': None,
            'partial_result': None,
            'error': None,
        }

    background_tasks.add_task(_run_translation, job_id, user['user_id'], target_lang)
    return {'job_id': job_id, 'status': 'running'}


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

    # Kick off embedding computation in background (Adele's signal)
    _schedule_profile_embedding(user['user_id'])

    # --- USAGE: Log billable profile embed event ---
    try:
        from lib.usage_tracker import log_event
        log_event(conn, user['user_id'], 'profile_embed',
                  context={'profile_id': profile_id, 'skills_count': len(all_keywords),
                           'work_entries': imported_count})
    except Exception as e:
        log.warning(f"Usage tracking failed for profile_embed: {e}")

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


@router.patch("/me/skills")
def update_my_skill(
    body: SkillUpdate,
    user: dict = Depends(require_user),
    conn=Depends(get_db)
):
    """
    Add or remove a skill.
    source='extracted' operates on skill_keywords (string[]).
    source='implied'   operates on implied_skills ({name,...}[]).
    """
    import json as _json
    if body.action not in ("add", "remove"):
        raise HTTPException(status_code=400, detail="action must be 'add' or 'remove'")
    if body.source not in ("extracted", "implied"):
        raise HTTPException(status_code=400, detail="source must be 'extracted' or 'implied'")

    skill = body.skill.strip()
    if not skill:
        raise HTTPException(status_code=400, detail="skill must not be empty")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT profile_id, skill_keywords, implied_skills FROM profiles WHERE user_id = %s",
            (user['user_id'],)
        )
        profile = cur.fetchone()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile_id = profile['profile_id']

        if body.source == "extracted":
            kws = profile['skill_keywords'] or []
            if isinstance(kws, str):
                kws = _json.loads(kws)
            kw_set = set(str(s) for s in kws)
            if body.action == "add":
                kw_set.add(skill)
            else:
                kw_set.discard(skill)
            cur.execute(
                "UPDATE profiles SET skill_keywords = %s, updated_at = NOW() WHERE profile_id = %s",
                (Json(sorted(kw_set)), profile_id)
            )
        else:
            implied = profile['implied_skills'] or []
            if isinstance(implied, str):
                implied = _json.loads(implied)
            if body.action == "add":
                existing = {e['name'].lower() for e in implied if isinstance(e, dict) and e.get('name')}
                if skill.lower() not in existing:
                    implied.append({
                        "name": skill,
                        "category": "GENERAL",
                        "confidence": "high",
                        "evidence": "Added manually"
                    })
            else:
                implied = [
                    e for e in implied
                    if not (isinstance(e, dict) and e.get('name', '').strip() == skill)
                ]
            cur.execute(
                "UPDATE profiles SET implied_skills = %s, updated_at = NOW() WHERE profile_id = %s",
                (Json(implied), profile_id)
            )

        conn.commit()
    return {"ok": True}


# Note: /me/reextract endpoint removed (2026-02-03)
# Clara/Diego profile facet extraction pipeline was deprecated.
# Skills now come from profiles.skill_keywords which is populated during profile import.


# ─────────────────────────────────────────────────────────
# Profile-as-Markdown + Activity Log  (split-pane profile page)
# ─────────────────────────────────────────────────────────

@router.get("/me/markdown")
def get_profile_markdown(request: Request, user: dict = Depends(require_user), conn=Depends(get_db)):
    """
    Render the current user's profile as a Markdown document.
    Used by the split-pane profile builder's right-side preview.
    """
    from api.i18n import get_language_from_request
    lang = get_language_from_request(request)

    _T = {
        'de': {
            'work':             'Berufserfahrung',
            'education':        'Ausbildung',
            'projects':         'Projekte',
            'skills':           'Fähigkeiten',
            'prefs':            'Suchpräferenzen',
            'desired_roles':    'Wunschrollen',
            'desired_locs':     'Wunschorte',
            'salary':           'Gehaltsvorstellung',
            'min_seniority':    'Mindestlevel',
            'present':          'heute',
            'years':            'Jahre',
            'months':           'Monate',
            'no_profile':       '_Noch kein Profil vorhanden. Sprich mit Adele, lade deinen Lebenslauf hoch, oder füll das Formular aus._',
        },
        'en': {
            'work':             'Work Experience',
            'education':        'Education',
            'projects':         'Projects',
            'skills':           'Skills',
            'prefs':            'Search Preferences',
            'desired_roles':    'Target Roles',
            'desired_locs':     'Preferred Locations',
            'salary':           'Salary Expectation',
            'min_seniority':    'Minimum Level',
            'present':          'present',
            'years':            'years',
            'months':           'months',
            'no_profile':       '_No profile yet. Chat with Adele, upload your CV, or fill in the form._',
        },
    }
    T = _T.get(lang, _T['en'])

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
            return {"markdown": T['no_profile'], "completeness": 0}

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
                    end = T['present']
                elif job.get('end_date'):
                    end = job['end_date'].strftime('%m/%Y')
                else:
                    end = '?'
                date_range = f"{start} – {end}"
            elif job.get('duration_months'):
                years = job['duration_months'] / 12
                date_range = f"~{years:.0f} {T['years']}" if years >= 1 else f"~{job['duration_months']} {T['months']}"
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
        lines.append(f"## {T['work']}")
        lines.append('')
        _render_entries(work_history, lines)

    # Education
    if education:
        lines.append(f"## {T['education']}")
        lines.append('')
        _render_entries(education, lines)

    # Projects
    if projects:
        lines.append(f"## {T['projects']}")
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
        lines.append(f"## {T['skills']}")
        lines.append('')
        lines.append(', '.join(f"**{s}**" for s in skills))
        lines.append('')

    # Preferences
    prefs_parts = []
    if profile.get('desired_roles'):
        prefs_parts.append(f"**{T['desired_roles']}:** {', '.join(profile['desired_roles'])}")
    if profile.get('desired_locations'):
        prefs_parts.append(f"**{T['desired_locs']}:** {', '.join(profile['desired_locations'])}")
    sal_parts = []
    if profile.get('expected_salary_min'):
        sal_parts.append(f"{profile['expected_salary_min']:,}€")
    if profile.get('expected_salary_max'):
        sal_parts.append(f"{profile['expected_salary_max']:,}€")
    if sal_parts:
        prefs_parts.append(f"**{T['salary']}:** {' – '.join(sal_parts)}")
    if profile.get('min_seniority'):
        prefs_parts.append(f"**{T['min_seniority']}:** {profile['min_seniority']}")

    if prefs_parts:
        lines.append(f"## {T['prefs']}")
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
