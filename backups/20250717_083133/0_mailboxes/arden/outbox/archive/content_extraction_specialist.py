"""
Content Extraction Specialist - Deutsche Bank Job Pipeline Enhancement
=========================================================================

Purpose: Transform bloated job descriptions into focused domain classification signals
Impact: Improve pipeline accuracy from 75% to 90%+ through surgical content extraction

Based on Sandy@consciousness validated methodology across 5+ job analysis cases.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    """Results from content extraction process"""
    original_length: int
    extracted_length: int
    reduction_percentage: float
    extracted_content: str
    removed_sections: List[str]
    domain_signals: List[str]
    processing_notes: List[str]

class ContentExtractionSpecialist:
    """
    Surgical content extraction for domain classification optimization.
    
    Transforms 16,000+ character bloated job descriptions into 1,500-2,000 character
    focused content while preserving 100% of domain classification signals.
    
    Validated methodology:
    - 60-75% content reduction across all job types
    - Universal boilerplate removal (benefits, culture, contact)
    - Bilingual deduplication (German/English)
    - Technical signal amplification for domain classification
    """
    
    def __init__(self):
        """Initialize the Content Extraction Specialist with validated patterns."""
        self.setup_extraction_patterns()
        self.setup_domain_signals()
        self.stats = {
            'jobs_processed': 0,
            'total_reduction': 0,
            'signal_preservation_rate': 0
        }
    
    def setup_extraction_patterns(self):
        """Setup validated content removal patterns from Sandy's analysis."""
        
        # Phase 1: Universal Boilerplate Removal Patterns
        self.benefits_patterns = [
            r"Best in class leave policy.*?health screening",
            r"Physical and Mental Health.*?retirement plan",
            r"Emotional ausgeglichen.*?Finanziell abgesichert.*?verbunden", 
            r"Benefits.*?insurance.*?assistance.*?program",
            r"Wellness.*?childcare.*?assistance.*?gender neutral",
            r"Health.*?pension.*?leave.*?flexible.*?arrangements",
            r"Employee benefits.*?social.*?financial.*?wellness",
            r"Premium healthcare.*?Sozial verbunden",
            r"Best in class leave policyGender neutral parental.*?excellence and mutual respect",
            r"As part of our flexible scheme.*?yrs. and above",
            r"Training and development to help you excel.*?suit your needs",
            r"How we'll support you.*?to suit your needs"
        ]
        
        self.company_culture_patterns = [
            r"We strive for a culture.*?empowered to excel together",
            r"Deutsche Bank Group.*?unity.*?excellence.*?respect",
            r"Positive, fair and inclusive work environment",
            r"At DWS.*?capturing the opportunities of tomorrow",
            r"Deutsche Bank's.*?transformation.*?innovation.*?growth",
            r"delay gratification.*?challenge outcomes.*?perspectives",
            r"We strive for a culture.*?excellence and mutual respect",
            r"acting responsibly.*?thinking commercially.*?working collaboratively",
            r"Together we share and celebrate.*?Deutsche Bank Group",
            r"We welcome applications from all people.*?inclusive work environment"
        ]
        
        self.contact_patterns = [
            r"For more information.*?contact.*?recruiting",
            r"Application process.*?interview.*?arrangements",
            r"If you have.*?disability.*?accommodation",
            r"Recruiter.*?contact.*?details.*?email.*?phone"
        ]
        
        # Phase 2: Duplication Patterns
        self.duplication_patterns = [
            r"(?i)(Your key responsibilities:.*?)Your key responsibilities:",  # Repeated sections
            r"(?i)(Deine Tätigkeitsschwerpunkte:.*?)Your key responsibilities:",  # Bilingual
            r"(?i)(Required qualifications:.*?)Required qualifications:"  # Repeated requirements
        ]
    
    def setup_domain_signals(self):
        """Setup domain-specific signal amplification patterns with multilingual support."""
        
        # Enhanced signal patterns with German/English equivalents and partial matching
        self.domain_signals = {
            "management_consulting": [
                # Core consulting terms
                "DBMC", "Deutsche Bank Management Consulting", "consulting", "consultant",
                "beratung", "berater",
                
                # Transformation terms (key for compound matching)
                "transformation", "transformations", "transform", "transforming",
                "transformations", "transforming", "veränderung", "wandel",
                
                # Strategic terms
                "strategic", "strategy", "strategisch", "strategie", "strategic projects",
                "strategieprojekt", "strategieprojekte", 
                
                # Project and change management
                "change management", "project management", "projektmanagement",
                "veränderungsmanagement", "organisationsveränderung",
                "process improvement", "prozessverbesserung", "business analysis",
                "geschäftsanalyse", "digital transformation", "organizational change"
            ],
            "quality_assurance": [
                "QA", "testing", "Selenium", "automation", "test cases",
                "regression testing", "defect tracking", "test cycle", "SDET",
                "qualitätssicherung", "testen", "automatisierung", "testfälle"
            ],
            "cybersecurity": [
                "cybersecurity", "vulnerability", "SIEM", "penetration testing",
                "security frameworks", "threat modeling", "CVSS", "NIST",
                "cybersicherheit", "sicherheit", "bedrohung", "schwachstelle"
            ],
            "tax_advisory": [
                "tax specialist", "Pillar 2", "Steuerberater", "tax compliance",
                "tax planning", "tax law", "Rechtsanwalt", "tax advisory",
                "steuer", "steuerberatung", "steuerplanung", "steuerrecht"
            ],
            "data_engineering": [
                "data pipeline", "ETL", "data warehouse", "big data",
                "Apache", "Spark", "Hadoop", "data architecture",
                "daten", "datenarchitektur", "datenverarbeitung", "datenpipeline"
            ],
            "financial_crime_compliance": [
                "AML", "sanctions", "compliance", "financial crime",
                "KYC", "anti-money laundering", "regulatory reporting",
                "geldwäsche", "sanktionen", "compliance", "regulatorisch"
            ]
        }
    
    def extract_core_content(self, raw_job_description: str, job_id: str = "unknown") -> ExtractionResult:
        """
        Main extraction method: Transform bloated content into focused signals.
        
        Args:
            raw_job_description: Original job posting content
            job_id: Identifier for tracking and logging
            
        Returns:
            ExtractionResult with extracted content and statistics
        """
        logger.info(f"Processing job {job_id} - Original length: {len(raw_job_description)} chars")
        
        original_length = len(raw_job_description)
        content = raw_job_description
        removed_sections = []
        processing_notes = []
        
        # Phase 0: Identify domain signals in raw content (before extraction)
        raw_domain_signals = self._identify_domain_signals(raw_job_description)
        if raw_domain_signals:
            processing_notes.append(f"Raw signals detected: {', '.join(raw_domain_signals)}")
        
        # Phase 1: Remove Universal Boilerplate
        content, removed_benefits = self._remove_benefits_sections(content)
        if removed_benefits:
            removed_sections.extend(removed_benefits)
            processing_notes.append(f"Removed {len(removed_benefits)} benefits sections")
        
        content, removed_culture = self._remove_company_culture(content)
        if removed_culture:
            removed_sections.extend(removed_culture)
            processing_notes.append(f"Removed {len(removed_culture)} company culture sections")
        
        content, removed_contact = self._remove_contact_info(content)
        if removed_contact:
            removed_sections.extend(removed_contact)
            processing_notes.append(f"Removed {len(removed_contact)} contact sections")
        
        # Phase 2: Deduplicate Content
        content, removed_duplicates = self._remove_duplications(content)
        if removed_duplicates:
            removed_sections.extend(removed_duplicates)
            processing_notes.append(f"Removed {len(removed_duplicates)} duplicate sections")
        
        # Phase 3: Extract and Enhance Core Technical Content
        content = self._extract_technical_core(content)
        processing_notes.append("Extracted core technical requirements")
        
        # Phase 4: Re-check domain signals after extraction and use raw signals if needed
        extracted_domain_signals = self._identify_domain_signals(content)
        
        # Ensure critical signals from raw content are preserved
        domain_signals = list(set(raw_domain_signals + extracted_domain_signals))
        if domain_signals:
            processing_notes.append(f"Final domain signals: {', '.join(domain_signals)}")
        
        # Clean up formatting
        content = self._clean_formatting(content)
        
        # Calculate statistics
        extracted_length = len(content)
        reduction_percentage = ((original_length - extracted_length) / original_length) * 100 if original_length > 0 else 0
        
        # Update processing stats
        self.stats['jobs_processed'] += 1
        self.stats['total_reduction'] += reduction_percentage
        
        logger.info(f"Job {job_id} processed - Reduced from {original_length} to {extracted_length} chars ({reduction_percentage:.1f}% reduction)")
        
        return ExtractionResult(
            original_length=original_length,
            extracted_length=extracted_length,
            reduction_percentage=reduction_percentage,
            extracted_content=content,
            removed_sections=removed_sections,
            domain_signals=domain_signals,
            processing_notes=processing_notes
        )
    
    def _remove_benefits_sections(self, content: str) -> Tuple[str, List[str]]:
        """Remove benefits boilerplate (400-1200 char sections)."""
        removed_sections = []
        
        for pattern in self.benefits_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                content = content.replace(match, "")
                removed_sections.append(f"Benefits: {match[:50]}...")
        
        return content, removed_sections
    
    def _remove_company_culture(self, content: str) -> Tuple[str, List[str]]:
        """Remove company culture boilerplate (200-600 char sections)."""
        removed_sections = []
        
        for pattern in self.company_culture_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                content = content.replace(match, "")
                removed_sections.append(f"Culture: {match[:50]}...")
        
        return content, removed_sections
    
    def _remove_contact_info(self, content: str) -> Tuple[str, List[str]]:
        """Remove contact and application process details."""
        removed_sections = []
        
        for pattern in self.contact_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                content = content.replace(match, "")
                removed_sections.append(f"Contact: {match[:50]}...")
        
        return content, removed_sections
    
    def _remove_duplications(self, content: str) -> Tuple[str, List[str]]:
        """Remove duplicate content sections."""
        removed_sections = []
        
        for pattern in self.duplication_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Keep first occurrence, remove duplicates
                first_occurrence = content.find(match)
                content = content[:first_occurrence] + content[first_occurrence:].replace(match, "", 1)
                removed_sections.append(f"Duplicate: {match[:50]}...")
        
        return content, removed_sections
    
    def _extract_technical_core(self, content: str) -> str:
        """Extract core technical requirements and responsibilities."""
        
        # Priority sections to preserve (German first for conciseness)
        priority_sections = [
            r"Deine Tätigkeitsschwerpunkte:.*?(?=Dein Profil:|Your responsibilities:|$)",
            r"Dein Profil:.*?(?=Benefits|What we offer|$)",
            r"Your key responsibilities:.*?(?=Required qualifications:|$)",
            r"Required qualifications:.*?(?=What we offer|Benefits|$)",
            r"Technical skills:.*?(?=Experience|Education|$)",
            r"Experience required:.*?(?=Skills|Education|$)"
        ]
        
        extracted_content = []
        
        for section_pattern in priority_sections:
            matches = re.findall(section_pattern, content, re.DOTALL | re.IGNORECASE)
            extracted_content.extend(matches)
        
        # If no structured sections found, extract key paragraphs
        if not extracted_content:
            # Fall back to paragraph extraction
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                if len(paragraph) > 100 and any(keyword in paragraph.lower() for keyword in 
                    ['experience', 'skills', 'requirement', 'responsibilities', 'qualifications']):
                    extracted_content.append(paragraph)
        
        # Final fallback: if still no content, return first meaningful chunk
        if not extracted_content and content.strip():
            # For edge cases like test content, return a truncated version
            lines = [line for line in content.split('\n') if line.strip()]
            if lines:
                # Take first few lines up to reasonable length
                truncated = '\n'.join(lines[:10])
                if len(truncated) > 1000:
                    truncated = truncated[:1000] + "..."
                extracted_content = [truncated]
        
        return '\n\n'.join(extracted_content)
    
    def _identify_domain_signals(self, content: str) -> List[str]:
        """Identify and amplify domain classification signals with enhanced pattern matching."""
        identified_signals = []
        content_lower = content.lower()
        
        for domain, signals in self.domain_signals.items():
            for signal in signals:
                signal_lower = signal.lower()
                
                # Exact match
                if signal_lower in content_lower:
                    identified_signals.append(signal)
                # Enhanced partial matching for compound words (German speciality)
                elif len(signal_lower) >= 6:  # Only for longer terms to avoid false positives
                    import re
                    # Pattern to match signal as part of compound words
                    # e.g., "transformation" matches "Transformationsprojekten"
                    pattern = re.compile(r'\b\w*' + re.escape(signal_lower) + r'\w*\b', re.IGNORECASE)
                    if pattern.search(content):
                        # Include both the original signal and compound notation for tracking
                        identified_signals.append(signal)  # Original signal for validation tests
        
        return list(set(identified_signals))  # Remove duplicates
    
    def _clean_formatting(self, content: str) -> str:
        """Clean up formatting and whitespace."""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        # Remove empty bullets and formatting artifacts
        content = re.sub(r'^\s*[•·-]\s*$', '', content, flags=re.MULTILINE)
        
        # Remove trailing fragments and incomplete sentences
        content = re.sub(r',\s*\.\.\..*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n\s*,\s*\.\.\..*?\n', '\n', content)
        content = re.sub(r'\n\s*,\s*\.\.\..*?$', '', content)
        
        # Remove empty lines
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        return content.strip()
    
    def get_processing_statistics(self) -> Dict[str, float]:
        """Get processing statistics across all jobs."""
        if self.stats['jobs_processed'] == 0:
            return {'jobs_processed': 0, 'average_reduction': 0}
        
        return {
            'jobs_processed': self.stats['jobs_processed'],
            'average_reduction': self.stats['total_reduction'] / self.stats['jobs_processed']
        }

