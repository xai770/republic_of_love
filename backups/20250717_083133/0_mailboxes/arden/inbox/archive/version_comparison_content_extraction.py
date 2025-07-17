#!/usr/bin/env python3
"""
Content Extraction Specialist - VERSION COMPARISON
==================================================

Comprehensive testing of all Content Extraction Specialist versions
Tests versions 3.1, 3.2, and 3.3 against golden test cases
Generates detailed comparison report

Usage: python version_comparison_content_extraction.py
Output: version_comparison_results.json + console report

Date: June 27, 2025
Purpose: Accurate version performance documentation
"""

import json
import sys
import time
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

class VersionTester:
    """Test multiple versions of Content Extraction Specialist"""
    
    def __init__(self):
        self.golden_test_path = "/home/xai/Documents/llm_factory/0_mailboxes/terminator@llm_factory/inbox/archive/golden_test_cases_content_extraction_v2.json"
        self.results = {
            "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version_comparison": {},
            "summary": {}
        }
    
    def load_golden_tests(self) -> Dict[str, Any]:
        """Load golden test cases"""
        try:
            with open(self.golden_test_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading golden tests: {e}")
            sys.exit(1)
    
    def load_specialist_module(self, version_path: str, module_name: str):
        """Dynamically load a specialist module"""
        try:
            spec = importlib.util.spec_from_file_location(module_name, version_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            print(f"Error loading {version_path}: {e}")
            return None
    
    def calculate_accuracy(self, extracted_skills: List[str], expected_skills: List[str]) -> Tuple[float, List[str], List[str]]:
        """Calculate accuracy with fuzzy matching"""
        extracted_lower = [skill.lower().strip() for skill in extracted_skills]
        expected_lower = [skill.lower().strip() for skill in expected_skills]
        
        matched_skills = []
        missing_skills = []
        extra_skills = list(extracted_skills)
        
        for expected in expected_skills:
            expected_lower_item = expected.lower().strip()
            best_match = None
            
            # Exact match first
            for extracted in extracted_skills:
                if extracted.lower().strip() == expected_lower_item:
                    best_match = extracted
                    break
            
            # Fuzzy match for similar skills
            if not best_match:
                for extracted in extracted_skills:
                    extracted_lower_item = extracted.lower().strip()
                    if (expected_lower_item in extracted_lower_item or 
                        extracted_lower_item in expected_lower_item or
                        self._are_similar_skills(expected_lower_item, extracted_lower_item)):
                        best_match = extracted
                        break
            
            if best_match:
                matched_skills.append(expected)
                if best_match in extra_skills:
                    extra_skills.remove(best_match)
            else:
                missing_skills.append(expected)
        
        accuracy = len(matched_skills) / len(expected_skills) * 100 if expected_skills else 0
        return accuracy, missing_skills, extra_skills
    
    def _are_similar_skills(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are similar"""
        skill1_clean = skill1.replace(' ', '').replace('-', '').replace('_', '')
        skill2_clean = skill2.replace(' ', '').replace('-', '').replace('_', '')
        return skill1_clean == skill2_clean
    
    def check_format_compliance(self, extracted_skills: List[str]) -> Tuple[bool, List[str]]:
        """Check format compliance"""
        format_issues = []
        
        for skill in extracted_skills:
            if any(skill.strip().startswith(f"{i}.") for i in range(1, 20)):
                format_issues.append(f"Numbered list: '{skill}'")
            if len(skill.split()) > 5:
                format_issues.append(f"Verbose: '{skill}'")
            if '(' in skill and ')' in skill:
                format_issues.append(f"Parenthetical: '{skill}'")
        
        return len(format_issues) == 0, format_issues
    
    def test_version(self, version_name: str, version_path: str, specialist_class_name: str) -> Dict[str, Any]:
        """Test a single version"""
        print(f"\nTesting {version_name}...")
        print(f"Path: {version_path}")
        
        # Load the specialist module
        module = self.load_specialist_module(version_path, f"specialist_{version_name}")
        if not module:
            return {"error": f"Failed to load {version_path}"}
        
        # Get the specialist class
        try:
            specialist_class = getattr(module, specialist_class_name)
            specialist = specialist_class()
        except Exception as e:
            return {"error": f"Failed to instantiate {specialist_class_name}: {e}"}
        
        # Load golden tests
        test_data = self.load_golden_tests()
        test_cases = test_data.get('test_cases', [])
        
        version_results = {
            "version": version_name,
            "path": version_path,
            "specialist_class": specialist_class_name,
            "test_results": [],
            "overall_accuracy": 0.0,
            "format_compliance": 0.0,
            "processing_time": 0.0
        }
        
        total_accuracy = 0
        total_format_compliant = 0
        total_processing_time = 0
        
        for i, test_case in enumerate(test_cases):
            print(f"  Test {i+1}/5: {test_case['name']}")
            
            start_time = time.time()
            try:
                # Extract skills
                if hasattr(specialist, 'extract_skills'):
                    result = specialist.extract_skills(test_case['job_description'])
                    if hasattr(result, 'all_skills'):
                        extracted_skills = result.all_skills
                    else:
                        extracted_skills = result
                else:
                    # Try alternative method names
                    extracted_skills = []
                
                processing_time = time.time() - start_time
                total_processing_time += processing_time
                
                # Calculate accuracy
                accuracy, missing, extra = self.calculate_accuracy(
                    extracted_skills, test_case['expected_skills']
                )
                
                # Check format compliance
                format_compliant, format_issues = self.check_format_compliance(extracted_skills)
                
                test_result = {
                    "test_id": test_case['id'],
                    "test_name": test_case['name'],
                    "accuracy": round(accuracy, 1),
                    "format_compliant": format_compliant,
                    "format_issues": format_issues,
                    "processing_time": round(processing_time, 2),
                    "extracted_count": len(extracted_skills),
                    "expected_count": len(test_case['expected_skills']),
                    "missing_count": len(missing),
                    "extra_count": len(extra)
                }
                
                version_results["test_results"].append(test_result)
                total_accuracy += accuracy
                if format_compliant:
                    total_format_compliant += 1
                
                print(f"    Accuracy: {accuracy:.1f}% | Format: {'✓' if format_compliant else '✗'}")
                
            except Exception as e:
                print(f"    Error: {e}")
                version_results["test_results"].append({
                    "test_id": test_case['id'],
                    "test_name": test_case['name'],
                    "error": str(e),
                    "accuracy": 0.0,
                    "format_compliant": False
                })
        
        # Calculate overall metrics
        version_results["overall_accuracy"] = round(total_accuracy / len(test_cases), 1) if test_cases else 0
        version_results["format_compliance"] = round((total_format_compliant / len(test_cases)) * 100, 1) if test_cases else 0
        version_results["avg_processing_time"] = round(total_processing_time / len(test_cases), 2) if test_cases else 0
        
        print(f"  Overall: {version_results['overall_accuracy']}% accuracy, {version_results['format_compliance']}% format compliance")
        
        return version_results
    
    def run_comparison(self):
        """Run comprehensive version comparison"""
        print("Content Extraction Specialist - VERSION COMPARISON")
        print("=" * 60)
        
        versions_to_test = [
            {
                "name": "v3.1_ENHANCED",
                "path": "/home/xai/Documents/llm_factory/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_specialist_v3_1_ENHANCED.py",
                "class": "ContentExtractionSpecialistV31"
            },
            {
                "name": "v3.2_OPTIMIZED", 
                "path": "/home/xai/Documents/llm_factory/0_mailboxes/sandy@consciousness/inbox/archive/content_extraction_specialist_v3_2_OPTIMIZED.py",
                "class": "ContentExtractionSpecialistV32"
            },
            {
                "name": "v3.3_PRODUCTION",
                "path": "/home/xai/Documents/llm_factory/0_mailboxes/sandy@consciousness/inbox/content_extraction_specialist_v3_3_PRODUCTION.py",
                "class": "ContentExtractionSpecialistV33"
            }
        ]
        
        for version_info in versions_to_test:
            if Path(version_info["path"]).exists():
                result = self.test_version(
                    version_info["name"],
                    version_info["path"], 
                    version_info["class"]
                )
                self.results["version_comparison"][version_info["name"]] = result
            else:
                print(f"\nSkipping {version_info['name']} - file not found: {version_info['path']}")
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        with open("version_comparison_results.json", "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\nDetailed results saved to: version_comparison_results.json")
    
    def generate_summary(self):
        """Generate comparison summary"""
        versions = self.results["version_comparison"]
        
        print(f"\n{'='*60}")
        print("VERSION COMPARISON SUMMARY")
        print(f"{'='*60}")
        
        print(f"{'Version':<15} {'Accuracy':<10} {'Format':<8} {'Status':<15}")
        print("-" * 50)
        
        best_accuracy = 0
        best_version = None
        
        for version_name, result in versions.items():
            if "error" not in result:
                accuracy = result["overall_accuracy"]
                format_comp = result["format_compliance"]
                status = "PASS" if accuracy >= 90 and format_comp >= 95 else "FAIL"
                
                print(f"{version_name:<15} {accuracy:<10}% {format_comp:<8}% {status:<15}")
                
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_version = version_name
        
        self.results["summary"] = {
            "best_performing_version": best_version,
            "best_accuracy": best_accuracy,
            "total_versions_tested": len([v for v in versions.values() if "error" not in v]),
            "production_ready_versions": len([v for v in versions.values() if "error" not in v and v["overall_accuracy"] >= 90 and v["format_compliance"] >= 95])
        }
        
        print(f"\nBest Performing Version: {best_version} ({best_accuracy}%)")
        print(f"Production Ready Versions: {self.results['summary']['production_ready_versions']}")

def main():
    tester = VersionTester()
    tester.run_comparison()

if __name__ == "__main__":
    main()
