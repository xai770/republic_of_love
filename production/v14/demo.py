#!/usr/bin/env python3
"""
TY_EXTRACT V14 - Demo Script
============================

Demonstrates the complete pipeline with external configuration.
"""

import logging
from pathlib import Path

from .config import Config
from .pipeline import TyExtractPipeline

def setup_logging(log_level: str):
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )

def main():
    """Run the demo"""
    
    print("🚀 TY_EXTRACT V14 Demo - External Config Version")
    print("=" * 50)
    
    try:
        # Load configuration from external files
        print("📋 Loading external configuration...")
        config = Config.load_from_external()
        
        # Setup logging based on external config
        setup_logging(config.log_level)
        
        logger = logging.getLogger('ty_extract_v14.demo')
        logger.info("✅ External configuration loaded successfully")
        logger.info(f"🤖 LLM Model: {config.llm_model}")
        logger.info(f"📂 Output Directory: {config.output_dir}")
        logger.info(f"🔧 Pipeline Version: {config.pipeline_version}")
        
        # Display configuration snapshot
        if config.config_snapshot:
            logger.info(f"📸 Config Hash: {config.config_snapshot.config_hash[:8]}")
            logger.info(f"📝 Templates: {list(config.config_snapshot.templates.keys())}")
        
        # Initialize and run pipeline
        print("🔄 Initializing pipeline...")
        pipeline = TyExtractPipeline(config)
        
        print("▶️ Running extraction pipeline...")
        result = pipeline.run()
        
        # Display results
        print("\n" + "=" * 50)
        print("📊 EXTRACTION RESULTS")
        print("=" * 50)
        print(f"✅ Total jobs processed: {result.total_jobs}")
        print(f"⏱️ Processing time: {result.processing_time:.1f} seconds")
        print(f"📁 Output directory: {result.output_path}")
        
        if result.total_jobs > 0:
            avg_time = result.processing_time / result.total_jobs
            print(f"⚡ Average time per job: {avg_time:.1f} seconds")
        
        # Show configuration snapshot saved
        config.save_config_snapshot(result.output_path)
        logger.info("📸 Configuration snapshot saved with results")
        
        print("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logging.error(f"Demo failed: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
