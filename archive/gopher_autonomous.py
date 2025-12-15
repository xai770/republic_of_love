#!/usr/bin/env python3
"""
GOPHER AUTONOMOUS: LLM-Guided Recursive Taxonomy Builder
Transforms chaos into hierarchy through autonomous AI navigation
"""

import json
import requests
import sys
from datetime import datetime
from pathlib import Path

# Configuration
MODEL = "qwen2.5:7b"
OLLAMA_API = "http://localhost:11434/api/generate"
MAX_DEPTH = 6
BRANCHES_PER_LEVEL = 3

def ask_llm(conversation_history, prompt):
    """Send prompt to LLM and get clean text response"""
    
    full_prompt = conversation_history + f"\n\nUSER: {prompt}\n\nASSISTANT:"
    
    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 500
        }
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return ""

def extract_numbered_items(text):
    """Extract items from numbered list"""
    items = []
    for line in text.split('\n'):
        line = line.strip()
        if line and line[0].isdigit() and '.' in line:
            # Extract "1. Category Name - explanation"
            parts = line.split('.', 1)
            if len(parts) > 1:
                item = parts[1].strip()
                # Remove explanation after hyphen
                if ' - ' in item:
                    item = item.split(' - ')[0].strip()
                if item and len(item) < 100:  # Sanity check
                    items.append(item)
    return items

def is_leaf_node(response):
    """Check if LLM indicates this is a leaf node"""
    markers = ['leaf_node', 'leaf node', 'atomic skill', 'specific skill', 
               'cannot be broken', 'already specific']
    return any(marker in response.lower() for marker in markers)

