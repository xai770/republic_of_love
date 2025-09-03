#!/usr/bin/env python3
"""
TY_EXTRACT V14 Runner
====================

Simple runner script for testing the V14 pipeline.
This handles the import path issues when running directly.
"""

import sys
from pathlib import Path

# Add the modules directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Now import and run the pipeline
try:
    from ty_extract_versions.ty_extract_v14.config import Config
    from ty_extract_versions.ty_extract_v14.pipeline import TyExtractPipeline
    from ty_extract_versions.ty_extract_v14.reports import ReportGenerator
    import logging
    from datetime import datetime
    
    def main():
        """Run the V14 pipeline"""
        
        print("🚀 Starting TY_EXTRACT V14 Pipeline")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        try:
            # Create configuration from external files
            config = Config.load_from_external()
            print("📋 Configuration loaded from external files")
            
            # Print configuration summary
            print(f"\n📊 Configuration Summary:")
            print(f"   • Data directory: {config.data_dir}")
            print(f"   • Output directory: {config.output_dir}")  
            print(f"   • LLM model: {config.llm_model}")
            print(f"   • Excel reports: {'✅' if config.generate_excel else '❌'}")
            print(f"   • Markdown reports: {'✅' if config.generate_markdown else '❌'}")
            
            # Initialize pipeline
            pipeline = TyExtractPipeline(config)
            
            # Run pipeline
            print(f"\n🔄 Processing files from: {config.data_dir}")
            result = pipeline.run()
            
            # Print results summary
            print(f"\n🎯 Pipeline Results:")
            print(f"   • Jobs extracted: {result.total_jobs}")
            print(f"   • Total skills found: {result.total_skills}")
            print(f"   • Processing time: {result.duration:.2f}s")
            print(f"   • Status: {'✅ Success' if result.success else '❌ Failed'}")
            
            if result.error_message:
                print(f"   • Error: {result.error_message}")
            
            # Generate reports if we have jobs
            if result.total_jobs > 0:
                print(f"\n📊 Generating reports...")
                report_generator = ReportGenerator(config)
                reports = report_generator.generate_reports(result.jobs)
                
                if reports:
                    print(f"   • Reports generated:")
                    for report_type, path in reports.items():
                        print(f"     - {report_type.title()}: {path}")
                else:
                    print(f"   • No reports generated")
            
            # Print completion message
            if result.total_jobs > 0:
                print(f"\n✅ Pipeline completed successfully!")
                print(f"📂 Check {config.output_dir} for output files")
            else:
                print(f"\n⚠️ Pipeline completed but no jobs were extracted")
                print(f"💡 Check your data files and LLM connectivity")
                
            return 0 if result.success else 1
            
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    if __name__ == "__main__":
        exit_code = main()
        sys.exit(exit_code)
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("💡 Make sure you're running from the correct directory")
    sys.exit(1)
