#!/usr/bin/env python3
"""
Simple Framework Test
====================

A minimal test to verify framework components work.
"""

import sys
from pathlib import Path

# Add framework to path
sys.path.insert(0, '/home/xai/Documents/republic_of_love')

def test_framework():
    """Test individual framework components"""
    
    print("🧪 Testing LLM Optimization Framework Components")
    print("=" * 50)
    
    # Test 1: Import core modules
    print("\n1️⃣ Testing imports...")
    try:
        from llm_optimization_framework.utils.dialogue_parser import DialogueEntry
        from llm_optimization_framework.utils.quality_assessor import QualityAssessor
        from llm_optimization_framework.core.metrics import PerformanceMetrics
        from llm_optimization_framework.configs.settings import TemplateConfigs
        print("   ✅ All imports successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return
    
    # Test 2: Create mock data
    print("\n2️⃣ Creating mock dialogue entry...")
    try:
        mock_entry = DialogueEntry(
            model_name="test_model",
            test_id="concise_extraction",
            test_type="concise_extraction",
            response_text="**Your Tasks:** Test response with proper structure",
            prompt_text="Test prompt",
            processing_time=1.0,
            response_length=50,
            success=True,
            metadata={"test": True}
        )
        print(f"   ✅ Created entry for {mock_entry.model_name}")
    except Exception as e:
        print(f"   ❌ Mock data creation failed: {e}")
        return
    
    # Test 3: Quality assessment
    print("\n3️⃣ Testing quality assessment...")
    try:
        quality_assessor = QualityAssessor()
        quality_score = quality_assessor.assess_quality(
            mock_entry.response_text, 
            mock_entry.test_id
        )
        print(f"   ✅ Quality score: {quality_score.overall_score:.3f}")
    except Exception as e:
        print(f"   ❌ Quality assessment failed: {e}")
        return
    
    # Test 4: Performance metrics
    print("\n4️⃣ Testing performance metrics...")
    try:
        metrics_calc = PerformanceMetrics()
        model_metrics = metrics_calc.calculate_model_metrics([mock_entry], "test_model")
        print(f"   ✅ Model metrics calculated: {model_metrics.overall_score:.3f}")
        print(f"   ✅ Performance tier: {model_metrics.performance_tier}")
    except Exception as e:
        print(f"   ❌ Performance metrics failed: {e}")
        return
    
    # Test 5: Configuration
    print("\n5️⃣ Testing configuration...")
    try:
        config = TemplateConfigs.job_matching_specialist()
        print(f"   ✅ Configuration loaded: {config.project_name}")
        print(f"   ✅ Quality weight: {config.category_weights.quality}")
    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
        return
    
    print("\n🎉 All tests passed! Framework is working correctly.")
    print("\n📋 Summary:")
    print(f"   • DialogueEntry: ✅ Working")
    print(f"   • QualityAssessor: ✅ Working") 
    print(f"   • PerformanceMetrics: ✅ Working")
    print(f"   • Configuration: ✅ Working")
    print(f"   • Mock Quality Score: {quality_score.overall_score:.3f}")
    print(f"   • Mock Model Score: {model_metrics.overall_score:.3f}")

if __name__ == "__main__":
    test_framework()
