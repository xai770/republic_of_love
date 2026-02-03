"""
Actor Schema Extraction
=======================

Auto-extract input/output schema from thick actor files.

Actors can declare schema in their docstrings using a simple format:

Input:  postings.posting_id (via work_query)
Output: postings.extracted_requirements, postings.source_language

Or with type hints:

Output Fields:
    - posting_id: int - The posting that was processed
    - requirements_count: int - Number of verified requirements
    - success: bool - Whether extraction succeeded
    
This module provides utilities to:
1. Parse schema from actor docstrings
2. Generate JSON Schema from actor metadata
3. Validate actor outputs against declared schema
4. Auto-generate RAQ config suggestions

Usage:
    from core.actor_schema import extract_schema, validate_output
    
    schema = extract_schema('/path/to/actors/postings__extracted_requirements_U.py')
    # Returns: {
    #     'input': {'table': 'postings', 'columns': ['posting_id']},
    #     'output': {'table': 'postings', 'columns': ['extracted_requirements', 'source_language']},
    #     'output_fields': [
    #         {'name': 'posting_id', 'type': 'int', 'description': '...'},
    #         ...
    #     ]
    # }
    
    errors = validate_output(schema, {'success': True, 'posting_id': 123})
    # Returns: [] or list of validation errors

Author: Arden (GitHub Copilot)
Date: 2026-01-08
"""

import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def extract_schema(actor_path: str) -> Dict[str, Any]:
    """
    Extract schema metadata from an actor file.
    
    Looks for patterns in the module docstring:
    - Input:  table.column (via work_query)
    - Output: table.column1, table.column2
    - Output Fields: ... (structured field list)
    
    Also inspects the actor class for TASK_TYPE_ID and other metadata.
    
    Args:
        actor_path: Path to the actor .py file
        
    Returns:
        Dict with 'input', 'output', 'output_fields', 'task_type_id', 'actor_class_name'
    """
    path = Path(actor_path)
    if not path.exists():
        raise FileNotFoundError(f"Actor file not found: {actor_path}")
    
    content = path.read_text()
    
    schema = {
        'actor_path': str(path),
        'actor_name': path.stem,
        'input': None,
        'output': None,
        'output_fields': [],
        'task_type_id': None,
        'actor_class_name': None,
    }
    
    # Extract module docstring
    docstring = _extract_module_docstring(content)
    if docstring:
        schema['input'] = _parse_io_line(docstring, 'Input')
        schema['output'] = _parse_io_line(docstring, 'Output')
        schema['output_fields'] = _parse_output_fields(docstring)
    
    # Extract TASK_TYPE_ID and actor class
    schema['task_type_id'] = _extract_task_type_id(content)
    schema['actor_class_name'] = _extract_actor_class_name(content)
    
    return schema


def validate_output(schema: Dict[str, Any], output: Dict[str, Any]) -> List[str]:
    """
    Validate an actor output against its declared schema.
    
    Args:
        schema: Schema dict from extract_schema()
        output: Actor output dict
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check output_fields if declared
    for field in schema.get('output_fields', []):
        name = field.get('name')
        expected_type = field.get('type', 'any')
        
        if name not in output:
            # 'success' is always required
            if name == 'success':
                errors.append(f"Missing required field: {name}")
            continue
        
        value = output[name]
        
        # Type validation
        if expected_type == 'int' and not isinstance(value, int):
            errors.append(f"Field '{name}' expected int, got {type(value).__name__}")
        elif expected_type == 'str' and not isinstance(value, str):
            errors.append(f"Field '{name}' expected str, got {type(value).__name__}")
        elif expected_type == 'bool' and not isinstance(value, bool):
            errors.append(f"Field '{name}' expected bool, got {type(value).__name__}")
        elif expected_type == 'list' and not isinstance(value, list):
            errors.append(f"Field '{name}' expected list, got {type(value).__name__}")
        elif expected_type == 'dict' and not isinstance(value, dict):
            errors.append(f"Field '{name}' expected dict, got {type(value).__name__}")
    
    return errors


def suggest_raq_config(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Suggest RAQ config based on extracted schema.
    
    Args:
        schema: Schema dict from extract_schema()
        
    Returns:
        Suggested raq_config dict
    """
    config = {
        'state_tables': [],
        'compare_output_field': "output->>'success'"
    }
    
    # If output table is declared, suggest it as state_table
    if schema.get('output'):
        output_info = schema['output']
        if output_info.get('table'):
            config['state_tables'].append({
                'table': output_info['table'],
                'filter': '1=1',  # User should customize
                'columns': output_info.get('columns', [])
            })
    
    return config


