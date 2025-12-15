#!/usr/bin/env python3
"""
Taxonomy File Writer (Turing Native)
=====================================

Writes skills to filesystem based on folder mapping from LLM.
Part of Workflow 3003 (Turing-native taxonomy maintenance).

Created: 2025-11-10
Author: Arden
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add config to path
sys.path.insert(0, '/home/xai/Documents/ty_learn')
from config.paths import SKILLS_TAXONOMY_DIR

# Base directory for taxonomy
TAXONOMY_DIR = SKILLS_TAXONOMY_DIR

def sanitize_filename(name):
    """Convert skill name to valid filename"""
    if not name:
        return "unnamed"
    sanitized = str(name).lower().replace(' ', '_')
    sanitized = sanitized.replace('/', '_').replace('\\', '_')
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c in '_-.')
    return sanitized.strip('_') or "unnamed"

def write_skill_file(skill, file_path):
    """
    Write a single skill .md file
    
    Args:
        skill: Dict with skill_id, skill_name, description, aliases, parent_skill_id
        file_path: Path object for the target file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure parent directories exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build markdown content
        content = []
        content.append(f"# {skill['skill_name']}")
        content.append("")
        
        if skill.get('description'):
            content.append(f"**Description:** {skill['description']}")
            content.append("")
        
        if skill.get('aliases'):
            aliases_str = ", ".join(skill['aliases'])
            content.append(f"**Also known as:** {aliases_str}")
            content.append("")
        
        content.append(f"**Skill ID:** {skill['skill_id']}")
        
        if skill.get('parent_skill_id'):
            content.append(f"**Parent Skill ID:** {skill['parent_skill_id']}")
        
        content.append("")
        content.append(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        return True
        
    except Exception as e:
        print(f"ERROR writing {file_path}: {e}", file=sys.stderr)
        return False

def main():
    """
    Main entry point
    
    Expects JSON input via stdin with:
    - skills_json: Array of skill objects
    - folder_mapping: Dict with skill_paths mapping
    """
    
    print("=" * 60)
    print("TAXONOMY FILE WRITER (Turing Native)")
    print("=" * 60)
    
    try:
        # Read JSON from stdin (Turing passes it this way)
        input_data = sys.stdin.read()
        
        if not input_data.strip():
            print("ERROR: No input data received", file=sys.stderr)
            return 1
        
        data = json.loads(input_data)
        
        skills = data.get('skills_json', [])
        folder_mapping = data.get('folder_mapping', {})
        skill_paths = folder_mapping.get('skill_paths', {})
        
        if not skills:
            print("ERROR: No skills data provided", file=sys.stderr)
            return 1
        
        if not skill_paths:
            print("ERROR: No folder mapping provided", file=sys.stderr)
            return 1
        
        print(f"\nProcessing {len(skills)} skills...")
        print(f"Target directory: {TAXONOMY_DIR}")
        
        # Clear existing taxonomy directory
        if TAXONOMY_DIR.exists():
            import shutil
            shutil.rmtree(TAXONOMY_DIR)
            print(f"Cleared existing taxonomy directory")
        
        TAXONOMY_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create skills dictionary for quick lookup
        skills_dict = {str(s['skill_id']): s for s in skills}
        
        # Write each skill to its designated path
        success_count = 0
        error_count = 0
        
        for skill_id_str, relative_path in skill_paths.items():
            skill = skills_dict.get(skill_id_str)
            
            if not skill:
                print(f"WARNING: Skill ID {skill_id_str} not found in skills data")
                error_count += 1
                continue
            
            file_path = TAXONOMY_DIR / relative_path
            
            if write_skill_file(skill, file_path):
                success_count += 1
            else:
                error_count += 1
        
        # Generate summary
        print("\n" + "=" * 60)
        print("RESULTS:")
        print("=" * 60)
        print(f"✅ Successfully written: {success_count} files")
        print(f"❌ Errors: {error_count} files")
        print(f"📁 Total folders: {len(list(TAXONOMY_DIR.rglob('*/')))}")
        print(f"📄 Total files: {len(list(TAXONOMY_DIR.rglob('*.md')))}")
        
        # Output JSON result for Turing
        result = {
            "success": error_count == 0,
            "files_written": success_count,
            "errors": error_count,
            "total_folders": len(list(TAXONOMY_DIR.rglob('*/'))),
            "total_files": len(list(TAXONOMY_DIR.rglob('*.md'))),
            "timestamp": datetime.now().isoformat()
        }
        
        print("\nJSON_OUTPUT_START")
        print(json.dumps(result, indent=2))
        print("JSON_OUTPUT_END")
        
        return 0 if error_count == 0 else 1
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
