#!/usr/bin/env python3
"""
Snapshot Generator for ty_report_base Validation
Creates ground truth examples for Misty & Xai review

This generates 3 scenarios:
1. Simple single-job extraction
2. Multi-job batch processing  
3. Edge case with malformed/missing data
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the ty_report_base modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from ty_report_base.engine.report_generator import ReportGenerator

# Also add V11.0 hooks for full integration test
sys.path.insert(0, str(Path(__file__).parent.parent / "modules" / "ty_extract_versions" / "ty_extract_v11.0" / "calls"))
from report_hooks import V11ReportHooks

def create_simple_single_job():
    """Scenario 1: Clean, well-formed single job extraction"""
    print("📋 Creating Scenario 1: Simple Single Job")
    
    input_block = {
        "title": "Senior Software Engineer - Backend",
        "company": "TechFlow Solutions",
        "location": "Berlin, Germany",
        "job_type": "Full-time",
        "salary_range": "€75,000 - €95,000",
        "requirements": [
            "5+ years Python experience",
            "FastAPI or Django framework",
            "PostgreSQL database design", 
            "Docker containerization",
            "CI/CD pipeline experience"
        ],
        "description": "Join our growing team building scalable microservices for financial technology. You'll architect backend systems, mentor junior developers, and collaborate with product teams to deliver high-quality software solutions.",
        "benefits": [
            "Remote-friendly work culture",
            "30 days vacation",
            "Learning budget €2,000/year",
            "Health insurance"
        ],
        "extracted_at": "2025-07-22T17:15:00Z",
        "extraction_confidence": 0.94,
        "source_url": "https://example-jobs.com/senior-backend-dev"
    }
    
    hooks = V11ReportHooks()
    report = hooks.generate_extraction_report(
        extraction_blocks=[input_block],
        job_metadata={
            "extraction_version": "v11.0",
            "extraction_method": "structured_fail_fast",
            "source_type": "job_portal",
            "processing_time_ms": 1247
        }
    )
    
    return {
        "scenario": "simple_single_job",
        "input_block": input_block,
        "generated_report": report,
        "notes": "Clean, well-structured job posting with all standard fields present"
    }

def create_multi_job_batch():
    """Scenario 2: Multiple jobs in batch processing"""
    print("📋 Creating Scenario 2: Multi-Job Batch")
    
    input_blocks = [
        {
            "title": "Data Scientist",
            "company": "AI Research Lab",
            "location": "Munich, Germany", 
            "requirements": ["Python", "TensorFlow", "Statistics", "PhD preferred"],
            "extraction_confidence": 0.89,
            "source_url": "https://research-jobs.com/data-scientist"
        },
        {
            "title": "DevOps Engineer", 
            "company": "CloudNative Corp",
            "location": "Remote (EU timezone)",
            "requirements": ["Kubernetes", "AWS", "Terraform", "Monitoring"],
            "salary_range": "€65,000 - €85,000",
            "extraction_confidence": 0.91,
            "source_url": "https://devops-jobs.com/k8s-engineer"
        },
        {
            "title": "Product Manager - B2B SaaS",
            "company": "StartupAccel",
            "location": "Hamburg, Germany",
            "requirements": ["5+ years PM experience", "B2B SaaS", "Agile/Scrum", "Stakeholder management"],
            "extraction_confidence": 0.76,
            "source_url": "https://pm-jobs.com/b2b-saas-pm",
            "notes": "Lower confidence due to mixed formatting in source"
        }
    ]
    
    hooks = V11ReportHooks()
    report = hooks.generate_extraction_report(
        extraction_blocks=input_blocks,
        job_metadata={
            "extraction_version": "v11.0", 
            "batch_id": "batch_20250722_171500",
            "total_processed": 3,
            "extraction_method": "structured_fail_fast",
            "avg_confidence": 0.85
        }
    )
    
    return {
        "scenario": "multi_job_batch",
        "input_blocks": input_blocks,
        "generated_report": report,
        "notes": "Batch of 3 jobs with varying data completeness and confidence levels"
    }

def create_edge_case_malformed():
    """Scenario 3: Edge case with missing/malformed data"""
    print("📋 Creating Scenario 3: Edge Case - Malformed Data")
    
    # Simulate various data quality issues
    input_blocks = [
        {
            "title": "",  # Missing title
            "company": "UnknownCorp",
            "requirements": None,  # Null requirements
            "extraction_confidence": 0.23,  # Very low confidence
            "source_url": "https://broken-site.com/job123"
        },
        {
            "title": "Software Engineer Software Engineer Software Engineer",  # Duplicated
            "company": "",  # Missing company
            "location": "   ",  # Whitespace only
            "requirements": ["Python", "Python", "Python", ""],  # Duplicates and empty
            "salary_range": "Competitive salary negotiable upon experience level",  # Non-standard format
            "extraction_confidence": 0.45,
            "extraction_errors": ["title_duplication_detected", "company_field_empty"],
            "source_url": "https://messy-jobs.com/duplicate-title"
        }
    ]
    
    hooks = V11ReportHooks()
    report = hooks.generate_extraction_report(
        extraction_blocks=input_blocks,
        job_metadata={
            "extraction_version": "v11.0",
            "extraction_warnings": [
                "low_confidence_jobs_detected", 
                "missing_critical_fields",
                "data_quality_issues"
            ],
            "processing_notes": "Edge case test - intentionally malformed data"
        }
    )
    
    return {
        "scenario": "edge_case_malformed", 
        "input_blocks": input_blocks,
        "generated_report": report,
        "notes": "Edge case testing with missing fields, low confidence, and malformed data"
    }

def save_snapshot(snapshot_data, scenario_name):
    """Save snapshot data to files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_path = Path(__file__).parent / "report_output_snapshots"
    
    # Save complete snapshot
    snapshot_file = base_path / f"{scenario_name}_{timestamp}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
    
    # Save human-readable summary
    summary_file = base_path / f"{scenario_name}_{timestamp}_summary.md"
    with open(summary_file, 'w') as f:
        f.write(f"# Snapshot Summary: {scenario_name}\n\n")
        f.write(f"**Generated:** {timestamp}\n")
        f.write(f"**Scenario:** {snapshot_data['notes']}\n\n")
        
        f.write("## Input Data\n")
        if 'input_block' in snapshot_data:
            f.write("**Single Job Block:**\n")
            f.write(f"- Title: {snapshot_data['input_block'].get('title', 'N/A')}\n")
            f.write(f"- Company: {snapshot_data['input_block'].get('company', 'N/A')}\n")
            f.write(f"- Confidence: {snapshot_data['input_block'].get('extraction_confidence', 'N/A')}\n")
        elif 'input_blocks' in snapshot_data:
            f.write(f"**Multi-Job Batch:** {len(snapshot_data['input_blocks'])} jobs\n")
            for i, block in enumerate(snapshot_data['input_blocks'], 1):
                f.write(f"- Job {i}: {block.get('title', 'N/A')} @ {block.get('company', 'N/A')}\n")
        
        f.write("\n## Generated Report\n")
        report = snapshot_data['generated_report']
        f.write(f"- **Title:** {report['title']}\n")
        f.write(f"- **Generated by:** {report['metadata']['generated_by']}\n")
        f.write(f"- **Timestamp:** {report['metadata']['timestamp']}\n")
        f.write(f"- **Empathy enabled:** {report['metadata']['empathy_enabled']}\n")
        f.write(f"- **QA flags:** {report['metadata']['qa_flags']}\n")
        f.write(f"- **Sections:** {len(report['sections'])}\n")
        
        for section in report['sections']:
            f.write(f"  - {section['name']}\n")
    
    return snapshot_file, summary_file

if __name__ == "__main__":
    print("🌟 ty_report_base Validation Snapshot Generator")
    print("=" * 55)
    print("Creating ground truth examples for Misty & Xai review\n")
    
    try:
        # Generate all scenarios
        scenario1 = create_simple_single_job()
        scenario2 = create_multi_job_batch()
        scenario3 = create_edge_case_malformed()
        
        # Save snapshots
        print("\n💾 Saving snapshots...")
        
        for scenario in [scenario1, scenario2, scenario3]:
            snapshot_file, summary_file = save_snapshot(scenario, scenario['scenario'])
            print(f"✅ Saved: {snapshot_file.name}")
            print(f"   📄 Summary: {summary_file.name}")
        
        print(f"\n🎉 Snapshot Generation Complete!")
        print(f"📁 All files saved to: tests/report_output_snapshots/")
        print(f"✨ Ready for Misty & Xai review!")
        
    except Exception as e:
        print(f"❌ Snapshot generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
