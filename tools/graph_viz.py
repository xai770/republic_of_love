#!/usr/bin/env python3
"""
graph_viz.py - Visualize OWL skill graph based on 'requires' relationships

Shows how skills cluster naturally through overlap, without folder hierarchy.

Usage:
    python3 tools/graph_viz.py                    # Full graph stats
    python3 tools/graph_viz.py agile              # Ego graph for 'agile'
    python3 tools/graph_viz.py --cluster          # Find natural clusters
    python3 tools/graph_viz.py --export dot       # Export to DOT format
    python3 tools/graph_viz.py --export html      # Interactive HTML (pyvis)

Author: Sandy
Date: 2026-01-21
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.database import get_connection
import psycopg2.extras


def get_graph_stats(conn):
    """Get basic stats about the requires graph."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    stats = {}
    
    # Total nodes and edges
    cur.execute("SELECT COUNT(*) as cnt FROM owl")
    stats['total_nodes'] = cur.fetchone()['cnt']
    
    cur.execute("SELECT COUNT(*) as cnt FROM owl_relationships WHERE relationship = 'requires'")
    stats['requires_edges'] = cur.fetchone()['cnt']
    
    cur.execute("SELECT COUNT(*) as cnt FROM owl_relationships WHERE relationship = 'belongs_to'")
    stats['belongs_to_edges'] = cur.fetchone()['cnt']
    
    # Nodes with requires links
    cur.execute("SELECT COUNT(DISTINCT owl_id) as cnt FROM owl_relationships WHERE relationship = 'requires'")
    stats['nodes_with_requires'] = cur.fetchone()['cnt']
    
    # Strength distribution
    cur.execute("""
        SELECT 
            CASE 
                WHEN strength >= 0.9 THEN '0.90-1.00 (very high)'
                WHEN strength >= 0.7 THEN '0.70-0.89 (high)'
                WHEN strength >= 0.5 THEN '0.50-0.69 (medium)'
                ELSE '0.00-0.49 (low)'
            END as bucket,
            COUNT(*) as count
        FROM owl_relationships 
        WHERE relationship = 'requires'
        GROUP BY bucket
        ORDER BY bucket DESC
    """)
    stats['strength_distribution'] = {row['bucket']: row['count'] for row in cur.fetchall()}
    
    # Average connections per node
    cur.execute("""
        SELECT AVG(conn_count)::numeric(5,2) as avg
        FROM (
            SELECT owl_id, COUNT(*) as conn_count 
            FROM owl_relationships 
            WHERE relationship = 'requires'
            GROUP BY owl_id
        ) t
    """)
    stats['avg_connections'] = float(cur.fetchone()['avg'] or 0)
    
    # Most connected nodes
    cur.execute("""
        SELECT o.canonical_name, COUNT(*) as connections
        FROM owl_relationships r
        JOIN owl o ON r.owl_id = o.owl_id
        WHERE r.relationship = 'requires'
        GROUP BY o.canonical_name
        ORDER BY connections DESC
        LIMIT 10
    """)
    stats['most_connected'] = [(row['canonical_name'], row['connections']) for row in cur.fetchall()]
    
    # Most linked-TO nodes (hubs)
    cur.execute("""
        SELECT o.canonical_name, COUNT(*) as incoming
        FROM owl_relationships r
        JOIN owl o ON r.related_owl_id = o.owl_id
        WHERE r.relationship = 'requires'
        GROUP BY o.canonical_name
        ORDER BY incoming DESC
        LIMIT 10
    """)
    stats['hub_nodes'] = [(row['canonical_name'], row['incoming']) for row in cur.fetchall()]
    
    return stats


