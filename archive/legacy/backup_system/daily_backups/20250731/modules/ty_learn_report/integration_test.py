#!/usr/bin/env python3
"""
TY_LEARN_REPORT - Integration Test Script
Tests the QA framework against real V10.0 and V7.1 outputs
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Add the QA module to path
qa_path = Path(__file__).parent / "versions" / "v1.0_basic_qa"
sys.path.insert(0, str(qa_path))

from status_reporter import TyLearnQA  # type: ignore

def find_output_files(workspace_root: str) -> Dict[str, List[str]]:
    """Find V7.1 and V10.0 output files in the workspace"""
    
    workspace = Path(workspace_root)
    results: Dict[str, List[str]] = {"v7.1": [], "v10.0": []}
    
    # Look for V7.1 outputs
    v71_paths = [
        workspace / "modules" / "ty_extract_versions" / "ty_extract_v7.1_template_based" / "output",
        workspace / "modules" / "ty_extract_versions" / "ty_extract_v7.1" / "output"
    ]
    
    for path in v71_paths:
        if path.exists():
            for file in path.glob("*.md"):
                if file.stat().st_size > 100:  # Skip tiny files
                    results["v7.1"].append(str(file))
    
    # Look for V10.0 outputs
    v10_paths = [
        workspace / "modules" / "ty_extract_versions" / "ty_extract_v10.0_qwen3_optimized" / "output"
    ]
    
    for path in v10_paths:
        if path.exists():
            for file in path.glob("*.md"):
                if file.stat().st_size > 100:  # Skip tiny files
                    results["v10.0"].append(str(file))
    
    return results

def test_qa_system():
    """Test the QA system with available outputs"""
    
    print("🔍 TY_LEARN QA INTEGRATION TEST")
    print("=" * 50)
    
    qa = TyLearnQA()
    
    # Find workspace root (go up from current location)
    current = Path(__file__).parent
    workspace_root = None
    
    for parent in current.parents:
        if (parent / "modules").exists() and (parent / "0_mailboxes").exists():
            workspace_root = parent
            break
    
    if not workspace_root:
        print("❌ Could not find workspace root")
        return
    
    print(f"📁 Workspace: {workspace_root}")
    
    # Find output files
    files = find_output_files(str(workspace_root))
    
    print(f"\n📊 Found Files:")
    print(f"  V7.1 outputs: {len(files['v7.1'])}")
    print(f"  V10.0 outputs: {len(files['v10.0'])}")
    
    if not files["v7.1"]:
        print("\n⚠️  No V7.1 outputs found - creating sample baseline")
        baseline_content = create_sample_baseline()
    else:
        print(f"\n📖 Reading V7.1 baseline: {files['v7.1'][0].name}")
        with open(files['v7.1'][0], 'r', encoding='utf-8') as f:
            baseline_content = f.read()
    
    if not files["v10.0"]:
        print("❌ No V10.0 outputs found - cannot run comparison")
        return
    
    # Test with first V10.0 output
    candidate_file = files["v10.0"][0]
    print(f"📖 Reading V10.0 candidate: {candidate_file.name}")
    
    with open(candidate_file, 'r', encoding='utf-8') as f:
        candidate_content = f.read()
    
    print(f"\n🔬 Running QA comparison...")
    
    # Run comparison
    report = qa.compare_outputs(baseline_content, candidate_content, "text")
    
    print("\n" + "="*60)
    print(report)
    
    # Also do a quick check
    print("\n" + "="*60)
    print("🚀 QUICK CHECK RESULTS")
    print("="*60)
    
    quick_result = qa.quick_check(candidate_content)
    for key, value in quick_result.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    # Test with multiple files if available
    if len(files["v10.0"]) > 1:
        print(f"\n📊 Testing additional V10.0 files ({len(files['v10.0'])-1} more)...")
        
        scores = []
        for i, file in enumerate(files["v10.0"][1:], 2):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            quick = qa.quick_check(content)
            scores.append(quick["overall_score"])
            print(f"  File {i}: {file.name} - Score: {quick['overall_score']:.1f}")
        
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"\n📈 Average Quality Score: {avg_score:.1f}/100")

def create_sample_baseline() -> str:
    """Create a sample baseline if no V7.1 outputs are found"""
    return """# Senior Backend Developer - Requirements & Responsibilities

## Your Tasks
* **System Architecture**: Design and implement scalable backend systems using Python/Django
* **API Development**: Build RESTful APIs and microservices for web applications
* **Database Management**: Optimize database queries and manage data migrations
* **Code Review**: Conduct thorough code reviews and mentor junior developers
* **Performance Optimization**: Identify and resolve performance bottlenecks

## Your Profile  
* **Education & Experience**: Bachelor's degree in Computer Science with 5+ years backend development
* **Technical Skills**: Expert-level Python, Django, PostgreSQL, Redis, Docker
* **Soft Skills**: Strong communication, team leadership, and problem-solving abilities
* **Language Skills**: Fluent English required, German advantageous
"""

if __name__ == "__main__":
    test_qa_system()
