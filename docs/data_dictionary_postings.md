# Postings Table - Data Dictionary
# Last Updated: 2026-02-03
# Maintainer: Arden

## Column Lifecycle Status
# ACTIVE    - In use, being populated and queried
# SPARSE_OK - Intentionally sparse (e.g., only set on specific conditions)
# DEPRECATED - No longer populated, sunset in progress
# DROP_CANDIDATE - Marked for removal in next schema cleanup

## Core Identification
| Column | Type | Status | Fill% | Description | Added |
|--------|------|--------|-------|-------------|-------|
| posting_id | SERIAL PK | ACTIVE | 100% | Surrogate key for joins | 2024-01 |
| external_id | TEXT | ACTIVE | 100% | Source-prefixed ID (e.g., "aa-12345") | 2024-01 |
| external_job_id | TEXT | ACTIVE | 100% | Raw ID from source API | 2025-01 |
| posting_name | TEXT | ACTIVE | 100% | Employer name or fallback title | 2024-01 |

## Job Content
| Column | Type | Status | Fill% | Description | Added |
|--------|------|--------|-------|-------------|-------|
| job_title | TEXT | ACTIVE | 100% | Job title from source | 2024-01 |
| job_description | TEXT | ACTIVE | 75% | Full job description (HTML cleaned) | 2024-01 |
| extracted_summary | TEXT | SPARSE_OK | 9% | LLM summary (DB postings only) | 2025-06 |
| job_description_en | TEXT | DROP_CANDIDATE | 4% | English translation - never completed | 2025-03 |
| extracted_requirements | JSONB | DROP_CANDIDATE | 3% | Old requirements extraction - replaced | 2025-04 |

## Location
| Column | Type | Status | Fill% | Description | Added |
|--------|------|--------|-------|-------------|-------|
| location_city | TEXT | ACTIVE | 100% | City name | 2024-01 |
| location_postal_code | TEXT | ACTIVE | 42% | German PLZ / Zipcode | 2025-01 |
| location_state | TEXT | ACTIVE | 42% | Bundesland / State | 2025-01 |
| location_country | TEXT | ACTIVE | 98% | Country (default: Deutschland) | 2024-01 |

## Classification (Berufenet)
| Column | Type | Status | Fill% | Description | Added |
|--------|------|--------|-------|-------------|-------|
| berufenet_id | INTEGER | ACTIVE | 22% | Official Berufenet occupation ID | 2025-08 |
| berufenet_name | TEXT | ACTIVE | 22% | Official occupation name | 2025-08 |
| berufenet_kldb | TEXT | ACTIVE | 22% | KldB 2010 classification code | 2025-08 |
| berufenet_score | FLOAT | ACTIVE | 58% | Match confidence (0.0-1.0) | 2025-08 |
| berufenet_verified | TEXT | ACTIVE | 58% | Verification status | 2025-08 |
| qualification_level | TEXT | ACTIVE | 22% | Required qualification level | 2025-08 |
| domain_gate | TEXT | ACTIVE | 62% | Regulated domain flag | 2025-10 |
| competency_keywords | JSONB | DROP_CANDIDATE | 3% | Old keyword extraction - replaced | 2025-04 |

## Source & Metadata
| Column | Type | Status | Fill% | Description | Added |
|--------|------|--------|-------|-------------|-------|
| source | TEXT | ACTIVE | 100% | Source identifier (arbeitsagentur/deutsche_bank) | 2024-01 |
| source_metadata | JSONB | ACTIVE | 100% | Full API response + context | 2025-01 |
| external_url | TEXT | ACTIVE | 100% | Link to original posting | 2024-01 |
| source_language | TEXT | ACTIVE | 13% | Detected language code | 2025-03 |
| source_id | INTEGER FK | DROP_CANDIDATE | 0% | Old FK to sources table - unused | 2024-06 |

## Lifecycle & Timestamps
| Column | Type | Status | Fill% | Description | Added |
|--------|------|--------|-------|-------------|-------|
| posting_status | TEXT | ACTIVE | 100% | active/filled/expired/withdrawn/archived | 2025-01 |
| first_seen_at | TIMESTAMP | ACTIVE | 100% | When we first fetched this posting | 2025-01 |
| last_seen_at | TIMESTAMP | ACTIVE | 100% | Last time seen in source API | 2025-01 |
| updated_at | TIMESTAMP | ACTIVE | 100% | Last modification in our DB | 2024-01 |
| enabled | BOOLEAN | ACTIVE | 100% | Soft-disable for matching | 2024-01 |
| invalidated | BOOLEAN | ACTIVE | 100% | Marked as bad data | 2025-06 |
| invalidated_at | TIMESTAMP | SPARSE_OK | 4% | When invalidated | 2025-06 |
| invalidated_reason | TEXT | SPARSE_OK | 4% | Why invalidated | 2025-06 |

## Deprecated / Dead Columns
| Column | Type | Status | Fill% | Description | Removal Target |
|--------|------|--------|-------|-------------|----------------|
| employment_career_level | TEXT | DROP_CANDIDATE | 0% | Never implemented | 2026-Q1 |
| sect_decomposed_at | TIMESTAMP | DROP_CANDIDATE | 0% | Old experiment | 2026-Q1 |
| ihl_score | INTEGER | DROP_CANDIDATE | 3% | IHL feature deprecated | 2026-Q1 |
| processing_notes | TEXT | DROP_CANDIDATE | 2% | Debug noise | 2026-Q1 |
| created_by_task_log_id | INTEGER | DROP_CANDIDATE | 0% | Over-engineered audit | 2026-Q1 |
| updated_by_task_log_id | INTEGER | DROP_CANDIDATE | 0% | Over-engineered audit | 2026-Q1 |
| processing_failures | INTEGER | ACTIVE | 100% | Retry counter (default 0) | - |

---

## PROPOSED ADDITIONS (require review)

### beruf (AA occupation category)
- **Source**: `source_metadata->'raw_api_response'->>'beruf'`
- **Fill Rate**: ~42% (AA postings with raw_api_response)
- **Use Case**: Dashboard filtering, occupation-based matching
- **Decision**: ADD as column (high query frequency expected)
- **Migration**: Backfill from existing JSONB data

### lat/lon (coordinates)
- **Source**: `source_metadata->'raw_api_response'->'arbeitsort'->'koordinaten'`
- **Fill Rate**: ~42%
- **Use Case**: Distance-based job search
- **Decision**: DEFER (PostGIS needed, low priority)

---

## Schema Change Process

1. **Propose**: Add to PROPOSED section above with rationale
2. **Review**: Discuss fill rate, query patterns, alternatives (JSONB?)
3. **Implement**: Create migration file, update this dictionary
4. **Monitor**: Check fill rate after 30 days
5. **Retire**: Mark as DEPRECATED when superseded, DROP after 90 days
