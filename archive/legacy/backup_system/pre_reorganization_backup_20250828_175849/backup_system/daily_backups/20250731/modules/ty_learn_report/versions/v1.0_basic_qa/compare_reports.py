"""
TY_LEARN_REPORT - Core Comparison Engine
Compares two job extraction outputs and generates QA results
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from section_parser import SectionParser, ParsedReport, Section

class QAStatus(Enum):
    """QA status levels"""
    PASS = "PASS"
    WARN = "WARN" 
    FAIL = "FAIL"

class IssueType(Enum):
    """Types of issues that can be detected"""
    MISSING_SECTION = "MISSING_SECTION"
    LENGTH_DISCREPANCY = "LENGTH_DISCREPANCY"
    EMPTY_CONTENT = "EMPTY_CONTENT"
    FORMAT_VIOLATION = "FORMAT_VIOLATION"
    NOISE_CONTAMINATION = "NOISE_CONTAMINATION"
    STRUCTURE_MISMATCH = "STRUCTURE_MISMATCH"

class IssueSeverity(Enum):
    """Severity levels for issues"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class QAIssue:
    """Represents a specific QA issue found during comparison"""
    type: IssueType
    severity: IssueSeverity
    section: Optional[str]
    details: str
    baseline_value: Optional[Any] = None
    candidate_value: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "section": self.section,
            "details": self.details,
            "baseline_value": self.baseline_value,
            "candidate_value": self.candidate_value
        }

