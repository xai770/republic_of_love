#!/usr/bin/env python3
"""
Content Extraction Specialist - Integration Examples
====================================================

For: Terminator@LLM-Factory
From: Arden@Republic-of-Love
Date: June 24, 2025

Production-ready integration examples for the LLM Factory pipeline.
"""

from content_extraction_specialist import ContentExtractionSpecialist, ExtractionResult
import json
import time
from typing import List, Dict, Any

class LLMFactoryIntegration:
    """Example integration for LLM Factory pipeline with Ollama support."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.1"):
        """
        Initialize the Content Extraction Specialist with Ollama configuration.
        
        Args:
            ollama_url: URL of the Ollama service
            model: Ollama model to use for processing
        """
        self.specialist = ContentExtractionSpecialist(ollama_url=ollama_url, model=model)
        self.stats = {
            'processed': 0,
            'total_time': 0,
            'total_llm_time': 0,
            'total_reduction': 0
        }
    
    def process_single_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single job description.
        
        Args:
            job_data: Dictionary containing job information
                     Expected keys: 'id', 'description', 'domain' (optional)
        
        Returns:
            Enhanced job data with extracted content and signals
        """
        start_time = time.time()
        
        # Extract core content
        result = self.specialist.extract_core_content(
            raw_job_description=job_data['description'],
            job_id=str(job_data.get('id', 'unknown'))
        )
        
        processing_time = time.time() - start_time
        
        # Update stats
        self.stats['processed'] += 1
        self.stats['total_time'] += processing_time
        self.stats['total_llm_time'] += result.llm_processing_time
        self.stats['total_reduction'] += result.reduction_percentage
        
        # Return enhanced job data
        enhanced_job = {
            **job_data,
            'extracted_content': result.extracted_content,
            'domain_signals': result.domain_signals,
            'content_reduction': result.reduction_percentage,
            'original_length': result.original_length,
            'extracted_length': result.extracted_length,
            'processing_time': processing_time,
            'llm_processing_time': result.llm_processing_time,
            'model_used': result.model_used,
            'processing_notes': result.processing_notes
        }
        
        return enhanced_job
    
    def process_batch(self, job_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of jobs efficiently.
        
        Args:
            job_batch: List of job dictionaries
        
        Returns:
            List of enhanced job dictionaries
        """
        enhanced_jobs = []
        
        for job in job_batch:
            try:
                enhanced_job = self.process_single_job(job)
                enhanced_jobs.append(enhanced_job)
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing job {job.get('id', 'unknown')}: {str(e)}")
                enhanced_jobs.append({
                    **job,
                    'processing_error': str(e),
                    'extraction_failed': True
                })
        
        return enhanced_jobs
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get processing performance statistics including LLM metrics."""
        if self.stats['processed'] == 0:
            return {
                'jobs_processed': 0, 
                'avg_time': 0, 
                'avg_llm_time': 0,
                'avg_reduction': 0, 
                'throughput': 0
            }
        
        return {
            'jobs_processed': self.stats['processed'],
            'avg_processing_time': self.stats['total_time'] / self.stats['processed'],
            'avg_llm_time': self.stats['total_llm_time'] / self.stats['processed'],
            'avg_reduction': self.stats['total_reduction'] / self.stats['processed'], 
            'throughput_jobs_per_sec': self.stats['processed'] / self.stats['total_time'] if self.stats['total_time'] > 0 else 0,
            'llm_throughput_jobs_per_sec': self.stats['processed'] / self.stats['total_llm_time'] if self.stats['total_llm_time'] > 0 else 0
        }

def example_pipeline_integration():
    """Example of how to integrate with an existing pipeline."""
    
    # Initialize the integration
    integrator = LLMFactoryIntegration()
    
    # Example job data (replace with your actual data source)
    sample_jobs = [
        {
            'id': '50571',
            'title': 'Senior Consultant - Deutsche Bank Management Consulting',
            'description': 'Long job description with boilerplate...',
            'expected_domain': 'management_consulting'
        },
        {
            'id': '52953', 
            'title': 'QA Engineer',
            'description': 'Quality assurance engineer position...',
            'expected_domain': 'quality_assurance'
        }
    ]
    
    # Process the batch
    enhanced_jobs = integrator.process_batch(sample_jobs)
    
    # Get performance metrics
    stats = integrator.get_performance_stats()
    
    print("🚀 LLM Factory Integration Example")
    print("=" * 50)
    print(f"Jobs processed: {stats['jobs_processed']}")
    print(f"Average processing time: {stats['avg_processing_time']:.3f}s")
    print(f"Average content reduction: {stats['avg_reduction']:.1f}%")
    print(f"Throughput: {stats['throughput_jobs_per_sec']:.1f} jobs/sec")
    print()
    
    # Show results for first job
    if enhanced_jobs:
        job = enhanced_jobs[0]
        print(f"📋 Sample Result (Job {job['id']}):")
        print(f"Content reduction: {job['content_reduction']:.1f}%")
        print(f"Domain signals: {job['domain_signals'][:5]}...")  # First 5 signals
        print(f"Extracted length: {job['extracted_length']} chars")

def example_streaming_integration():
    """Example for streaming/real-time processing."""
    
    integrator = LLMFactoryIntegration()
    
    def process_job_stream(job_generator):
        """Process jobs from a generator/stream."""
        for job in job_generator:
            try:
                enhanced_job = integrator.process_single_job(job)
                yield enhanced_job
            except Exception as e:
                yield {**job, 'processing_error': str(e)}
    
    # Example usage:
    # for enhanced_job in process_job_stream(your_job_stream):
    #     # Send to next pipeline stage
    #     pass

def example_error_handling():
    """Example of robust error handling in production."""
    
    integrator = LLMFactoryIntegration()
    
    def safe_process_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with comprehensive error handling."""
        try:
            # Validate input
            if 'description' not in job_data:
                raise ValueError("Missing 'description' field")
            
            if not isinstance(job_data['description'], str):
                raise ValueError("'description' must be a string")
            
            if len(job_data['description'].strip()) == 0:
                raise ValueError("Empty job description")
            
            # Process the job
            enhanced_job = integrator.process_single_job(job_data)
            enhanced_job['processing_status'] = 'success'
            
            return enhanced_job
            
        except ValueError as e:
            return {
                **job_data,
                'processing_status': 'validation_error',
                'error_message': str(e),
                'extracted_content': '',
                'domain_signals': []
            }
        except Exception as e:
            return {
                **job_data,
                'processing_status': 'processing_error', 
                'error_message': str(e),
                'extracted_content': '',
                'domain_signals': []
            }

def example_monitoring_integration():
    """Example of how to add monitoring/logging."""
    
    import logging
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('llm_factory_content_extraction')
    
    integrator = LLMFactoryIntegration()
    
    def monitored_process_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process job with monitoring."""
        job_id = job_data.get('id', 'unknown')
        
        logger.info(f"Starting content extraction for job {job_id}")
        
        start_time = time.time()
        enhanced_job = integrator.process_single_job(job_data)
        processing_time = time.time() - start_time
        
        # Log metrics
        logger.info(f"Job {job_id} processed: "
                   f"{enhanced_job['content_reduction']:.1f}% reduction, "
                   f"{processing_time:.3f}s, "
                   f"{len(enhanced_job['domain_signals'])} signals")
        
        # Alert on anomalies
        if processing_time > 1.0:
            logger.warning(f"Slow processing for job {job_id}: {processing_time:.3f}s")
        
        if enhanced_job['content_reduction'] < 10:
            logger.warning(f"Low reduction for job {job_id}: {enhanced_job['content_reduction']:.1f}%")
        
        return enhanced_job

if __name__ == "__main__":
    print("Content Extraction Specialist - Integration Examples")
    print("=" * 60)
    print()
    
    # Run the main example
    example_pipeline_integration()
    
    print()
    print("✅ Integration examples completed successfully!")
    print("📚 See function implementations above for detailed usage patterns.")
