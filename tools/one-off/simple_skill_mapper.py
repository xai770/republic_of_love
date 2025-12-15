#!/usr/bin/env python3
"""
Simple Skill Mapper - Fast and Reliable
========================================

Hybrid approach recommended by our LLMs:
1. Fuzzy string matching for direct matches (fast)
2. Simple LLM prompt for ambiguous cases (accurate)
3. No complex 15-turn conversations

Usage:
    echo '["Python", "SAP", "Azure"]' | python3 simple_skill_mapper.py
"""

import sys
import json
import requests
from difflib import get_close_matches
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_connection

# Ollama configuration
OLLAMA_API = "http://localhost:11434/api/generate"
MAPPING_MODEL = "qwen2.5:7b"


class SimpleSkillMapper:
    """Hybrid skill mapper using fuzzy matching + LLM"""
    
    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        self._load_taxonomy()
    
    def _load_taxonomy(self):
        """Load all taxonomy skills into memory"""
        # Load ALL skills, not just those in hierarchy
        self.cursor.execute("""
            SELECT DISTINCT skill_name
            FROM skill_aliases
            WHERE skill_name IS NOT NULL
            ORDER BY skill_name
        """)
        
        self.taxonomy_skills = []
        for row in self.cursor.fetchall():
            self.taxonomy_skills.append(row['skill_name'])
        
        # Also load hierarchy for domain context
        self.cursor.execute("""
            SELECT DISTINCT 
                child.skill_name as skill,
                parent.skill_name as domain
            FROM skill_hierarchy sh
            JOIN skill_aliases parent ON sh.parent_skill_id = parent.skill_id
            JOIN skill_aliases child ON sh.skill_id = child.skill_id
        """)
        
        self.skill_to_domain = {}
        for row in self.cursor.fetchall():
            self.skill_to_domain[row['skill']] = row['domain']
        
        print(f"[INFO] Loaded {len(self.taxonomy_skills)} taxonomy skills", file=sys.stderr)
    
    def normalize(self, text):
        """Normalize skill name for matching"""
        return text.lower().strip().replace('-', '_').replace(' ', '_')
    
    def fuzzy_match(self, skill_name, cutoff=0.8):
        """
        Try to match skill using fuzzy string matching
        
        Returns:
            - Exact taxonomy skill name if match found
            - None if no good match
        """
        normalized = self.normalize(skill_name)
        
        # Try exact match first
        for tax_skill in self.taxonomy_skills:
            if self.normalize(tax_skill) == normalized:
                return tax_skill
        
        # Try fuzzy match
        matches = get_close_matches(
            normalized, 
            [self.normalize(s) for s in self.taxonomy_skills],
            n=1,
            cutoff=cutoff
        )
        
        if matches:
            # Find original skill name
            matched_normalized = matches[0]
            for tax_skill in self.taxonomy_skills:
                if self.normalize(tax_skill) == matched_normalized:
                    return tax_skill
        
        return None
    
    def llm_match_batch(self, unmatched_skills):
        """
        Use LLM to match skills that fuzzy matching couldn't handle
        
        Simple prompt: give skills + taxonomy, ask for JSON mapping
        """
        if not unmatched_skills:
            return {}
        
        # Group taxonomy by domain for better context
        domains_text = ""
        domain_skills = {}
        
        for skill, domain in self.skill_to_domain.items():
            if domain not in domain_skills:
                domain_skills[domain] = []
            domain_skills[domain].append(skill)
        
        # Create concise domain listing
        for domain in sorted(domain_skills.keys()):
            skills = domain_skills[domain][:30]  # Limit to 30 per domain
            domains_text += f"\n{domain}: {', '.join(skills)}"
            if len(domain_skills[domain]) > 30:
                domains_text += f" ... (+{len(domain_skills[domain])-30} more)"
        
        prompt = f"""Map these extracted skills to our canonical taxonomy.

EXTRACTED SKILLS:
{json.dumps(unmatched_skills, indent=2)}

TAXONOMY SKILLS (organized by domain):
{domains_text}

RULES:
1. Return exact taxonomy SKILL names (not domain names)
2. Skills are lowercase with underscores (e.g., "sql", "python", "aws", "azure")
3. Match semantically: "SQL Server" -> "sql", "Oracle" -> "sql", "Azure" -> "azure"
4. If no good match exists, omit that skill
5. Do NOT return domain names (like "INFRASTRUCTURE_AND_CLOUD"), only skill names

Return ONLY a JSON object mapping extracted to taxonomy skills:
{{"Oracle 19c": "sql", "Python": "python", "Azure": "azure"}}

Your mapping:"""

        payload = {
            "model": MAPPING_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500}
        }
        
        try:
            response = requests.post(OLLAMA_API, json=payload, timeout=90)
            response.raise_for_status()
            result = response.json().get('response', '{}')
            
            print(f"[DEBUG] LLM response (first 500 chars): {result[:500]}", file=sys.stderr)
            
            # Extract JSON from response
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                mapping = json.loads(json_str)
                
                # Check if it's actually a mapping object (dict), not a list
                if not isinstance(mapping, dict):
                    print(f"[ERROR] LLM returned non-dict: {type(mapping)}", file=sys.stderr)
                    return {}
                
                # Validate that mapped values exist in taxonomy
                validated = {}
                for key, value in mapping.items():
                    if value in self.taxonomy_skills:
                        validated[key] = value
                        print(f"[DEBUG] Validated: '{key}' -> '{value}'", file=sys.stderr)
                    else:
                        print(f"[WARN] LLM suggested '{value}' but not in taxonomy", file=sys.stderr)
                
                return validated
            else:
                print(f"[ERROR] No JSON found in LLM response", file=sys.stderr)
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing failed: {e}", file=sys.stderr)
            print(f"[ERROR] Attempted to parse: {result[json_start:json_end][:200]}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] LLM mapping failed: {e}", file=sys.stderr)
        
        return {}
    
    def map_skills(self, raw_skills):
        """
        Map raw skills to taxonomy using hybrid approach
        
        Args:
            raw_skills: List of dicts with 'skill' key, or list of strings
            
        Returns:
            List of taxonomy skill names
        """
        # Extract skill names from input
        if raw_skills and isinstance(raw_skills[0], dict):
            skill_names = [s.get('skill', '') for s in raw_skills]
        else:
            skill_names = raw_skills
        
        matched_skills = []
        unmatched_skills = []
        
        # Phase 1: Fuzzy matching (fast)
        print(f"[INFO] Phase 1: Fuzzy matching {len(skill_names)} skills...", file=sys.stderr)
        for skill in skill_names:
            if not skill:
                continue
            
            match = self.fuzzy_match(skill)
            if match:
                matched_skills.append(match)
                print(f"[MATCH] '{skill}' -> '{match}' (fuzzy)", file=sys.stderr)
            else:
                unmatched_skills.append(skill)
                print(f"[MISS] '{skill}' - no fuzzy match", file=sys.stderr)
        
        # Phase 2: LLM matching for unmatched (accurate)
        if unmatched_skills:
            print(f"\n[INFO] Phase 2: LLM matching {len(unmatched_skills)} unmatched skills...", file=sys.stderr)
            llm_mapping = self.llm_match_batch(unmatched_skills)
            
            for skill, taxonomy_skill in llm_mapping.items():
                matched_skills.append(taxonomy_skill)
                print(f"[MATCH] '{skill}' -> '{taxonomy_skill}' (LLM)", file=sys.stderr)
        
        # Remove duplicates while preserving order
        unique_skills = []
        seen = set()
        for skill in matched_skills:
            if skill not in seen:
                unique_skills.append(skill)
                seen.add(skill)
        
        print(f"\n[RESULT] Mapped {len(unique_skills)} unique skills", file=sys.stderr)
        return unique_skills
    
    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