def get_ego_graph(conn, skill_name: str, depth: int = 2, min_strength: float = 0.5):
    """
    Get ego graph centered on a skill - all nodes within N hops.
    
    Returns:
        {
            'center': str,
            'nodes': [{'id': int, 'name': str, 'folder': str}],
            'edges': [{'source': str, 'target': str, 'strength': float}]
        }
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Find the center node
    cur.execute("""
        SELECT owl_id, canonical_name 
        FROM owl 
        WHERE canonical_name ILIKE %s
        LIMIT 1
    """, (f'%{skill_name}%',))
    
    center = cur.fetchone()
    if not center:
        return None
    
    center_id, center_name = center['owl_id'], center['canonical_name']
    
    # BFS to find all connected nodes within depth
    visited = {center_id}
    frontier = {center_id}
    nodes = {}
    edges = []
    
    for _ in range(depth):
        if not frontier:
            break
            
        # Get all connections from frontier - use IN clause with integers
        frontier_list = list(frontier)
        placeholders = ','.join(['%s'] * len(frontier_list))
        
        cur.execute(f"""
            SELECT 
                r.owl_id, r.related_owl_id, r.strength,
                o1.canonical_name as source_name,
                o2.canonical_name as target_name
            FROM owl_relationships r
            JOIN owl o1 ON r.owl_id = o1.owl_id
            JOIN owl o2 ON r.related_owl_id = o2.owl_id
            WHERE r.relationship = 'requires'
              AND r.strength >= %s
              AND (r.owl_id IN ({placeholders}) OR r.related_owl_id IN ({placeholders}))
        """, (min_strength, *frontier_list, *frontier_list))
        
        new_frontier = set()
        for row in cur.fetchall():
            owl_id = row['owl_id']
            related_id = row['related_owl_id']
            strength = row['strength']
            source_name = row['source_name']
            target_name = row['target_name']
            
            edges.append({
                'source': source_name,
                'target': target_name,
                'strength': float(strength)
            })
            
            for nid, nname in [(owl_id, source_name), (related_id, target_name)]:
                if nid not in visited:
                    new_frontier.add(nid)
                    visited.add(nid)
                nodes[nid] = nname
        
        frontier = new_frontier
    
    # Get folder info for each node
    node_list = []
    for owl_id, name in nodes.items():
        cur.execute("""
            SELECT o2.canonical_name
            FROM owl_relationships r
            JOIN owl o2 ON r.related_owl_id = o2.owl_id
            WHERE r.owl_id = %s AND r.relationship = 'belongs_to'
            LIMIT 1
        """, (owl_id,))
        folder = cur.fetchone()
        node_list.append({
            'id': owl_id,
            'name': name,
            'folder': folder['canonical_name'] if folder else 'unclassified'
        })
    
    return {
        'center': center_name,
        'nodes': node_list,
        'edges': edges
    }


def find_clusters(conn, min_cluster_size: int = 5, min_strength: float = 0.9):
    """
    Find natural skill clusters using connected components on requires graph.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Build adjacency list
    cur.execute("""
        SELECT 
            o1.canonical_name as source, o2.canonical_name as target, r.strength
        FROM owl_relationships r
        JOIN owl o1 ON r.owl_id = o1.owl_id
        JOIN owl o2 ON r.related_owl_id = o2.owl_id
        WHERE r.relationship = 'requires'
          AND r.strength >= %s
    """, (min_strength,))
    
    adj = defaultdict(set)
    for row in cur.fetchall():
        adj[row['source']].add(row['target'])
        adj[row['target']].add(row['source'])
    
    # Find connected components
    visited = set()
    clusters = []
    
    def dfs(node, cluster):
        visited.add(node)
        cluster.append(node)
        for neighbor in adj[node]:
            if neighbor not in visited:
                dfs(neighbor, cluster)
    
    for node in adj:
        if node not in visited:
            cluster = []
            dfs(node, cluster)
            if len(cluster) >= min_cluster_size:
                clusters.append(sorted(cluster))
    
    # Sort clusters by size
    clusters.sort(key=len, reverse=True)
    
    return clusters


