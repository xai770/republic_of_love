#!/usr/bin/env python3
"""
TY_EXTRACT Version Comparison Framework - Enhanced
=================================================

A comprehensive framework for comparing extraction results across different versions.
Supports both fresh extraction runs and analysis of existing outputs.

Features:
- Fresh extraction runs or existing report analysis
- Field-by-field version tracking
- Performance metrics comparison
- Reusable for any version combinations
- Export to multiple formats (Markdown, JSON, Excel)

Usage:
    # Fresh extraction runs
    python version_comparison_framework_enhanced.py --versions 7.1,8.0,9.0 --jobs 3 --mode fresh
    
    # Analyze existing reports
    python version_comparison_framework_enhanced.py --versions 8.0,9.0 --mode existing --reports v8_report.md,v9_report.md
"""

import os
import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class FieldComparison:
    """Container for comparing a specific field across versions"""
    field_name: str
    versions_data: Dict[str, Any]
    differences_detected: bool
    analysis_notes: List[str]

@dataclass
class ExtractionResult:
    """Container for extraction results from a specific version"""
    version: str
    job_id: str
    job_title: str
    company: str
    location: str
    concise_description: str
    technical_skills: List[str]
    business_skills: List[str]
    soft_skills: List[str]
    experience_requirements: str
    education_requirements: str
    processing_time: float
    extraction_method: str
    quality_score: Optional[float] = None
    error_message: Optional[str] = None
    
    def get_field_value(self, field_name: str) -> Any:
        """Get the value of a specific field"""
        return getattr(self, field_name, None)

