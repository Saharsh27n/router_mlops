import { useState } from 'react'
import {
  Activity,
  Bot,
  BrainCircuit,
  Compass,
  Cpu,
  Layers,
  MessageSquare,
  Sparkles,
} from 'lucide-react'

export function Navbar({ activeTab, onSelectTab, health, error }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="navbar-logo">
          <BrainCircuit size={18} color="#fff" />
        </div>
        <span className="navbar-title">SmartRoute</span>
        <span className="badge badge-model" style={{ marginLeft: 6, fontSize: '0.68rem' }}>
          AIOps Gateway
        </span>
      </div>

      <div className="navbar-nav">
        <button
          className={`nav-link ${activeTab === 'landing' ? 'active' : ''}`}
          onClick={() => onSelectTab('landing')}
        >
          <Sparkles size={15} />
          <span>Overview</span>
        </button>

        <button
          className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onSelectTab('dashboard')}
        >
          <Activity size={15} />
          <span>Telemetry & Ops</span>
        </button>

        <button
          className={`nav-link ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => onSelectTab('chat')}
        >
          <MessageSquare size={15} />
          <span>Interactive Chat</span>
        </button>
      </div>

      <div className="navbar-status">
        <div className={`status-dot ${error ? 'offline' : ''}`} />
        <span>
          {error ? 'Degraded' : health?.provider ? `${health.provider.toUpperCase()} Online` : 'Connecting...'}
        </span>
      </div>
    </nav>
  )
}
