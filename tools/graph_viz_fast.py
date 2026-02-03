#!/usr/bin/env python3
"""
graph_viz_fast.py - Fast graph visualization using materialized views

OPTIMIZATIONS vs graph_viz.py:
1. Uses mv_skill_hub_scores for pre-computed hub metrics
2. Uses mv_skill_2hop for pre-computed 2-hop paths  
3. Static SVG output (no physics simulation)
4. Canvas-based HTML for large graphs
5. Pre-filtered by strength threshold

Usage:
    python3 tools/graph_viz_fast.py risk_management          # SVG ego graph
    python3 tools/graph_viz_fast.py --hubs                   # Top hub skills
    python3 tools/graph_viz_fast.py --html agile             # Fast HTML
    python3 tools/graph_viz_fast.py --benchmark              # Compare speed

Author: Sandy
Date: 2026-01-21
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2.extras
from core.database import get_connection


def get_hubs_fast(conn, limit: int = 20) -> List[Dict]:
    """Get top hub skills from materialized view (instant!)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("""
        SELECT owl_id, canonical_name, incoming_count, avg_incoming_strength
        FROM mv_skill_hub_scores
        WHERE incoming_count > 0
        ORDER BY incoming_count DESC
        LIMIT %s
    """, (limit,))
    
    return [dict(row) for row in cur.fetchall()]


