#!/usr/bin/env python3
"""
Generate Taxonomy Index
========================

Traverses skills_taxonomy/ directory and creates INDEX.md with hierarchical navigation.

Created: 2025-11-10
Author: Arden
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add config to path
sys.path.insert(0, '/home/xai/Documents/ty_learn')
from config.paths import SKILLS_TAXONOMY_DIR

# Directory to index
TAXONOMY_DIR = SKILLS_TAXONOMY_DIR
INDEX_FILE = TAXONOMY_DIR / 'INDEX.md'

def count_items(path):
    """Count files and folders in a directory tree"""
    files = 0
    folders = 0
    for root, dirs, filenames in os.walk(path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        folders += len(dirs)
        files += len([f for f in filenames if f.endswith('.md') and f != 'INDEX.md'])
    return files, folders

def generate_tree(path, prefix='', is_last=True, depth=0, max_depth=None):
    """
    Generate tree structure with proper indentation and connectors.
    
    Args:
        path: Directory path to traverse
        prefix: Current line prefix for tree drawing
        is_last: Whether this is the last item in parent
        depth: Current depth level
        max_depth: Maximum depth to traverse (None for unlimited)
    
    Returns:
        List of markdown lines
    """
    lines = []
    
    # Stop if max depth reached
    if max_depth is not None and depth >= max_depth:
        return lines
    
    # Get all items (folders and .md files, excluding INDEX.md)
    try:
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        items = [item for item in items if not item.name.startswith('.')]
        items = [item for item in items if item.is_dir() or (item.suffix == '.md' and item.name != 'INDEX.md')]
    except PermissionError:
        return lines
    
    for idx, item in enumerate(items):
        is_last_item = (idx == len(items) - 1)
        
        # Tree connector
        if is_last_item:
            connector = '└── '
            extension = '    '
        else:
            connector = '├── '
            extension = '│   '
        
        # Format item name
        if item.is_dir():
            # Count items in this folder
            files, folders = count_items(item)
            display_name = f"**{item.name}/** ({files} skills, {folders} subfolders)"
        else:
            # Markdown file - make it a link
            skill_name = item.stem
            relative_path = item.relative_to(TAXONOMY_DIR)
            display_name = f"[{skill_name}]({relative_path})"
        
        lines.append(f"{prefix}{connector}{display_name}")
        
        # Recurse into directories
        if item.is_dir():
            new_prefix = prefix + extension
            lines.extend(generate_tree(item, new_prefix, is_last_item, depth + 1, max_depth))
    
    return lines

def generate_index():
    """Generate INDEX.md for skills_taxonomy/"""
    
    if not TAXONOMY_DIR.exists():
        print(f"ERROR: {TAXONOMY_DIR} does not exist")
        return False
    
    # Count total items
    total_files, total_folders = count_items(TAXONOMY_DIR)
    
    # Generate tree
    tree_lines = generate_tree(TAXONOMY_DIR, prefix='', depth=0, max_depth=None)
    
    # Build INDEX.md content
    content = [
        "# Skills Taxonomy - Hierarchical Index",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Skills:** {total_files}",
        f"**Total Folders:** {total_folders}",
        "",
        "---",
        "",
        "## Navigation",
        "",
    ]
    
    content.extend(tree_lines)
    
    content.extend([
        "",
        "---",
        "",
        "## About This Taxonomy",
        "",
        "This skills taxonomy is automatically maintained by **Turing Workflow 3002**:",
        "",
        "1. **Export**: Skills extracted from database → `.md` files",
        "2. **Organize**: AI-driven infinite-depth semantic organization",
        "3. **Index**: This navigation file generated automatically",
        "",
        "The taxonomy uses **content-driven depth** - no arbitrary folder limits.",
        "Organization is based on semantic relationships analyzed by AI.",
        "",
        f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ])
    
    # Write INDEX.md
    try:
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        print(f"✅ INDEX.md generated successfully")
        print(f"   Location: {INDEX_FILE}")
        print(f"   Total skills: {total_files}")
        print(f"   Total folders: {total_folders}")
        print(f"   Tree depth: {len(tree_lines)} lines")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to write INDEX.md: {e}")
        return False

def main():
    """Main entry point"""
    print("=" * 60)
    print("TAXONOMY INDEX GENERATOR")
    print("=" * 60)
    
    success = generate_index()
    
    if success:
        print("\n✅ Index generation complete")
        return 0
    else:
        print("\n❌ Index generation failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
