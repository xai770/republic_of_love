# Privacy Architecture: PII Stripping Workflow

**Author:** Arden  
**Date:** 2025-11-30  
**Status:** Draft Proposal

---

## Core Principle

> **What we don't have, we can't leak.**

The goal is not "secure storage of PII" - it's "never having PII in the first place."

---

## The Anonymization Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROFILE INGESTION FLOW                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  USER DEVICE                    │  OUR SYSTEM                       │
│  ────────────                   │  ──────────                       │
│                                 │                                    │
│  ┌──────────────┐              │                                    │
│  │ User uploads │              │                                    │
│  │ resume.pdf   │──────────────┼──→ HTTPS ───┐                     │
│  └──────────────┘              │              │                     │
│                                 │              ▼                     │
│                                 │  ┌─────────────────────┐          │
│                                 │  │ INGESTION GATEWAY   │          │
│                                 │  │ (RAM only, no disk) │          │
│                                 │  └──────────┬──────────┘          │
│                                 │             │                      │
│                                 │             ▼                      │
│                                 │  ┌─────────────────────┐          │
│                                 │  │ LOCAL LLM           │          │
│                                 │  │ (mistral:7b)        │          │
│                                 │  │                     │          │
│                                 │  │ Extract:            │          │
│                                 │  │ - Skills            │          │
│                                 │  │ - Experience years  │          │
│                                 │  │ - Industries        │          │
│                                 │  │ - Education level   │          │
│                                 │  │                     │          │
│                                 │  │ STRIP:              │          │
│                                 │  │ - Names             │          │
│                                 │  │ - Companies         │          │
│                                 │  │ - Schools           │          │
│                                 │  │ - Dates             │          │
│                                 │  │ - Contact info      │          │
│                                 │  └──────────┬──────────┘          │
│                                 │             │                      │
│                                 │             ▼                      │
│                                 │  ┌─────────────────────┐          │
│                                 │  │ ANONYMIZED PROFILE  │          │
│                                 │  │ (JSON)              │          │
│                                 │  └──────────┬──────────┘          │
│                                 │             │                      │
│                                 │             ▼                      │
│                                 │  ┌─────────────────────┐          │
│                                 │  │ PostgreSQL          │          │
│                                 │  │ user_profiles       │          │
│                                 │  └─────────────────────┘          │
│                                 │                                    │
│  ORIGINAL FILE NEVER TOUCHES DISK ON OUR SERVERS                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Ingestion Gateway

A minimal service that:
- Receives uploaded files via HTTPS
- Holds them in RAM only (never written to disk)
- Passes to local LLM for processing
- Discards original immediately after processing

```python
# Pseudocode - NOT actual implementation

class IngestionGateway:
    """
    Stateless file processor. 
    Files exist only in RAM during processing.
    """
    
    def process_resume(self, file_bytes: bytes, user_id: int) -> dict:
        # 1. Parse file in memory
        text = self._extract_text(file_bytes)  # RAM only
        
        # 2. Send to local LLM for anonymization
        anonymized = self.llm.anonymize_profile(text)
        
        # 3. Validate anonymization (paranoia check)
        if self._contains_pii(anonymized):
            raise PIILeakageError("Anonymization failed safety check")
        
        # 4. Store anonymized version only
        self.db.save_profile(user_id, anonymized)
        
        # 5. Original text goes out of scope here
        # Python GC handles cleanup, or explicit:
        del text
        del file_bytes
        
        return {"status": "ok", "profile_version": anonymized["version"]}
```

### 2. Local LLM Anonymizer

The LLM runs locally (Ollama). Data never leaves our infrastructure.

