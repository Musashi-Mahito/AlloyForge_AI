import React, { useState, useEffect } from 'react';
import { Network, HelpCircle } from 'lucide-react';

const SELECTABLE_ALLOYS = [
  "Ti-35Nb-7Zr-5Ta",
  "Ti-6Al-4V",
  "Ni-30Cr-6Mo",
  "Fe-18Cr-12Ni-2Mo"
];

export default function GraphPage() {
  const [selectedAlloy, setSelectedAlloy] = useState(SELECTABLE_ALLOYS[0]);
  const [graphData, setGraphData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hoveredNode, setHoveredNode] = useState<any>(null);

  const fetchGraphData = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`http://localhost:8000/api/v1/retrieve/graph-neighborhood?alloy_name=${selectedAlloy}`);
      if (!response.ok) {
        throw new Error("Failed to query Neo4j graph API.");
      }
      const data = await response.json();
      setGraphData(data);
    } catch (err: any) {
      setError("Neo4j database offline. Displaying local knowledge graph representation.");
      
      // Fallback local mockup representing a star graph layout
      setTimeout(() => {
        const mockNodes = [
          { id: selectedAlloy, label: selectedAlloy, type: "Alloy", properties: { phase: "beta", aus_score: 0.942 } },
          { id: "beta", label: "beta", type: "Phase", properties: {} },
          { id: "10.1016/j.matdes.2016.12.011", label: "Review on low modulus...", type: "Paper", properties: { doi: "10.1016/j.matdes.2016.12.011", year: 2017 } },
          { id: "Ti", label: "Ti (53%)", type: "Element", properties: { vec: 4, radius: 147 } },
          { id: "Nb", label: "Nb (35%)", type: "Element", properties: { vec: 5, radius: 146 } },
          { id: "Zr", label: "Zr (7%)", type: "Element", properties: { vec: 4, radius: 160 } },
          { id: "Ta", label: "Ta (5%)", type: "Element", properties: { vec: 5, radius: 146 } },
          { id: "Ti-29Nb-13Ta-4.6Zr", label: "Ti-29Nb-13Ta", type: "Alloy", properties: { aus_score: 0.91 } }
        ];
        
        const mockLinks = [
          { source: selectedAlloy, target: "beta", type: "HAS_PHASE" },
          { source: selectedAlloy, target: "10.1016/j.matdes.2016.12.011", type: "REPORTED_IN" },
          { source: selectedAlloy, target: "Ti", type: "CONTAINS", value: 53 },
          { source: selectedAlloy, target: "Nb", type: "CONTAINS", value: 35 },
          { source: selectedAlloy, target: "Zr", type: "CONTAINS", value: 7 },
          { source: selectedAlloy, target: "Ta", type: "CONTAINS", value: 5 },
          { source: selectedAlloy, target: "Ti-29Nb-13Ta-4.6Zr", type: "SIMILAR_TO", value: 0.75 }
        ];
        setGraphData({ nodes: mockNodes, links: mockLinks });
        setLoading(false);
      }, 500);
    } finally {
      if (graphData) setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphData();
  }, [selectedAlloy]);

  // SVG dimensions
  const width = 600;
  const height = 500;
  const centerX = width / 2;
  const centerY = height / 2;

  // Render nodes mapped radially
  const getPosition = (index: number, total: number, radius = 180) => {
    const angle = (index * 2 * Math.PI) / total;
    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  };

  const getNodeColor = (type: string) => {
    switch (type) {
      case "Alloy": return "var(--accent-cyan)";
      case "Element": return "var(--accent-emerald)";
      case "Phase": return "var(--accent-indigo)";
      case "Paper": return "#f43f5e"; // rose
      default: return "var(--text-secondary)";
    }
  };

  // Pre-calculate positions of nodes
  const positionedNodes = React.useMemo(() => {
    if (!graphData || !graphData.nodes) return [];
    
    // Find center node
    const nodes = [...graphData.nodes];
    const centerIdx = nodes.findIndex((n: any) => n.id === selectedAlloy);
    
    let centerNode: any = null;
    if (centerIdx !== -1) {
      centerNode = { ...nodes[centerIdx], x: centerX, y: centerY };
      nodes.splice(centerIdx, 1);
    }
    
    const count = nodes.length;
    const result = nodes.map((node: any, idx: number) => {
      const pos = getPosition(idx, count, node.type === "Alloy" ? 220 : 160);
      return { ...node, x: pos.x, y: pos.y };
    });
    
    if (centerNode) {
      result.unshift(centerNode);
    }
    return result;
  }, [graphData, selectedAlloy]);

  const positionedLinks = React.useMemo(() => {
    if (!positionedNodes.length || !graphData || !graphData.links) return [];
    
    const nodeMap = new Map(positionedNodes.map((n: any) => [n.id, n]));
    
    return graphData.links.map((link: any) => {
      const sourceNode = nodeMap.get(link.source);
      const targetNode = nodeMap.get(link.target);
      if (sourceNode && targetNode) {
        return {
          ...link,
          x1: sourceNode.x,
          y1: sourceNode.y,
          x2: targetNode.x,
          y2: targetNode.y
        };
      }
      return null;
    }).filter(Boolean);
  }, [positionedNodes, graphData]);

  return (
    <div>
      <div className="dashboard-title-section">
        <h2>🕸️ Alloy Knowledge Graph</h2>
        <p className="dashboard-subtitle">Visualize relational connections between alloy compositions, phases, elemental structures, and supporting scientific literature.</p>
      </div>

      <div className="grid-cols-2">
        {/* Left Side: Selectors & details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card">
            <div className="card-title">
              <Network size={20} style={{ color: 'var(--accent-cyan)' }} />
              <span>Target Alloy</span>
            </div>

            <div className="slider-group">
              <label style={{ fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.25rem' }}>Select Alloy Node:</label>
              <select 
                className="form-input"
                value={selectedAlloy}
                onChange={(e) => setSelectedAlloy(e.target.value)}
              >
                {SELECTABLE_ALLOYS.map(a => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
            {error && <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '1rem' }}>{error}</p>}
          </div>

          <div className="card" style={{ flex: 1 }}>
            <div className="card-title">
              <HelpCircle size={20} style={{ color: 'var(--accent-indigo)' }} />
              <span>Node Metadata Inspector</span>
            </div>

            {hoveredNode ? (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: getNodeColor(hoveredNode.type) }}></div>
                  <span style={{ fontSize: '1.1rem', fontWeight: 600 }}>{hoveredNode.id}</span>
                </div>

                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid var(--border-dark)', height: '2.5rem' }}>
                      <td style={{ color: 'var(--text-secondary)' }}>Node Type</td>
                      <td style={{ textAlign: 'right', fontWeight: 600 }}>{hoveredNode.type}</td>
                    </tr>
                    {Object.entries(hoveredNode.properties || {}).map(([k, v]: any) => (
                      <tr style={{ borderBottom: '1px solid var(--border-dark)', height: '2.5rem' }} key={k}>
                        <td style={{ color: 'var(--text-secondary)' }}>{k}</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{typeof v === 'number' ? v.toFixed(3) : String(v)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Hover over a node in the graph visualization to inspect its chemical and structural properties.
              </p>
            )}
          </div>
        </div>

        {/* Right Side: Graph Canvas SVG */}
        <div className="card" style={{ padding: '0.5rem' }}>
          {loading ? (
            <div style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <p style={{ color: 'var(--text-secondary)' }}>Querying Graph connections...</p>
            </div>
          ) : (
            <svg viewBox={`0 0 ${width} ${height}`} className="graph-canvas" style={{ background: 'var(--bg-darker)', display: 'block', borderRadius: '12px' }}>
              {/* Draw Edges */}
              {positionedLinks.map((link: any, i: number) => (
                <g key={i}>
                  <line 
                    x1={link.x1} y1={link.y1} x2={link.x2} y2={link.y2} 
                    style={{ stroke: 'var(--border-dark)', strokeWidth: 1.5 }}
                  />
                  {/* Small link type label */}
                  <text 
                    x={(link.x1 + link.x2) / 2} 
                    y={(link.y1 + link.y2) / 2 - 4} 
                    fill="var(--text-muted)" 
                    fontSize="8" 
                    textAnchor="middle"
                  >
                    {link.type}
                  </text>
                </g>
              ))}

              {/* Draw Nodes */}
              {positionedNodes.map((node: any) => {
                const color = getNodeColor(node.type);
                const isCenter = node.id === selectedAlloy;
                
                return (
                  <g 
                    key={node.id} 
                    transform={`translate(${node.x},${node.y})`}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHoveredNode(node)}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    {/* Glow for center */}
                    {isCenter && (
                      <circle r="26" fill={color} opacity="0.15" />
                    )}
                    <circle 
                      r={isCenter ? 18 : 12} 
                      fill={color} 
                      style={{ 
                        stroke: 'var(--bg-darker)', 
                        strokeWidth: 2,
                        filter: isCenter ? 'drop-shadow(0px 0px 8px rgba(6, 182, 212, 0.5))' : 'none'
                      }}
                    />
                    <text 
                      y={isCenter ? 32 : 24} 
                      fill="var(--text-primary)" 
                      fontSize="9.5" 
                      fontWeight={isCenter ? 600 : 400}
                      textAnchor="middle"
                    >
                      {node.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}
