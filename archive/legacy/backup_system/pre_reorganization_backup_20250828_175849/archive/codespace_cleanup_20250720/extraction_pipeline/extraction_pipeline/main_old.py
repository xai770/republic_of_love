#!/usr/bin/env python3
"""
Extraction Pipeline - Main Entry Point
======================================

Command-line interface for the job extraction pipeline V7.0.
Clean migration from Sandy's production V7.0 implementation.

Author: Arden (migrated from Sandy V7.0)
Version: 7.0
Date: 2025-07-19
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from .config import Config
from .pipeline import create_extraction_pipeline


def timestamp():
    """Get current timestamp for console output"""
    return datetime.now().strftime("%H:%M:%S")


def setup_logging(verbose: bool = False) -> None:
    """Setup clean logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


def load_job_data(file_path: Path) -> List[Dict[str, Any]]:
    """Load job data from JSON file
    
    Args:
        file_path: Path to JSON file containing job data
        
    Returns:
        List of job dictionaries
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Look for common job data keys
            if 'jobs' in data:
                return data['jobs']
            elif 'results' in data:
                return data['results']
            elif 'data' in data:
                return data['data']
            else:
                # Assume the dict itself is a single job
                return [data]
        else:
            raise ValueError("Invalid JSON structure")
    
    except Exception as e:
        print(f"❌ Error loading job data from {file_path}: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Extraction Pipeline V7.0 - Comprehensive job requirements extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process jobs from JSON file
  python -m extraction_pipeline jobs.json
  
  # Process with custom output directory
  python -m extraction_pipeline jobs.json --output /path/to/output
  
  # Process with custom model
  python -m extraction_pipeline jobs.json --model gemma3n:latest
        """
    )
    
    parser.add_argument(
        'input_file',
        nargs='?',
        help='JSON file containing job data to process (optional)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output directory for reports (default: ./output)',
        default='output'
    )
    parser.add_argument(
        '--model', '-m',
        help='Ollama model to use for extraction (default: gemma3n:latest)',
        default='gemma3n:latest'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--jobs', '-j',
        type=int,
        help='Number of jobs to process (for testing)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Setup logging first
    setup_logging(args.verbose)
    
    print(f"[{timestamp()}] 🚀 Extraction Pipeline V7.0")
    print("=" * 50)
    print(f"[{timestamp()}] Output directory: {args.output}")
    print(f"[{timestamp()}] Model: {args.model}")
    
    # Handle input data
    job_data = []
    
    if args.input_file:
        # Load from file
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"❌ Input file not found: {input_path}")
            sys.exit(1)
        
        print(f"[{timestamp()}] 📂 Loading job data from: {args.input_file}")
        job_data = load_job_data(input_path)
    else:
        # Use sample data for testing
        print(f"[{timestamp()}] 📂 No input file provided, using sample data for testing")
        job_data = [
            {
                "id": "sample_001",
                "title": "Software Engineer",
                "company": "Tech Corp",
                "description": "We are looking for a skilled software engineer with experience in Python, JavaScript, and cloud technologies. The ideal candidate should have strong problem-solving skills and be able to work in an agile environment.",
                "location": "Berlin, Germany"
            }
        ]
    
    # Limit jobs if specified
    if args.jobs and args.jobs < len(job_data):
        job_data = job_data[:args.jobs]
        print(f"[{timestamp()}] 📝 Limited to {args.jobs} jobs for processing")
    
    print(f"[{timestamp()}] ✅ Loaded {len(job_data)} jobs")
    
    # Create configuration
    config = Config()
    config.output_directory = args.output
    config.model_name = args.model
    
    # Create and run pipeline
    print(f"[{timestamp()}] 🔧 Initializing pipeline...")
    pipeline = create_extraction_pipeline(config)
    
    print(f"[{timestamp()}] ⚡ Processing jobs...")
    results = pipeline.process_jobs(job_data)
    
    # Display results
    if 'error' in results:
        print(f"❌ Pipeline error: {results['error']}")
        sys.exit(1)
    
    metadata = results.get('metadata', {})
    summary = results.get('summary', {})
    reports = results.get('reports', {})
    
    print(f"\\n[{timestamp()}] ✅ Pipeline execution completed!")
    print("=" * 50)
    print(f"[{timestamp()}] Jobs processed: {metadata.get('total_jobs_processed', 0)}")
    print(f"[{timestamp()}] Skills extracted: {metadata.get('total_skills_extracted', 0)}")
    print(f"[{timestamp()}] Pipeline version: {metadata.get('pipeline_version', 'Unknown')}")
    
    print(f"\\n[{timestamp()}] 📊 Skills Summary:")
    skills_summary = summary.get('skills_by_category', {})
    for category, count in skills_summary.items():
        print(f"  {category}: {count} skills")
    
    print(f"\\n[{timestamp()}] 📄 Generated Reports:")
    for report_type, path in reports.items():
        if path.startswith("Error:"):
            print(f"  ❌ {report_type.title()}: {path}")
        else:
            print(f"  ✅ {report_type.title()}: {path}")
    
    print(f"\\n[{timestamp()}] 🎉 All processing completed successfully!")


if __name__ == "__main__":
    main()

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import ExtractionPipeline

def timestamp():
    """Get current timestamp for console output"""
    return datetime.now().strftime("%H:%M:%S")

def setup_logging(verbose: bool = False) -> None:
    """Setup clean logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Extraction Pipeline - Clean Job Requirements Extraction"
    )
    
    parser.add_argument(
        '--jobs', '-j',
        type=int,
        default=10,
        help='Number of jobs to process (default: 10)'
    )
    
    parser.add_argument(
        '--fetch-fresh', '-f',
        action='store_true',
        help='Fetch fresh jobs from API before processing'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help='Custom output directory'
    )
    
    return parser.parse_args()

def print_header(max_jobs: int):
    """Print clean header"""
    print("=" * 80)
    print("🚀 EXTRACTION PIPELINE v7.0 - Clean Job Requirements Extraction")
    print("=" * 80)
    print(f"📊 Processing: {max_jobs} jobs")
    print(f"🕐 Started: {timestamp()}")
    print(f"📝 Format: Enhanced Data Dictionary v4.2")
    print("=" * 80)

def print_summary(results):
    """Print execution summary"""
    if "error" in results:
        print(f"\n❌ Error: {results['error']}")
        return
    
    metadata = results.get('metadata', {})
    jobs_processed = metadata.get('total_jobs_processed', 0)
    duration = metadata.get('duration', 0)
    
    print("\n" + "=" * 80)
    print("✅ EXTRACTION PIPELINE COMPLETED")
    print("=" * 80)
    print(f"📊 Jobs Processed: {jobs_processed}")
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"📈 Pipeline Version: {metadata.get('pipeline_version', '7.0')}")
    
    if 'excel_report' in metadata:
        print(f"📋 Excel Report: {metadata['excel_report']}")
    if 'markdown_report' in metadata:
        print(f"📄 Markdown Report: {metadata['markdown_report']}")
    
    print("=" * 80)

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Print header
    print_header(args.jobs)
    
    try:
        # Initialize pipeline
        pipeline = ExtractionPipeline()
        
        # Run pipeline
        results = pipeline.run(
            max_jobs=args.jobs,
            fetch_fresh=args.fetch_fresh
        )
        
        # Print summary
        print_summary(results)
        
        # Exit with appropriate code
        if "error" in results:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        logging.exception("Pipeline execution failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
