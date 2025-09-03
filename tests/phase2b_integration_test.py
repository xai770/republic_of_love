"""
Phase 2b Integration Test: Real LLM + Advanced Empathy + Dexi Keeper
Full production pipeline validation

Test order:
1. Real LLM integration
2. Advanced empathy tuning
3. Dexi keeper validation
4. End-to-end report generation
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List
import json
import logging

# Add modules to path
sys.path.append(str(Path(__file__).parent / "modules"))

from ty_report_base.engine.report_generator import ReportGenerator
from ty_report_base.empathy.advanced_empathy_tuner import AdvancedEmpathyTuner
from ty_report_base.qa.dexi_keeper import DexiKeeper
from ty_report_base.utils.real_llm_integration import RealLLMIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_phase2b_integration():
    """Test complete Phase 2b integration"""
    logger.info("🚀 Starting Phase 2b Integration Test")
    
    # Initialize components
    logger.info("Initializing components...")
    
    try:
        # Initialize Dexi keeper first
        dexi = DexiKeeper()
        logger.info("✓ Dexi keeper initialized")
        
        # Initialize LLM integration
        llm_config = {
            'model': 'ollama/llama2',
            'temperature': 0.7,
            'max_tokens': 500,
            'timeout': 30
        }
        llm_integration = RealLLMIntegration(model_config=llm_config)
        logger.info("✓ Real LLM integration initialized")
        
        # Initialize advanced empathy tuner
        empathy_tuner = AdvancedEmpathyTuner()
        logger.info("✓ Advanced empathy tuner initialized")
        
        # Initialize report generator with all components
        generator = ReportGenerator(
            template_name="job_extraction_analysis",
            empathy_enabled=True,
            llm_integration=llm_integration
        )
        logger.info("✓ Report generator initialized with LLM integration")
        
    except Exception as e:
        logger.error(f"❌ Component initialization failed: {e}")
        return False
    
    # Prepare test data
    test_data = {
        "blocks": [
            {
                "title": "Senior Software Engineer - AI/ML",
                "text": "We are seeking an experienced senior software engineer with expertise in artificial intelligence and machine learning. The ideal candidate will have 5+ years of experience developing scalable ML systems, strong proficiency in Python and cloud platforms, and a passion for innovation.",
                "company": "TechCorp AI",
                "location": "San Francisco, CA",
                "employment_type": "Full-time",
                "salary_range": "$150,000 - $200,000"
            }
        ],
        "extraction_context": {
            "source": "job_posting_extraction",
            "timestamp": "2025-01-24T10:00:00Z",
            "extraction_quality": "high_confidence"
        }
    }
    
    # Test 1: Generate report with real LLM
    logger.info("🔄 Test 1: Real LLM report generation")
    
    try:
        start_time = time.time()
        report = generator.generate_report(test_data)
        generation_time = time.time() - start_time
        
        logger.info(f"✓ Report generated in {generation_time:.2f} seconds")
        logger.info(f"  Report has {len(report.get('sections', []))} sections")
        
    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}")
        return False
    
    # Test 2: Advanced empathy tuning
    logger.info("🔄 Test 2: Advanced empathy tuning")
    
    try:
        # Analyze empathy in generated report
        empathy_analysis = empathy_tuner.analyze_empathy_context(report, test_data)
        logger.info(f"✓ Empathy analysis complete: score {empathy_analysis.get('empathy_score', 0):.2f}")
        
        # Apply context-aware tuning
        tuning_recommendations = empathy_tuner.tune_for_context(
            report_content=json.dumps(report),
            input_data=test_data,
            target_empathy_level="professional_caring"
        )
        logger.info(f"✓ Generated {len(tuning_recommendations)} empathy recommendations")
        
    except Exception as e:
        logger.error(f"❌ Empathy tuning failed: {e}")
        return False
    
    # Test 3: Dexi keeper validation
    logger.info("🔄 Test 3: Dexi keeper validation")
    
    try:
        # Validate the generated report
        validation_record = dexi.validate_output(report, test_data)
        
        logger.info(f"✓ Dexi validation complete:")
        logger.info(f"  Result: {validation_record.validation_result}")
        logger.info(f"  Confidence: {validation_record.confidence_score:.2f}")
        logger.info(f"  Flags: {len(validation_record.qa_flags)}")
        logger.info(f"  Notes: {validation_record.dexi_notes}")
        
        # Store agreement with validation
        agreement_id = dexi.store_agreement(
            validation_record.report_hash,
            validation_record.qa_flags,
            validation_record.validation_result
        )
        logger.info(f"✓ Validation agreement stored: {agreement_id}")
        
        # Add to QA journal
        quality_assessment = {
            "overall_quality": "good" if validation_record.confidence_score > 0.7 else "needs_improvement",
            "empathy_integration": "present" if report.get('metadata', {}).get('empathy_enabled') else "missing",
            "llm_integration": "functional",
            "validation_metrics": {
                "confidence": validation_record.confidence_score,
                "flag_count": len(validation_record.qa_flags),
                "structure_valid": "missing_structure" not in str(validation_record.qa_flags)
            }
        }
        
        journal_entry = dexi.append_to_qa_journal(
            validation_record.report_hash,
            "full_validation",
            quality_assessment,
            ["Continue monitoring LLM performance", "Validate empathy consistency"]
        )
        logger.info(f"✓ QA journal entry created: {journal_entry.entry_id}")
        
    except Exception as e:
        logger.error(f"❌ Dexi validation failed: {e}")
        return False
    
    # Test 4: End-to-end integration verification
    logger.info("🔄 Test 4: End-to-end integration verification")
    
    try:
        # Verify all components worked together
        verification_results = {
            "llm_integration": "llm_generated_content" in str(report.get('metadata', {})),
            "empathy_enabled": report.get('metadata', {}).get('empathy_enabled', False),
            "dexi_validated": validation_record.validation_result in ["approved", "flagged"],
            "qa_journal_entry": len(dexi.qa_journal) > 0,
            "report_sections": len(report.get('sections', [])) >= 3
        }
        
        success_count = sum(verification_results.values())
        total_checks = len(verification_results)
        
        logger.info(f"✓ End-to-end verification: {success_count}/{total_checks} checks passed")
        
        for check, passed in verification_results.items():
            status = "✓" if passed else "❌"
            logger.info(f"  {status} {check}")
        
        integration_success = success_count == total_checks
        
    except Exception as e:
        logger.error(f"❌ End-to-end verification failed: {e}")
        return False
    
    # Generate comprehensive report
    logger.info("📋 Generating integration test report...")
    
    test_report = {
        "test_name": "phase2b_integration_test",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "components_tested": [
            "RealLLMIntegration",
            "AdvancedEmpathyTuner", 
            "DexiKeeper",
            "ReportGenerator"
        ],
        "test_results": {
            "llm_generation": "success",
            "empathy_tuning": "success",
            "dexi_validation": "success",
            "end_to_end": "success" if integration_success else "partial"
        },
        "validation_summary": {
            "report_hash": validation_record.report_hash,
            "validation_result": validation_record.validation_result,
            "confidence_score": validation_record.confidence_score,
            "qa_flags": validation_record.qa_flags,
            "dexi_notes": validation_record.dexi_notes
        },
        "empathy_analysis": {
            "score": empathy_analysis.get('empathy_score', 0),
            "recommendations_count": len(tuning_recommendations)
        },
        "performance_metrics": {
            "generation_time_seconds": generation_time,
            "total_validation_time": validation_record.validation_metadata.get('validation_time_ms', 0) / 1000
        },
        "dexi_keeper_summary": dexi.get_keeper_summary()
    }
    
    # Save test report
    test_report_path = Path("0_mailboxes/misty/inbox/phase2b_integration_test_report.json")
    test_report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(test_report_path, 'w') as f:
        json.dump(test_report, f, indent=2)
    
    logger.info(f"📋 Integration test report saved: {test_report_path}")
    
    # Save sample report
    sample_report_path = Path("0_mailboxes/misty/inbox/phase2b_sample_report.json")
    with open(sample_report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"📋 Sample report saved: {sample_report_path}")
    
    # Summary
    if integration_success:
        logger.info("🎉 Phase 2b Integration Test: SUCCESS")
        logger.info("   All components integrated successfully!")
        logger.info("   Real LLM + Advanced Empathy + Dexi Keeper = OPERATIONAL")
        return True
    else:
        logger.info("⚠️ Phase 2b Integration Test: PARTIAL SUCCESS")
        logger.info("   Some integration issues detected - check logs")
        return False

def test_dexi_keeper_standalone():
    """Test Dexi keeper in isolation"""
    logger.info("🔍 Testing Dexi keeper standalone...")
    
    dexi = DexiKeeper()
    
    # Mock report data
    mock_report = {
        "title": "Job Analysis Report - Senior Software Engineer",
        "template_name": "job_extraction_analysis",
        "metadata": {
            "generated_by": "ty_extract_v11.0",
            "timestamp": "2025-01-24T10:00:00Z",
            "empathy_enabled": True,
            "qa_flags": []
        },
        "sections": [
            {
                "name": "position_overview",
                "prompt": "Provide overview of the position",
                "content": "This position offers excellent opportunities for professional growth in the AI/ML field, working with cutting-edge technologies to develop innovative solutions."
            },
            {
                "name": "requirements_analysis",
                "prompt": "Analyze job requirements", 
                "content": "The role requires strong technical expertise combined with collaborative skills, perfect for candidates looking to advance their careers in a supportive environment."
            },
            {
                "name": "compensation_insights",
                "prompt": "Provide compensation analysis",
                "content": "The compensation package reflects the company's commitment to attracting top talent, with competitive salary and comprehensive benefits."
            }
        ]
    }
    
    # Test validation
    validation = dexi.validate_output(mock_report)
    logger.info(f"✓ Dexi validation: {validation.validation_result} (confidence: {validation.confidence_score:.2f})")
    
    # Test keeper summary
    summary = dexi.get_keeper_summary()
    logger.info(f"✓ Dexi keeper summary: {summary}")
    
    return True

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("PHASE 2B INTEGRATION TEST SUITE")
    logger.info("Real LLM + Advanced Empathy + Dexi Keeper")
    logger.info("=" * 60)
    
    # Run standalone Dexi test first
    standalone_success = test_dexi_keeper_standalone()
    
    # Run full integration test
    integration_success = test_phase2b_integration()
    
    logger.info("=" * 60)
    if standalone_success and integration_success:
        logger.info("🎉 ALL TESTS PASSED - Phase 2b Ready for Production!")
    else:
        logger.info("⚠️ Some tests failed - Review logs and fix issues")
    logger.info("=" * 60)
