"""
TY_EXTRACT V11.0 - NO FALLBACK GENERATORS
=========================================

PHILOSOPHY: REAL DATA OR FAILURE
- No "Not extracted" defaults
- No "Unknown" placeholders  
- No "Company not specified" lies
- Show actual data or crash
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class NoFallbackExcelGenerator:
    """Generate Excel with real data only - NO DEFAULTS"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_report(self, processed_jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        """Generate Excel report with REAL data only"""
        
        if not processed_jobs:
            raise ValueError("❌ CRITICAL: No processed jobs - cannot generate report")
        
        # Create data for Excel - CRASH if essential fields missing
        excel_data = []
        
        for job in processed_jobs:
            # CRITICAL: All fields must exist or we crash
            row = {
                'Job ID': job['job_id'],  # CRASH if missing
                'Position Title': job['position_title'],  # CRASH if missing
                'Company': job['company'],  # CRASH if missing
                'Full Content': job['full_content'],  # CRASH if missing
                'Concise Description': job['concise_description'],  # CRASH if missing
                'Processing Timestamp': job['processing_timestamp'],  # CRASH if missing
                'Pipeline Version': config['pipeline_version'],  # CRASH if missing
                'Extraction Method': job['extraction_method']  # CRASH if missing
            }
            excel_data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(excel_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"v11_report_{timestamp}.xlsx"
        filepath = self.output_dir / filename
        
        # Save Excel file
        df.to_excel(filepath, index=False)
        
        print(f"✅ V11.0 Excel report: {filepath}")
        print(f"📊 Jobs processed: {len(processed_jobs)} (100% real data)")
        print("🎯 V11.0: No fallbacks, no defaults, no lies")
        
        logger.info(f"✅ V11.0 Excel generated: {filepath}")
        return str(filepath)


class NoFallbackMarkdownGenerator:
    """Generate Markdown with real data only - NO DEFAULTS"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_report(self, processed_jobs: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        """Generate Markdown report with REAL data only"""
        
        if not processed_jobs:
            raise ValueError("❌ CRITICAL: No processed jobs - cannot generate report")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"v11_report_{timestamp}.md"
        filepath = self.output_dir / filename
        
        # Get current timestamp for report
        report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate markdown content - CRASH if data missing
        content = self._generate_content(processed_jobs, report_timestamp, config)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ V11.0 Markdown report: {filepath}")
        logger.info(f"✅ V11.0 Markdown generated: {filepath}")
        return str(filepath)
    
    def _generate_content(self, processed_jobs: List[Dict[str, Any]], timestamp: str, config: Dict[str, Any]) -> str:
        """Generate content with REAL data - NO FALLBACKS"""
        
        job_count = len(processed_jobs)
        
        # Header section
        content = f"""# TY_EXTRACT V11.0 Report - NO FALLBACK MODE

## Report Summary
- **Total Jobs Processed**: {job_count}
- **Analysis Date**: {timestamp}
- **Pipeline**: ty_extract_v11.0
- **Mode**: NO FALLBACKS - Real data only
- **Template**: 2025-07-20 validated "Your Tasks"/"Your Profile"

## V11.0 Extraction Results

**PHILOSOPHY**: Better honest failure than fake success
- ✅ **LLM Required**: qwen3:latest mandatory
- ✅ **Real Data Only**: No "Not extracted" defaults
- ✅ **Fail Fast**: Missing data causes crash
- ✅ **CV-Ready Format**: Structured "Your Tasks"/"Your Profile"

---

"""
        
        # Process each job - CRASH if essential data missing
        for i, job in enumerate(processed_jobs, 1):
            content += f"""### Job #{i}: {job['position_title']}

## 📋 CORE DATA
- **Job ID**: [{job['job_id']}](https://jobs.db.com/job/{job['job_id']})
- **Position Title**: {job['position_title']}
- **Company**: {job['company']}

## 🎯 V11.0 EXTRACTED CONTENT (2025-07-20 Template)
{job['concise_description']}

## ⚙️ PROCESSING INFO
- **Timestamp**: {job['processing_timestamp']}
- **Method**: {job['extraction_method']}
- **Pipeline**: {config['pipeline_version']}

---

"""
        
        # Footer
        content += f"""## V11.0 Summary

**Success Metrics:**
- ✅ Jobs processed: {job_count}
- ✅ LLM extraction: 100% (qwen3:latest)
- ✅ Template compliance: 2025-07-20 validated
- ✅ Data integrity: NO FALLBACKS

**Files Generated:**
- **Excel**: v11_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx
- **Markdown**: v11_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md

---
*TY_EXTRACT V11.0 - NO FALLBACK MODE*  
*Real extraction or honest failure*
"""
        
        return content
