#!/usr/bin/env python3
"""
Update by_recipe_runner.py to use new schema names
Renames: variations → test_cases, recipes → workflows, sessions → conversations
"""

import re

# Read the file
with open('/home/xai/Documents/ty_learn/scripts/by_recipe_runner.py', 'r') as f:
    content = f.content()

# Variable renames (within code, not SQL)
replacements = [
    # Keep variation_data → test_case_data for now (will do separately)
    (r'\brecipe_run_id\b', 'workflow_run_id'),
    (r'\brecipe_session_id\b', 'conversation_step_id'),
    (r'\bsession_run_id\b', 'conversation_run_id'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Write back
with open('/home/xai/Documents/ty_learn/scripts/by_recipe_runner.py', 'w') as f:
    f.write(content)

print("✅ Updated variable names in by_recipe_runner.py")
print("   - recipe_run_id → workflow_run_id")
print("   - recipe_session_id → conversation_step_id")
print("   - session_run_id → conversation_run_id")
