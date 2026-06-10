import React, { useState } from 'react';
import { Target, Sparkles, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

export default function OptimizePage() {
  const [constraints, setConstraints] = useState({
    elastic_modulus_max: 45.0,
    uts_min: 800.0,
    corrosion_rate_max: 0.02
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [candidates, setCandidates] = useState<any[]>([]);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const handleConstraintChange = (key: string, val: number) => {
    setConstraints(prev => ({ ...prev, [key]: val }));
  };

  const runDiscovery = async () => {
    setLoading(true);
    setError("");
    setCandidates([]);
    
    try {
      const response = await fetch("http://localhost:8000/api/v1/recommend/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ constraints })
      });
      
      if (!response.ok) {
        throw new Error("Failed to discover alloys. Ensure backend services are running.");
      }
      
      const data = await response.json();
      setCandidates(data);
    } catch (err: any) {
      setError(err.message || "Online retrieval failed. Loading local optimization mockup.");
      
      // Fallback local mockup
      setTimeout(() => {
        setCandidates([
          {
            name: "New-0.55Ti-0.28Nb-0.10Zr-0.06Ta",
            composition: { Ti: 0.555, Nb: 0.28, Zr: 0.105, Ta: 0.06 },
            is_novel: true,
            properties: { elastic_modulus: 38.2, yield_strength: 865.0, uts: 945.0, corrosion_rate: 0.0018, biocompatibility_score: 0.98 },
            descriptors: { vec: 4.18, delta: 4.25, delta_h_mix: 1.1 },
            aus_score: 0.942,
            rag_score: 0.952,
            graph_score: 0.85,
            recommendation_score: 0.924,
            confidence_score: 0.88,
            citations: [
              {
                title: "Recent research and development in titanium alloys for biomedical applications",
                authors: "M. Niinomi",
                journal: "Materials Science and Engineering: A",
                year: 2008,
                doi: "10.1016/j.msea.2007.09.053",
                relevance_score: 0.952,
                matching_snippet: "Beta-type titanium alloys such as Ti-Nb-Zr-Ta systems exhibit low elastic modulus ranging from 55 to 65 GPa, mitigating stress-shielding effects and promoting bone remodeling in clinical orthopedic implants."
              }
            ]
          },
          {
            name: "Ti-35Nb-7Zr-5Ta (Beta Reference)",
            composition: { Ti: 0.53, Nb: 0.35, Zr: 0.07, Ta: 0.05 },
            is_novel: false,
            properties: { elastic_modulus: 39.5, yield_strength: 810.0, uts: 890.0, corrosion_rate: 0.0015, biocompatibility_score: 0.98 },
            descriptors: { vec: 4.25, delta: 4.12, delta_h_mix: 1.25 },
            aus_score: 0.925,
            rag_score: 0.912,
            graph_score: 0.95,
            recommendation_score: 0.916,
            confidence_score: 0.96,
            citations: [
              {
                title: "Review on low modulus beta-type titanium alloys for implant materials",
                authors: "L. Zhang et al.",
                journal: "Materials & Design",
                year: 2017,
                doi: "10.1016/j.matdes.2016.12.011",
                relevance_score: 0.912,
                matching_snippet: "The Ti-35Nb-7Zr-5Ta alloy exhibits a stable body-centered cubic beta phase structure, yielding an elastic modulus of approximately 38 GPa."
              }
            ]
          }
        ]);
        setLoading(false);
      }, 800);
    } finally {
      if (candidates.length > 0) setLoading(false);
    }
  };

  const toggleExpand = (idx: number) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div>
      <div className="dashboard-title-section">
        <h2>🎯 Multi-Objective Inverse Design</h2>
        <p className="dashboard-subtitle">Define target properties limits, run genetic algorithms, and retrieve candidate alloys ranked by property performance and research evidence.</p>
      </div>

      <div className="grid-cols-2">
        {/* Constraints */}
        <div className="card" style={{ height: 'fit-content' }}>
          <div className="card-title">
            <Target size={20} style={{ color: 'var(--accent-cyan)' }} />
            <span>Target Specifications</span>
          </div>

          <div className="slider-group">
            <div className="slider-label-row">
              <span className="slider-name">Max Elastic Modulus</span>
              <span className="slider-value">{constraints.elastic_modulus_max} GPa</span>
            </div>
            <input 
              type="range" min="30" max="150" step="5"
              value={constraints.elastic_modulus_max}
              onChange={(e) => handleConstraintChange("elastic_modulus_max", parseFloat(e.target.value))}
              className="slider-input"
            />
          </div>

          <div className="slider-group">
            <div className="slider-label-row">
              <span className="slider-name">Min UTS</span>
              <span className="slider-value">{constraints.uts_min} MPa</span>
            </div>
            <input 
              type="range" min="300" max="1500" step="50"
              value={constraints.uts_min}
              onChange={(e) => handleConstraintChange("uts_min", parseFloat(e.target.value))}
              className="slider-input"
            />
          </div>

          <div className="slider-group" style={{ marginBottom: '2rem' }}>
            <div className="slider-label-row">
              <span className="slider-name">Max Corrosion Rate</span>
              <span className="slider-value">{constraints.corrosion_rate_max.toFixed(4)} mm/yr</span>
            </div>
            <input 
              type="range" min="0.001" max="0.05" step="0.002"
              value={constraints.corrosion_rate_max}
              onChange={(e) => handleConstraintChange("corrosion_rate_max", parseFloat(e.target.value))}
              className="slider-input"
            />
          </div>

          <button className="btn" style={{ width: '100%' }} onClick={runDiscovery} disabled={loading}>
            <Sparkles size={18} />
            {loading ? "Searching Composition Space..." : "Synthesize Alloy Candidates"}
          </button>
        </div>

        {/* Candidate List */}
        <div>
          {loading && (
            <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
              <p style={{ color: 'var(--text-secondary)' }}>Triggering NSGA-II solver & scanning papers store...</p>
            </div>
          )}
          
          {error && (
            <p style={{ color: 'var(--accent-rose)', fontSize: '0.85rem', marginBottom: '1rem' }}>{error}</p>
          )}

          {candidates.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Top {candidates.length} Recommendations</h3>
              {candidates.map((cand, idx) => (
                <div className="card" key={idx} style={{ padding: '1.25rem' }}>
                  <div className="candidate-header">
                    <div>
                      <span className="candidate-name">{cand.name}</span>
                      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                        {cand.is_novel ? (
                          <span className="novel-badge">Novel Discovery</span>
                        ) : (
                          <span className="published-badge">Seeded Reference</span>
                        )}
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Confidence: {(cand.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Recommendation Score</div>
                      <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{(cand.recommendation_score * 100).toFixed(1)}</div>
                    </div>
                  </div>

                  {/* Composition percentages pills */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', margin: '1rem 0' }}>
                    {Object.entries(cand.composition).map(([el, wt]: any) => (
                      <div key={el} style={{ background: 'var(--bg-darker)', border: '1px solid var(--border-dark)', borderRadius: '6px', padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{el}</span>: {wt.toFixed(3)}
                      </div>
                    ))}
                  </div>

                  {/* Physical Properties list */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', background: 'var(--bg-darker)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.85rem', marginBottom: '1rem' }}>
                    <div>
                      <span style={{ color: 'var(--text-secondary)' }}>E: </span>
                      <span style={{ fontWeight: 600 }}>{cand.properties.elastic_modulus.toFixed(1)} GPa</span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-secondary)' }}>UTS: </span>
                      <span style={{ fontWeight: 600 }}>{cand.properties.uts.toFixed(0)} MPa</span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-secondary)' }}>Corrosion: </span>
                      <span style={{ fontWeight: 600 }}>{cand.properties.corrosion_rate.toFixed(4)}</span>
                    </div>
                  </div>

                  {/* Scores breakdown */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-dark)', paddingTop: '0.75rem' }}>
                    <span>AUS score: <strong>{cand.aus_score.toFixed(3)}</strong></span>
                    <span>RAG score: <strong>{cand.rag_score.toFixed(3)}</strong></span>
                    <span>Graph score: <strong>{cand.graph_score.toFixed(3)}</strong></span>
                  </div>

                  {/* RAG expander */}
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px dotted var(--border-dark)' }}>
                    <div 
                      style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.8rem', color: 'var(--accent-indigo)', cursor: 'pointer' }}
                      onClick={() => toggleExpand(idx)}
                    >
                      <BookOpen size={14} />
                      <span>{expandedIndex === idx ? "Hide Supporting Evidence" : "Show Supporting Evidence"}</span>
                      {expandedIndex === idx ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </div>

                    {expandedIndex === idx && cand.citations && (
                      <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(99, 102, 241, 0.04)', borderLeft: '2px solid var(--accent-indigo)', borderRadius: '4px' }}>
                        {cand.citations.map((cit: any, cIdx: number) => (
                          <div key={cIdx} style={{ fontSize: '0.8rem' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{cit.title}</div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', margin: '0.2rem 0' }}>
                              {cit.authors} | {cit.journal} ({cit.year}) | DOI: {cit.doi}
                            </div>
                            <p style={{ fontStyle: 'italic', color: 'var(--text-secondary)', marginTop: '0.4rem', lineHeight: '1.4' }}>
                              "...{cit.matching_snippet}..."
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
