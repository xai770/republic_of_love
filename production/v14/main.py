"""
TY_EXTRACT V14 - Main Entry Point
================================

Clean, intuitive job extraction pipeline with comprehensive reporting.

This module provides a simple interface to extract job data from files,
process them through LLM analysis, and generate formatted reports.

Example:
    python -m modules.ty_extract_versions.ty_extract_v14.main
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add the parent directory to Python path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

# Import V14 modules
from config import Config
from pipeline import TyExtractPipeline

# Set up logging for this module
logger = logging.getLogger('ty_extract_v14.main')

def setup_logging(config: Config) -> None:
    """Configure logging based on config settings"""
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, config.log_level.upper())
    root_logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Create file handler if logging to file is enabled
    if hasattr(config, 'log_to_file') and config.log_to_file:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        log_file = config.output_dir / f"ty_extract_v14_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

def main(config_path: Optional[str] = None) -> int:
    """
    Main entry point for TY_EXTRACT V14
    
    Args:
        config_path: Optional path to custom configuration file
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    
    try:
        # Load configuration from external files
        print("🚀 Starting TY_EXTRACT V14 Pipeline")
        
        if config_path:
            # Load config from custom path
            config_dir = Path(config_path).parent
            config = Config.load_from_external(config_dir)
            print(f"📋 Loaded external configuration from: {config_path}")
        else:
            # Load config from default location
            config = Config.load_from_external()
            print("📋 Loaded external configuration from default location")
        
        # Setup logging
        setup_logging(config)
        logger.info("🔧 Logging configured with external config")
        
        # Log configuration snapshot info
        if config.config_snapshot:
            logger.info(f"📸 Config hash: {config.config_snapshot.config_hash[:8]}")
            logger.info(f"📝 Templates loaded: {list(config.config_snapshot.templates.keys())}")
        
        # Initialize pipeline
        pipeline = TyExtractPipeline(config)
        logger.info("⚙️ Pipeline initialized with external config")
        
        # Print configuration summary
        print(f"\n📊 Configuration Summary:")
        print(f"   • Pipeline version: {config.pipeline_version}")
        print(f"   • Data directory: {config.data_dir}")
        print(f"   • Output directory: {config.output_dir}")  
        print(f"   • LLM model: {config.llm_model}")
        print(f"   • Excel reports: {'✅' if config.generate_excel else '❌'}")
        print(f"   • Markdown reports: {'✅' if config.generate_markdown else '❌'}")
        print(f"   • Log level: {config.log_level.upper()}")
        
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
        
        # Note: Reports will be added when pipeline integration is complete
        print(f"   • Reports: Will be generated once pipeline is fully integrated")
        
        # Print completion message
        if result.total_jobs > 0:
            print(f"\n✅ Pipeline completed successfully!")
            print(f"📂 Check {config.output_dir} for output files")
        else:
            print(f"\n⚠️ Pipeline completed but no jobs were extracted")
            print(f"💡 Check your data files and LLM connectivity")
        
        logger.info("🏁 Main execution completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⏹️ Pipeline interrupted by user")
        logger.info("Pipeline interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        return 1

def run_with_custom_config(
    data_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    llm_model: Optional[str] = None,
    **kwargs
) -> int:
    """
    Run pipeline with custom configuration parameters
    
    Args:
        data_dir: Custom data directory
        output_dir: Custom output directory  
        llm_model: Custom LLM model
        **kwargs: Additional configuration parameters
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    
    try:
        # Start with external config as base
        config = Config.load_from_external()
        
        # Override with provided parameters
        if data_dir:
            config.data_dir = Path(data_dir)
        if output_dir:
            config.output_dir = Path(output_dir)
        if llm_model:
            config.llm_model = llm_model
            
        # Apply any additional parameters
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Setup logging
        setup_logging(config)
        
        # Initialize and run pipeline
        pipeline = TyExtractPipeline(config)
        result = pipeline.run()
        
        return 0 if result.total_jobs > 0 else 1
        
    except Exception as e:
        logger.error(f"Custom config run failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    """Run pipeline when called as module"""
    
    # Parse simple command line arguments
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        
    # Run main function
    exit_code = main(config_path)
    sys.exit(exit_code)
