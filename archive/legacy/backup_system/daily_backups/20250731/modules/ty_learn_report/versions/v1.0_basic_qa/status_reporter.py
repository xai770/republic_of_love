"""
TY_LEARN_REPORT - Status Reporter
Generates formatted reports from QA comparison results
"""

from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from compare_reports import QAResult, QAStatus, IssueType, IssueSeverity, ReportComparator

class StatusReporter:
    """Generates human-readable and JSON reports from QA results"""
    
    def __init__(self):
        pass
    
    def generate_report(self, result: QAResult, format: str = "text") -> str:
        """Generate a formatted report from QA result
        
        Args:
            result: QA comparison result
            format: Output format ('text', 'json', 'markdown')
        """
        if format == "json":
            return self._generate_json_report(result)
        elif format == "markdown":
            return self._generate_markdown_report(result)
        else:
            return self._generate_text_report(result)
    
    def _generate_text_report(self, result: QAResult) -> str:
        """Generate human-readable text report"""
        
        lines = []
        
        # Header
        lines.append("=" * 60)
        lines.append("TY_LEARN QA COMPARISON REPORT")
        lines.append("=" * 60)
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Overall Status
        status_emoji = {
            QAStatus.PASS: "✅",
            QAStatus.WARN: "⚠️", 
            QAStatus.FAIL: "❌"
        }
        
        lines.append(f"Overall Status: {status_emoji.get(result.status, '')} {result.status.value}")
        lines.append(f"Quality Score: {result.overall_score:.1f}/100")
        lines.append("")
        
        # Metrics Summary
        lines.append("📊 METRICS SUMMARY")
        lines.append("-" * 20)
        metrics = result.metrics.to_dict()
        for key, value in metrics.items():
            if key != "overall_score":
                formatted_key = key.replace("_", " ").title()
                lines.append(f"{formatted_key:.<20} {value:.1f}%")
        lines.append("")
        
        # Report Info
        if result.baseline_info and result.candidate_info:
            lines.append("📋 REPORT INFO")
            lines.append("-" * 15)
            
            baseline = result.baseline_info
            candidate = result.candidate_info
            
            lines.append(f"Baseline Sections: {baseline['total_sections']} ({baseline['word_count']} words)")
            lines.append(f"Candidate Sections: {candidate['total_sections']} ({candidate['word_count']} words)")
            lines.append("")
            
            lines.append("Section Comparison:")
            baseline_sections = set(baseline['section_names'])
            candidate_sections = set(candidate['section_names'])
            
            common = baseline_sections & candidate_sections
            missing = baseline_sections - candidate_sections
            extra = candidate_sections - baseline_sections
            
            if common:
                lines.append(f"  ✅ Shared: {', '.join(sorted(common))}")
            if missing:
                lines.append(f"  ❌ Missing: {', '.join(sorted(missing))}")
            if extra:
                lines.append(f"  ➕ Extra: {', '.join(sorted(extra))}")
            lines.append("")
        
        # Issues
        if result.issues:
            lines.append("🚨 ISSUES DETECTED")
            lines.append("-" * 20)
            
            # Group issues by severity
            severity_order = [IssueSeverity.CRITICAL, IssueSeverity.HIGH, IssueSeverity.MEDIUM, IssueSeverity.LOW]
            severity_emojis = {
                IssueSeverity.CRITICAL: "🔥",
                IssueSeverity.HIGH: "🚨",
                IssueSeverity.MEDIUM: "⚠️",
                IssueSeverity.LOW: "ℹ️"
            }
            
            for severity in severity_order:
                severity_issues = [issue for issue in result.issues if issue.severity == severity]
                if not severity_issues:
                    continue
                    
                lines.append(f"{severity_emojis[severity]} {severity.value.upper()} ({len(severity_issues)})")
                
                for issue in severity_issues:
                    section_info = f" [{issue.section}]" if issue.section else ""
                    lines.append(f"  • {issue.details}{section_info}")
                    
                    if issue.baseline_value is not None and issue.candidate_value is not None:
                        lines.append(f"    Baseline: {issue.baseline_value}, Candidate: {issue.candidate_value}")
                lines.append("")
        else:
            lines.append("✅ No issues detected!")
            lines.append("")
        
        # Recommendations
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 20)
        
        if result.status == QAStatus.FAIL:
            lines.append("❌ FAILURE - Immediate attention required:")
            critical_issues = [i for i in result.issues if i.severity == IssueSeverity.CRITICAL]
            if critical_issues:
                lines.append("  • Address critical missing sections")
            if result.overall_score < 50:
                lines.append("  • Review prompt engineering and LLM configuration")
                lines.append("  • Consider using a different model or parameters")
                
        elif result.status == QAStatus.WARN:
            lines.append("⚠️  WARNING - Monitor and consider improvements:")
            if result.metrics.section_coverage < 80:
                lines.append("  • Improve section detection and generation")
            if result.metrics.format_compliance < 90:
                lines.append("  • Review output format and parsing logic")
                
        else:
            lines.append("✅ PASS - Quality is acceptable")
            lines.append("  • Continue monitoring for consistency")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self, result: QAResult) -> str:
        """Generate markdown-formatted report"""
        
        lines = []
        
        # Header
        lines.append("# TY_Learn QA Comparison Report")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        # Status Badge
        status_badges = {
            QAStatus.PASS: "![PASS](https://img.shields.io/badge/QA-PASS-green)",
            QAStatus.WARN: "![WARN](https://img.shields.io/badge/QA-WARN-yellow)",
            QAStatus.FAIL: "![FAIL](https://img.shields.io/badge/QA-FAIL-red)"
        }
        
        lines.append(f"{status_badges.get(result.status, '')} **Score: {result.overall_score:.1f}/100**")
        lines.append("")
        
        # Metrics Table
        lines.append("## 📊 Metrics Summary")
        lines.append("")
        lines.append("| Metric | Score |")
        lines.append("|--------|-------|")
        
        metrics = result.metrics.to_dict()
        for key, value in metrics.items():
            if key != "overall_score":
                formatted_key = key.replace("_", " ").title()
                lines.append(f"| {formatted_key} | {value:.1f}% |")
        lines.append("")
        
        # Issues
        if result.issues:
            lines.append("## 🚨 Issues Detected")
            lines.append("")
            
            severity_order = [IssueSeverity.CRITICAL, IssueSeverity.HIGH, IssueSeverity.MEDIUM, IssueSeverity.LOW]
            severity_emojis = {
                IssueSeverity.CRITICAL: "🔥",
                IssueSeverity.HIGH: "🚨", 
                IssueSeverity.MEDIUM: "⚠️",
                IssueSeverity.LOW: "ℹ️"
            }
            
            for severity in severity_order:
                severity_issues = [issue for issue in result.issues if issue.severity == severity]
                if not severity_issues:
                    continue
                    
                lines.append(f"### {severity_emojis[severity]} {severity.value.title()} Issues")
                lines.append("")
                
                for issue in severity_issues:
                    section_info = f" (Section: `{issue.section}`)" if issue.section else ""
                    lines.append(f"- **{issue.type.value.replace('_', ' ').title()}**{section_info}")
                    lines.append(f"  {issue.details}")
                    
                    if issue.baseline_value is not None and issue.candidate_value is not None:
                        lines.append(f"  - Baseline: `{issue.baseline_value}`, Candidate: `{issue.candidate_value}`")
                lines.append("")
        
        # Report Info
        if result.baseline_info and result.candidate_info:
            lines.append("## 📋 Report Comparison")
            lines.append("")
            
            baseline = result.baseline_info
            candidate = result.candidate_info
            
            lines.append("| Aspect | Baseline | Candidate |")
            lines.append("|--------|----------|-----------|")
            lines.append(f"| Sections | {baseline['total_sections']} | {candidate['total_sections']} |")
            lines.append(f"| Word Count | {baseline['word_count']} | {candidate['word_count']} |")
            lines.append(f"| Has Tasks | {baseline['has_tasks']} | {candidate['has_tasks']} |")
            lines.append(f"| Has Profile | {baseline['has_profile']} | {candidate['has_profile']} |")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_json_report(self, result: QAResult) -> str:
        """Generate JSON-formatted report"""
        
        report_data = result.to_dict()
        report_data["generated_at"] = datetime.now().isoformat()
        report_data["report_version"] = "1.0"
        
        return json.dumps(report_data, indent=2)

