#!/usr/bin/env python3
"""
🤖 PRODUCTION VALIDATION SUITE - Content Extraction Specialist
For: Terminator (LLM Factory Integration)
From: Arden@Republic-of-Love

This comprehensive test suite validates the Content Extraction Specialist
for production deployment in the LLM Factory pipeline.

Usage:
    python production_validation_suite.py

Expected Output:
    ✅ All tests passing
    📊 Performance benchmarks within SLA
    🎯 Ready for production deployment
"""

import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from content_extraction_specialist import ContentExtractionSpecialist, ExtractionResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionValidationSuite:
    """Comprehensive validation suite for production deployment."""
    
    def __init__(self):
        self.specialist = ContentExtractionSpecialist()
        self.test_results = []
        self.performance_metrics = {}
        
    def load_test_data(self) -> Dict[str, Any]:
        """Load test job data for validation."""
        test_jobs = {}
        
        # Job 50571 - Management Consulting (known good)
        job50571_path = Path("../inbox/job50571_reprocessed_llm.json")
        if job50571_path.exists():
            with open(job50571_path, 'r', encoding='utf-8') as f:
                job50571_data = json.load(f)
                test_jobs['50571'] = {
                    'description': job50571_data.get('description', ''),
                    'category': 'management_consulting',
                    'expected_signals': ['DBMC', 'transformation', 'strategic', 'consulting']
                }
        
        # Job 52953 - QA Engineer (known good)
        job52953_path = Path("../inbox/job52953_reprocessed_llm.json")
        if job52953_path.exists():
            with open(job52953_path, 'r', encoding='utf-8') as f:
                job52953_data = json.load(f)
                test_jobs['52953'] = {
                    'description': job52953_data.get('description', ''),
                    'category': 'qa_engineer',
                    'expected_signals': ['QA', 'testing', 'Selenium', 'automation']
                }
        
        return test_jobs
    
    def test_content_extraction(self, test_jobs: Dict[str, Any]) -> bool:
        """Test core content extraction functionality."""
        logger.info("🧪 Testing Content Extraction...")
        
        all_passed = True
        
        for job_id, job_data in test_jobs.items():
            try:
                # Extract content
                start_time = time.time()
                result = self.specialist.extract_core_content(
                    job_data['description'], 
                    job_id
                )
                end_time = time.time()
                
                # Validate extraction result
                processing_time = end_time - start_time
                reduction_percentage = result.reduction_percentage
                
                # Test assertions
                assert isinstance(result, ExtractionResult), "Result must be ExtractionResult object"
                assert len(result.extracted_content) > 0, "Extracted content cannot be empty"
                assert 0 <= reduction_percentage <= 100, "Reduction percentage must be 0-100%"
                assert processing_time < 2.0, f"Processing time {processing_time:.2f}s exceeds 2s SLA"
                
                # Validate domain signals
                for expected_signal in job_data['expected_signals']:
                    assert any(expected_signal.lower() in signal.lower() 
                             for signal in result.domain_signals), \
                           f"Expected signal '{expected_signal}' not found in domain signals"
                
                self.test_results.append({
                    'job_id': job_id,
                    'category': job_data['category'],
                    'original_length': len(job_data['description']),
                    'extracted_length': len(result.extracted_content),
                    'reduction_percentage': reduction_percentage,
                    'processing_time': processing_time,
                    'domain_signals_found': len(result.domain_signals),
                    'success': True
                })
                
                logger.info(f"✅ Job {job_id} ({job_data['category']}): "
                          f"{reduction_percentage:.1f}% reduction, "
                          f"{processing_time:.2f}s processing time")
                
            except Exception as e:
                logger.error(f"❌ Job {job_id} failed: {str(e)}")
                self.test_results.append({
                    'job_id': job_id,
                    'category': job_data['category'],
                    'error': str(e),
                    'success': False
                })
                all_passed = False
        
        return all_passed
    
    def test_batch_processing(self, test_jobs: Dict[str, Any]) -> bool:
        """Test batch processing performance."""
        logger.info("🔄 Testing Batch Processing...")
        
        try:
            # Create batch of job descriptions
            job_descriptions = [job_data['description'] for job_data in test_jobs.values()]
            job_ids = list(test_jobs.keys())
            
            # Process batch
            start_time = time.time()
            batch_results = []
            
            for i, description in enumerate(job_descriptions):
                result = self.specialist.extract_core_content(description, job_ids[i])
                batch_results.append(result)
            
            end_time = time.time()
            
            # Validate batch performance
            total_time = end_time - start_time
            avg_time_per_job = total_time / len(job_descriptions)
            
            assert avg_time_per_job < 2.0, f"Average processing time {avg_time_per_job:.2f}s exceeds 2s SLA"
            assert len(batch_results) == len(job_descriptions), "Batch processing must handle all jobs"
            
            self.performance_metrics['batch_processing'] = {
                'total_jobs': len(job_descriptions),
                'total_time': total_time,
                'avg_time_per_job': avg_time_per_job,
                'throughput_jobs_per_second': len(job_descriptions) / total_time
            }
            
            logger.info(f"✅ Batch processing: {avg_time_per_job:.2f}s avg per job, "
                       f"{len(job_descriptions)/total_time:.1f} jobs/sec throughput")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch processing failed: {str(e)}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and graceful degradation."""
        logger.info("🛡️ Testing Error Handling...")
        
        try:
            # Test empty input
            result = self.specialist.extract_core_content("", "test_empty")
            assert result.extracted_content == "", "Empty input should return empty output"
            
            # Test malformed input
            result = self.specialist.extract_core_content("   \n\t   ", "test_whitespace")
            assert len(result.extracted_content.strip()) == 0, "Whitespace-only input should return empty"
            
            # Test very long input (stress test)
            long_text = "This is a test job description. " * 10000  # ~340KB
            start_time = time.time()
            result = self.specialist.extract_core_content(long_text, "test_long")
            end_time = time.time()
            
            assert (end_time - start_time) < 5.0, "Large input processing should complete within 5s"
            assert len(result.extracted_content) > 0, "Large input should produce output"
            
            logger.info("✅ Error handling: All edge cases handled gracefully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error handling failed: {str(e)}")
            return False
    
    def test_domain_signal_preservation(self, test_jobs: Dict[str, Any]) -> bool:
        """Test domain signal preservation across job categories."""
        logger.info("🎯 Testing Domain Signal Preservation...")
        
        signal_preservation_results = {}
        
        for job_id, job_data in test_jobs.items():
            try:
                result = self.specialist.extract_core_content(job_data['description'], job_id)
                
                # Check if expected signals are preserved
                preserved_signals = []
                missing_signals = []
                
                for expected_signal in job_data['expected_signals']:
                    if any(expected_signal.lower() in signal.lower() 
                           for signal in result.domain_signals):
                        preserved_signals.append(expected_signal)
                    else:
                        # Check if signal exists in extracted content
                        if expected_signal.lower() in result.extracted_content.lower():
                            preserved_signals.append(expected_signal)
                        else:
                            missing_signals.append(expected_signal)
                
                preservation_rate = len(preserved_signals) / len(job_data['expected_signals'])
                
                signal_preservation_results[job_id] = {
                    'category': job_data['category'],
                    'total_expected': len(job_data['expected_signals']),
                    'preserved': len(preserved_signals),
                    'missing': missing_signals,
                    'preservation_rate': preservation_rate
                }
                
                assert preservation_rate >= 0.8, \
                       f"Signal preservation rate {preservation_rate:.1%} below 80% threshold"
                
                logger.info(f"✅ Job {job_id}: {preservation_rate:.1%} signal preservation rate")
                
            except Exception as e:
                logger.error(f"❌ Signal preservation test failed for job {job_id}: {str(e)}")
                return False
        
        # Overall preservation rate
        total_expected = sum(r['total_expected'] for r in signal_preservation_results.values())
        total_preserved = sum(r['preserved'] for r in signal_preservation_results.values())
        overall_rate = total_preserved / total_expected if total_expected > 0 else 0
        
        self.performance_metrics['signal_preservation'] = {
            'overall_rate': overall_rate,
            'by_category': signal_preservation_results
        }
        
        logger.info(f"✅ Overall signal preservation: {overall_rate:.1%}")
        return overall_rate >= 0.9  # 90% threshold for production
    
    def test_production_sla_compliance(self) -> bool:
        """Test compliance with production SLA requirements."""
        logger.info("📋 Testing Production SLA Compliance...")
        
        sla_results = {
            'processing_time_sla': True,  # <2s per job
            'success_rate_sla': True,     # >95% success rate
            'reduction_target': True,     # 40-70% reduction
            'signal_preservation_sla': True  # >90% signal preservation
        }
        
        # Check processing time SLA
        processing_times = [r.get('processing_time', 0) for r in self.test_results if r.get('success')]
        if processing_times:
            max_processing_time = max(processing_times)
            avg_processing_time = sum(processing_times) / len(processing_times)
            
            if max_processing_time >= 2.0:
                sla_results['processing_time_sla'] = False
                logger.warning(f"⚠️ Max processing time {max_processing_time:.2f}s exceeds 2s SLA")
        
        # Check success rate SLA
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get('success'))
        success_rate = successful_tests / total_tests if total_tests > 0 else 0
        
        if success_rate < 0.95:
            sla_results['success_rate_sla'] = False
            logger.warning(f"⚠️ Success rate {success_rate:.1%} below 95% SLA")
        
        # Check reduction targets
        reductions = [r.get('reduction_percentage', 0) for r in self.test_results if r.get('success')]
        if reductions:
            avg_reduction = sum(reductions) / len(reductions)
            if not (40 <= avg_reduction <= 70):
                logger.warning(f"⚠️ Average reduction {avg_reduction:.1f}% outside 40-70% target range")
        
        # Check signal preservation SLA
        signal_rate = self.performance_metrics.get('signal_preservation', {}).get('overall_rate', 0)
        if signal_rate < 0.9:
            sla_results['signal_preservation_sla'] = False
            logger.warning(f"⚠️ Signal preservation {signal_rate:.1%} below 90% SLA")
        
        all_sla_met = all(sla_results.values())
        
        if all_sla_met:
            logger.info("✅ All production SLAs met")
        else:
            logger.error("❌ Some production SLAs not met")
        
        self.performance_metrics['sla_compliance'] = sla_results
        return all_sla_met
    
    def generate_production_report(self) -> Dict[str, Any]:
        """Generate comprehensive production readiness report."""
        logger.info("📊 Generating Production Readiness Report...")
        
        # Calculate overall statistics
        successful_jobs = [r for r in self.test_results if r.get('success')]
        
        if successful_jobs:
            avg_reduction = sum(r['reduction_percentage'] for r in successful_jobs) / len(successful_jobs)
            avg_processing_time = sum(r['processing_time'] for r in successful_jobs) / len(successful_jobs)
            max_processing_time = max(r['processing_time'] for r in successful_jobs)
        else:
            avg_reduction = 0
            avg_processing_time = 0
            max_processing_time = 0
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_summary': {
                'total_tests': len(self.test_results),
                'successful_tests': len(successful_jobs),
                'success_rate': len(successful_jobs) / len(self.test_results) if self.test_results else 0
            },
            'performance_metrics': {
                'average_content_reduction': avg_reduction,
                'average_processing_time': avg_processing_time,
                'max_processing_time': max_processing_time,
                'signal_preservation_rate': self.performance_metrics.get('signal_preservation', {}).get('overall_rate', 0)
            },
            'sla_compliance': self.performance_metrics.get('sla_compliance', {}),
            'detailed_results': self.test_results,
            'production_readiness': {
                'ready_for_deployment': all(self.performance_metrics.get('sla_compliance', {}).values()),
                'confidence_level': 'HIGH' if len(successful_jobs) == len(self.test_results) else 'MEDIUM'
            }
        }
        
        return report
    
    def run_full_validation(self) -> bool:
        """Run complete validation suite."""
        logger.info("🚀 Starting Production Validation Suite...")
        logger.info("=" * 50)
        
        # Load test data
        test_jobs = self.load_test_data()
        if not test_jobs:
            logger.error("❌ No test data found. Please ensure job data files are available.")
            return False
        
        logger.info(f"📋 Loaded {len(test_jobs)} test jobs")
        
        # Run all validation tests
        tests_passed = []
        
        tests_passed.append(self.test_content_extraction(test_jobs))
        tests_passed.append(self.test_batch_processing(test_jobs))
        tests_passed.append(self.test_error_handling())
        tests_passed.append(self.test_domain_signal_preservation(test_jobs))
        tests_passed.append(self.test_production_sla_compliance())
        
        # Generate final report
        report = self.generate_production_report()
        
        # Display results
        logger.info("=" * 50)
        logger.info("📊 PRODUCTION VALIDATION RESULTS")
        logger.info("=" * 50)
        
        if all(tests_passed):
            logger.info("🎉 ALL TESTS PASSED - READY FOR PRODUCTION!")
            logger.info(f"✅ Success Rate: {report['test_summary']['success_rate']:.1%}")
            logger.info(f"✅ Avg Content Reduction: {report['performance_metrics']['average_content_reduction']:.1f}%")
            logger.info(f"✅ Avg Processing Time: {report['performance_metrics']['average_processing_time']:.2f}s")
            logger.info(f"✅ Signal Preservation: {report['performance_metrics']['signal_preservation_rate']:.1%}")
            logger.info("🚀 Deploy with confidence!")
        else:
            logger.error("❌ SOME TESTS FAILED - REVIEW BEFORE PRODUCTION")
            failed_tests = sum(1 for passed in tests_passed if not passed)
            logger.error(f"❌ {failed_tests} out of {len(tests_passed)} test suites failed")
        
        # Save detailed report
        with open('production_validation_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("📄 Detailed report saved to: production_validation_report.json")
        
        return all(tests_passed)

def main():
    """Main entry point for production validation."""
    print("🤖 Content Extraction Specialist - Production Validation Suite")
    print("For: Terminator (LLM Factory Integration)")
    print("From: Arden@Republic-of-Love")
    print()
    
    # Change to the directory containing the test files
    script_dir = Path(__file__).parent
    original_dir = Path.cwd()
    
    try:
        # Change to script directory to find test data
        import os
        os.chdir(script_dir)
        
        # Run validation suite
        validator = ProductionValidationSuite()
        success = validator.run_full_validation()
        
        # Return appropriate exit code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"❌ Validation suite failed with error: {str(e)}")
        sys.exit(1)
        
    finally:
        # Restore original directory
        os.chdir(original_dir)

if __name__ == "__main__":
    main()
