#!/usr/bin/env python3
"""
Fix column order in CREATE TABLE statements: xxx_id first, xxx_name second
"""

import re
import sys

# Table definitions with column order fixes
TABLE_FIXES = {
    'actors': {
        'id_col': 'actor_id',
        'name_col': 'actor_name',
        'first_cols': ['actor_id', 'actor_name']
    },
    'capabilities': {
        'id_col': 'capability_id',
        'name_col': 'capability_name',
        'first_cols': ['capability_id', 'capability_name']
    },
    'canonicals': {
        'id_col': 'canonical_id',
        'name_col': 'canonical_name',
        'first_cols': ['canonical_id', 'canonical_name']
    },
    'postings': {
        'id_col': 'posting_id',
        'name_col': 'posting_name',
        'first_cols': ['posting_id', 'posting_name']
    },
    'profiles': {
        'id_col': 'profile_id',
        'name_col': 'full_name',  # profiles uses full_name not profile_name
        'first_cols': ['profile_id', 'full_name']
    },
    'skill_aliases': {
        'id_col': 'skill_id',
        'name_col': 'skill_name',
        'first_cols': ['skill_id', 'skill_name']
    },
    'skills_pending_taxonomy': {
        'id_col': 'pending_skill_id',
        'name_col': 'raw_skill_name',
        'first_cols': ['pending_skill_id', 'raw_skill_name']
    },
    'schema_documentation': {
        'id_col': 'documentation_id',
        'name_col': 'table_name',
        'first_cols': ['documentation_id', 'table_name']
    }
}


def extract_column_definition(lines, col_name):
    """Extract a column definition (may span multiple lines for constraints)"""
    for i, line in enumerate(lines):
        if line.strip().startswith(col_name + ' '):
            # Found the column, extract it (may span multiple lines)
            col_lines = [line]
            # Check if this column def continues (doesn't end with comma)
            if not line.rstrip().endswith(','):
                # Look ahead for continuation
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    col_lines.append(next_line)
                    if next_line.rstrip().endswith(','):
                        break
                    j += 1
            return ''.join(col_lines), i, i + len(col_lines)
    return None, -1, -1


def fix_table_columns(sql_content, table_name, fix_config):
    """Reorder columns in a CREATE TABLE statement"""
    # Find the CREATE TABLE statement
    pattern = rf'CREATE TABLE public\.{table_name} \('
    match = re.search(pattern, sql_content)
    if not match:
        print(f"Warning: Table {table_name} not found", file=sys.stderr)
        return sql_content
    
    # Find the end of the CREATE TABLE statement
    start_pos = match.end()
    paren_count = 1
    end_pos = start_pos
    
    while end_pos < len(sql_content) and paren_count > 0:
        char = sql_content[end_pos]
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        end_pos += 1
    
    # Extract the table definition
    table_header = sql_content[match.start():start_pos]
    table_body = sql_content[start_pos:end_pos-1]  # Exclude final )
    table_footer = sql_content[end_pos-1:]  # Include ); and rest
    
    # Split table body into lines
    lines = table_body.strip().split('\n')
    
    # Separate column definitions from constraints
    column_defs = []
    constraint_defs = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('CONSTRAINT ') or stripped.startswith('CHECK '):
            constraint_defs.append(line)
        elif stripped and not stripped.startswith('--'):
            column_defs.append(line)
    
    # Build column dict
    columns = {}
    i = 0
    while i < len(column_defs):
        line = column_defs[i].strip()
        if not line:
            i += 1
            continue
        
        # Extract column name (first word)
        col_name = line.split()[0]
        columns[col_name] = column_defs[i]
        i += 1
    
    # Reorder: first_cols first, then rest
    first_cols = fix_config['first_cols']
    new_order = []
    
    # Add the priority columns first
    for col in first_cols:
        if col in columns:
            new_order.append(columns[col])
            del columns[col]
    
    # Add remaining columns
    for col_name in sorted(columns.keys()):
        new_order.append(columns[col_name])
    
    # Add constraints at the end
    new_order.extend(constraint_defs)
    
    # Ensure proper comma placement
    for i in range(len(new_order)):
        line = new_order[i].rstrip()
        if i < len(new_order) - 1:
            # Not the last line, should have comma
            if not line.endswith(','):
                new_order[i] = line + ','
        else:
            # Last line, should NOT have comma
            if line.endswith(','):
                new_order[i] = line[:-1]
    
    # Rebuild table definition
    new_body = '\n'.join(new_order)
    new_table = table_header + '\n' + new_body + '\n' + table_footer
    
    # Replace in original content
    return sql_content[:match.start()] + new_table


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/base_yoga_schema_current.sql'
    output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/base_yoga_schema_fixed.sql'
    
    print(f"Reading {input_file}...")
    with open(input_file, 'r') as f:
        content = f.read()
    
    print(f"Original size: {len(content)} bytes")
    
    # Fix each table
    for table_name, fix_config in TABLE_FIXES.items():
        print(f"Fixing {table_name}...")
        content = fix_table_columns(content, table_name, fix_config)
    
    print(f"Writing {output_file}...")
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Fixed size: {len(content)} bytes")
    print("Done!")


if __name__ == '__main__':
    main()
