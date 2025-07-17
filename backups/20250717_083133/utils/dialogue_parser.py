#!/usr/bin/env python3
"""
Dialogue Parser Module
=====================

Extracts structured data from LLM dialogue logs for analysis.
Supports various log formats and conversation structures.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DialogueEntry:
    """Structured representation of a single dialogue entry"""
    model_name: str
    test_type: str
    test_id: str
    processing_time: float
    response_length: int
    response_text: str
    prompt_text: str
    success: bool
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class DialogueParser:
    """Parse dialogue logs and extract structured information"""
    
    def __init__(self, test_type_patterns: Optional[Dict[str, str]] = None):
        """
        Initialize parser with test type detection patterns
        
        Args:
            test_type_patterns: Custom patterns for detecting test types
        """
        self.test_type_patterns = test_type_patterns or self._default_patterns()
    
    def _default_patterns(self) -> Dict[str, str]:
        """Default test type detection patterns"""
        return {
            "concise_extraction": "Your Tasks.*Your Profile",
            "requirements_focus": "I only need the requirements",
            "structured_analysis": "=== TECHNICAL REQUIREMENTS ===",
            "skills_categorization": "=== SOFT SKILLS ==="
        }
    
    def parse_dialogue_file(self, log_file: Path) -> Optional[DialogueEntry]:
        """
        Parse a single dialogue log file
        
        Args:
            log_file: Path to the dialogue log file
            
        Returns:
            DialogueEntry object or None if parsing fails
        """
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract basic information
            model_name = self._extract_model_name(content)
            processing_time = self._extract_processing_time(content)
            response_text = self._extract_response(content)
            prompt_text = self._extract_prompt(content)
            
            # Determine test type
            test_type, test_id = self._determine_test_type(content)
            
            # Calculate derived metrics
            response_length = len(response_text)
            success = self._assess_basic_success(response_text, test_id)
            
            # Extract timestamp from filename or content
            timestamp = self._extract_timestamp(log_file, content)
            
            return DialogueEntry(
                model_name=model_name,
                test_type=test_type,
                test_id=test_id,
                processing_time=processing_time,
                response_length=response_length,
                response_text=response_text,
                prompt_text=prompt_text,
                success=success,
                timestamp=timestamp,
                metadata={"source_file": str(log_file)}
            )
            
        except Exception as e:
            print(f"Error parsing {log_file}: {e}")
            return None
    
    def parse_directory(self, dialogue_dir: Path, pattern: str = "*.md") -> List[DialogueEntry]:
        """
        Parse all dialogue files in a directory
        
        Args:
            dialogue_dir: Directory containing dialogue logs
            pattern: File pattern to match (default: "*.md")
            
        Returns:
            List of DialogueEntry objects
        """
        entries = []
        log_files = list(dialogue_dir.glob(pattern))
        
        print(f"📊 Found {len(log_files)} dialogue files to parse")
        
        for log_file in log_files:
            entry = self.parse_dialogue_file(log_file)
            if entry:
                entries.append(entry)
        
        print(f"✅ Successfully parsed {len(entries)} dialogue entries")
        return entries
    
    def _extract_model_name(self, content: str) -> str:
        """Extract model name from dialogue content"""
        model_match = re.search(r'Model: ([^\n]+)', content)
        return model_match.group(1).strip() if model_match else "unknown"
    
    def _extract_processing_time(self, content: str) -> float:
        """Extract processing time from dialogue content"""
        time_match = re.search(r'Processing Time: ([\d.]+) seconds', content)
        return float(time_match.group(1)) if time_match else 0.0
    
    def _extract_response(self, content: str) -> str:
        """Extract model response from dialogue content"""
        response_match = re.search(
            r'### Raw Response from Model:\s*```\s*(.*?)\s*```', 
            content, 
            re.DOTALL
        )
        return response_match.group(1).strip() if response_match else ""
    
    def _extract_prompt(self, content: str) -> str:
        """Extract prompt from dialogue content"""
        prompt_match = re.search(
            r'### Prompt Sent to Model:\s*```\s*(.*?)\s*```', 
            content, 
            re.DOTALL
        )
        return prompt_match.group(1).strip() if prompt_match else ""
    
    def _determine_test_type(self, content: str) -> tuple[str, str]:
        """Determine test type and ID from content"""
        for test_id, pattern in self.test_type_patterns.items():
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                test_type = self._format_test_type(test_id)
                return test_type, test_id
        
        return "Unknown", "unknown"
    
    def _format_test_type(self, test_id: str) -> str:
        """Convert test ID to human-readable format"""
        format_map = {
            "concise_extraction": "Concise Job Description Extraction",
            "requirements_focus": "Requirements Focus Extraction", 
            "structured_analysis": "Structured Technical Analysis",
            "skills_categorization": "Skills Categorization"
        }
        return format_map.get(test_id, test_id.replace("_", " ").title())
    
    def _assess_basic_success(self, response_text: str, test_id: str) -> bool:
        """Basic success assessment based on response length and content"""
        if len(response_text) < 50:
            return False
        
        # Test-specific success criteria
        if test_id == "structured_analysis":
            return "===" in response_text
        elif test_id == "skills_categorization":
            return "=== SOFT SKILLS ===" in response_text
        elif test_id == "concise_extraction":
            return any(term in response_text.lower() for term in ["your tasks", "your profile"])
        elif test_id == "requirements_focus":
            return any(term in response_text.lower() for term in ["requirement", "skill", "experience"])
        
        return True
    
    def _extract_timestamp(self, log_file: Path, content: str) -> Optional[datetime]:
        """Extract timestamp from filename or content"""
        # Try to extract from filename (format: YYYYMMDD_HHMMSS)
        timestamp_match = re.search(r'(\d{8}_\d{6})', log_file.name)
        if timestamp_match:
            try:
                return datetime.strptime(timestamp_match.group(1), "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        
        # Try to extract from content
        time_match = re.search(r'Generated: ([\d-]+ [\d:]+)', content)
        if time_match:
            try:
                return datetime.strptime(time_match.group(1), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        
        return None


class BatchDialogueParser:
    """Parse multiple dialogue directories with different configurations"""
    
    def __init__(self):
        self.parsers = {}
    
    def add_parser(self, name: str, parser: DialogueParser):
        """Add a named parser configuration"""
        self.parsers[name] = parser
    
    def parse_all(self, directories: Dict[str, Path]) -> Dict[str, List[DialogueEntry]]:
        """Parse multiple directories with their respective parsers"""
        results = {}
        
        for dir_name, dir_path in directories.items():
            parser = self.parsers.get(dir_name, DialogueParser())
            results[dir_name] = parser.parse_directory(dir_path)
        
        return results