def export_dot(conn, output_file: str = 'owl_graph.dot', min_strength: float = 0.7):
    """Export graph to DOT format for Graphviz."""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            o1.canonical_name as source,
            o2.canonical_name as target,
            r.strength
        FROM owl_relationships r
        JOIN owl o1 ON r.owl_id = o1.owl_id
        JOIN owl o2 ON r.related_owl_id = o2.owl_id
        WHERE r.relationship = 'requires'
          AND r.strength >= %s
        LIMIT 500
    """, (min_strength,))
    
    edges = cur.fetchall()
    
    with open(output_file, 'w') as f:
        f.write('digraph OWL {\n')
        f.write('  rankdir=LR;\n')
        f.write('  node [shape=box, fontsize=10];\n')
        
        for source, target, strength in edges:
            # Escape quotes in names
            s = source.replace('"', '\\"')[:30]
            t = target.replace('"', '\\"')[:30]
            width = float(strength) * 2
            f.write(f'  "{s}" -> "{t}" [penwidth={width:.1f}];\n')
        
        f.write('}\n')
    
    print(f"Exported {len(edges)} edges to {output_file}")
    print(f"Render with: dot -Tpng {output_file} -o owl_graph.png")


def export_html(conn, output_file: str = 'owl_graph.html', center: str = None, min_strength: float = 0.5):
    """Export interactive HTML visualization using pyvis."""
    try:
        from pyvis.network import Network
    except ImportError:
        print("pyvis not installed. Run: pip install pyvis")
        return
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get edges
    if center:
        # Ego graph
        graph = get_ego_graph(conn, center, depth=1, min_strength=min_strength)  # Reduced depth for speed
        if not graph:
            print(f"No skill found matching '{center}'")
            return
        edges = [(e['source'], e['target'], e['strength']) for e in graph['edges']]
        title = f"OWL Graph: {center}"
    else:
        # Full graph (limited)
        cur.execute("""
            SELECT 
                o1.canonical_name as source, o2.canonical_name as target, r.strength
            FROM owl_relationships r
            JOIN owl o1 ON r.owl_id = o1.owl_id
            JOIN owl o2 ON r.related_owl_id = o2.owl_id
            WHERE r.relationship = 'requires'
              AND r.strength >= %s
            LIMIT 300
        """, (min_strength,))
        edges = [(r['source'], r['target'], r['strength']) for r in cur.fetchall()]
        title = "OWL Skills Graph (requires relationships)"
    
    # Build pyvis network with physics DISABLED for fast render
    net = Network(height='800px', width='100%', directed=True, notebook=False)
    
    nodes_added = set()
    for source, target, strength in edges:
        if source not in nodes_added:
            net.add_node(source, label=source[:25], title=source)
            nodes_added.add(source)
        if target not in nodes_added:
            net.add_node(target, label=target[:25], title=target)
            nodes_added.add(target)
        
        net.add_edge(source, target, value=float(strength), title=f"{strength:.2f}")
    
    # FAST OPTIONS: disable physics, use hierarchical layout
    net.set_options('''
    var options = {
      "nodes": {"font": {"size": 10}, "shape": "dot", "size": 10},
      "edges": {"arrows": {"to": {"enabled": true, "scaleFactor": 0.3}}, "smooth": false},
      "physics": {"enabled": false},
      "layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed"}}
    }
    ''')
    
    net.save_graph(output_file)
    print(f"Exported interactive graph to {output_file}")
    print(f"Open in browser: file://{Path(output_file).absolute()}")


def print_graph_stats(stats):
    """Pretty print graph statistics."""
    print("\n" + "="*60)
    print("OWL SKILL GRAPH STATISTICS (requires relationships)")
    print("="*60)
    
    print(f"\n📊 BASIC COUNTS")
    print(f"   Total nodes:           {stats['total_nodes']:,}")
    print(f"   'requires' edges:      {stats['requires_edges']:,}")
    print(f"   'belongs_to' edges:    {stats['belongs_to_edges']:,}")
    print(f"   Nodes with requires:   {stats['nodes_with_requires']:,} ({100*stats['nodes_with_requires']/stats['total_nodes']:.1f}%)")
    print(f"   Avg connections/node:  {stats['avg_connections']:.2f}")
    
    print(f"\n📈 EDGE STRENGTH DISTRIBUTION")
    for bucket, count in sorted(stats['strength_distribution'].items(), reverse=True):
        bar = '█' * (count // 100)
        print(f"   {bucket}: {count:,} {bar}")
    
    print(f"\n🔗 MOST CONNECTED (outgoing requires)")
    for i, (name, count) in enumerate(stats['most_connected'], 1):
        print(f"   {i:2}. {name[:45]:45} → {count} connections")
    
    print(f"\n🎯 HUB NODES (incoming requires - many skills need these)")
    for i, (name, count) in enumerate(stats['hub_nodes'], 1):
        print(f"   {i:2}. {name[:45]:45} ← {count} skills require this")


def print_ego_graph(graph):
    """Pretty print ego graph."""
    print(f"\n🎯 EGO GRAPH: {graph['center']}")
    print(f"   Nodes: {len(graph['nodes'])}")
    print(f"   Edges: {len(graph['edges'])}")
    
    # Group nodes by folder
    by_folder = defaultdict(list)
    for node in graph['nodes']:
        by_folder[node['folder']].append(node['name'])
    
    print(f"\n📁 NODES BY FOLDER (shows where graph crosses folder boundaries)")
    for folder, skills in sorted(by_folder.items(), key=lambda x: -len(x[1])):
        print(f"   {folder} ({len(skills)} nodes)")
        for skill in skills[:5]:
            print(f"      • {skill}")
        if len(skills) > 5:
            print(f"      ... and {len(skills)-5} more")
    
    print(f"\n🔗 STRONGEST CONNECTIONS")
    sorted_edges = sorted(graph['edges'], key=lambda e: -e['strength'])[:15]
    for edge in sorted_edges:
        print(f"   {edge['source'][:30]:30} ──{edge['strength']:.2f}──► {edge['target'][:30]}")


def print_clusters(clusters, min_strength):
    """Pretty print clusters."""
    print(f"\n🔮 NATURAL CLUSTERS (connected components, strength ≥ {min_strength})")
    print(f"   Found {len(clusters)} clusters with 5+ members\n")
    
    for i, cluster in enumerate(clusters[:10], 1):
        # Try to find a theme
        words = defaultdict(int)
        for skill in cluster:
            for word in skill.split('_'):
                if len(word) > 3:
                    words[word] += 1
        
        top_words = sorted(words.items(), key=lambda x: -x[1])[:3]
        theme = ', '.join(w[0] for w in top_words)
        
        print(f"   CLUSTER {i}: {len(cluster)} skills (theme: {theme})")
        for skill in cluster[:5]:
            print(f"      • {skill}")
        if len(cluster) > 5:
            print(f"      ... and {len(cluster)-5} more")
        print()


def main():
    parser = argparse.ArgumentParser(description='Visualize OWL skill graph')
    parser.add_argument('skill', nargs='?', help='Skill name for ego graph')
    parser.add_argument('--cluster', action='store_true', help='Find natural clusters')
    parser.add_argument('--export', choices=['dot', 'html'], help='Export format')
    parser.add_argument('--min-strength', type=float, default=0.5, help='Minimum edge strength')
    parser.add_argument('--output', '-o', help='Output file path')
    
    args = parser.parse_args()
    
    with get_connection() as conn:
        if args.export == 'dot':
            output = args.output or 'output/owl_graph.dot'
            export_dot(conn, output, args.min_strength)
        
        elif args.export == 'html':
            output = args.output or 'output/owl_graph.html'
            export_html(conn, output, args.skill, args.min_strength)
        
        elif args.cluster:
            clusters = find_clusters(conn, min_strength=args.min_strength)
            print_clusters(clusters, args.min_strength)
        
        elif args.skill:
            graph = get_ego_graph(conn, args.skill, depth=2, min_strength=args.min_strength)
            if graph:
                print_ego_graph(graph)
            else:
                print(f"No skill found matching '{args.skill}'")
        
        else:
            stats = get_graph_stats(conn)
            print_graph_stats(stats)


if __name__ == '__main__':
    main()
