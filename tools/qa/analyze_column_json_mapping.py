#!/usr/bin/env python3
"""
Column vs JSON Mapping Analyzer
================================

Analyzes which columns in postings table have corresponding data 
in the source_metadata JSON from Deutsche Bank API.

Shows:
1. Columns actively populated from API
2. Columns with no JSON counterpart (candidates for removal)
3. JSON fields not mapped to columns (potential gaps)

Author: Arden & xai
Date: 2025-11-07
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection
import json
import psycopg2.extras

print()
print("=" * 80)
print("COLUMN vs JSON MAPPING ANALYSIS")
print("=" * 80)
print()

conn = get_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Get all column names
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'postings' 
    ORDER BY column_name
""")
all_columns = set(row['column_name'] for row in cur.fetchall())

print(f"📊 Total columns in postings table: {len(all_columns)}")
print()

# Get sample JSON to see what fields we actually receive
cur.execute("""
    SELECT source_metadata 
    FROM postings 
    WHERE source_id = 1 
      AND source_metadata IS NOT NULL
    LIMIT 5
""")

# Collect all JSON keys from samples
all_json_keys = set()
for row in cur.fetchall():
    metadata = row['source_metadata']
    if metadata and 'raw_api_response' in metadata:
        response = metadata['raw_api_response']
        all_json_keys.update(response.keys())

print(f"📥 Fields in Deutsche Bank API response: {len(all_json_keys)}")
print()

# Define the mapping from import script
MAPPED_FIELDS = {
    # Column name: (JSON path, description)
    'external_job_id': ('PositionID', 'MAPPED in import_deutsche_bank_v2.py'),
    'job_title': ('PositionTitle', 'MAPPED in import_deutsche_bank_v2.py'),
    'posting_name': ('PositionTitle', 'MAPPED (duplicate of job_title)'),
    'location_city': ('PositionLocation[0].CityName', 'MAPPED in import_deutsche_bank_v2.py'),
    'location_country': ('PositionLocation[0].CountryName', 'MAPPED in import_deutsche_bank_v2.py'),
    'employment_career_level': ('CareerLevel[0].Name', 'MAPPED in import_deutsche_bank_v2.py'),
    'external_url': ('ApplyURI[0]', 'MAPPED in import_deutsche_bank_v2.py (cleaned)'),
    'posting_position_uri': ('PositionURI', 'MAPPED in import_deutsche_bank_v2.py'),
    'source_metadata': ('(entire response)', 'MAPPED (full JSON stored)'),
    'posting_status': ('(derived)', 'MAPPED (set to "active" on import)'),
    'fetched_at': ('(timestamp)', 'MAPPED (NOW() on import)'),
    'first_seen_at': ('PublicationStartDate', 'MAPPED indirectly via NOW()'),
    'last_seen_at': ('(timestamp)', 'MAPPED (NOW() on update)'),
    'source_id': ('(constant)', 'MAPPED (hardcoded to 1)'),
    
    # Populated by other tools
    'job_description': ('(Workday scrape)', 'POPULATED by fetch_workday_descriptions.py'),
    'posting_id': ('(auto-increment)', 'PRIMARY KEY (auto)'),
    'enabled': ('(manual)', 'SET manually (default true)'),
    
    # Columns filled by workflows
    'ihl_score': ('(workflow)', 'POPULATED by workflow 1121'),
    'ihl_category': ('(workflow)', 'POPULATED by workflow 1121'),
    'ihl_analyzed_at': ('(workflow)', 'POPULATED by workflow 1121'),
    'ihl_workflow_run_id': ('(workflow)', 'POPULATED by workflow 1121'),
    'skill_keywords': ('(workflow)', 'POPULATED by workflow extraction'),
}

# Analyze each column
print("=" * 80)
print("COLUMN ANALYSIS")
print("=" * 80)
print()

mapped_cols = []
workflow_cols = []
unmapped_cols = []
metadata_cols = []

