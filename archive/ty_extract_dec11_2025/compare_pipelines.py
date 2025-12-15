#!/usr/bin/env python3
"""
Pipeline Comparison Script
==========================

Runs both the baseline and TY_EXTRACT pipelines and creates a comprehensive
comparison report.

Usage:
    python compare_pipelines.py --jobs 2
"""

import argparse
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
import sys
import os

def run_command_with_timeout(command, timeout=3000, capture_output=True):
    """Run a command with timeout and capture output"""
    try:
        start_time = time.time()
        
        if capture_output:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=timeout
            )
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'success': result.returncode == 0,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        else:
            # For commands that need real-time output
            start_time = time.time()
            result = subprocess.run(command, shell=True, timeout=timeout)
            end_time = time.time()
            duration = end_time - start_time
            
            return {
                'success': result.returncode == 0,
                'duration': duration,
                'stdout': '',
                'stderr': '',
                'returncode': result.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'duration': timeout,
            'stdout': '',
            'stderr': f'Command timed out after {timeout} seconds',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'duration': 0,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

def get_latest_output_files(output_dir):
    """Get the latest output files from a directory"""
    output_path = Path(output_dir)
    if not output_path.exists():
        return None, None
    
    # Find latest Excel and Markdown files
    excel_files = list(output_path.glob("*report*.xlsx"))
    md_files = list(output_path.glob("*report*.md"))
    
    latest_excel = max(excel_files, key=os.path.getctime) if excel_files else None
    latest_md = max(md_files, key=os.path.getctime) if md_files else None
    
    return latest_excel, latest_md

def analyze_output_file(file_path):
    """Analyze an output file and return statistics"""
    if not file_path or not file_path.exists():
        return {"error": "File not found"}
    
    try:
        file_size = file_path.stat().st_size
        created_time = datetime.fromtimestamp(file_path.stat().st_ctime)
        
        analysis = {
            "file_path": str(file_path),
            "file_size": file_size,
            "created_time": created_time.isoformat(),
            "file_type": file_path.suffix
        }
        
        if file_path.suffix == '.md':
            # Analyze markdown content
            content = file_path.read_text(encoding='utf-8')
            analysis.update({
                "line_count": len(content.splitlines()),
                "character_count": len(content),
                "jobs_mentioned": content.count("Job #") + content.count("🔍 Job"),
                "skills_mentioned": content.count("skill") + content.count("Skills")
            })
        
        return analysis
        
    except Exception as e:
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Compare baseline and TY_EXTRACT pipelines")
    parser.add_argument('--jobs', '-j', type=int, default=2, help='Number of jobs to process')
    parser.add_argument('--timeout', '-t', type=int, default=3000, help='Timeout in seconds (default: 3000)')
    parser.add_argument('--baseline-only', action='store_true', help='Run only baseline pipeline')
    parser.add_argument('--ty-only', action='store_true', help='Run only TY_EXTRACT pipeline')
    
    args = parser.parse_args()
    
    # Create report
    report = {
        "comparison_date": datetime.now().isoformat(),
        "jobs_processed": args.jobs,
        "baseline_pipeline": {},
        "ty_extract_pipeline": {},
        "comparison": {}
    }
    
    print("=" * 80)
    print("🔍 PIPELINE COMPARISON TOOL")
    print("=" * 80)
    print(f"📊 Jobs to process: {args.jobs}")
    print(f"⏱️  Timeout: {args.timeout} seconds")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Run baseline pipeline
    if not args.ty_only:
        print("\n🚀 RUNNING BASELINE PIPELINE...")
        print("=" * 50)
        
        baseline_cmd = f"cd /home/xai/Documents/sandy && python run_daily_report.py --jobs {args.jobs}"
        print(f"📋 Command: {baseline_cmd}")
        print("📊 Real-time output:\n")
        baseline_result = run_command_with_timeout(baseline_cmd, timeout=args.timeout, capture_output=False)
        
        report["baseline_pipeline"] = {
            "command": baseline_cmd,
            "duration": baseline_result['duration'],
            "success": baseline_result['success'],
            "returncode": baseline_result['returncode'],
            "stderr": "Real-time output displayed above"
        }
        
        if baseline_result['success']:
            print(f"\n✅ Baseline completed in {baseline_result['duration']:.2f} seconds")
            # Analyze output files
            excel_file, md_file = get_latest_output_files("/home/xai/Documents/sandy/output")
            report["baseline_pipeline"]["output_excel"] = analyze_output_file(excel_file)
            report["baseline_pipeline"]["output_markdown"] = analyze_output_file(md_file)
        else:
            print(f"\n❌ Baseline failed after {baseline_result['duration']:.2f} seconds")
            print(f"   Return code: {baseline_result['returncode']}")
    
    # Run TY_EXTRACT pipeline
    if not args.baseline_only:
        print("\n🚀 RUNNING TY_EXTRACT PIPELINE...")
        print("=" * 50)
        
        ty_cmd = f"cd /home/xai/Documents/sandy/ty_extract && python main.py --jobs {args.jobs}"
        print(f"📋 Command: {ty_cmd}")
        print("📊 Real-time output:\n")
        ty_result = run_command_with_timeout(ty_cmd, timeout=args.timeout, capture_output=False)
        
        report["ty_extract_pipeline"] = {
            "command": ty_cmd,
            "duration": ty_result['duration'],
            "success": ty_result['success'],
            "returncode": ty_result['returncode'],
            "stderr": "Real-time output displayed above"
        }
        
        if ty_result['success']:
            print(f"\n✅ TY_EXTRACT completed in {ty_result['duration']:.2f} seconds")
            # Analyze output files
            excel_file, md_file = get_latest_output_files("/home/xai/Documents/sandy/ty_extract/output")
            report["ty_extract_pipeline"]["output_excel"] = analyze_output_file(excel_file)
            report["ty_extract_pipeline"]["output_markdown"] = analyze_output_file(md_file)
        else:
            print(f"\n❌ TY_EXTRACT failed after {ty_result['duration']:.2f} seconds")
            print(f"   Return code: {ty_result['returncode']}")
    
    # Create comparison
    print("\n📊 COMPARISON RESULTS")
    print("=" * 80)
    
    if not args.baseline_only and not args.ty_only:
        baseline_duration = report["baseline_pipeline"].get("duration", 0)
        ty_duration = report["ty_extract_pipeline"].get("duration", 0)
        
        if baseline_duration > 0 and ty_duration > 0:
            speedup = baseline_duration / ty_duration
            report["comparison"] = {
                "baseline_duration": baseline_duration,
                "ty_extract_duration": ty_duration,
                "speedup_factor": speedup,
                "time_saved": baseline_duration - ty_duration
            }
            
            print(f"⚡ PERFORMANCE COMPARISON:")
            print(f"   • Baseline:   {baseline_duration:.2f} seconds")
            print(f"   • TY_EXTRACT: {ty_duration:.2f} seconds")
            print(f"   • Speedup:    {speedup:.1f}x faster")
            print(f"   • Time saved: {baseline_duration - ty_duration:.2f} seconds")
        else:
            print("⚠️  Cannot compare - one or both pipelines failed")
    
    # Save report
    report_file = Path("/home/xai/Documents/sandy/ty_extract/pipeline_comparison_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 DETAILED REPORT SAVED:")
    print(f"   {report_file}")
    
    # Create human-readable summary
    summary_file = Path("/home/xai/Documents/sandy/ty_extract/pipeline_comparison_summary.md")
    with open(summary_file, 'w') as f:
        f.write("# Pipeline Comparison Summary\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Jobs Processed:** {args.jobs}\n\n")
        
        if not args.ty_only:
            f.write("## Baseline Pipeline\n")
            baseline = report["baseline_pipeline"]
            f.write(f"- **Duration:** {baseline.get('duration', 0):.2f} seconds\n")
            f.write(f"- **Success:** {'✅' if baseline.get('success') else '❌'}\n")
            if baseline.get('stderr'):
                f.write(f"- **Error:** {baseline['stderr'][:200]}...\n")
            f.write("\n")
        
        if not args.baseline_only:
            f.write("## TY_EXTRACT Pipeline\n")
            ty = report["ty_extract_pipeline"]
            f.write(f"- **Duration:** {ty.get('duration', 0):.2f} seconds\n")
            f.write(f"- **Success:** {'✅' if ty.get('success') else '❌'}\n")
            if ty.get('stderr'):
                f.write(f"- **Error:** {ty['stderr'][:200]}...\n")
            f.write("\n")
        
        if "comparison" in report:
            comp = report["comparison"]
            f.write("## Performance Comparison\n")
            f.write(f"- **Baseline Duration:** {comp['baseline_duration']:.2f} seconds\n")
            f.write(f"- **TY_EXTRACT Duration:** {comp['ty_extract_duration']:.2f} seconds\n")
            f.write(f"- **Speedup Factor:** {comp['speedup_factor']:.1f}x\n")
            f.write(f"- **Time Saved:** {comp['time_saved']:.2f} seconds\n")
    
    print(f"📄 SUMMARY REPORT SAVED:")
    print(f"   {summary_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