class GopherExplorer:
    def __init__(self, job_file):
        self.job_file = Path(job_file)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = Path(f"temp/gopher_hierarchy_{self.timestamp}.txt")
        self.tree_file = Path(f"temp/gopher_tree_{self.timestamp}.json")
        self.conversation = ""
        self.hierarchy_tree = []
        self.node_count = 0
        
        # Load job posting
        with open(self.job_file) as f:
            job_data = json.load(f)
            self.job_title = job_data['job_content']['title']
            self.job_description = job_data['job_content']['description']
        
        # Initialize files
        self.output_file.parent.mkdir(exist_ok=True)
        self.output_file.write_text("")
        
        print("╔══════════════════════════════════════════════════════════════════════════╗")
        print("║  🌍 GOPHER AUTONOMOUS: CHAOS → HIERARCHY TRANSFORMER                    ║")
        print("╚══════════════════════════════════════════════════════════════════════════╝")
        print(f"\n📄 Job: {self.job_title}")
        print(f"🤖 Model: {MODEL}")
        print(f"📊 Max Depth: {MAX_DEPTH} | Branches/Level: {BRANCHES_PER_LEVEL}")
        print("\n🚀 Starting autonomous exploration...\n")
    
    def explore_node(self, node_name, path, level):
        """Recursively explore a node in the taxonomy tree"""
        
        self.node_count += 1
        
        # Depth limit
        if level >= MAX_DEPTH:
            full_path = f"{path}/{node_name}" if path else node_name
            print(f"  {'  ' * level}⚠️  Max depth reached: {node_name}")
            self.hierarchy_tree.append(full_path)
            self.output_file.open('a').write(f"{full_path}\n")
            return
        
        # Build prompt based on level
        if level == 0:
            prompt = f"""Analyze this job posting and identify 5-8 TOP-LEVEL skill categories.

JOB TITLE: {self.job_title}

KEY ACTIVITIES: {self.job_description[:500]}...

Examples of top categories: TECHNICAL, SOFT_SKILLS, DOMAIN_KNOWLEDGE, BUSINESS_ANALYSIS, LEADERSHIP

Output ONLY a numbered list (no other text):
1. CATEGORY_NAME - brief explanation
2. CATEGORY_NAME - brief explanation
..."""
        else:
            prompt = f"""Looking at this job posting, break down the category '{node_name}' into subcategories.

Context path: {path}
Job: {self.job_title}

If '{node_name}' is already a specific atomic skill (cannot be broken down further), respond with:
LEAF_NODE

Otherwise, list 5-8 subcategories as a numbered list:
1. SUBCATEGORY - explanation
2. SUBCATEGORY - explanation
..."""
        
        # Get LLM response
        print(f"{'  ' * level}🔍 Level {level}: {node_name}")
        response = ask_llm(self.conversation, prompt)
        
        # Update conversation history
        self.conversation += f"\n\nUSER: {prompt}\n\nASSISTANT: {response}"
        
        # Check if leaf node
        if is_leaf_node(response):
            full_path = f"{path}/{node_name}" if path else node_name
            print(f"{'  ' * level}  ✓ Leaf: {node_name}")
            self.hierarchy_tree.append(full_path)
            self.output_file.open('a').write(f"{full_path}\n")
            return
        
        # Extract child categories
        children = extract_numbered_items(response)
        
        if not children:
            full_path = f"{path}/{node_name}" if path else node_name
            print(f"{'  ' * level}  ⚠️  No children found, treating as leaf")
            self.hierarchy_tree.append(full_path)
            self.output_file.open('a').write(f"{full_path}\n")
            return
        
        print(f"{'  ' * level}  📊 Found {len(children)} children")
        
        # Ask LLM to select most relevant branches
        if len(children) > BRANCHES_PER_LEVEL:
            selection_prompt = f"""From these {len(children)} subcategories under '{node_name}':

{chr(10).join(f"{i+1}. {c}" for i, c in enumerate(children))}

For the job '{self.job_title}', which {BRANCHES_PER_LEVEL} are MOST relevant to explore?

Respond with ONLY the category names (one per line, no numbers):"""
            
            selection_response = ask_llm(self.conversation, selection_prompt)
            self.conversation += f"\n\nUSER: {selection_prompt}\n\nASSISTANT: {selection_response}"
            
            # Parse selected branches
            selected = []
            for line in selection_response.split('\n'):
                line = line.strip()
                if line and not any(skip in line.lower() for skip in ['from', 'which', 'relevant', 'respond', 'job']):
                    # Try to match to original children
                    for child in children:
                        if line.lower() in child.lower() or child.lower() in line.lower():
                            if child not in selected:
                                selected.append(child)
                                break
            
            if selected:
                children = selected[:BRANCHES_PER_LEVEL]
                print(f"{'  ' * level}  🧭 LLM selected: {', '.join(children)}")
            else:
                children = children[:BRANCHES_PER_LEVEL]
                print(f"{'  ' * level}  🎲 Using first {BRANCHES_PER_LEVEL}")
        
        # Recursively explore selected children
        new_path = f"{path}/{node_name}" if path else node_name
        for i, child in enumerate(children, 1):
            print(f"{'  ' * level}  └─ Branch {i}/{len(children)}: {child}")
            self.explore_node(child, new_path, level + 1)
    
    def run(self):
        """Execute the autonomous exploration"""
        
        try:
            self.explore_node("ROOT", "", 0)
            
            print("\n" + "="*75)
            print("✅ EXPLORATION COMPLETE!")
            print("="*75)
            print(f"\n📊 Statistics:")
            print(f"   Nodes explored: {self.node_count}")
            print(f"   Leaf nodes: {len(self.hierarchy_tree)}")
            print(f"   Max depth: {MAX_DEPTH}")
            print(f"\n📁 Output files:")
            print(f"   Hierarchy: {self.output_file}")
            print(f"\n🌳 Discovered Hierarchy Tree:")
            print("-" * 75)
            for path in self.hierarchy_tree:
                depth = path.count('/')
                indent = "  " * depth
                node = path.split('/')[-1]
                print(f"{indent}📂 {node}")
            
            # Save tree as JSON
            tree_data = {
                "job_title": self.job_title,
                "timestamp": self.timestamp,
                "model": MODEL,
                "hierarchy": self.hierarchy_tree,
                "stats": {
                    "nodes_explored": self.node_count,
                    "leaf_nodes": len(self.hierarchy_tree),
                    "max_depth": MAX_DEPTH
                }
            }
            self.tree_file.write_text(json.dumps(tree_data, indent=2))
            print(f"\n💾 JSON tree: {self.tree_file}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            print(f"Partial results saved to: {self.output_file}")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

def run_from_json_input():
    """
    Accept JSON input for subprocess execution by universal executor.
    
    Input format (via stdin):
    {
      "prompt": "Extract skills from...",
      "context": {
        "job_description": "...",
        "job_title": "..."
      },
      "config": {
        "max_depth": 6,
        "branches_per_level": 3,
        "model": "qwen2.5:7b",
        "timeout_seconds": 300
      }
    }
    
    Output format (to stdout):
    {
      "hierarchy": ["ROOT/TECH/PYTHON", "ROOT/TECH/SQL", ...],
      "stats": {
        "nodes_explored": 10,
        "leaf_nodes": 7,
        "max_depth": 6
      }
    }
    """
    import sys
    import json
    import tempfile
    
    # Read JSON from stdin
    input_data = json.loads(sys.stdin.read())
    
    prompt = input_data.get('prompt', '')
    context = input_data.get('context', {})
    config = input_data.get('config', {})
    
    # Extract job description from context or prompt
    job_description = context.get('job_description', prompt)
    job_title = context.get('job_title', 'Unknown Position')
    
    # Override defaults with config
    global MAX_DEPTH, BRANCHES_PER_LEVEL, MODEL
    MAX_DEPTH = config.get('max_depth', MAX_DEPTH)
    BRANCHES_PER_LEVEL = config.get('branches_per_level', BRANCHES_PER_LEVEL)
    MODEL = config.get('model', MODEL)
    
    # Create temp job file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "job_content": {
                "title": job_title,
                "description": job_description,
                "company": context.get('company', 'Unknown')
            }
        }, f)
        job_file = f.name
    
    try:
        # Run exploration (suppress console output)
        import io
        import contextlib
        
        # Capture stdout to suppress verbose output
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer):
            explorer = GopherExplorer(job_file)
            explorer.run()
        
        # Return JSON output to stdout
        result = {
            "hierarchy": explorer.hierarchy_tree,
            "stats": {
                "nodes_explored": explorer.node_count,
                "leaf_nodes": len(explorer.hierarchy_tree),
                "max_depth": MAX_DEPTH
            },
            "job_title": job_title,
            "timestamp": explorer.timestamp
        }
        print(json.dumps(result, indent=2))
        
    finally:
        # Cleanup temp file
        import os
        if os.path.exists(job_file):
            os.unlink(job_file)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--json-input':
        run_from_json_input()
    else:
        # Original CLI mode
        job_file = sys.argv[1] if len(sys.argv) > 1 else "data/postings/job64834.json"
        
        explorer = GopherExplorer(job_file)
        explorer.run()
