#!/usr/bin/env python3
"""
Test Workflow 3002 and 3003 A/B Comparison
===========================================

Simple test runner for taxonomy maintenance workflows.
"""

import time
import subprocess
import sys

def run_workflow_3002():
    """Run Workflow 3002 (script-heavy)"""
    print("=" * 70)
    print("🔥 TESTING WORKFLOW 3002 (Script-Heavy Taxonomy Maintenance)")
    print("=" * 70)
    
    start = time.time()
    
    # Step 1: Export skills from database
    print("\n📤 Step 1/3: Exporting skills from database...")
    result1 = subprocess.run(
        ['python3', 'tools/rebuild_skills_taxonomy.py'],
        capture_output=True,
        text=True
    )
    
    if result1.returncode != 0:
        print(f"❌ Export failed: {result1.stderr}")
        return False
    
    print("✅ Export complete")
    
    # Step 2: Organize taxonomy with AI
    print("\n🤖 Step 2/3: Organizing taxonomy with infinite-depth AI...")
    result2 = subprocess.run(
        ['python3', 'tools/multi_round_organize.py', 
         '--folder-threshold', '15',
         '--file-threshold', '25',
         '--max-iterations', '20'],
        capture_output=True,
        text=True
    )
    
    if result2.returncode != 0:
        print(f"❌ Organization failed: {result2.stderr}")
        return False
    
    print("✅ Organization complete")
    
    # Step 3: Generate index
    print("\n📑 Step 3/3: Generating INDEX.md...")
    result3 = subprocess.run(
        ['python3', 'tools/generate_taxonomy_index.py'],
        capture_output=True,
        text=True
    )
    
    if result3.returncode != 0:
        print(f"❌ Index generation failed: {result3.stderr}")
        return False
    
    print("✅ Index generation complete")
    
    elapsed = time.time() - start
    
    print("\n" + "=" * 70)
    print("📊 WORKFLOW 3002 RESULTS:")
    print("=" * 70)
    print(f"Status: ✅ SUCCESS")
    print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Avg per step: {elapsed/3:.1f}s")
    print("=" * 70)
    
    return True

def check_taxonomy_output():
    """Check the output of taxonomy maintenance"""
    import os
    from pathlib import Path
    
    taxonomy_dir = Path('/home/xai/Documents/ty_learn/skills_taxonomy')
    index_file = taxonomy_dir / 'INDEX.md'
    
    print("\n📁 Checking output...")
    
    if not taxonomy_dir.exists():
        print("❌ skills_taxonomy/ directory not found")
        return False
    
    md_files = list(taxonomy_dir.rglob('*.md'))
    folders = [d for d in taxonomy_dir.rglob('*') if d.is_dir()]
    
    print(f"   📄 Total .md files: {len(md_files)}")
    print(f"   📁 Total folders: {len(folders)}")
    
    if index_file.exists():
        with open(index_file) as f:
            index_content = f.read()
            if 'Skills Taxonomy' in index_content:
                print(f"   ✅ INDEX.md exists and valid")
            else:
                print(f"   ⚠️  INDEX.md exists but may be invalid")
    else:
        print(f"   ❌ INDEX.md not found")
    
    return True

def main():
    print("\n🧪 A/B TESTING TAXONOMY MAINTENANCE WORKFLOWS")
    print("=" * 70)
    
    # Test Workflow 3002
    success_3002 = run_workflow_3002()
    
    if success_3002:
        check_taxonomy_output()
    
    print("\n" + "=" * 70)
    print("🏁 TEST COMPLETE")
    print("=" * 70)
    
    if success_3002:
        print("✅ Workflow 3002: PASSED")
        print("\n💡 NOTE: Workflow 3003 requires TuringOrchestrator execution")
        print("   Use: orchestrator.execute_workflow(3003, {...})")
    else:
        print("❌ Workflow 3002: FAILED")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