```python
ANONYMIZATION_PROMPT = """
You are a profile anonymizer. Extract career information while REMOVING all identifying details.

INPUT: A resume or CV text
OUTPUT: JSON with anonymized career data

EXTRACT (keep these):
- Skills and technologies
- Years of experience (total and per skill)  
- Career level (junior/mid/senior/executive)
- Industries worked in (generalize: "Deutsche Bank" → "banking")
- Role types (generalize: "VP Risk at DB" → "senior risk management")
- Education level (generalize: "MBA from INSEAD" → "MBA")
- Languages spoken
- Certifications (keep cert names, remove dates/IDs)

REMOVE (never include):
- Names (person, company, school)
- Dates (employment, graduation, birth)
- Locations more specific than country
- Contact information (email, phone, address, LinkedIn)
- Personal identifiers (employee ID, passport, etc.)
- References to specific people
- Anything that could identify this specific person

OUTPUT FORMAT:
{
  "years_experience": 12,
  "career_level": "senior",
  "skills": [
    {"name": "risk management", "years": 8, "proficiency": "expert"},
    {"name": "python", "years": 5, "proficiency": "intermediate"}
  ],
  "industries": ["banking", "consulting"],
  "roles": ["risk analyst", "risk manager", "senior risk officer"],
  "education": [
    {"level": "masters", "field": "finance"},
    {"level": "bachelors", "field": "mathematics"}
  ],
  "languages": ["english", "german"],
  "certifications": ["FRM", "CFA Level 2"]
}

IMPORTANT: If you're unsure whether something is PII, REMOVE IT.
Better to lose data than to leak identity.

---
RESUME TEXT:
{resume_text}
---

Anonymized JSON:
"""
```

### 3. PII Detection Safety Net

Even after LLM anonymization, we run a second check:

```python
class PIIDetector:
    """
    Paranoid PII detection. 
    Runs AFTER LLM anonymization as safety net.
    """
    
    # Patterns that should NEVER appear in anonymized output
    BLOCKLIST_PATTERNS = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone (US format)
        r'\b\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}\b',  # Intl phone
        r'\b\d{2}[./-]\d{2}[./-]\d{4}\b',  # Date DD/MM/YYYY
        r'\b(19|20)\d{2}\b',  # Years (1900s-2000s)
        r'\blinkedin\.com/in/\w+\b',  # LinkedIn URLs
        r'\b\d{5,}\b',  # Long numbers (IDs, SSN fragments)
    ]
    
    # Known company names (partial list, would be comprehensive)
    COMPANY_NAMES = [
        'deutsche bank', 'goldman sachs', 'jp morgan', 'morgan stanley',
        'mckinsey', 'bcg', 'bain', 'deloitte', 'kpmg', 'pwc', 'ey',
        # ... hundreds more
    ]
    
    # Known university names
    UNIVERSITY_NAMES = [
        'harvard', 'stanford', 'mit', 'oxford', 'cambridge', 'insead',
        # ... hundreds more
    ]
    
    def check(self, text: str) -> list[str]:
        """Returns list of PII violations found, empty if clean."""
        violations = []
        text_lower = text.lower()
        
        for pattern in self.BLOCKLIST_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"Pattern match: {pattern}")
        
        for company in self.COMPANY_NAMES:
            if company in text_lower:
                violations.append(f"Company name: {company}")
        
        for uni in self.UNIVERSITY_NAMES:
            if uni in text_lower:
                violations.append(f"University name: {uni}")
        
        return violations
```

---

## Feedback Anonymization

Same principle applies to user feedback:

```
User types: "I worked with Klaus at Siemens, terrible manager"
                              ↓
                    Local LLM processes
                              ↓
Stored as: {"sentiment": "negative", 
            "reason": "management_experience",
            "applies_to": "company_id_47",
            "strength": -0.8}
```

The verbatim text with names is **never stored**.