class TyLearnQA:
    """Main QA interface for ty_learn reports"""
    
    def __init__(self):
        self.comparator = ReportComparator()
        self.reporter = StatusReporter()
    
    def compare_outputs(self, baseline_content: str, candidate_content: str, 
                       output_format: str = "text") -> str:
        """Compare two job extraction outputs and return formatted report
        
        Args:
            baseline_content: Reference output (V7.1, known good, etc.)
            candidate_content: Test output (V10.0, new model, etc.)
            output_format: 'text', 'json', or 'markdown'
            
        Returns:
            Formatted QA report string
        """
        
        # Run comparison
        result = self.comparator.compare(baseline_content, candidate_content)
        
        # Generate report
        report_result = self.reporter.generate_report(result, output_format)
        return str(report_result)
    
    def quick_check(self, content: str) -> Dict[str, Any]:
        """Quick quality check of a single output (no baseline comparison)
        
        Args:
            content: Job extraction output to check
            
        Returns:
            Dictionary with basic quality metrics
        """
        
        # Use empty baseline for structure checking only
        empty_baseline = "# Empty\n\n## Tasks\n\n## Profile\n"
        result = self.comparator.compare(empty_baseline, content)
        
        return {
            "has_tasks_section": result.candidate_info["has_tasks"] if result.candidate_info else False,
            "has_profile_section": result.candidate_info["has_profile"] if result.candidate_info else False,
            "section_count": result.candidate_info["total_sections"] if result.candidate_info else 0,
            "word_count": result.candidate_info["word_count"] if result.candidate_info else 0,
            "format_issues": len([i for i in result.issues if i.type.value in ["FORMAT_VIOLATION", "NOISE_CONTAMINATION"]]),
            "overall_score": result.overall_score
        }

# Test the complete system
if __name__ == "__main__":
    qa = TyLearnQA()
    
    baseline = """
## Business Analyst (E-invoicing) - Requirements & Responsibilities

### Your Tasks
* **Process Management**: Design and implement E-invoicing processes for the company
* **Data Analysis**: Validate invoice information for accuracy and completeness
* **System Integration**: Coordinate with IT teams for seamless integration

### Your Profile  
* **Education & Experience**: Bachelor's degree in economics, business, or related field
* **Technical Skills**: Proficiency in SimCorp Dimension, SAP, and data analysis tools
* **Language Skills**: Fluent in English and German
"""
    
    candidate_bad = """
**Key Responsibilities:**
- Some basic tasks here
- More undefined tasks

**What We Offer:**
- Great health insurance package
- Flexible work arrangements
- Company car and travel allowances
"""
    
    # Test comparison
    report = qa.compare_outputs(baseline, candidate_bad, "text")
    print(report)
    
    print("\n" + "="*60 + "\n")
    
    # Test quick check
    quick_result = qa.quick_check(candidate_bad)
    print("Quick Check Result:")
    for key, value in quick_result.items():
        print(f"  {key}: {value}")
