"""
TY_LEARN_REPORT - Section Parser
Extracts and analyzes markdown sections from job extraction outputs
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class Section:
    """Represents a parsed section from job extraction output"""
    name: str
    content: str
    start_line: int
    end_line: int
    word_count: int
    char_count: int
    
    @property
    def is_empty(self) -> bool:
        """Check if section has meaningful content"""
        return len(self.content.strip()) < 10
    
    @property  
    def bullet_count(self) -> int:
        """Count bullet points in section"""
        return len(re.findall(r'^\s*[*-]\s+', self.content, re.MULTILINE))

@dataclass
class ParsedReport:
    """Complete parsed job extraction report"""
    title: str
    sections: Dict[str, Section]
    raw_content: str
    total_word_count: int
    total_char_count: int
    format_type: str  # "standard", "malformed", "unknown"
    
    @property
    def has_tasks_section(self) -> bool:
        """Check if report has a tasks section"""
        return any("task" in name.lower() for name in self.sections.keys())
    
    @property
    def has_profile_section(self) -> bool:
        """Check if report has a profile/requirements section"""
        return any(keyword in name.lower() for keyword in ["profile", "requirement", "skill", "experience"] 
                  for name in self.sections.keys())

class SectionParser:
    """Parses job extraction outputs into structured sections"""
    
    # Standard section patterns we expect
    EXPECTED_SECTIONS = [
        "your tasks",
        "your profile", 
        "requirements",
        "responsibilities",
        "qualifications"
    ]
    
    # Patterns that indicate noise/contamination
    NOISE_PATTERNS = [
        "what we offer",
        "benefits",
        "company culture",
        "about us",
        "extraction rules",
        "quality standards"
    ]
    
    def __init__(self):
        self.section_regex = re.compile(r'^#{1,4}\s*(.+)$', re.MULTILINE)
        self.bullet_regex = re.compile(r'^\s*[*-]\s+(.+)$', re.MULTILINE)
    
    def parse(self, content: str) -> ParsedReport:
        """Parse job extraction content into structured sections"""
        
        # Extract title
        title = self._extract_title(content)
        
        # Find all section headers
        sections = self._extract_sections(content)
        
        # Calculate totals
        total_words = len(content.split())
        total_chars = len(content)
        
        # Determine format type
        format_type = self._classify_format(sections, content)
        
        return ParsedReport(
            title=title,
            sections=sections,
            raw_content=content,
            total_word_count=total_words,
            total_char_count=total_chars,
            format_type=format_type
        )
    
    def _extract_title(self, content: str) -> str:
        """Extract job title from content"""
        lines = content.strip().split('\n')
        
        # Look for title patterns
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line and not line.startswith('#'):
                continue
            
            # Remove markdown formatting
            title = re.sub(r'^#+\s*', '', line)
            title = re.sub(r'\*\*([^*]+)\*\*', r'\1', title)  # Remove bold
            
            if len(title) > 10 and any(word in title.lower() for word in 
                                     ['analyst', 'manager', 'specialist', 'lead', 'developer']):
                return title.strip()
        
        return "Unknown Job Title"
    
    def _extract_sections(self, content: str) -> Dict[str, Section]:
        """Extract all sections from content"""
        sections = {}
        lines = content.split('\n')
        
        current_section = None
        current_content: List[str] = []
        start_line = 0
        
        for i, line in enumerate(lines):
            # Check if this is a section header
            header_match = re.match(r'^#{1,4}\s*(.+)$', line.strip())
            
            if header_match:
                # Save previous section if exists
                if current_section:
                    section_content = '\n'.join(current_content).strip()
                    sections[current_section] = Section(
                        name=current_section,
                        content=section_content,
                        start_line=start_line,
                        end_line=i-1,
                        word_count=len(section_content.split()),
                        char_count=len(section_content)
                    )
                
                # Start new section
                current_section = header_match.group(1).strip()
                current_content = []
                start_line = i + 1
                
            elif current_section:
                current_content.append(line)
        
        # Don't forget the last section
        if current_section:
            section_content = '\n'.join(current_content).strip()
            sections[current_section] = Section(
                name=current_section,
                content=section_content,
                start_line=start_line,
                end_line=len(lines),
                word_count=len(section_content.split()),
                char_count=len(section_content)
            )
        
        return sections
    
    def _classify_format(self, sections: Dict[str, Section], content: str) -> str:
        """Classify the format type of the report"""
        
        # Check for noise contamination
        section_names_lower = [name.lower() for name in sections.keys()]
        
        if any(noise in ' '.join(section_names_lower) for noise in self.NOISE_PATTERNS):
            return "contaminated"
        
        # Check for standard format
        has_tasks = any("task" in name for name in section_names_lower)
        has_profile = any(keyword in name for keyword in ["profile", "requirement"] 
                         for name in section_names_lower)
        
        if has_tasks and has_profile:
            return "standard"
        
        # Check for alternative valid formats
        if len(sections) >= 2 and any("responsib" in name for name in section_names_lower):
            return "alternative"
        
        return "malformed"

# Test the parser with sample data
if __name__ == "__main__":
    parser = SectionParser()
    
    # Test with good format
    sample_good = """
## Business Analyst (E-invoicing) - Requirements & Responsibilities

### Your Tasks
* **Process Management**: Design and implement E-invoicing processes
* **Data Analysis**: Validate invoice information for accuracy

### Your Profile
* **Education & Experience**: Bachelor's degree in economics
* **Technical Skills**: Proficiency in SimCorp Dimension, SAP
"""
    
    result = parser.parse(sample_good)
    print(f"Format: {result.format_type}")
    print(f"Sections: {list(result.sections.keys())}")
    print(f"Has tasks: {result.has_tasks_section}")
    print(f"Has profile: {result.has_profile_section}")