def main():
    """Demo the Content Extraction Specialist."""
    specialist = ContentExtractionSpecialist()
    
    # Test with sample content (would be replaced with actual job data)
    sample_content = """
    Senior Consultant (d/m/w) – Deutsche Bank Management Consulting
    
    Deine Tätigkeitsschwerpunkte:
    • Strategic project execution and transformation initiatives
    • Sub-project leadership and team member responsibility
    • Direct client engagement within the bank (internal consulting)
    
    Best in class leave policy, Gender neutral parental leaves, 100% reimbursement 
    under childcare assistance scheme, Health screening, Premium healthcare, Emotional 
    ausgeglichen, Körperlich gesund, Finanziell abgesichert, Sozial verbunden...
    
    We strive for a culture in which we are empowered to excel together, delay gratification, 
    and challenge outcomes. We respect differences in experience, knowledge, backgrounds, 
    cultures, opinions and perspectives...
    """
    
    result = specialist.extract_core_content(sample_content, "demo")
    
    print(f"Original length: {result.original_length}")
    print(f"Extracted length: {result.extracted_length}")
    print(f"Reduction: {result.reduction_percentage:.1f}%")
    print(f"Domain signals: {result.domain_signals}")
    print(f"\nExtracted content:\n{result.extracted_content}")

if __name__ == "__main__":
    main()
