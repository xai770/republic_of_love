#!/usr/bin/env python3
"""
Utility functions for the requirements extraction system.

This module contains helper functions used across the requirements extraction
and validation modules.

Author: Investigation Team
Date: 2025-07-08
Version: 2.0
"""

import re
from typing import Dict, Any, List, Set


def normalize_text(text: str) -> str:
    """
    Normalize text for better pattern matching.
    
    Args:
        text: Raw text to normalize
        
    Returns:
        Normalized text with consistent spacing
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_context(text: str, start: int, end: int, window: int = 150) -> str:
    """
    Get context around a match.
    
    Args:
        text: Full text
        start: Start position of match
        end: End position of match
        window: Context window size in characters
        
    Returns:
        Context string around the match
    """
    context_start = max(0, start - window)
    context_end = min(len(text), end + window)
    return text[context_start:context_end]


def determine_proficiency(context: str) -> str:
    """
    Determine proficiency level from context.
    
    Args:
        context: Context string around a skill mention
        
    Returns:
        Proficiency level: "basic", "intermediate", "advanced", "expert"
    """
    context_lower = context.lower()
    if any(word in context_lower for word in ['expert', 'fortgeschritten', 'senior', 'spezialist']):
        return 'expert'
    elif any(word in context_lower for word in ['gut', 'good', 'solid', 'fundiert', 'profound']):
        return 'advanced'
    elif any(word in context_lower for word in ['basic', 'grundlagen', 'kenntnis', 'knowledge']):
        return 'intermediate'
    else:
        return 'intermediate'  # Default


def is_mandatory(context: str) -> bool:
    """
    Determine if requirement is mandatory from context.
    
    Args:
        context: Context string around a requirement
        
    Returns:
        True if requirement appears mandatory, False otherwise
    """
    context_lower = context.lower()
    mandatory_indicators = ['muss', 'required', 'erforderlich', 'zwingend', 'notwendig']
    optional_indicators = ['wünschenswert', 'preferred', 'von vorteil', 'nice to have', 'idealerweise']
    
    if any(word in context_lower for word in mandatory_indicators):
        return True
    elif any(word in context_lower for word in optional_indicators):
        return False
    else:
        return True  # Default to mandatory


def extract_years_from_context(context: str) -> int:
    """
    Extract years of experience from context.
    
    Args:
        context: Context string that may contain years
        
    Returns:
        Number of years found, or 0 if none found
    """
    # Try German pattern first
    years_match = re.search(r'(\d+)\+?\s*Jahre?', context, re.IGNORECASE)
    if not years_match:
        # Try English pattern
        years_match = re.search(r'(\d+)\+?\s*years?', context, re.IGNORECASE)
    
    return int(years_match.group(1)) if years_match else 0


def deduplicate_skills(skills: List[str]) -> List[str]:
    """
    Deduplicate skills by normalizing and removing duplicates.
    
    Args:
        skills: List of skill strings
        
    Returns:
        Deduplicated list of skills
    """
    seen = set()
    result = []
    
    for skill in skills:
        normalized = skill.lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            result.append(skill)
    
    return result


def consolidate_education_requirements(requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Consolidate duplicate education requirements.
    
    Args:
        requirements: List of education requirement dictionaries
        
    Returns:
        Consolidated list with duplicates merged
    """
    if not requirements:
        return []
    
    # Group by level and field
    grouped = {}
    for req in requirements:
        key = (req.get('level', '').lower(), req.get('field', '').lower())
        if key not in grouped:
            grouped[key] = req
        else:
            # Merge alternatives
            existing = grouped[key]
            existing_alts = set(existing.get('alternatives', []))
            new_alts = set(req.get('alternatives', []))
            existing['alternatives'] = list(existing_alts.union(new_alts))
            
            # Take highest confidence
            existing['confidence'] = max(existing.get('confidence', 0), req.get('confidence', 0))
            
            # Mandatory if any is mandatory
            existing['is_mandatory'] = existing.get('is_mandatory', False) or req.get('is_mandatory', False)
    
    return list(grouped.values())


def consolidate_business_requirements(requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Consolidate duplicate business requirements.
    
    Args:
        requirements: List of business requirement dictionaries
        
    Returns:
        Consolidated list with duplicates merged
    """
    if not requirements:
        return []
    
    # Group by domain and experience_type
    grouped = {}
    for req in requirements:
        key = (req.get('domain', '').lower(), req.get('experience_type', '').lower())
        if key not in grouped:
            grouped[key] = req
        else:
            # Merge by taking the highest years requirement and confidence
            existing = grouped[key]
            existing['years_required'] = max(existing.get('years_required', 0), req.get('years_required', 0))
            existing['confidence'] = max(existing.get('confidence', 0), req.get('confidence', 0))
            
            # Mandatory if any is mandatory
            existing['is_mandatory'] = existing.get('is_mandatory', False) or req.get('is_mandatory', False)
            
            # Combine contexts
            existing_context = existing.get('context', '')
            new_context = req.get('context', '')
            if new_context and new_context not in existing_context:
                existing['context'] = f"{existing_context}; {new_context}"
    
    return list(grouped.values())


def group_soft_skills(skills: List[str]) -> Dict[str, List[str]]:
    """
    Group related soft skills together.
    
    Args:
        skills: List of soft skill strings
        
    Returns:
        Dictionary mapping skill groups to lists of related skills
    """
    skill_groups = {
        'communication': ['communication', 'kommunikation', 'presentation', 'verbal', 'written', 'schriftlich'],
        'teamwork': ['teamwork', 'zusammenarbeit', 'collaboration', 'cooperative', 'team'],
        'analytical': ['analytical', 'analysis', 'analyse', 'konzeptionell', 'logical', 'analytisch'],
        'initiative': ['initiative', 'eigeninitiative', 'proaktiv', 'proactive', 'self-motivated'],
        'problem_solving': ['lösungsorientierung', 'problem solving', 'problemlösung', 'troubleshooting'],
        'leadership': ['führung', 'leadership', 'management', 'mentor', 'guide', 'leitung'],
        'flexibility': ['flexibilität', 'flexibility', 'adaptability', 'anpassungsfähigkeit'],
        'creativity': ['kreativität', 'creativity', 'innovation', 'innovative', 'kreativ'],
        'organization': ['organisation', 'organization', 'strukturiert', 'structured', 'planning'],
        'customer_service': ['kundenservice', 'customer service', 'client facing', 'kundenorientiert']
    }
    
    grouped = {}
    unmatched = []
    
    for skill in skills:
        skill_lower = skill.lower().strip()
        matched = False
        
        for group, keywords in skill_groups.items():
            if any(keyword in skill_lower for keyword in keywords):
                if group not in grouped:
                    grouped[group] = []
                grouped[group].append(skill)
                matched = True
                break
        
        if not matched:
            unmatched.append(skill)
    
    # Add unmatched skills as their own groups
    for skill in unmatched:
        grouped[skill.lower().replace(' ', '_')] = [skill]
    
    return grouped