def get_ego_graph_fast(conn, skill_name: str, max_nodes: int = 50, min_strength: float = 0.5) -> Dict:
    """
    Get ego graph using pre-computed 2-hop paths from materialized view.
    MUCH faster than BFS traversal.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Find center node
    cur.execute("""
        SELECT owl_id, canonical_name 
        FROM owl 
        WHERE canonical_name ILIKE %s
        LIMIT 1
    """, (f'%{skill_name}%',))
    
    center = cur.fetchone()
    if not center:
        return None
    
    center_id = center['owl_id']
    center_name = center['canonical_name']
    
    # Get all connected nodes from 2-hop materialized view (FAST!)
    cur.execute("""
        WITH ego AS (
            -- Nodes where center is source
            SELECT target_id as owl_id, strength, min_hops, 'outgoing' as direction
            FROM mv_skill_2hop
            WHERE source_id = %s AND strength >= %s
            
            UNION ALL
            
            -- Nodes where center is target  
            SELECT source_id as owl_id, strength, min_hops, 'incoming' as direction
            FROM mv_skill_2hop
            WHERE target_id = %s AND strength >= %s
        )
        SELECT DISTINCT ON (e.owl_id)
            e.owl_id,
            o.canonical_name,
            e.strength,
            e.min_hops,
            e.direction,
            h.incoming_count as hub_score
        FROM ego e
        JOIN owl o ON e.owl_id = o.owl_id
        LEFT JOIN mv_skill_hub_scores h ON e.owl_id = h.owl_id
        ORDER BY e.owl_id, e.strength DESC
        LIMIT %s
    """, (center_id, min_strength, center_id, min_strength, max_nodes))
    
    nodes = [{'id': center_id, 'name': center_name, 'hub_score': 0, 'is_center': True}]
    edges = []
    
    for row in cur.fetchall():
        nodes.append({
            'id': row['owl_id'],
            'name': row['canonical_name'],
            'hub_score': row['hub_score'] or 0,
            'hops': row['min_hops'],
            'is_center': False
        })
        
        if row['direction'] == 'outgoing':
            edges.append({
                'source': center_name,
                'target': row['canonical_name'],
                'strength': float(row['strength'])
            })
        else:
            edges.append({
                'source': row['canonical_name'],
                'target': center_name,
                'strength': float(row['strength'])
            })
    
    return {
        'center': center_name,
        'nodes': nodes,
        'edges': edges
    }


def generate_svg(graph: Dict, output_file: str):
    """
    Generate static SVG visualization (no physics, instant render).
    Uses radial layout with hub score determining node size.
    """
    nodes = graph['nodes']
    edges = graph['edges']
    center_name = graph['center']
    
    # SVG dimensions
    width, height = 1200, 800
    cx, cy = width // 2, height // 2
    
    # Calculate positions using radial layout
    node_positions = {}
    center_node = [n for n in nodes if n.get('is_center')][0]
    node_positions[center_name] = (cx, cy)
    
    # Sort non-center nodes by hub score for better layout
    other_nodes = [n for n in nodes if not n.get('is_center')]
    other_nodes.sort(key=lambda n: -n.get('hub_score', 0))
    
    # Place nodes in concentric circles by hop count
    hop_1 = [n for n in other_nodes if n.get('hops', 1) == 1]
    hop_2 = [n for n in other_nodes if n.get('hops', 1) == 2]
    
    def place_circle(node_list, radius):
        for i, node in enumerate(node_list):
            angle = 2 * math.pi * i / max(len(node_list), 1)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            node_positions[node['name']] = (x, y)
    
    place_circle(hop_1, 200)
    place_circle(hop_2, 350)
    
    # Build SVG
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        '  .node { cursor: pointer; }',
        '  .node:hover circle { fill: #ff6b6b; }',
        '  .node text { font-family: Arial, sans-serif; font-size: 10px; }',
        '  .edge { stroke: #999; stroke-opacity: 0.6; fill: none; }',
        '  .center circle { fill: #e74c3c; }',
        '  .hub circle { fill: #3498db; }',
        '  .leaf circle { fill: #95a5a6; }',
        '</style>',
        '<defs>',
        '  <marker id="arrow" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="6" markerHeight="6" orient="auto">',
        '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#999"/>',
        '  </marker>',
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="#f8f9fa"/>',
    ]
    
    # Draw edges
    for edge in edges:
        src = edge['source']
        tgt = edge['target']
        if src in node_positions and tgt in node_positions:
            x1, y1 = node_positions[src]
            x2, y2 = node_positions[tgt]
            strength = edge['strength']
            stroke_width = max(1, strength * 3)
            svg_lines.append(
                f'<line class="edge" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke-width="{stroke_width}" marker-end="url(#arrow)"/>'
            )
    
    # Draw nodes
    for node in nodes:
        name = node['name']
        if name not in node_positions:
            continue
        x, y = node_positions[name]
        hub_score = node.get('hub_score', 0)
        radius = max(8, min(25, 8 + hub_score / 20))
        
        node_class = 'center' if node.get('is_center') else ('hub' if hub_score > 10 else 'leaf')
        
        # Truncate long names
        display_name = name[:25] + '...' if len(name) > 25 else name
        
        svg_lines.append(f'<g class="node {node_class}" transform="translate({x},{y})">')
        svg_lines.append(f'  <circle r="{radius}"/>')
        svg_lines.append(f'  <text dy="{radius + 12}" text-anchor="middle">{display_name}</text>')
        svg_lines.append('</g>')
    
    # Title
    svg_lines.append(f'<text x="10" y="25" font-family="Arial" font-size="16" font-weight="bold">')
    svg_lines.append(f'  Ego Graph: {center_name} ({len(nodes)} nodes, {len(edges)} edges)')
    svg_lines.append('</text>')
    
    svg_lines.append('</svg>')
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(svg_lines))
    
    print(f"Generated SVG: {output_file}")


def generate_fast_html(graph: Dict, output_file: str):
    """
    Generate lightweight HTML with canvas rendering (much faster than pyvis).
    """
    nodes = graph['nodes']
    edges = graph['edges']
    
    # Build node/edge data as JSON
    node_data = [
        {'id': n['name'], 'hub': n.get('hub_score', 0), 'center': n.get('is_center', False)}
        for n in nodes
    ]
    edge_data = [
        {'source': e['source'], 'target': e['target'], 'strength': e['strength']}
        for e in edges
    ]
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Fast Graph: {graph["center"]}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        #info {{ position: absolute; top: 10px; left: 10px; background: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        canvas {{ display: block; }}
    </style>
</head>
<body>
    <div id="info">
        <strong>{graph["center"]}</strong><br>
        Nodes: {len(nodes)} | Edges: {len(edges)}<br>
        <small>Drag to pan, scroll to zoom</small>
    </div>
    <canvas id="graph"></canvas>
    <script>
        const nodes = {json.dumps(node_data)};
        const edges = {json.dumps(edge_data)};
        
        const canvas = document.getElementById('graph');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        // Create node position map
        const nodeMap = new Map();
        const cx = canvas.width / 2, cy = canvas.height / 2;
        
        // Radial layout
        const center = nodes.find(n => n.center);
        if (center) nodeMap.set(center.id, {{x: cx, y: cy}});
        
        const others = nodes.filter(n => !n.center).sort((a,b) => b.hub - a.hub);
        others.forEach((n, i) => {{
            const angle = (2 * Math.PI * i) / others.length;
            const radius = 200 + (n.hub > 10 ? 0 : 100);
            nodeMap.set(n.id, {{
                x: cx + radius * Math.cos(angle),
                y: cy + radius * Math.sin(angle)
            }});
        }});
        
        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#f8f9fa';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw edges
            ctx.strokeStyle = '#ccc';
            edges.forEach(e => {{
                const src = nodeMap.get(e.source);
                const tgt = nodeMap.get(e.target);
                if (src && tgt) {{
                    ctx.lineWidth = e.strength * 2;
                    ctx.beginPath();
                    ctx.moveTo(src.x, src.y);
                    ctx.lineTo(tgt.x, tgt.y);
                    ctx.stroke();
                }}
            }});
            
            // Draw nodes
            nodes.forEach(n => {{
                const pos = nodeMap.get(n.id);
                if (!pos) return;
                const r = n.center ? 15 : (n.hub > 10 ? 10 : 6);
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, r, 0, 2 * Math.PI);
                ctx.fillStyle = n.center ? '#e74c3c' : (n.hub > 10 ? '#3498db' : '#95a5a6');
                ctx.fill();
                
                // Label
                ctx.fillStyle = '#333';
                ctx.font = '10px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(n.id.substring(0, 20), pos.x, pos.y + r + 12);
            }});
        }}
        
        draw();
    </script>
</body>
</html>'''
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Generated fast HTML: {output_file}")


def benchmark(conn):
    """Compare query times: direct vs materialized view."""
    import time
    
    print("\n" + "="*60)
    print("BENCHMARK: Direct Query vs Materialized View")
    print("="*60)
    
    test_skill = 'risk_management'
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Find skill ID
    cur.execute("SELECT owl_id FROM owl WHERE canonical_name = %s", (test_skill,))
    skill_id = cur.fetchone()['owl_id']
    
    # Test 1: Direct 2-hop query
    start = time.time()
    cur.execute("""
        WITH direct AS (
            SELECT related_owl_id, strength FROM owl_relationships 
            WHERE owl_id = %s AND relationship = 'requires'
        ),
        two_hop AS (
            SELECT r.related_owl_id, d.strength * r.strength as strength
            FROM direct d
            JOIN owl_relationships r ON d.related_owl_id = r.owl_id
            WHERE r.relationship = 'requires'
        )
        SELECT * FROM (SELECT * FROM direct UNION ALL SELECT * FROM two_hop) t
    """, (skill_id,))
    direct_rows = cur.fetchall()
    direct_time = time.time() - start
    
    # Test 2: Materialized view query
    start = time.time()
    cur.execute("""
        SELECT target_id, strength FROM mv_skill_2hop 
        WHERE source_id = %s
    """, (skill_id,))
    mv_rows = cur.fetchall()
    mv_time = time.time() - start
    
    print(f"\nSkill: {test_skill} (owl_id={skill_id})")
    print(f"\n📊 Direct 2-hop query:")
    print(f"   Time: {direct_time*1000:.2f} ms")
    print(f"   Rows: {len(direct_rows)}")
    
    print(f"\n⚡ Materialized view query:")
    print(f"   Time: {mv_time*1000:.2f} ms")
    print(f"   Rows: {len(mv_rows)}")
    
    speedup = direct_time / mv_time if mv_time > 0 else float('inf')
    print(f"\n🚀 Speedup: {speedup:.1f}x faster")
    
    # Test 3: Hub lookup
    start = time.time()
    cur.execute("""
        SELECT o.canonical_name, COUNT(*) 
        FROM owl_relationships r
        JOIN owl o ON r.related_owl_id = o.owl_id
        WHERE r.relationship = 'requires'
        GROUP BY o.canonical_name
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    _ = cur.fetchall()
    direct_hub_time = time.time() - start
    
    start = time.time()
    cur.execute("""
        SELECT canonical_name, incoming_count
        FROM mv_skill_hub_scores
        ORDER BY incoming_count DESC
        LIMIT 10
    """)
    _ = cur.fetchall()
    mv_hub_time = time.time() - start
    
    print(f"\n📊 Direct hub query: {direct_hub_time*1000:.2f} ms")
    print(f"⚡ MV hub query:     {mv_hub_time*1000:.2f} ms")
    print(f"🚀 Speedup: {direct_hub_time/mv_hub_time:.1f}x faster")


