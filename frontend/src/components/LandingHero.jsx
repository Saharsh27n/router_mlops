import { ArrowRight, Bot, Cpu, DollarSign, Gauge, GitCommit, Layers, ShieldCheck, Zap } from 'lucide-react'

export function LandingHero({ onLaunchChat, onOpenDashboard }) {
  return (
    <div className="hero-page">
      <section className="hero-section">
        <div className="hero-glow" />
        <div className="hero-content">
          <div className="hero-eyebrow">
            <Zap size={14} /> Production-Grade LLM Cost & Latency Optimization
          </div>

          <h1 className="hero-title">
            Intelligent Query Routing for <span className="gradient-text">AIOps Fleets</span>
          </h1>

          <p className="hero-subtitle">
            SmartRoute dynamically inspects incoming prompts via ultra-fast ML classifier (&lt;3ms)
            and escalates borderline queries to SLM judges. Save 30-70% on token expenditure without sacrificing reasoning quality.
          </p>

          <div className="hero-actions">
            <button className="btn btn-primary" onClick={onLaunchChat}>
              <span>Launch Interactive Chat</span>
              <ArrowRight size={16} />
            </button>
            <button className="btn btn-secondary" onClick={onOpenDashboard}>
              <Gauge size={16} />
              <span>Open Ops Dashboard</span>
            </button>
          </div>
        </div>
      </section>

      {/* Architecture Flow */}
      <section className="arch-section">
        <div className="section-label">Pipeline Architecture</div>
        <h2 className="section-title">Zero-Cold-Start Tiered Routing</h2>

        <div className="arch-flow">
          <div className="arch-node">
            <div className="arch-node-icon"><Bot size={22} color="#3b82f6" /></div>
            <div className="arch-node-label">Client Query</div>
            <div className="arch-node-desc">REST / OpenAI SDK</div>
          </div>

          <div className="arch-arrow">→</div>

          <div className="arch-node">
            <div className="arch-node-icon"><ShieldCheck size={22} color="#f59e0b" /></div>
            <div className="arch-node-label">Security & Cache</div>
            <div className="arch-node-desc">PII Redaction & Exact Cache</div>
          </div>

          <div className="arch-arrow">→</div>

          <div className="arch-node">
            <div className="arch-node-icon"><Zap size={22} color="#22c55e" /></div>
            <div className="arch-node-label">Tier-1 ML Router</div>
            <div className="arch-node-desc">TF-IDF + LinearSVC (&lt;3ms)</div>
          </div>

          <div className="arch-arrow">→</div>

          <div className="arch-node">
            <div className="arch-node-icon"><Layers size={22} color="#a855f7" /></div>
            <div className="arch-node-label">Tier-2 SLM Judge</div>
            <div className="arch-node-desc">Fast LLM if Conf &lt; Tau</div>
          </div>

          <div className="arch-arrow">→</div>

          <div className="arch-node">
            <div className="arch-node-icon"><Cpu size={22} color="#06b6d4" /></div>
            <div className="arch-node-label">Model Fleet</div>
            <div className="arch-node-desc">Fast, Balanced, Code, Think</div>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="features-section">
        <div className="section-label">Core Capabilities</div>
        <h2 className="section-title">Engineered for AIOps Assessments</h2>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon" style={{ background: '#3b82f625', color: '#3b82f6' }}>
              <Zap size={20} />
            </div>
            <h3>Sub-3ms ML Routing</h3>
            <p>
              Trained LinearSVC with calibrated Platt scaling scores intent in microseconds, routing simple queries instantly.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: '#a855f725', color: '#a855f7' }}>
              <Layers size={20} />
            </div>
            <h3>Hybrid SLM Escalation</h3>
            <p>
              Ambiguous prompts trigger zero-shot schema evaluation on a fast edge model before committing expensive 120B tokens.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: '#22c55e25', color: '#22c55e' }}>
              <DollarSign size={20} />
            </div>
            <h3>Autonomous Cost Arbitrage</h3>
            <p>
              Routes queries between $0.05/M and $1.20/M token models dynamically with heuristic cascade fallback on degraded answers.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: '#f59e0b25', color: '#f59e0b' }}>
              <ShieldCheck size={20} />
            </div>
            <h3>Defense & Sanitization</h3>
            <p>
              Built-in Regex and NER scrubbing detects emails, phones, and API credentials before payloads leave the gateway.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: '#ef444425', color: '#ef4444' }}>
              <GitCommit size={20} />
            </div>
            <h3>MLflow Model Lifecycle</h3>
            <p>
              Automated drift detection via Population Stability Index (PSI). Triggers automated retraining and champion model promotion.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon" style={{ background: '#06b6d425', color: '#06b6d4' }}>
              <Gauge size={20} />
            </div>
            <h3>Production Observability</h3>
            <p>
              Prometheus `/metrics` telemetry exporter, SQLite request event ledger, and sub-second live reactive dashboard.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