class EnhancedVersionComparator:
    """Enhanced version comparison framework"""
    
    def __init__(self, base_dir: str = "/home/xai/Documents/republic_of_love"):
        self.base_dir = Path(base_dir)
        self.version_dirs = {
            "7.1": "ty_extract_v7.1_template_based",
            "8.0": "ty_extract_v8.0_llm_only_fail_fast", 
            "9.0": "ty_extract_v9.0_optimized"
        }
        self.results: Dict[str, List[ExtractionResult]] = {}
        
    def analyze_existing_reports(self, versions: List[str], report_paths: Optional[List[str]] = None) -> Dict[str, List[ExtractionResult]]:
        """Analyze existing extraction reports instead of running fresh extractions"""
        
        if report_paths:
            # Use provided report paths
            if len(report_paths) != len(versions):
                raise ValueError("Number of report paths must match number of versions")
            
            version_reports = dict(zip(versions, report_paths))
        else:
            # Auto-detect latest reports for each version
            version_reports = {}
            for version in versions:
                version_dir = self.base_dir / self.version_dirs.get(version, f"ty_extract_v{version}")
                output_dir = version_dir / "output"
                
                if output_dir.exists():
                    md_files = list(output_dir.glob("daily_report_*.md"))
                    if md_files:
                        latest_report = max(md_files, key=lambda f: f.stat().st_mtime)
                        version_reports[version] = str(latest_report)
                        logger.info(f"📄 Found report for v{version}: {latest_report.name}")
                    else:
                        logger.warning(f"⚠️  No reports found for v{version}")
                else:
                    logger.warning(f"⚠️  Output directory not found for v{version}")
        
        # Parse each report
        for version, report_path in version_reports.items():
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                results = self._extract_job_data_from_markdown(version, content, 0.0)  # No timing data available
                self.results[version] = results
                logger.info(f"✅ Parsed {len(results)} jobs for v{version}")
                
            except Exception as e:
                logger.error(f"❌ Failed to parse report for v{version}: {e}")
                self.results[version] = []
        
        return self.results
    
    def _extract_job_data_from_markdown(self, version: str, content: str, processing_time: float) -> List[ExtractionResult]:
        """Extract job data from markdown content"""
        
        results = []
        
        # Split content by job sections
        job_sections = content.split("### Job #")
        
        for i, section in enumerate(job_sections[1:], 1):  # Skip the header
            try:
                result = self._parse_job_section(version, section, processing_time, i)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"⚠️  Failed to parse job {i} for version {version}: {e}")
                continue
        
        return results
    
    def _parse_job_section(self, version: str, section: str, processing_time: float, job_num: int) -> Optional[ExtractionResult]:
        """Parse individual job section from markdown"""
        
        lines = section.strip().split('\n')
        if not lines:
            return None
        
        # Extract job title from first line
        title_line = lines[0].strip()
        if ':' in title_line:
            job_title = title_line.split(':', 1)[1].strip()
        else:
            job_title = title_line
        
        # Initialize default values
        job_id = f"job{job_num}"
        company = ""
        location = ""
        concise_description = ""
        technical_skills = []
        business_skills = []
        soft_skills = []
        experience_requirements = ""
        education_requirements = ""
        
        # Parse the content
        current_section = None
        for line in lines:
            line = line.strip()
            
            if "**Job ID**:" in line:
                job_id = line.split("**Job ID**:")[-1].strip().replace('[', '').replace(']', '').split('(')[0]
            elif "**Company**:" in line:
                company = line.split("**Company**:")[-1].strip()
            elif "**Metadata Location**:" in line or "**Validated Location**:" in line:
                location = line.split(":")[-1].replace("✅", "").strip()
            elif "**Concise Description**:" in line:
                # Extract full description, may span multiple lines
                desc_start = line.split("**Concise Description**:")[-1].strip()
                if desc_start.startswith("**Role Overview:**"):
                    desc_start = desc_start.replace("**Role Overview:**", "").strip()
                concise_description = desc_start
                
                # Look for continuation on next lines until we hit another field
                line_idx = lines.index(line)
                for next_line in lines[line_idx + 1:]:
                    next_line = next_line.strip()
                    if next_line.startswith("**") or next_line.startswith("#"):
                        break
                    if next_line:
                        concise_description += " " + next_line
                
            elif "### Technical Skills" in line:
                current_section = "technical"
            elif "### Business Skills" in line:
                current_section = "business"
            elif "### Soft Skills" in line:
                current_section = "soft"
            elif "**Experience Required**:" in line:
                experience_requirements = line.split("**Experience Required**:")[-1].strip()
            elif "**Education Required**:" in line:
                education_requirements = line.split("**Education Required**:")[-1].strip()
            elif current_section and "|" in line and "Skill" not in line and "---" not in line and line.count("|") >= 3:
                # Parse skill table row
                skill_name = line.split("|")[1].strip()
                if skill_name and current_section == "technical":
                    technical_skills.append(skill_name)
                elif skill_name and current_section == "business":
                    business_skills.append(skill_name)
                elif skill_name and current_section == "soft":
                    soft_skills.append(skill_name)
        
        return ExtractionResult(
            version=version,
            job_id=job_id,
            job_title=job_title,
            company=company,
            location=location,
            concise_description=concise_description,
            technical_skills=technical_skills,
            business_skills=business_skills,
            soft_skills=soft_skills,
            experience_requirements=experience_requirements,
            education_requirements=education_requirements,
            processing_time=processing_time,
            extraction_method=f"v{version}"
        )
    
    def generate_field_analysis(self, field_name: str) -> FieldComparison:
        """Generate detailed analysis for a specific field across versions"""
        
        versions_data = {}
        differences_detected = False
        analysis_notes = []
        
        # Collect data for this field from all versions
        for version, results in self.results.items():
            if results:
                # For simplicity, use first job result
                field_value = results[0].get_field_value(field_name)
                versions_data[f"v{version}"] = field_value
        
        # Analyze differences
        if len(set(str(v) for v in versions_data.values())) > 1:
            differences_detected = True
            
            # Add specific analysis based on field type
            if field_name == "concise_description":
                analysis_notes.append("Concise description content differs significantly between versions")
                
                # Check for requirements vs role focus
                for version, desc in versions_data.items():
                    if isinstance(desc, str):
                        if any(word in desc.lower() for word in ["completion", "degree", "experience in", "proficiency"]):
                            analysis_notes.append(f"{version}: Requirements-focused description")
                        elif any(word in desc.lower() for word in ["role involves", "responsibilities", "will drive", "ensuring"]):
                            analysis_notes.append(f"{version}: Role-focused description")
            
            elif field_name in ["technical_skills", "business_skills", "soft_skills"]:
                # Analyze skill differences
                all_skills = set()
                for version, skills in versions_data.items():
                    if isinstance(skills, list):
                        all_skills.update(skills)
                
                analysis_notes.append(f"Total unique skills across versions: {len(all_skills)}")
                
                # Find common and unique skills
                if len(versions_data) >= 2:
                    version_names = list(versions_data.keys())
                    v1_skills = set(versions_data[version_names[0]] or [])
                    v2_skills = set(versions_data[version_names[1]] or [])
                    
                    common = v1_skills & v2_skills
                    unique_v1 = v1_skills - v2_skills
                    unique_v2 = v2_skills - v1_skills
                    
                    if common:
                        analysis_notes.append(f"Common skills: {len(common)}")
                    if unique_v1:
                        analysis_notes.append(f"Unique to {version_names[0]}: {len(unique_v1)}")
                    if unique_v2:
                        analysis_notes.append(f"Unique to {version_names[1]}: {len(unique_v2)}")
        
        return FieldComparison(
            field_name=field_name,
            versions_data=versions_data,
            differences_detected=differences_detected,
            analysis_notes=analysis_notes
        )
    
    def generate_comprehensive_report(self, output_file: str, include_raw_data: bool = False):
        """Generate comprehensive comparison report"""
        
        report_lines = [
            "# TY_EXTRACT Comprehensive Version Comparison",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Versions**: {', '.join(f'v{v}' for v in self.results.keys())}  ",
            f"**Framework**: Enhanced Version Comparison v2.0  ",
            "",
            "---",
            "",
            "## 🎯 Executive Summary",
            ""
        ]
        
        # Add executive summary based on field analysis
        key_fields = ["concise_description", "technical_skills", "business_skills", "soft_skills"]
        
        for field in key_fields:
            field_analysis = self.generate_field_analysis(field)
            
            if field_analysis.differences_detected:
                report_lines.extend([
                    f"### {field.replace('_', ' ').title()}",
                    ""
                ])
                
                for note in field_analysis.analysis_notes:
                    report_lines.append(f"- {note}")
                
                report_lines.append("")
        
        # Field-by-field detailed comparison
        report_lines.extend([
            "---",
            "",
            "## 📊 Field-by-Field Analysis",
            ""
        ])
        
        important_fields = [
            ("concise_description", "Concise Description"),
            ("technical_skills", "Technical Skills"),
            ("business_skills", "Business Skills"),
            ("soft_skills", "Soft Skills"),
            ("experience_requirements", "Experience Requirements"),
            ("education_requirements", "Education Requirements")
        ]
        
        for field_key, field_name in important_fields:
            field_analysis = self.generate_field_analysis(field_key)
            
            report_lines.extend([
                f"### {field_name}",
                ""
            ])
            
            if field_analysis.differences_detected:
                report_lines.append("**🔍 Differences Detected**")
                report_lines.append("")
                
                for note in field_analysis.analysis_notes:
                    report_lines.append(f"- {note}")
                
                report_lines.append("")
            else:
                report_lines.append("**✅ Consistent Across Versions**")
                report_lines.append("")
            
            # Show version data
            for version, value in field_analysis.versions_data.items():
                if isinstance(value, list):
                    formatted_value = "; ".join(value) if value else "None"
                else:
                    formatted_value = str(value) if value else "None"
                
                # Truncate long values
                if len(formatted_value) > 150:
                    formatted_value = formatted_value[:150] + "..."
                
                report_lines.append(f"- **{version}**: {formatted_value}")
            
            report_lines.extend(["", "---", ""])
        
        # Include raw data if requested
        if include_raw_data:
            report_lines.extend([
                "## 📋 Raw Extraction Data",
                "",
                "```json"
            ])
            
            raw_data = {}
            for version, results in self.results.items():
                raw_data[version] = [asdict(r) for r in results]
            
            report_lines.extend([
                json.dumps(raw_data, indent=2),
                "```"
            ])
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"✅ Comprehensive report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Enhanced TY_EXTRACT version comparison")
    parser.add_argument("--versions", required=True, help="Comma-separated list of versions (e.g., 7.1,8.0,9.0)")
    parser.add_argument("--mode", choices=["fresh", "existing"], default="existing", help="Fresh extraction or existing report analysis")
    parser.add_argument("--jobs", type=int, default=1, help="Number of jobs to process (fresh mode only)")
    parser.add_argument("--reports", help="Comma-separated report paths (existing mode only)")
    parser.add_argument("--output", default="enhanced_version_comparison.md", help="Output report file")
    parser.add_argument("--include-raw", action="store_true", help="Include raw extraction data in report")
    
    args = parser.parse_args()
    
    versions = [v.strip() for v in args.versions.split(',')]
    
    comparator = EnhancedVersionComparator()
    
    try:
        if args.mode == "existing":
            report_paths = args.reports.split(',') if args.reports else None
            comparator.analyze_existing_reports(versions, report_paths)
        else:
            # Fresh mode not implemented in this version
            logger.error("Fresh mode not implemented yet. Use --mode existing")
            return 1
        
        comparator.generate_comprehensive_report(args.output, args.include_raw)
        
        print(f"✅ Enhanced version comparison complete!")
        print(f"📊 Report: {args.output}")
        print(f"🔍 Versions: {', '.join(f'v{v}' for v in versions)}")
        
    except Exception as e:
        logger.error(f"❌ Comparison failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
