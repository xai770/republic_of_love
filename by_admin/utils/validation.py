"""
Validation utilities for LLMCore Admin GUI forms
"""

import re
from typing import List, Dict, Any, Optional

def validate_facet_id(facet_id: str) -> List[str]:
    """Validate facet ID format"""
    errors = []
    
    if not facet_id:
        errors.append("Facet ID is required")
    elif not re.match(r'^[a-z0-9._-]+$', facet_id):
        errors.append("Facet ID must contain only lowercase letters, numbers, dots, underscores, and hyphens")
    elif len(facet_id) > 50:
        errors.append("Facet ID must be 50 characters or less")
    
    return errors

def validate_canonical_code(canonical_code: str) -> List[str]:
    """Validate canonical code format"""
    errors = []
    
    if not canonical_code:
        errors.append("Canonical code is required")
    elif not re.match(r'^[a-z0-9_]+$', canonical_code):
        errors.append("Canonical code must contain only lowercase letters, numbers, and underscores")
    elif len(canonical_code) > 50:
        errors.append("Canonical code must be 50 characters or less")
    
    return errors

def validate_recipe_data(recipe_data: Dict[str, Any]) -> List[str]:
    """Validate recipe form data"""
    errors = []
    
    # Required fields
    if not recipe_data.get('canonical_code'):
        errors.append("Canonical code is required")
    
    # Version validation
    version = recipe_data.get('recipe_version')
    if version is not None:
        if not isinstance(version, int) or version < 1:
            errors.append("Recipe version must be a positive integer")
    
    # Max instruction cycles
    max_cycles = recipe_data.get('max_instruction_cycles')
    if max_cycles is not None:
        if not isinstance(max_cycles, int) or max_cycles < 1 or max_cycles > 100:
            errors.append("Max instruction cycles must be between 1 and 100")
    
    return errors

def validate_session_data(session_data: Dict[str, Any]) -> List[str]:
    """Validate session form data"""
    errors = []
    
    # Required fields
    if not session_data.get('session_name'):
        errors.append("Session name is required")
    
    if not session_data.get('actor_id'):
        errors.append("Actor ID is required")
    
    # Session number validation
    session_number = session_data.get('session_number')
    if session_number is not None:
        if not isinstance(session_number, int) or session_number < 1:
            errors.append("Session number must be a positive integer")
    
    # Execution order validation
    execution_order = session_data.get('execution_order')
    if execution_order is not None:
        if not isinstance(execution_order, int) or execution_order < 1:
            errors.append("Execution order must be a positive integer")
    
    # Context strategy validation
    context_strategy = session_data.get('context_strategy')
    if context_strategy:
        valid_strategies = ['default', 'isolated', 'inherited', 'shared']
        if context_strategy not in valid_strategies:
            errors.append(f"Context strategy must be one of: {', '.join(valid_strategies)}")
    
    return errors

def validate_instruction_data(instruction_data: Dict[str, Any]) -> List[str]:
    """Validate instruction form data"""
    errors = []
    
    # Required fields
    if not instruction_data.get('step_description'):
        errors.append("Step description is required")
    
    if not instruction_data.get('prompt_template'):
        errors.append("Prompt template is required")
    
    # Step number validation
    step_number = instruction_data.get('step_number')
    if step_number is not None:
        if not isinstance(step_number, int) or step_number < 1:
            errors.append("Step number must be a positive integer")
    
    # Timeout validation
    timeout = instruction_data.get('timeout_seconds')
    if timeout is not None:
        if not isinstance(timeout, int) or timeout < 1 or timeout > 86400:
            errors.append("Timeout must be between 1 and 86400 seconds (24 hours)")
    
    # Validate prompt template variables
    prompt_template = instruction_data.get('prompt_template', '')
    if prompt_template:
        template_errors = validate_prompt_template(prompt_template)
        errors.extend(template_errors)
    
    return errors

def validate_prompt_template(template: str) -> List[str]:
    """Validate prompt template variable syntax"""
    errors = []
    
    # Find all template variables
    variables = re.findall(r'\{([^}]+)\}', template)
    
    valid_variables = {
        'variations_param_1', 'variations_param_2', 'variations_param_3',
        'step1_response', 'step2_response', 'step3_response', 'step4_response', 'step5_response',
        'previous_response', 'recipe_run_id', 'variation_id', 'batch_id'
    }
    
    for var in variables:
        if var not in valid_variables and not re.match(r'^step\d+_response$', var):
            errors.append(f"Unknown template variable: {{{var}}}")
    
    return errors

def validate_variation_data(variation_data: Dict[str, Any]) -> List[str]:
    """Validate variation form data"""
    errors = []
    
    # Parameter 1 is required
    if not variation_data.get('variations_param_1'):
        errors.append("Parameter 1 is required")
    
    # Difficulty level validation
    difficulty = variation_data.get('difficulty_level')
    if difficulty is not None:
        if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 10:
            errors.append("Difficulty level must be between 1 and 10")
    
    # Complexity score validation
    complexity = variation_data.get('complexity_score')
    if complexity is not None:
        if not isinstance(complexity, (int, float)) or complexity < 0 or complexity > 1:
            errors.append("Complexity score must be between 0.0 and 1.0")
    
    return errors

def validate_branch_data(branch_data: Dict[str, Any]) -> List[str]:
    """Validate instruction branch form data"""
    errors = []
    
    # Required fields
    if not branch_data.get('branch_condition'):
        errors.append("Branch condition is required")
    
    if not branch_data.get('condition_type'):
        errors.append("Condition type is required")
    
    # Priority validation
    priority = branch_data.get('branch_priority')
    if priority is not None:
        if not isinstance(priority, int) or priority < 1:
            errors.append("Branch priority must be a positive integer")
    
    # Condition type validation
    condition_type = branch_data.get('condition_type')
    if condition_type:
        valid_types = ['contains', 'equals', 'regex', 'length', 'numeric']
        if condition_type not in valid_types:
            errors.append(f"Condition type must be one of: {', '.join(valid_types)}")
    
    # Operator validation
    operator = branch_data.get('condition_operator')
    if operator:
        valid_operators = ['==', '!=', '>', '<', '>=', '<=', 'contains', 'not_contains', 'matches']
        if operator not in valid_operators:
            errors.append(f"Condition operator must be one of: {', '.join(valid_operators)}")
    
    return errors

def validate_file_upload(uploaded_file, allowed_extensions: List[str], max_size_mb: int = 10) -> List[str]:
    """Validate uploaded file"""
    errors = []
    
    if not uploaded_file:
        return errors
    
    # Check file extension
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in allowed_extensions:
        errors.append(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")
    
    # Check file size
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        errors.append(f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)")
    
    return errors

def is_valid_email(email: str) -> bool:
    """Check if email format is valid"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_url(url: str) -> bool:
    """Check if URL format is valid"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return re.match(pattern, url) is not None