import React, { useState } from 'react';
import PredictPage from './pages/PredictPage.tsx';
import ExplainPage from './pages/ExplainPage.tsx';
import OptimizePage from './pages/OptimizePage.tsx';
import RAGPage from './pages/RAGPage.tsx';
import GraphPage from './pages/GraphPage.tsx';
import { Layers } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'predict' | 'explain' | 'optimize' | 'rag' | 'graph'>('predict');

  const renderContent = () => {
    switch (activeTab) {
      case 'predict':
        return <PredictPage />;
      case 'explain':
        return <ExplainPage />;
      case 'optimize':
        return <OptimizePage />;
      case 'rag':
        return <RAGPage />;
      case 'graph':
        return <GraphPage />;
      default:
        return <PredictPage />;
    }
  };

  return (
    <div className="app-container">
      {/* Navigation Header */}
      <header className="header">
        <div className="logo-group">
          <div className="logo-icon">
            <Layers size={20} color="#fff" />
          </div>
          <div>
            <span className="logo-text">AlloyForge AI</span>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Materials Discovery Platform
            </div>
          </div>
        </div>

        <nav className="nav-links">
          <button 
            className={`nav-item ${activeTab === 'predict' ? 'active' : ''}`}
            onClick={() => setActiveTab('predict')}
          >
            Property Sandbox
          </button>
          <button 
            className={`nav-item ${activeTab === 'explain' ? 'active' : ''}`}
            onClick={() => setActiveTab('explain')}
          >
            Explainable AI
          </button>
          <button 
            className={`nav-item ${activeTab === 'optimize' ? 'active' : ''}`}
            onClick={() => setActiveTab('optimize')}
          >
            Inverse Discovery
          </button>
          <button 
            className={`nav-item ${activeTab === 'rag' ? 'active' : ''}`}
            onClick={() => setActiveTab('rag')}
          >
            RAG Explorer
          </button>
          <button 
            className={`nav-item ${activeTab === 'graph' ? 'active' : ''}`}
            onClick={() => setActiveTab('graph')}
          >
            Knowledge Graph
          </button>
        </nav>

        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'var(--bg-darker)', border: '1px solid var(--border-dark)', padding: '0.4rem 0.8rem', borderRadius: '6px' }}>
          Lab Node: <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>Active</span>
        </div>
      </header>

      {/* Main Content Pane */}
      <main className="main-content">
        {renderContent()}
      </main>
    </div>
  );
}
