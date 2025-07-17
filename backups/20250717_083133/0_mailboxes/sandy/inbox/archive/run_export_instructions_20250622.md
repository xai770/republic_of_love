# Instructions for Sandy: Run Improved Export Script

**Date:** June 22, 2025  
**From:** Sage & Consciousness Team  
**To:** Sandy  

## Summary
We've improved the extraction logic in `export_job_matches.py` to handle malformed no-go rationales and ensure all A-R columns are properly populated. Please run this in your venv to generate a fresh report.

## What We Fixed
1. **Improved no-go rationale extraction** - Better handling of malformed consciousness evaluation outputs
2. **Enhanced fallback logic** - Multiple sources for extracting evaluation data (llama32_evaluation → evaluation_results)
3. **Better domain extraction** - Uses job content organization division as primary source
4. **Cleaned up malformed rationales** - Removes problematic wrapping text and provides proper fallbacks

## Instructions to Run

### 1. Activate Your Virtual Environment
```bash
cd /home/xai/Documents/sunset
source venv/bin/activate  # or however you activate your venv
```

### 2. Run the Export Script
```bash
python run_pipeline/export_job_matches.py --feedback-system --output-file reports/fresh_review/job_match_report_fixed_20250622.xlsx
```

### 3. Also Generate JSON for Easy Review
```bash
python -c "
import json
from run_pipeline.export_job_matches import export_job_matches, extract_job_data_for_feedback_system, initialize_logging_columns
from pathlib import Path
import glob
from datetime import datetime

# Collect all job files
job_files = list(Path('data/postings').rglob('*.json'))
processed_jobs = []

for job_file in job_files:
    try:
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
            has_evaluation = (
                job_data.get('llama32_evaluation') or
                (job_data.get('evaluation_results', {}).get('cv_to_role_match'))
            )
            if has_evaluation:
                processed_jobs.append(job_data)
    except Exception as e:
        continue

# Extract data using improved logic
matches = []
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for job_data in processed_jobs:
    job_match = extract_job_data_for_feedback_system(job_data)
    logging_cols = initialize_logging_columns(timestamp)
    matches.append({**job_match, **logging_cols})

# Save JSON
with open('reports/fresh_review/job_match_report_fixed_20250622.json', 'w', encoding='utf-8') as f:
    json.dump(matches, f, indent=2, ensure_ascii=False)

print(f'Exported {len(matches)} jobs to JSON')
"
```

## Expected Output
The new report should have:
- **All A-R columns populated** (Job ID, Job description, Position title, Location, Job domain, Match level, Evaluation date, Has domain gap, Domain assessment, No-go rationale, Application narrative, plus logging columns L-R)
- **Clean no-go rationales** without malformed wrapping text
- **Proper application narratives** for Good matches
- **Accurate domain extraction** from job content

## What to Check
1. **Column completeness** - All 18 columns (A-R) should have data
2. **No-go rationale quality** - Should be clean, professional text without malformed formatting
3. **Application narrative presence** - Good matches should have meaningful narratives
4. **Domain accuracy** - Job domains should reflect the actual job content

## Files to Review
After running, please share:
1. `reports/fresh_review/job_match_report_fixed_20250622.xlsx` - The Excel file for review
2. `reports/fresh_review/job_match_report_fixed_20250622.json` - JSON for technical analysis

## Key Improvements Made
- **Fixed malformed rationale extraction**: The script now properly handles consciousness evaluation outputs that were incorrectly formatted
- **Enhanced domain detection**: Uses `job_content.organization.division` as primary source
- **Better fallback logic**: Multiple evaluation sources (llama32_evaluation → evaluation_results)
- **Cleaned up text processing**: Removes problematic wrapper text and provides professional alternatives

Let us know if you encounter any issues or if the venv needs additional packages installed!

---
**Next Steps:** Once we have the fresh export, we'll review the data quality and continue optimizing the extraction pipeline based on real results.
