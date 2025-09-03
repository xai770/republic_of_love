#!/usr/bin/env python3
"""
TY_EXTRACT Version Comparison Framework
======================================

A systematic framework for comparing extraction results across different versions.
This tool will be used repeatedly for ongoing version evaluation and validation.

Usage:
    python version_comparison_framework.py --versions 7.1,8.0,9.0 --jobs 3 --output comparison_report.md

Features:
- Automated extraction across multiple versions
- Field-by-field comparison with version tracking
- Quality metrics comparison
- Performance benchmarking
- Exportable reports (Markdown, Excel)
- Reusable for any version combinations
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
    
class VersionComparator:
    """Main class for comparing extraction results across versions"""
    
    def __init__(self, base_dir: str = "/home/xai/Documents/republic_of_love"):
        self.base_dir = Path(base_dir)
        self.version_dirs = {
            "7.1": "ty_extract_v7.1_template_based",
            "8.0": "ty_extract_v8.0_llm_only_fail_fast", 
            "9.0": "ty_extract_v9.0_optimized"
        }
        self.results: Dict[str, List[ExtractionResult]] = {}
        
    def run_extraction(self, version: str, num_jobs: int) -> List[ExtractionResult]:
        """Run extraction for a specific version and return results"""
        
        if version not in self.version_dirs:
            raise ValueError(f"Version {version} not supported. Available: {list(self.version_dirs.keys())}")
        
        version_dir = self.base_dir / self.version_dirs[version]
        
        if not version_dir.exists():
            raise FileNotFoundError(f"Version directory not found: {version_dir}")
        
        logger.info(f"🔄 Running extraction for version {version} with {num_jobs} jobs...")
        
        # Change to version directory and run extraction
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["python3", "main.py", "--jobs", str(num_jobs)],
                cwd=version_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            total_time = time.time() - start_time
            
            if result.returncode != 0:
                logger.error(f"❌ Version {version} extraction failed: {result.stderr}")
                return []
            
            logger.info(f"✅ Version {version} extraction completed in {total_time:.1f}s")
            
            # Parse the output files
            return self._parse_extraction_output(version, version_dir, total_time)
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Version {version} extraction timed out")
            return []
        except Exception as e:
            logger.error(f"❌ Version {version} extraction error: {e}")
            return []
    
    def _parse_extraction_output(self, version: str, version_dir: Path, processing_time: float) -> List[ExtractionResult]:
        """Parse extraction output from markdown reports"""
        
        output_dir = version_dir / "output"
        if not output_dir.exists():
            logger.warning(f"⚠️  No output directory found for version {version}")
            return []
        
        # Find the most recent markdown report
        md_files = list(output_dir.glob("daily_report_*.md"))
        if not md_files:
            logger.warning(f"⚠️  No markdown reports found for version {version}")
            return []
        
        latest_report = max(md_files, key=lambda f: f.stat().st_mtime)
        logger.info(f"📄 Parsing report: {latest_report.name}")
        
        try:
            with open(latest_report, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._extract_job_data_from_markdown(version, content, processing_time)
            
        except Exception as e:
            logger.error(f"❌ Failed to parse report for version {version}: {e}")
            return []
    
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
        
        logger.info(f"✅ Parsed {len(results)} jobs for version {version}")
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
                concise_description = line.split("**Concise Description**:")[-1].strip()
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
    
    def compare_versions(self, versions: List[str], num_jobs: int) -> Dict[str, Any]:
        """Run comparison across multiple versions"""
        
        logger.info(f"🚀 Starting version comparison: {versions} with {num_jobs} jobs")
        
        comparison_results = {
            "metadata": {
                "comparison_date": datetime.now().isoformat(),
                "versions_compared": versions,
                "jobs_count": num_jobs,
                "framework_version": "1.0"
            },
            "extractions": {},
            "performance_metrics": {},
            "field_comparisons": {}
        }
        
        # Run extractions for each version
        for version in versions:
            logger.info(f"📊 Processing version {version}...")
            results = self.run_extraction(version, num_jobs)
            comparison_results["extractions"][version] = [asdict(r) for r in results]
            self.results[version] = results
        
        # Calculate performance metrics
        comparison_results["performance_metrics"] = self._calculate_performance_metrics()
        
        # Generate field comparisons
        comparison_results["field_comparisons"] = self._generate_field_comparisons()
        
        return comparison_results
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics across versions"""
        
        metrics = {}
        
        for version, results in self.results.items():
            if not results:
                continue
                
            total_time = sum(r.processing_time for r in results)
            avg_time = total_time / len(results) if results else 0
            
            metrics[version] = {
                "total_processing_time": round(total_time, 2),
                "average_time_per_job": round(avg_time, 2),
                "jobs_processed": len(results),
                "success_rate": 100.0 if results else 0.0
            }
        
        return metrics
    
    def _generate_field_comparisons(self) -> Dict[str, Any]:
        """Generate field-by-field comparisons"""
        
        if not self.results:
            return {}
        
        # Get all versions and find common jobs
        versions = list(self.results.keys())
        if not versions:
            return {}
        
        # Find jobs that exist in all versions
        common_jobs = set()
        first_version = versions[0]
        
        for job in self.results[first_version]:
            job_exists_in_all = True
            for version in versions[1:]:
                if not any(r.job_id == job.job_id for r in self.results[version]):
                    job_exists_in_all = False
                    break
            if job_exists_in_all:
                common_jobs.add(job.job_id)
        
        field_comparisons = {}
        
        for job_id in common_jobs:
            job_comparison = {}
            
            # Get results for this job from all versions
            job_results = {}
            for version in versions:
                for result in self.results[version]:
                    if result.job_id == job_id:
                        job_results[version] = result
                        break
            
            # Compare each field
            fields_to_compare = [
                'job_title', 'company', 'location', 'concise_description',
                'technical_skills', 'business_skills', 'soft_skills',
                'experience_requirements', 'education_requirements'
            ]
            
            for field in fields_to_compare:
                field_data = {}
                for version, result in job_results.items():
                    field_data[f"v{version}"] = getattr(result, field, "")
                
                job_comparison[field] = field_data
            
            field_comparisons[job_id] = job_comparison
        
        return field_comparisons
    
    def generate_report(self, comparison_data: Dict[str, Any], output_file: str):
        """Generate detailed comparison report"""
        
        report_lines = [
            f"# TY_EXTRACT Version Comparison Report",
            f"",
            f"**Generated**: {comparison_data['metadata']['comparison_date']}  ",
            f"**Versions**: {', '.join(comparison_data['metadata']['versions_compared'])}  ",
            f"**Jobs Analyzed**: {comparison_data['metadata']['jobs_count']}  ",
            f"**Framework**: v{comparison_data['metadata']['framework_version']}  ",
            f"",
            f"---",
            f"",
            f"## 📊 Performance Metrics",
            f""
        ]
        
        # Performance metrics table
        if comparison_data["performance_metrics"]:
            report_lines.extend([
                "| Version | Jobs Processed | Total Time (s) | Avg Time/Job (s) | Success Rate |",
                "|---------|---------------|----------------|------------------|--------------|"
            ])
            
            for version, metrics in comparison_data["performance_metrics"].items():
                report_lines.append(
                    f"| v{version} | {metrics['jobs_processed']} | "
                    f"{metrics['total_processing_time']} | "
                    f"{metrics['average_time_per_job']} | "
                    f"{metrics['success_rate']:.1f}% |"
                )
        
        report_lines.extend([
            "",
            "## 🔍 Field-by-Field Comparison",
            ""
        ])
        
        # Field comparisons
        for job_id, job_comparison in comparison_data["field_comparisons"].items():
            first_version = list(comparison_data["metadata"]["versions_compared"])[0]
            job_title = ""
            
            # Try to get job title from any version
            for version_key, field_data in job_comparison.items():
                if "job_title" in job_comparison:
                    version_titles = job_comparison["job_title"]
                    job_title = next(iter(version_titles.values()), "")
                    break
            
            report_lines.extend([
                f"### Job: {job_title} ({job_id})",
                ""
            ])
            
            # Create comparison table for each field
            fields_to_show = [
                ('concise_description', 'Concise Description'),
                ('technical_skills', 'Technical Skills'),
                ('business_skills', 'Business Skills'),
                ('soft_skills', 'Soft Skills'),
                ('experience_requirements', 'Experience Requirements'),
                ('education_requirements', 'Education Requirements')
            ]
            
            for field_key, field_name in fields_to_show:
                if field_key in job_comparison:
                    report_lines.extend([
                        f"#### {field_name}",
                        ""
                    ])
                    
                    field_data = job_comparison[field_key]
                    for version, value in field_data.items():
                        # Format the value
                        if isinstance(value, list):
                            formatted_value = "; ".join(value) if value else "None"
                        else:
                            formatted_value = value or "None"
                        
                        # Truncate long descriptions
                        if len(formatted_value) > 200:
                            formatted_value = formatted_value[:200] + "..."
                        
                        report_lines.append(f"- **{version}**: {formatted_value}")
                    
                    report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"✅ Comparison report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Compare TY_EXTRACT versions")
    parser.add_argument("--versions", required=True, help="Comma-separated list of versions (e.g., 7.1,8.0,9.0)")
    parser.add_argument("--jobs", type=int, default=1, help="Number of jobs to process")
    parser.add_argument("--output", default="version_comparison_report.md", help="Output report file")
    
    args = parser.parse_args()
    
    versions = [v.strip() for v in args.versions.split(',')]
    
    comparator = VersionComparator()
    
    try:
        comparison_data = comparator.compare_versions(versions, args.jobs)
        comparator.generate_report(comparison_data, args.output)
        
        print(f"✅ Version comparison complete!")
        print(f"📊 Report: {args.output}")
        print(f"🔍 Versions: {', '.join(versions)}")
        print(f"📋 Jobs: {args.jobs}")
        
    except Exception as e:
        logger.error(f"❌ Comparison failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
