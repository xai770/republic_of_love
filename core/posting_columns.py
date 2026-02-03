"""
Column Registry - Single source of truth for postings table columns.

WHY THIS EXISTS:
- Documentation gets stale. This file IS the documentation.
- If you add a column without updating this, grep will find your INSERT/SELECT.
- If you use a DEPRECATED column, your IDE will show the warning.

RULES:
1. Every column access should use these constants
2. Add new columns here FIRST, then write migration
3. Deprecated columns get a # DEPRECATED comment and removal date
"""

from typing import Final

# =============================================================================
# ACTIVE COLUMNS - Safe to use
# =============================================================================

# Identity
POSTING_ID: Final = 'posting_id'
EXTERNAL_ID: Final = 'external_id'
EXTERNAL_JOB_ID: Final = 'external_job_id'
POSTING_NAME: Final = 'posting_name'

# Content
JOB_TITLE: Final = 'job_title'
JOB_DESCRIPTION: Final = 'job_description'
EXTRACTED_SUMMARY: Final = 'extracted_summary'  # DB postings only
BERUF: Final = 'beruf'  # AA occupation category - Added 2026-02-03

# Location
LOCATION_CITY: Final = 'location_city'
LOCATION_POSTAL_CODE: Final = 'location_postal_code'
LOCATION_STATE: Final = 'location_state'
LOCATION_COUNTRY: Final = 'location_country'

# Classification
BERUFENET_ID: Final = 'berufenet_id'
BERUFENET_NAME: Final = 'berufenet_name'
BERUFENET_KLDB: Final = 'berufenet_kldb'
BERUFENET_SCORE: Final = 'berufenet_score'
BERUFENET_VERIFIED: Final = 'berufenet_verified'
QUALIFICATION_LEVEL: Final = 'qualification_level'
DOMAIN_GATE: Final = 'domain_gate'

# Source
SOURCE: Final = 'source'
SOURCE_METADATA: Final = 'source_metadata'
EXTERNAL_URL: Final = 'external_url'
SOURCE_LANGUAGE: Final = 'source_language'

# Lifecycle
POSTING_STATUS: Final = 'posting_status'
FIRST_SEEN_AT: Final = 'first_seen_at'
LAST_SEEN_AT: Final = 'last_seen_at'
UPDATED_AT: Final = 'updated_at'
ENABLED: Final = 'enabled'
INVALIDATED: Final = 'invalidated'
INVALIDATED_AT: Final = 'invalidated_at'
INVALIDATED_REASON: Final = 'invalidated_reason'
PROCESSING_FAILURES: Final = 'processing_failures'

# =============================================================================
# DEPRECATED - Do not use in new code. Will be removed.
# =============================================================================

# DEPRECATED 2026-02-03: Never implemented, 0% fill
# Remove after: 2026-04-01
EMPLOYMENT_CAREER_LEVEL: Final = 'employment_career_level'  # DEPRECATED

# DEPRECATED 2026-02-03: Old experiment, 0% fill  
# Remove after: 2026-04-01
SECT_DECOMPOSED_AT: Final = 'sect_decomposed_at'  # DEPRECATED

# DEPRECATED 2026-02-03: Replaced by source column, 0.1% fill
# Remove after: 2026-04-01
SOURCE_ID: Final = 'source_id'  # DEPRECATED

# DEPRECATED 2026-02-03: Over-engineered audit, 0.2% fill
# Remove after: 2026-04-01
CREATED_BY_TASK_LOG_ID: Final = 'created_by_task_log_id'  # DEPRECATED
UPDATED_BY_TASK_LOG_ID: Final = 'updated_by_task_log_id'  # DEPRECATED

# DEPRECATED 2026-02-03: Debug noise, 1.6% fill
# Remove after: 2026-04-01
PROCESSING_NOTES: Final = 'processing_notes'  # DEPRECATED

# DEPRECATED 2026-02-03: IHL feature deprecated, 2.6% fill
# Remove after: 2026-04-01
IHL_SCORE: Final = 'ihl_score'  # DEPRECATED

# DEPRECATED 2026-02-03: Replaced by berufenet columns, 2.6% fill
# Remove after: 2026-04-01
COMPETENCY_KEYWORDS: Final = 'competency_keywords'  # DEPRECATED

# DEPRECATED 2026-02-03: Old extraction, 2.7% fill
# Remove after: 2026-04-01
EXTRACTED_REQUIREMENTS: Final = 'extracted_requirements'  # DEPRECATED

# DEPRECATED 2026-02-03: Translation never completed, 4.4% fill
# Remove after: 2026-04-01
JOB_DESCRIPTION_EN: Final = 'job_description_en'  # DEPRECATED


# =============================================================================
# HELPER: List all active columns (for SELECT *)
# =============================================================================
ACTIVE_COLUMNS = [
    POSTING_ID, EXTERNAL_ID, EXTERNAL_JOB_ID, POSTING_NAME,
    JOB_TITLE, JOB_DESCRIPTION, EXTRACTED_SUMMARY, BERUF,
    LOCATION_CITY, LOCATION_POSTAL_CODE, LOCATION_STATE, LOCATION_COUNTRY,
    BERUFENET_ID, BERUFENET_NAME, BERUFENET_KLDB, BERUFENET_SCORE, 
    BERUFENET_VERIFIED, QUALIFICATION_LEVEL, DOMAIN_GATE,
    SOURCE, SOURCE_METADATA, EXTERNAL_URL, SOURCE_LANGUAGE,
    POSTING_STATUS, FIRST_SEEN_AT, LAST_SEEN_AT, UPDATED_AT, ENABLED,
    INVALIDATED, INVALIDATED_AT, INVALIDATED_REASON, PROCESSING_FAILURES,
]

DEPRECATED_COLUMNS = [
    EMPLOYMENT_CAREER_LEVEL, SECT_DECOMPOSED_AT, SOURCE_ID,
    CREATED_BY_TASK_LOG_ID, UPDATED_BY_TASK_LOG_ID, PROCESSING_NOTES,
    IHL_SCORE, COMPETENCY_KEYWORDS, EXTRACTED_REQUIREMENTS, JOB_DESCRIPTION_EN,
]
