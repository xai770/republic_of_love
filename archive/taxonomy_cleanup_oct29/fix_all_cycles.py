#!/usr/bin/env python3
"""
Fix ALL Circular References
============================

Find and break ALL circular reference chains in the taxonomy.
"""

import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'base_yoga',
    'user': 'base_admin',
    'password': 'base_yoga_secure_2025'
}

def find_cycles(conn):
    """Find all cycles using DFS"""
    
    cur = conn.cursor()
    
    # Get all parent-child relationships
    cur.execute("SELECT skill, parent_skill FROM skill_hierarchy")
    edges = cur.fetchall()
    cur.close()
    
    # Build graph
    graph = {}
    for child, parent in edges:
        if child not in graph:
            graph[child] = []
        graph[child].append(parent)
    
    cycles = []
    
    def dfs(node, path, visited_in_path):
        if node in visited_in_path:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(cycle)
            return
        
        if node not in graph:
            return
        
        visited_in_path.add(node)
        path.append(node)
        
        for parent in graph[node]:
            dfs(parent, path[:], visited_in_path.copy())
    
    # Try DFS from each node
    for node in graph:
        dfs(node, [], set())
    
    return cycles

def break_cycle(conn, cycle):
    """Break a cycle by removing the last edge"""
    
    # Remove the edge from cycle[-2] -> cycle[-1]
    if len(cycle) < 2:
        return
    
    child = cycle[-2]
    parent = cycle[-1]
    
    cur = conn.cursor()
    
    cur.execute("""
        DELETE FROM skill_hierarchy
        WHERE skill = %s AND parent_skill = %s
    """, (child, parent))
    
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    
    return deleted

def main():
    print("🔄 Finding ALL circular references...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    cycles = find_cycles(conn)
    
    if not cycles:
        print("✅ No cycles found!")
        conn.close()
        return
    
    print(f"\n⚠️  Found {len(cycles)} cycles\n")
    
    for i, cycle in enumerate(cycles[:20], 1):  # Show first 20
        print(f"{i}. {' → '.join(cycle)}")
    
    if len(cycles) > 20:
        print(f"... and {len(cycles) - 20} more")
    
    print(f"\n🔨 Breaking cycles by removing last edge in each...")
    
    for cycle in cycles:
        if len(cycle) >= 2:
            child = cycle[-2]
            parent = cycle[-1]
            deleted = break_cycle(conn, cycle)
            if deleted:
                print(f"   ✓ Removed: {child} → {parent}")
    
    conn.close()
    
    print(f"\n✅ Done! Removed edges from {len(cycles)} cycles")

if __name__ == "__main__":
    main()
