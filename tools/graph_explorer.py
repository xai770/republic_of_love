#!/usr/bin/env python3
"""
graph_explorer.py - Interactive expandable graph visualization

FEATURES:
- Physics simulation with D3.js force layout
- Click-to-expand: starts with top hubs, click to see connected nodes
- Shows ALL overlap relationships (requires with any strength)
- Color-coded by overlap strength
- Keeps expanding until no more connections

CONCEPT:
- "Children" = nodes with overlap (requires relationship)
- Overlap strength shown as edge thickness and color
- Hub score shown as node size

Usage:
    python3 tools/graph_explorer.py                    # Start with top 10 hubs
    python3 tools/graph_explorer.py risk_management   # Start with specific skill
    python3 tools/graph_explorer.py --min-strength 0.3 # Include weaker overlaps

Author: Sandy
Date: 2026-01-21
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2.extras
from core.database import get_connection


def get_initial_nodes(conn, start_skill: str = None, limit: int = 10) -> list:
    """Get initial nodes - either a specific skill or top hubs."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    if start_skill:
        cur.execute("""
            SELECT o.owl_id, o.canonical_name, 
                   COALESCE(h.incoming_count, 0) as hub_score
            FROM owl o
            LEFT JOIN mv_skill_hub_scores h USING (owl_id)
            WHERE o.canonical_name ILIKE %s
            LIMIT 1
        """, (f'%{start_skill}%',))
        result = cur.fetchone()
        return [dict(result)] if result else []
    else:
        # Get top hubs as starting points
        cur.execute("""
            SELECT owl_id, canonical_name, incoming_count as hub_score
            FROM mv_skill_hub_scores
            WHERE incoming_count > 10
            ORDER BY incoming_count DESC
            LIMIT %s
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]


def get_all_edges(conn, min_strength: float = 0.0) -> list:
    """Get ALL overlap edges for the entire graph."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("""
        SELECT 
            r.owl_id as source_id,
            o1.canonical_name as source,
            r.related_owl_id as target_id,
            o2.canonical_name as target,
            r.strength
        FROM owl_relationships r
        JOIN owl o1 ON r.owl_id = o1.owl_id
        JOIN owl o2 ON r.related_owl_id = o2.owl_id
        WHERE r.relationship = 'requires'
          AND r.strength >= %s
    """, (min_strength,))
    
    return [dict(row) for row in cur.fetchall()]


def get_all_nodes(conn) -> dict:
    """Get all nodes with their hub scores."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("""
        SELECT o.owl_id, o.canonical_name, 
               COALESCE(h.incoming_count, 0) as hub_score
        FROM owl o
        LEFT JOIN mv_skill_hub_scores h USING (owl_id)
    """)
    
    return {row['owl_id']: dict(row) for row in cur.fetchall()}


def generate_explorer_html(initial_nodes: list, all_nodes: dict, all_edges: list, 
                           output_file: str, min_strength: float):
    """Generate the interactive explorer HTML."""
    
    # Build adjacency list (both directions)
    adjacency = {}  # node_id -> [(neighbor_id, strength), ...]
    
    for edge in all_edges:
        src_id = edge['source_id']
        tgt_id = edge['target_id']
        strength = float(edge['strength'])
        
        if src_id not in adjacency:
            adjacency[src_id] = []
        if tgt_id not in adjacency:
            adjacency[tgt_id] = []
        
        adjacency[src_id].append({'id': tgt_id, 'strength': strength, 'direction': 'out'})
        adjacency[tgt_id].append({'id': src_id, 'strength': strength, 'direction': 'in'})
    
    # Prepare data for JavaScript
    nodes_js = {str(k): {
        'id': v['owl_id'],
        'name': v['canonical_name'],
        'hub': v['hub_score']
    } for k, v in all_nodes.items()}
    
    adj_js = {str(k): v for k, v in adjacency.items()}
    
    initial_ids = [n['owl_id'] for n in initial_nodes]
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>OWL Graph Explorer - Click to Expand</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: #1a1a2e; 
            color: #eee;
            overflow: hidden;
        }}
        #container {{ position: relative; width: 100vw; height: 100vh; }}
        svg {{ width: 100%; height: 100%; }}
        
        #controls {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 15px;
            border-radius: 8px;
            min-width: 280px;
            z-index: 100;
        }}
        #controls h3 {{ margin-bottom: 10px; color: #4ecdc4; }}
        #controls p {{ font-size: 12px; color: #888; margin: 5px 0; }}
        #stats {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #333; }}
        #stats span {{ display: block; font-size: 13px; margin: 3px 0; }}
        
        #legend {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 10px;
            border-radius: 8px;
            font-size: 11px;
        }}
        .legend-item {{ display: flex; align-items: center; margin: 4px 0; }}
        .legend-color {{ width: 20px; height: 10px; margin-right: 8px; border-radius: 2px; }}
        
        #tooltip {{
            position: absolute;
            background: rgba(0,0,0,0.9);
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            max-width: 300px;
            z-index: 1000;
        }}
        
        .node {{ cursor: pointer; }}
        .node circle {{ 
            stroke: #fff; 
            stroke-width: 1.5px;
            transition: all 0.2s;
        }}
        .node:hover circle {{ 
            stroke: #4ecdc4; 
            stroke-width: 3px;
            filter: brightness(1.3);
        }}
        .node.expanded circle {{ stroke: #ff6b6b; stroke-width: 2px; }}
        .node text {{ 
            font-size: 9px; 
            fill: #ccc;
            pointer-events: none;
        }}
        
        .link {{ 
            stroke-opacity: 0.6;
            transition: stroke-opacity 0.2s;
        }}
        .link:hover {{ stroke-opacity: 1; }}
        
        button {{
            background: #4ecdc4;
            border: none;
            color: #1a1a2e;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px 5px 5px 0;
            font-weight: bold;
        }}
        button:hover {{ background: #45b7aa; }}
        button.danger {{ background: #ff6b6b; }}
        button.danger:hover {{ background: #ee5a5a; }}
    </style>
</head>
<body>
    <div id="container">
        <svg></svg>
    </div>
    
    <div id="controls">
        <h3>🔍 OWL Graph Explorer</h3>
        <p>Click a node to expand its connections</p>
        <p>Overlap strength shown by edge color/thickness</p>
        <div id="stats">
            <span>📊 Visible nodes: <strong id="nodeCount">0</strong></span>
            <span>🔗 Visible edges: <strong id="edgeCount">0</strong></span>
            <span>📈 Min strength: <strong>{min_strength}</strong></span>
        </div>
        <div style="margin-top: 10px;">
            <button onclick="expandAll()">Expand All Visible</button>
            <button onclick="resetGraph()" class="danger">Reset</button>
        </div>
    </div>
    
    <div id="legend">
        <div class="legend-item"><div class="legend-color" style="background: #2ecc71;"></div> High overlap (0.8-1.0)</div>
        <div class="legend-item"><div class="legend-color" style="background: #f39c12;"></div> Medium overlap (0.5-0.8)</div>
        <div class="legend-item"><div class="legend-color" style="background: #e74c3c;"></div> Low overlap (0.0-0.5)</div>
        <div class="legend-item"><div class="legend-color" style="background: #9b59b6; width: 25px; height: 25px; border-radius: 50%;"></div> Hub node (many connections)</div>
    </div>
    
    <div id="tooltip"></div>

    <script>
        // Data from Python
        const allNodes = {json.dumps(nodes_js)};
        const adjacency = {json.dumps(adj_js)};
        const initialIds = {json.dumps(initial_ids)};
        
        // Graph state
        let visibleNodes = new Map();  // id -> node data
        let visibleEdges = [];         // {{source, target, strength}}
        let expandedNodes = new Set(); // ids that have been expanded
        
        // D3 setup
        const svg = d3.select("svg");
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        svg.attr("viewBox", [0, 0, width, height]);
        
        // Arrow marker for edges
        svg.append("defs").append("marker")
            .attr("id", "arrow")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("fill", "#999")
            .attr("d", "M0,-5L10,0L0,5");
        
        const g = svg.append("g");
        
        // Zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => g.attr("transform", event.transform));
        svg.call(zoom);
        
        // Force simulation
        const simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100).strength(0.5))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(40));
        
        // Graphics groups
        let linkGroup = g.append("g").attr("class", "links");
        let nodeGroup = g.append("g").attr("class", "nodes");
        
        // Color scale for overlap strength
        const colorScale = d3.scaleLinear()
            .domain([0, 0.5, 0.8, 1])
            .range(["#e74c3c", "#f39c12", "#f39c12", "#2ecc71"]);
        
        // Initialize with starting nodes
        function initGraph() {{
            initialIds.forEach(id => {{
                const node = allNodes[id];
                if (node) {{
                    visibleNodes.set(id, {{
                        id: id,
                        name: node.name,
                        hub: node.hub,
                        x: width/2 + (Math.random() - 0.5) * 200,
                        y: height/2 + (Math.random() - 0.5) * 200
                    }});
                }}
            }});
            updateGraph();
        }}
        
        // Expand a node - show its connections
        function expandNode(nodeId) {{
            if (expandedNodes.has(nodeId)) return;
            expandedNodes.add(nodeId);
            
            const neighbors = adjacency[nodeId] || [];
            let addedCount = 0;
            
            neighbors.forEach(neighbor => {{
                const neighborId = neighbor.id;
                const strength = neighbor.strength;
                
                // Add neighbor node if not visible
                if (!visibleNodes.has(neighborId)) {{
                    const nodeData = allNodes[neighborId];
                    if (nodeData) {{
                        const sourceNode = visibleNodes.get(nodeId);
                        visibleNodes.set(neighborId, {{
                            id: neighborId,
                            name: nodeData.name,
                            hub: nodeData.hub,
                            x: sourceNode.x + (Math.random() - 0.5) * 100,
                            y: sourceNode.y + (Math.random() - 0.5) * 100
                        }});
                        addedCount++;
                    }}
                }}
                
                // Add edge (check both directions to avoid duplicates)
                const edgeKey = [nodeId, neighborId].sort().join('-');
                const edgeExists = visibleEdges.some(e => 
                    [e.source.id || e.source, e.target.id || e.target].sort().join('-') === edgeKey
                );
                
                if (!edgeExists) {{
                    if (neighbor.direction === 'out') {{
                        visibleEdges.push({{source: nodeId, target: neighborId, strength: strength}});
                    }} else {{
                        visibleEdges.push({{source: neighborId, target: nodeId, strength: strength}});
                    }}
                }}
            }});
            
            updateGraph();
            return addedCount;
        }}
        
        // Update visualization
        function updateGraph() {{
            const nodes = Array.from(visibleNodes.values());
            const edges = visibleEdges.filter(e => {{
                const srcId = e.source.id || e.source;
                const tgtId = e.target.id || e.target;
                return visibleNodes.has(srcId) && visibleNodes.has(tgtId);
            }});
            
            // Update stats
            document.getElementById('nodeCount').textContent = nodes.length;
            document.getElementById('edgeCount').textContent = edges.length;
            
            // Links
            const link = linkGroup.selectAll("line")
                .data(edges, d => `${{d.source.id || d.source}}-${{d.target.id || d.target}}`);
            
            link.exit().remove();
            
            const linkEnter = link.enter().append("line")
                .attr("class", "link")
                .attr("stroke", d => colorScale(d.strength))
                .attr("stroke-width", d => 1 + d.strength * 4)
                .attr("marker-end", "url(#arrow)");
            
            // Nodes
            const node = nodeGroup.selectAll(".node")
                .data(nodes, d => d.id);
            
            node.exit().remove();
            
            const nodeEnter = node.enter().append("g")
                .attr("class", "node")
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended))
                .on("click", (event, d) => {{
                    event.stopPropagation();
                    expandNode(d.id);
                }})
                .on("mouseover", showTooltip)
                .on("mouseout", hideTooltip);
            
            nodeEnter.append("circle")
                .attr("r", d => 8 + Math.sqrt(d.hub || 0))
                .attr("fill", d => d.hub > 20 ? "#9b59b6" : "#3498db");
            
            nodeEnter.append("text")
                .attr("dy", d => 15 + Math.sqrt(d.hub || 0))
                .attr("text-anchor", "middle")
                .text(d => d.name.length > 20 ? d.name.substring(0, 20) + "..." : d.name);
            
            // Mark expanded nodes
            nodeGroup.selectAll(".node")
                .classed("expanded", d => expandedNodes.has(d.id));
            
            // Update simulation
            simulation.nodes(nodes);
            simulation.force("link").links(edges);
            simulation.alpha(0.3).restart();
        }}
        
        // Simulation tick
        simulation.on("tick", () => {{
            linkGroup.selectAll("line")
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            nodeGroup.selectAll(".node")
                .attr("transform", d => `translate(${{d.x}},${{d.y}})`);
        }});
        
        // Drag handlers
        function dragstarted(event) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }}
        
        function dragged(event) {{
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }}
        
        function dragended(event) {{
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }}
        
        // Tooltip
        function showTooltip(event, d) {{
            const neighbors = adjacency[d.id] || [];
            const outgoing = neighbors.filter(n => n.direction === 'out').length;
            const incoming = neighbors.filter(n => n.direction === 'in').length;
            const isExpanded = expandedNodes.has(d.id);
            
            const tooltip = document.getElementById('tooltip');
            tooltip.innerHTML = `
                <strong>${{d.name}}</strong><br>
                Hub score: ${{d.hub || 0}}<br>
                Overlaps with: ${{neighbors.length}} skills<br>
                → Outgoing: ${{outgoing}} | ← Incoming: ${{incoming}}<br>
                <em>${{isExpanded ? '✓ Expanded' : 'Click to expand'}}</em>
            `;
            tooltip.style.left = (event.pageX + 10) + 'px';
            tooltip.style.top = (event.pageY - 10) + 'px';
            tooltip.style.opacity = 1;
        }}
        
        function hideTooltip() {{
            document.getElementById('tooltip').style.opacity = 0;
        }}
        
        // Expand all visible nodes
        function expandAll() {{
            const nodesToExpand = Array.from(visibleNodes.keys())
                .filter(id => !expandedNodes.has(id));
            nodesToExpand.forEach(id => expandNode(id));
        }}
        
        // Reset to initial state
        function resetGraph() {{
            visibleNodes.clear();
            visibleEdges = [];
            expandedNodes.clear();
            initGraph();
        }}
        
        // Start
        initGraph();
    </script>
</body>
</html>'''
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Generated explorer: {output_file}")
    print(f"  Initial nodes: {len(initial_nodes)}")
    print(f"  Total nodes in graph: {len(all_nodes)}")
    print(f"  Total edges (overlap ≥ {min_strength}): {len(all_edges)}")


def main():
    parser = argparse.ArgumentParser(description='Interactive OWL Graph Explorer')
    parser.add_argument('skill', nargs='?', help='Starting skill (default: top hubs)')
    parser.add_argument('--min-strength', type=float, default=0.0, 
                        help='Minimum overlap strength to include (default: 0 = all)')
    parser.add_argument('--initial-hubs', type=int, default=10,
                        help='Number of initial hub nodes (if no skill specified)')
    parser.add_argument('-o', '--output', default='output/graph_explorer.html',
                        help='Output file path')
    
    args = parser.parse_args()
    
    with get_connection() as conn:
        print("Loading graph data...")
        initial_nodes = get_initial_nodes(conn, args.skill, args.initial_hubs)
        
        if not initial_nodes:
            print(f"No skill found matching '{args.skill}'")
            return
        
        all_nodes = get_all_nodes(conn)
        all_edges = get_all_edges(conn, args.min_strength)
        
        print(f"Generating explorer...")
        generate_explorer_html(initial_nodes, all_nodes, all_edges, 
                               args.output, args.min_strength)
        
        print(f"\nOpen in browser: file://{Path(args.output).absolute()}")


if __name__ == '__main__':
    main()