for col in sorted(all_columns):
    if col in MAPPED_FIELDS:
        source, desc = MAPPED_FIELDS[col]
        if 'workflow' in desc.lower():
            workflow_cols.append((col, source, desc))
        else:
            mapped_cols.append((col, source, desc))
    elif col.startswith('metadata_'):
        metadata_cols.append(col)
    else:
        unmapped_cols.append(col)

# Print results
print("✅ COLUMNS ACTIVELY MAPPED FROM API:")
print("-" * 80)
for col, source, desc in sorted(mapped_cols):
    print(f"   {col:30} <- {source}")
print()

print("🔄 COLUMNS POPULATED BY WORKFLOWS:")
print("-" * 80)
for col, source, desc in sorted(workflow_cols):
    print(f"   {col:30} <- {desc}")
print()

print("📋 METADATA-PREFIXED COLUMNS (typically timestamps/tracking):")
print("-" * 80)
for col in sorted(metadata_cols):
    print(f"   {col}")
print()

print("❓ COLUMNS WITH NO CLEAR DATA SOURCE:")
print("-" * 80)
for col in sorted(unmapped_cols):
    print(f"   {col}")
print()

# Check how many records have values in unmapped columns
print("=" * 80)
print("UNMAPPED COLUMN USAGE ANALYSIS")
print("=" * 80)
print()

cur.execute("SELECT COUNT(*) FROM postings WHERE source_id = 1")
total_rows = cur.fetchone()['count']

print(f"Total Deutsche Bank postings: {total_rows}")
print()

usage_stats = []
for col in sorted(unmapped_cols):
    cur.execute(f"""
        SELECT 
            COUNT(*) FILTER (WHERE {col} IS NOT NULL) as filled,
            COUNT(DISTINCT {col}) as unique_vals
        FROM postings 
        WHERE source_id = 1
    """)
    result = cur.fetchone()
    filled = result['filled']
    unique = result['unique_vals']
    pct = (filled / total_rows * 100) if total_rows > 0 else 0
    usage_stats.append((col, filled, unique, pct))

for col, filled, unique, pct in sorted(usage_stats, key=lambda x: x[3], reverse=True):
    if filled > 0:
        print(f"   {col:30} {filled:3}/{total_rows} ({pct:5.1f}%) - {unique} unique")
    else:
        print(f"   {col:30} EMPTY (0%)")

print()

# Show available JSON fields not mapped
print("=" * 80)
print("JSON FIELDS NOT MAPPED TO COLUMNS")
print("=" * 80)
print()

KNOWN_JSON_FIELDS = {
    'PositionID', 'PositionTitle', 'PositionURI', 'PositionLocation',
    'CareerLevel', 'OrganizationName', 'ApplyURI', 'PublicationStartDate',
    'PublicationEndDate', 'PublicationChannel'
}

unmapped_json = all_json_keys - KNOWN_JSON_FIELDS
if unmapped_json:
    print("Fields in JSON but not extracted to columns:")
    for field in sorted(unmapped_json):
        print(f"   {field}")
else:
    print("✅ All JSON fields are either mapped to columns or known.")

print()

# Recommendations
print("=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print()

print("KEEP (actively used):")
print("  - All columns mapped from API (14 columns)")
print("  - All workflow-populated columns (5 columns)")
print("  - job_description (populated by scraper)")
print("  - posting_id, enabled, source_id (core fields)")
print()

print("REVIEW (no clear data source, check usage above):")
empty_unmapped = [col for col, filled, _, _ in usage_stats if filled == 0]
if empty_unmapped:
    print(f"  - {len(empty_unmapped)} columns are 100% empty:")
    for col in empty_unmapped[:10]:  # Show first 10
        print(f"    • {col}")
    if len(empty_unmapped) > 10:
        print(f"    ... and {len(empty_unmapped) - 10} more")
else:
    print("  - All unmapped columns have some data")

print()
print("✨ Analysis complete!")
print()

conn.close()
