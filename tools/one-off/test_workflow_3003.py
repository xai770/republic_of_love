#!/usr/bin/env python3
"""
Test Workflow 3003 (Turing-Native Taxonomy Maintenance)
========================================================

Tests the LLM-driven recursive taxonomy maintenance workflow.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.workflow_executor import WorkflowExecutor

def test_workflow_3003():
    """Test Workflow 3003 via WorkflowExecutor"""
    
    print("=" * 70)
    print("🔥 TESTING WORKFLOW 3003 (Turing-Native Taxonomy Maintenance)")
    print("=" * 70)
    
    # Initialize executor
    executor = WorkflowExecutor()
    
    # Test data for workflow 3003
    test_data = {
        'taxonomy_trigger': {
            'reason': 'A/B testing - comparing with Workflow 3002',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    
    print(f"\n📋 Test Input:")
    print(f"   Reason: {test_data['taxonomy_trigger']['reason']}")
    print(f"   Timestamp: {test_data['taxonomy_trigger']['timestamp']}")
    
    start = time.time()
    
    print(f"\n🚀 Starting Workflow 3003...")
    print(f"   Workflow will:")
    print(f"   1. Query all skills from DB (LLM)")
    print(f"   2. Analyze and propose taxonomy structure (LLM)")
    print(f"   3. Create folder mapping (LLM)")
    print(f"   4. Check thresholds and recurse if needed (LLM, max 20x)")
    print(f"   5. Write files to filesystem (script)")
    print(f"   6. Generate INDEX.md (LLM)")
    print()
    
    try:
        # Execute workflow
        result = executor.execute_workflow(
            workflow_id=3003,
            initial_variables=test_data
        )
        
        elapsed = time.time() - start
        
        print("\n" + "=" * 70)
        print("📊 WORKFLOW 3003 RESULTS:")
        print("=" * 70)
        
        if result.get('status') == 'completed':
            print(f"Status: ✅ SUCCESS")
            print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
            
            # Count conversations executed
            if 'conversation_results' in result:
                conv_count = len(result['conversation_results'])
                print(f"Conversations executed: {conv_count}")
                
                # Check for recursion
                organize_count = sum(1 for c in result['conversation_results'] 
                                   if 'organize' in c.get('conversation_name', '').lower())
                if organize_count > 1:
                    print(f"🔄 Recursive organization: {organize_count} iterations")
            
            print("\n📁 Output:")
            check_taxonomy_output()
            
        else:
            print(f"Status: ❌ FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return False
        
        print("=" * 70)
        return True
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ EXCEPTION after {elapsed:.1f}s:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_taxonomy_output():
    """Check the output of taxonomy maintenance"""
    from pathlib import Path
    
    taxonomy_dir = Path('/home/xai/Documents/ty_learn/skills_taxonomy')
    index_file = taxonomy_dir / 'INDEX.md'
    
    if not taxonomy_dir.exists():
        print("   ❌ skills_taxonomy/ directory not found")
        return
    
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
        print(f"   ⚠️  INDEX.md not found")

def main():
    print("\n🧪 WORKFLOW 3003 TEST")
    print("=" * 70)
    
    success = test_workflow_3003()
    
    print("\n" + "=" * 70)
    print("🏁 TEST COMPLETE")
    print("=" * 70)
    
    if success:
        print("✅ Workflow 3003: PASSED")
    else:
        print("❌ Workflow 3003: FAILED")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