def main():
    """Main entry point for delegate actor execution"""
    try:
        # Read input from stdin
        input_text = sys.stdin.read().strip()
        
        # Strip markdown code fences if present
        if input_text.startswith('```json'):
            input_text = input_text[7:]  # Remove ```json
        if input_text.startswith('```'):
            input_text = input_text[3:]  # Remove ```
        if input_text.endswith('```'):
            input_text = input_text[:-3]  # Remove closing ```
        input_text = input_text.strip()
        
        # Parse input
        try:
            parsed = json.loads(input_text)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}", file=sys.stderr)
            print(f"[ERROR] Input (first 200 chars): {input_text[:200]}", file=sys.stderr)
            # Try splitting as comma-separated as fallback
            parsed = [s.strip() for s in input_text.split(',') if s.strip()]
        
        # Handle different input formats:
        # 1. Direct list of skills: ["Python", "AWS"]
        # 2. List of skill objects: [{"skill": "Python", ...}]
        # 3. Workflow input with decision key: {"decision": [...skills...]}
        if isinstance(parsed, dict):
            # Check for workflow input format with 'decision' key
            if 'decision' in parsed:
                raw_skills = parsed['decision']
                print(f"[INFO] Extracted {len(raw_skills)} skills from 'decision' key", file=sys.stderr)
            elif 'skills' in parsed:
                raw_skills = parsed['skills']
                print(f"[INFO] Extracted {len(raw_skills)} skills from 'skills' key", file=sys.stderr)
            else:
                print(f"[ERROR] Unexpected dict format, no 'decision' or 'skills' key", file=sys.stderr)
                raw_skills = []
        else:
            raw_skills = parsed
        
        # Map skills
        mapper = SimpleSkillMapper()
        taxonomy_skills = mapper.map_skills(raw_skills)
        mapper.close()
        
        # Output as JSON array
        print(json.dumps(taxonomy_skills))
        
        return 0
        
    except Exception as e:
        error = {"error": str(e)}
        print(json.dumps(error))
        return 1


if __name__ == '__main__':
    sys.exit(main())
