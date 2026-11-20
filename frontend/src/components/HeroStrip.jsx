import { ArrowDownRight, Bot, Cpu, DollarSign, Layers, ShieldCheck, Zap } from 'lucide-react'

const fmtUsd = (n) => `$${(n ?? 0).toFixed(4)}`
const fmtPct = (n) => `${(n ?? 0).toFixed(1)}%`

export function HeroStrip({ stats, modelInfo }) {
  if (!stats) return <div className="card">Loading fleet telemetry…</div>

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-label">
          <Bot size={13} color="var(--accent)" /> Total Requests
        </div>
        <div className="stat-value accent">{stats.requests ?? 0}</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">
          <DollarSign size={13} color="var(--green)" /> Cost Saved
        </div>
        <div className="stat-value green">{fmtUsd(stats.saved_usd)}</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">
          <ArrowDownRight size={13} color="var(--green)" /> Savings vs 120B
        </div>
        <div className="stat-value green">{fmtPct(stats.savings_pct)}</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">
          <Layers size={13} color="var(--amber)" /> Cascade Rate
        </div>
        <div className="stat-value amber">
          {fmtPct(stats.requests ? (100 * stats.escalations) / stats.requests : 0)}
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-label">
          <Zap size={13} color="var(--cyan)" /> Cache Hit Rate
        </div>
        <div className="stat-value">{fmtPct(stats.cache_hit_rate_pct)}</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">
          <ShieldCheck size={13} color="var(--purple)" /> PII Redactions
        </div>
        <div className="stat-value">{stats.redactions ?? 0}</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">
          <Cpu size={13} color="var(--muted)" /> Active Champion
        </div>
        <div className="stat-value muted-val">
          {modelInfo ? `${modelInfo.alias} v${modelInfo.version}` : 'Local-v1'}
        </div>
      </div>
    </div>
  )
}
