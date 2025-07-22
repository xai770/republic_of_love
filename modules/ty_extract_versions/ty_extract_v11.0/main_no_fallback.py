#!/usr/bin/env python3
"""
TY_EXTRACT V11.0 - NO FALLBACK MODE
===================================

PHILOSOPHY: HONEST RESULTS ONLY
- LLM required or immediate crash
- Missing data -> immediate crash  
- Extraction failed -> immediate crash
- No mocks, no stubs, no lies

Usage:
    python main_no_fallback.py           # Process 1 job
    python main_no_fallback.py --jobs 5  # Process 5 jobs
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline_no_fallback import NoFallbackPipeline

def timestamp():
    """Get current timestamp"""
    return datetime.now().strftime("%H:%M:%S")

def setup_logging(verbose: bool = False) -> None:
    """Setup logging"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="TY_EXTRACT V11.0 - NO FALLBACK MODE"
    )
    
    parser.add_argument(
        '--jobs', 
        type=int, 
        default=1,
        help='Number of jobs to process (default: 1)'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--fetch-fresh', 
        action='store_true',
        help='Fetch fresh jobs from API first'
    )
    
    return parser.parse_args()

def main():
    """Main entry point - FAIL FAST"""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    print(f"[{timestamp()}] TY_EXTRACT V11.0: Starting NO FALLBACK mode with {args.jobs} jobs")
    print(f"[{timestamp()}] 🚨 WARNING: This mode will CRASH on any error - no compromises!")
    
    try:
        # Initialize pipeline - CRASH if LLM unavailable
        pipeline = NoFallbackPipeline()
        
        # Run extraction - CRASH on any failure
        result = pipeline.run(
            max_jobs=args.jobs,
            fetch_fresh=args.fetch_fresh
        )
        
        # Show results
        print("\n" + "="*80)
        print("✅ TY_EXTRACT V11.0 - NO FALLBACK SUCCESS")
        print("="*80)
        print(f"✅ Jobs Processed: {result['jobs_processed']}")
        print(f"⏱️  Duration: {result['duration_seconds']:.1f} seconds")
        print(f"🔬 Pipeline: {result['pipeline_version']}")
        print(f"🤖 Method: {result['extraction_method']}")
        print()
        print("📁 Generated Reports:")
        print(f"   • Excel: {result['excel_report']}")
        print(f"   • Markdown: {result['markdown_report']}")
        print()
        print("🎉 V11.0 NO FALLBACK MODE: 100% REAL DATA")
        print("✅ No mocks, no stubs, no lies - honest extraction only!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TY_EXTRACT V11.0 FAILED: {e}")
        print("🚨 This is expected behavior in NO FALLBACK mode")
        print("🔧 Fix the underlying issue - no bandaids allowed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