@dataclass
class QAMetrics:
    """Metrics calculated during comparison"""
    section_coverage: float  # % of expected sections present
    content_similarity: float  # Overall content similarity score
    format_compliance: float  # Format adherence score
    length_variance: float  # Average length difference %
    structure_score: float  # Structure alignment score
    
    @property
    def overall_score(self) -> float:
        """Calculate overall quality score"""
        return (
            self.section_coverage * 0.3 +
            self.content_similarity * 0.25 +
            self.format_compliance * 0.25 +
            (100 - min(self.length_variance, 100)) * 0.1 +
            self.structure_score * 0.1
        )
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization"""
        return {
            "section_coverage": round(self.section_coverage, 1),
            "content_similarity": round(self.content_similarity, 1),
            "format_compliance": round(self.format_compliance, 1),
            "length_variance": round(self.length_variance, 1),
            "structure_score": round(self.structure_score, 1),
            "overall_score": round(self.overall_score, 1)
        }

@dataclass
class QAResult:
    """Complete QA comparison result"""
    status: QAStatus
    metrics: QAMetrics
    issues: List[QAIssue] = field(default_factory=list)
    baseline_info: Optional[Dict[str, Any]] = None
    candidate_info: Optional[Dict[str, Any]] = None
    comparison_timestamp: Optional[str] = None
    
    @property
    def overall_score(self) -> float:
        """Get overall quality score"""
        return self.metrics.overall_score
    
    def add_issue(self, issue: QAIssue) -> None:
        """Add an issue to the result"""
        self.issues.append(issue)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "status": self.status.value,
            "overall_score": round(self.overall_score, 1),
            "metrics": self.metrics.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
            "baseline_info": self.baseline_info,
            "candidate_info": self.candidate_info,
            "comparison_timestamp": self.comparison_timestamp
        }

class ReportComparator:
    """Main comparison engine for job extraction outputs"""
    
    # Thresholds for different issue types
    LENGTH_DISCREPANCY_THRESHOLD = 30.0  # % difference
    EMPTY_CONTENT_MIN_CHARS = 10
    
    def __init__(self):
        self.parser = SectionParser()
    
    def compare(self, baseline_content: str, candidate_content: str) -> QAResult:
        """Compare two job extraction outputs and return QA result"""
        
        # Parse both reports
        baseline = self.parser.parse(baseline_content)
        candidate = self.parser.parse(candidate_content)
        
        # Initialize result
        result = QAResult(
            status=QAStatus.PASS,  # Will be updated based on issues
            metrics=QAMetrics(0, 0, 0, 0, 0),  # Will be calculated
            baseline_info=self._get_report_info(baseline),
            candidate_info=self._get_report_info(candidate)
        )
        
        # Run all comparisons
        self._check_missing_sections(baseline, candidate, result)
        self._check_length_discrepancies(baseline, candidate, result)
        self._check_empty_content(candidate, result)
        self._check_format_violations(candidate, result)
        self._check_noise_contamination(candidate, result)
        
        # Calculate metrics
        result.metrics = self._calculate_metrics(baseline, candidate, result)
        
        # Determine overall status
        result.status = self._determine_status(result)
        
        return result
    
    def _get_report_info(self, report: ParsedReport) -> Dict[str, Any]:
        """Extract basic info about a report"""
        return {
            "title": report.title,
            "format_type": report.format_type,
            "total_sections": len(report.sections),
            "section_names": list(report.sections.keys()),
            "word_count": report.total_word_count,
            "char_count": report.total_char_count,
            "has_tasks": report.has_tasks_section,
            "has_profile": report.has_profile_section
        }
    
    def _check_missing_sections(self, baseline: ParsedReport, candidate: ParsedReport, result: QAResult) -> None:
        """Check for missing sections in candidate vs baseline"""
        
        baseline_sections = set(baseline.sections.keys())
        candidate_sections = set(candidate.sections.keys())
        
        missing = baseline_sections - candidate_sections
        extra = candidate_sections - baseline_sections
        
        for section in missing:
            result.add_issue(QAIssue(
                type=IssueType.MISSING_SECTION,
                severity=IssueSeverity.HIGH,
                section=section,
                details=f"Section '{section}' present in baseline but missing in candidate",
                baseline_value=baseline.sections[section].word_count,
                candidate_value=0
            ))
        
        # Check for critical section requirements
        if not candidate.has_tasks_section:
            result.add_issue(QAIssue(
                type=IssueType.MISSING_SECTION,
                severity=IssueSeverity.CRITICAL,
                section="Tasks Section",
                details="No tasks/responsibilities section found in candidate"
            ))
            
        if not candidate.has_profile_section:
            result.add_issue(QAIssue(
                type=IssueType.MISSING_SECTION,
                severity=IssueSeverity.CRITICAL,
                section="Profile Section", 
                details="No profile/requirements section found in candidate"
            ))
    
    def _check_length_discrepancies(self, baseline: ParsedReport, candidate: ParsedReport, result: QAResult) -> None:
        """Check for significant length differences between matching sections"""
        
        for section_name in baseline.sections:
            if section_name not in candidate.sections:
                continue  # Already handled in missing sections
                
            baseline_section = baseline.sections[section_name]
            candidate_section = candidate.sections[section_name]
            
            baseline_length = baseline_section.word_count
            candidate_length = candidate_section.word_count
            
            if baseline_length == 0:
                continue  # Skip empty baseline sections
            
            # Calculate percentage difference
            diff_percent = abs(baseline_length - candidate_length) / baseline_length * 100
            
            if diff_percent > self.LENGTH_DISCREPANCY_THRESHOLD:
                severity = IssueSeverity.HIGH if diff_percent > 50 else IssueSeverity.MEDIUM
                
                direction = "shorter" if candidate_length < baseline_length else "longer"
                
                result.add_issue(QAIssue(
                    type=IssueType.LENGTH_DISCREPANCY,
                    severity=severity,
                    section=section_name,
                    details=f"Section '{section_name}' is {diff_percent:.1f}% {direction} than baseline",
                    baseline_value=baseline_length,
                    candidate_value=candidate_length
                ))
    
    def _check_empty_content(self, candidate: ParsedReport, result: QAResult) -> None:
        """Check for empty or minimal content in candidate sections"""
        
        for section_name, section in candidate.sections.items():
            if section.is_empty:
                result.add_issue(QAIssue(
                    type=IssueType.EMPTY_CONTENT,
                    severity=IssueSeverity.HIGH,
                    section=section_name,
                    details=f"Section '{section_name}' has minimal or no content ({section.char_count} chars)",
                    candidate_value=section.char_count
                ))
    
    def _check_format_violations(self, candidate: ParsedReport, result: QAResult) -> None:
        """Check for format violations in candidate"""
        
        if candidate.format_type == "malformed":
            result.add_issue(QAIssue(
                type=IssueType.FORMAT_VIOLATION,
                severity=IssueSeverity.HIGH,
                section=None,
                details="Report format is malformed - missing expected section structure"
            ))
        elif candidate.format_type == "contaminated":
            result.add_issue(QAIssue(
                type=IssueType.NOISE_CONTAMINATION,
                severity=IssueSeverity.MEDIUM,
                section=None,
                details="Report contains noise sections (benefits, company info, etc.)"
            ))
    
    def _check_noise_contamination(self, candidate: ParsedReport, result: QAResult) -> None:
        """Check for noise/contamination in candidate content"""
        
        noise_keywords = ["what we offer", "benefits", "company culture", "perks"]
        
        for section_name, section in candidate.sections.items():
            content_lower = section.content.lower()
            
            for noise in noise_keywords:
                if noise in content_lower:
                    result.add_issue(QAIssue(
                        type=IssueType.NOISE_CONTAMINATION,
                        severity=IssueSeverity.MEDIUM,
                        section=section_name,
                        details=f"Section contains noise content: '{noise}'"
                    ))
                    break
    
    def _calculate_metrics(self, baseline: ParsedReport, candidate: ParsedReport, result: QAResult) -> QAMetrics:
        """Calculate comparison metrics"""
        
        # Section coverage: what % of expected sections are present
        expected_sections = {"tasks", "profile", "requirements", "responsibilities"}
        candidate_section_words = {name.lower().replace(" ", "") for name in candidate.sections.keys()}
        
        coverage_count = sum(1 for expected in expected_sections 
                           if any(expected in section for section in candidate_section_words))
        section_coverage = (coverage_count / len(expected_sections)) * 100
        
        # Format compliance: penalize format violations
        format_compliance = 100.0
        for issue in result.issues:
            if issue.type in [IssueType.FORMAT_VIOLATION, IssueType.NOISE_CONTAMINATION]:
                format_compliance -= 25
            elif issue.type == IssueType.MISSING_SECTION and issue.severity == IssueSeverity.CRITICAL:
                format_compliance -= 30
        format_compliance = max(0, format_compliance)
        
        # Content similarity: rough estimate based on word count similarity
        baseline_words = baseline.total_word_count
        candidate_words = candidate.total_word_count
        
        if baseline_words > 0:
            word_ratio = min(candidate_words, baseline_words) / max(candidate_words, baseline_words)
            content_similarity = word_ratio * 100
        else:
            content_similarity = 0
        
        # Length variance: average % difference across sections
        length_diffs = []
        for section_name in baseline.sections:
            if section_name in candidate.sections:
                b_len = baseline.sections[section_name].word_count
                c_len = candidate.sections[section_name].word_count
                if b_len > 0:
                    diff = abs(b_len - c_len) / b_len * 100
                    length_diffs.append(diff)
        
        length_variance = sum(length_diffs) / len(length_diffs) if length_diffs else 0
        
        # Structure score: basic check for expected structure
        structure_score = 100.0
        if not candidate.has_tasks_section:
            structure_score -= 40
        if not candidate.has_profile_section:
            structure_score -= 40
        structure_score = max(0, structure_score)
        
        return QAMetrics(
            section_coverage=section_coverage,
            content_similarity=content_similarity,
            format_compliance=format_compliance,
            length_variance=length_variance,
            structure_score=structure_score
        )
    
    def _determine_status(self, result: QAResult) -> QAStatus:
        """Determine overall QA status based on issues and metrics"""
        
        # Check for critical issues
        critical_issues = [issue for issue in result.issues if issue.severity == IssueSeverity.CRITICAL]
        if critical_issues:
            return QAStatus.FAIL
        
        # Check for high severity issues
        high_issues = [issue for issue in result.issues if issue.severity == IssueSeverity.HIGH]
        if len(high_issues) >= 2:
            return QAStatus.FAIL
        elif high_issues:
            return QAStatus.WARN
        
        # Check overall score
        if result.overall_score < 60:
            return QAStatus.FAIL
        elif result.overall_score < 80:
            return QAStatus.WARN
        
        return QAStatus.PASS

# Test the comparator
if __name__ == "__main__":
    comparator = ReportComparator()
    
    baseline = """
## Business Analyst (E-invoicing) - Requirements & Responsibilities

### Your Tasks
* **Process Management**: Design and implement E-invoicing processes
* **Data Analysis**: Validate invoice information for accuracy

### Your Profile  
* **Education & Experience**: Bachelor's degree in economics
* **Technical Skills**: Proficiency in SimCorp Dimension, SAP
"""
    
    candidate_good = baseline  # Same content
    
    candidate_bad = """
**Key Responsibilities:**
- Some tasks here
- More tasks

**Company Benefits:**
- Great health insurance
- Flexible work arrangements
"""
    
    # Test good comparison
    result_good = comparator.compare(baseline, candidate_good)
    print(f"Good comparison: {result_good.status.value} ({result_good.overall_score:.1f})")
    
    # Test bad comparison  
    result_bad = comparator.compare(baseline, candidate_bad)
    print(f"Bad comparison: {result_bad.status.value} ({result_bad.overall_score:.1f})")
    print(f"Issues: {len(result_bad.issues)}")
    for issue in result_bad.issues:
        print(f"  - {issue.type.value}: {issue.details}")