```python
FEEDBACK_ANONYMIZATION_PROMPT = """
You are a feedback anonymizer. Extract the MEANING of feedback while removing ALL identifying details.

INPUT: User feedback about a job recommendation
OUTPUT: JSON with structured, anonymized feedback

EXTRACT (the meaning):
- Sentiment (positive/negative/neutral)
- Reason category (skill_mismatch, salary, location, company_culture, 
                   management, work_life_balance, industry, other)
- Strength (-1.0 to +1.0)
- What it applies to (posting, company, industry, skill, location)

REMOVE (identifying details):
- Names of people
- Specific incidents
- Dates
- Anything that could identify someone

EXAMPLES:

Input: "I worked with Klaus at this company, he was a nightmare"
Output: {"sentiment": "negative", "reason": "management", "strength": -0.8, 
         "applies_to": "company"}

Input: "I applied here last year and they ghosted me"
Output: {"sentiment": "negative", "reason": "company_culture", "strength": -0.6,
         "applies_to": "company"}

Input: "This looks perfect, exactly what I'm looking for!"
Output: {"sentiment": "positive", "reason": "general_fit", "strength": 0.9,
         "applies_to": "posting"}

---
USER FEEDBACK:
{feedback_text}
---

Anonymized JSON:
"""
```

---

## Data Flow Guarantees

| Stage | What We Have | What We Store |
|-------|--------------|---------------|
| OAuth callback | Google ID token with email | SHA256 hash of subject ID |
| Resume upload | Full PDF/DOCX | Nothing (RAM only) |
| After LLM processing | Anonymized JSON | Anonymized JSON |
| Feedback received | Verbatim text | Structured sentiment only |
| Session | Auth token | SHA256 hash of token |

---

## Attack Vectors & Mitigations

### Vector 1: Database Breach
**If stolen:** Attacker gets anonymized profiles (skills, experience)
**Cannot get:** Names, companies, contact info (we don't have them)
**Mitigation:** Data is useless for identity theft

### Vector 2: LLM Prompt Injection
**Risk:** Malicious resume tries to make LLM output PII
**Mitigation:** PII detector runs AFTER LLM, catches leaks

### Vector 3: Insider Threat
**Risk:** Employee with DB access
**Cannot do:** Identify users (no PII to correlate)
**Mitigation:** Even we can't deanonymize users

### Vector 4: Correlation Attack
**Risk:** Combine our data with LinkedIn to identify
**Mitigation:** Generalized industries/roles make correlation hard
**Residual risk:** Someone with VERY unique skill combo might be identifiable

### Vector 5: Log Injection
**Risk:** PII ends up in application logs
**Mitigation:** Anonymization happens BEFORE any logging
**Policy:** Never log raw input, only anonymized output

---

## Infrastructure Requirements

### Local LLM Server
- Ollama running on same machine/cluster
- No network calls to external AI services
- Models: mistral:7b or similar for anonymization

### RAM-Only Processing
- Ingestion service configured with no disk writes
- Temp directory mounted as RAM disk (tmpfs)
- No swap (or encrypted swap)

### Network Isolation
- Ingestion service cannot reach internet (except for OAuth validation)
- LLM service is localhost only
- Database is internal network only

---

## Compliance Notes

### GDPR
- **Right to erasure:** Delete user_id, all linked data cascades
- **Data minimization:** We collect only what's needed for matching
- **Purpose limitation:** Data used only for job matching
- **Storage limitation:** Set retention periods, auto-expire

### German BDSG
- Additional protections for employment data
- May need works council consultation if used by employers
- Our use case (individual job seekers) is likely exempt

---

## Open Questions

1. **What if LLM fails to anonymize properly?**
   - Current: PII detector catches it, rejects submission
   - Better: Retry with different prompt? Manual review queue?

2. **How do we handle non-text resumes?**
   - PDF with images of text?
   - Scanned documents?
   - Video resumes?

3. **What about profile photos?**
   - Never accept them?
   - Strip EXIF but keep image?
   - Convert to avatar/cartoon?

4. **Should we offer "verified professional" status?**
   - LinkedIn verification without seeing identity?
   - Employer verification flow?

---

*Next: [03_MATCHING_ALGORITHM.md](03_MATCHING_ALGORITHM.md) - How do we score posting vs profile?*