def main():
    parser = argparse.ArgumentParser(description='Fast graph visualization')
    parser.add_argument('skill', nargs='?', help='Skill name for ego graph')
    parser.add_argument('--hubs', action='store_true', help='Show top hub skills')
    parser.add_argument('--html', action='store_true', help='Generate HTML output')
    parser.add_argument('--benchmark', action='store_true', help='Run speed benchmark')
    parser.add_argument('--max-nodes', type=int, default=50, help='Max nodes in ego graph')
    parser.add_argument('-o', '--output', help='Output file path')
    
    args = parser.parse_args()
    
    with get_connection() as conn:
        if args.benchmark:
            benchmark(conn)
        
        elif args.hubs:
            hubs = get_hubs_fast(conn)
            print("\n🎯 TOP HUB SKILLS (from materialized view)")
            print("-" * 50)
            for i, h in enumerate(hubs, 1):
                print(f"{i:2}. {h['canonical_name'][:40]:40} ← {h['incoming_count']} skills")
        
        elif args.skill:
            start = time.time()
            graph = get_ego_graph_fast(conn, args.skill, args.max_nodes)
            query_time = time.time() - start
            
            if not graph:
                print(f"No skill found matching '{args.skill}'")
                return
            
            print(f"Query time: {query_time*1000:.1f} ms")
            
            if args.html:
                output = args.output or f'output/{args.skill}_fast.html'
                generate_fast_html(graph, output)
            else:
                output = args.output or f'output/{args.skill}_fast.svg'
                generate_svg(graph, output)
        
        else:
            print("Usage:")
            print("  python3 tools/graph_viz_fast.py risk_management     # SVG graph")
            print("  python3 tools/graph_viz_fast.py --html agile        # Fast HTML")
            print("  python3 tools/graph_viz_fast.py --hubs              # Top hubs")
            print("  python3 tools/graph_viz_fast.py --benchmark         # Speed test")


if __name__ == '__main__':
    main()
