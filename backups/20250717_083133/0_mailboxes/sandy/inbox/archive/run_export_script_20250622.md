# Sandy: Run Export Script Instructions
**Date:** June 22, 2025  
**From:** Sage & Xai  
**To:** Sandy  
**Priority:** High  

## Task Overview
We've improved the job match export script and need you to run it in your venv to generate fresh Excel and JSON reports with all A-R columns properly populated.

## What We Fixed
- Enhanced extraction logic for "no-go rationale" and application narrative fields
- Better handling of malformed outputs from consciousness evaluation
- Ensured all A-R columns are populated correctly
- Added proper fallbacks for missing data

## Instructions

### 1. Navigate to SUNSET directory
```bash
cd /home/xai/Documents/sunset
```

### 2. Activate your venv
```bash
source your_venv_name/bin/activate  # Replace with your actual venv name
```

### 3. Run the export script
```bash
python run_pipeline/export_job_matches.py --feedback-system --output-file reports/fresh_review/job_match_report_fixed_20250622.xlsx
```

### 4. Also generate JSON version
```bash
python run_pipeline/export_job_matches.py --feedback-system --output-format csv --output-file reports/fresh_review/job_match_report_fixed_20250622.json
```

## Expected Output
- Excel file: `reports/fresh_review/job_match_report_fixed_20250622.xlsx`
- JSON file: `reports/fresh_review/job_match_report_fixed_20250622.json`
- Both files should contain ~5 rows with all columns A-R populated
- "No-go rationale" and "Application narrative" fields should now be properly extracted

## What to Check
1. Verify all columns A-R are present and populated
2. Check that "No-go rationale" contains meaningful content (not malformed text)
3. Ensure "Application narrative" is present for Good matches
4. Confirm hyperlinks in Job ID column work correctly

## If You Encounter Issues
1. Check that your venv has pandas and openpyxl installed
2. Verify you're in the sunset directory
3. Check that the reports/fresh_review directory exists (script should create it)
4. Let us know immediately if any errors occur

## Next Steps
Once generated, we'll review the new reports to ensure data quality and then proceed with any final optimizations needed for the job matching pipeline.

---
**Note:** This improved script addresses the malformed "no-go rationale" extraction we identified earlier. The output should now be clean and ready for the feedback system workflow.
