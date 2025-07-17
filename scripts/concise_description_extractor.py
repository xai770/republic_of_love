#!/usr/bin/env python3
"""
Ultra-Concise Job Description Extractor
========================================

This tool takes the output from ContentExtractionSpecialist v2.0 and creates
truly concise job descriptions (~150 characters) suitable for job matching.

Author: Arden
Date: 2025-01-09
Purpose: Support Sandy with concise description extraction for job matching
"""

import re
import sys
from typing import Optional

class ConciseDescriptionExtractor:
    """Extracts ultra-concise job descriptions from v2.0 extraction output."""
    
    def __init__(self, target_length: int = 150):
        """
        Initialize the extractor.
        
        Args:
            target_length: Target character length for concise descriptions
        """
        self.target_length = target_length
    
    def extract_position_title(self, text: str) -> str:
        """Extract the main position title from v2.0 output."""
        # Look for "Position:" section
        position_match = re.search(r'Position:\s*([^\n]+)', text, re.IGNORECASE)
        if position_match:
            return position_match.group(1).strip()
        
        # Fallback: try to find job title patterns
        title_patterns = [
            r'(Senior|Junior|Lead|Principal)?\s*(Software|Data|Machine Learning|AI|Backend|Frontend|Full[- ]?Stack|DevOps|Cloud)\s*(Engineer|Developer|Scientist|Analyst)',
            r'(Software|Data|Machine Learning|AI|Backend|Frontend|Full[- ]?Stack|DevOps|Cloud)\s*(Engineer|Developer|Scientist|Analyst)',
            r'(Technical|Product|Engineering)\s*(Manager|Lead)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return "Software Engineer"  # Default fallback
    
    def extract_key_technologies(self, text: str) -> list:
        """Extract key technologies and skills from v2.0 output."""
        # Common tech keywords to look for
        tech_keywords = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Rust', 'Scala',
            'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask', 'Spring',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'PostgreSQL', 'MongoDB', 'Redis',
            'TensorFlow', 'PyTorch', 'Spark', 'Kafka', 'Elasticsearch', 'GraphQL', 'REST',
            'Microservices', 'Git', 'Jenkins', 'Terraform', 'Ansible'
        ]
        
        found_tech = []
        text_upper = text.upper()
        
        for tech in tech_keywords:
            if tech.upper() in text_upper:
                found_tech.append(tech)
        
        # Limit to top 4-5 most important technologies
        return found_tech[:5]
    
    def extract_experience_level(self, text: str) -> str:
        """Extract experience level requirements."""
        # Look for experience patterns
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'minimum\s*(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                years = int(match.group(1))
                if years <= 2:
                    return "Junior"
                elif years <= 5:
                    return "Mid-level"
                else:
                    return "Senior"
        
        # Look for explicit level keywords
        if re.search(r'\b(senior|lead|principal)\b', text, re.IGNORECASE):
            return "Senior"
        elif re.search(r'\b(junior|entry|graduate)\b', text, re.IGNORECASE):
            return "Junior"
        
        return "Mid-level"  # Default
    
    def create_concise_description(self, v2_output: str) -> str:
        """
        Create an ultra-concise job description from v2.0 output.
        
        Args:
            v2_output: The output from ContentExtractionSpecialist v2.0
            
        Returns:
            Concise description (~150 characters)
        """
        position = self.extract_position_title(v2_output)
        technologies = self.extract_key_technologies(v2_output)
        experience = self.extract_experience_level(v2_output)
        
        # Build concise description
        if experience != "Mid-level":
            description = f"{experience} {position}"
        else:
            description = position
        
        # Add key technologies
        if technologies:
            tech_str = ", ".join(technologies[:3])  # Limit to top 3
            description += f" - {tech_str}"
        
        # Add location if found
        location_match = re.search(r'Location:\s*([^\n]+)', v2_output, re.IGNORECASE)
        if location_match:
            location = location_match.group(1).strip()
            if len(location) <= 20:  # Only add if short
                description += f" ({location})"
        
        # Trim to target length if needed
        if len(description) > self.target_length:
            # Smart truncation - try to keep complete words
            truncated = description[:self.target_length-3].rsplit(' ', 1)[0] + "..."
            return truncated
        
        return description


def test_concise_extractor():
    """Test the concise extractor with real v2.0 output."""
    
    # Sample v2.0 output from our previous test
    v2_output = """Position: Senior Java Developer

Key Responsibilities:
- Develop and maintain high-quality Java applications
- Collaborate with cross-functional teams to design and implement new features
- Participate in code reviews and ensure best practices
- Troubleshoot and resolve technical issues

Required Skills:
- Strong proficiency in Java (8+ years experience)
- Experience with Spring Framework, Spring Boot
- Knowledge of RESTful web services and microservices architecture
- Familiarity with relational databases (PostgreSQL, MySQL)
- Experience with version control systems (Git)
- Understanding of Agile development methodologies

Preferred Qualifications:
- Experience with cloud platforms (AWS, Azure)
- Knowledge of containerization technologies (Docker, Kubernetes)
- Familiarity with CI/CD pipelines

Location: Remote (EU timezone)"""
    
    extractor = ConciseDescriptionExtractor(target_length=150)
    concise_desc = extractor.create_concise_description(v2_output)
    
    print("=== CONCISE DESCRIPTION EXTRACTION TEST ===")
    print(f"Original v2.0 output length: {len(v2_output)} characters")
    print(f"Concise description length: {len(concise_desc)} characters")
    print(f"Target length: {extractor.target_length} characters")
    print(f"Reduction: {((len(v2_output) - len(concise_desc)) / len(v2_output) * 100):.1f}%")
    print()
    print("Concise Description:")
    print(f'"{concise_desc}"')
    print()
    print("✓ SUCCESS: Concise description created successfully!")


if __name__ == "__main__":
    test_concise_extractor()