def to_json_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert actor schema to JSON Schema format.
    
    Args:
        schema: Schema dict from extract_schema()
        
    Returns:
        JSON Schema dict
    """
    json_schema = {
        'type': 'object',
        'properties': {},
        'required': []
    }
    
    type_mapping = {
        'int': {'type': 'integer'},
        'str': {'type': 'string'},
        'bool': {'type': 'boolean'},
        'list': {'type': 'array'},
        'dict': {'type': 'object'},
        'any': {},
    }
    
    for field in schema.get('output_fields', []):
        name = field.get('name')
        field_type = field.get('type', 'any')
        description = field.get('description', '')
        
        prop = type_mapping.get(field_type, {}).copy()
        if description:
            prop['description'] = description
        
        json_schema['properties'][name] = prop
        
        # Mark 'success' as required
        if name == 'success':
            json_schema['required'].append(name)
    
    return json_schema


# =============================================================================
# PRIVATE HELPERS
# =============================================================================

def _extract_module_docstring(content: str) -> Optional[str]:
    """Extract the module-level docstring from Python source."""
    try:
        tree = ast.parse(content)
        return ast.get_docstring(tree)
    except SyntaxError:
        return None


def _parse_io_line(docstring: str, prefix: str) -> Optional[Dict[str, Any]]:
    """
    Parse an Input: or Output: line from docstring.
    
    Examples:
        Input:  postings.posting_id (via work_query)
        Output: postings.extracted_requirements, postings.source_language
    """
    pattern = rf'^{prefix}:\s*(.+?)(?:\n|$)'
    match = re.search(pattern, docstring, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    
    line = match.group(1).strip()
    
    # Remove trailing comments like "(via work_query)"
    line = re.sub(r'\s*\(.*\)\s*$', '', line)
    
    # Parse table.column format
    parts = [p.strip() for p in line.split(',')]
    
    result = {'columns': [], 'table': None}
    
    for part in parts:
        if '.' in part:
            table, column = part.split('.', 1)
            if result['table'] is None:
                result['table'] = table.strip()
            result['columns'].append(column.strip())
        else:
            result['columns'].append(part)
    
    return result


def _parse_output_fields(docstring: str) -> List[Dict[str, Any]]:
    """
    Parse Output Fields block from docstring.
    
    Format:
        Output Fields:
            - field_name: type - Description
            - other_field: str - Another desc
    """
    fields = []
    
    # Find "Output Fields:" section
    pattern = r'Output Fields:\s*\n((?:\s*-[^\n]+\n?)+)'
    match = re.search(pattern, docstring, re.IGNORECASE)
    if not match:
        return fields
    
    block = match.group(1)
    
    # Parse each line
    line_pattern = r'^\s*-\s*(\w+):\s*(\w+)(?:\s*-\s*(.*))?$'
    for line in block.split('\n'):
        line_match = re.match(line_pattern, line.strip())
        if line_match:
            fields.append({
                'name': line_match.group(1),
                'type': line_match.group(2),
                'description': line_match.group(3) or ''
            })
    
    return fields


def _extract_task_type_id(content: str) -> Optional[int]:
    """Extract TASK_TYPE_ID constant from source."""
    match = re.search(r'TASK_TYPE_ID\s*=\s*(\d+)', content)
    if match:
        return int(match.group(1))
    return None


def _extract_actor_class_name(content: str) -> Optional[str]:
    """Extract the actor class name (class with process method)."""
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == 'process':
                        return node.name
    except SyntaxError:
        pass
    return None


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import json
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python actor_schema.py <actor_file.py>")
        print("\nExamples:")
        print("  python core/actor_schema.py actors/postings__extracted_requirements_U.py")
        sys.exit(1)
    
    actor_path = sys.argv[1]
    
    try:
        schema = extract_schema(actor_path)
        print(f"\n🔍 Schema for {schema['actor_name']}:")
        print(f"   Class: {schema['actor_class_name']}")
        print(f"   Task Type ID: {schema['task_type_id']}")
        print(f"\n   Input: {schema['input']}")
        print(f"   Output: {schema['output']}")
        
        if schema['output_fields']:
            print("\n   Output Fields:")
            for f in schema['output_fields']:
                print(f"     - {f['name']}: {f['type']} - {f['description']}")
        
        print("\n   Suggested RAQ Config:")
        raq = suggest_raq_config(schema)
        print(f"   {json.dumps(raq, indent=2)}")
        
        print("\n   JSON Schema:")
        js = to_json_schema(schema)
        print(f"   {json.dumps(js, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
