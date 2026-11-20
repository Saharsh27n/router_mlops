function formatModel(model) {
  if (!model) return '—'
  const name = model.split('/').pop()
  if (name.includes('llama-3.1-8b')) return 'llama-3.1-8b'
  if (name.includes('llama-3.3-70b')) return 'llama-3.3-70b'
  if (name.includes('deepseek-r1')) return 'deepseek-r1'
  if (name.includes('qwen')) return 'qwen-2.5'
  if (name.includes('20b')) return 'gpt-20b'
  if (name.includes('120b')) return 'gpt-120b'
  return name.slice(0, 14)
}

function timeAgo(iso) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  return `${Math.round(seconds / 60)}m ago`
}

export function RequestFeed({ rows }) {
  return (
    <div className="card">
      <h2>Live Telemetry Feed</h2>
      <div className="feed">
        <div className="feed-row feed-header">
          <span>Query</span>
          <span>Classification</span>
          <span>Target Model</span>
          <span>Signals</span>
          <span>Latency</span>
          <span>Cost</span>
          <span>When</span>
        </div>
        {rows.length === 0 && <div className="feed-empty">No requests recorded yet. Send a query to see live routing.</div>}
        {rows.map((row) => (
          <div className="feed-row" key={row.id}>
            <span className="truncate" title={row.query}>
              {row.query}
            </span>
            <span className={`pill pill-${row.predicted_label}`}>{row.predicted_label}</span>
            <span className="pill pill-model">
              {formatModel(row.model)}
            </span>
            <span className="flags">
              {!!row.escalated && <span className="flag-badge esc" title="Cascade escalated">⬆ esc</span>}
              {!!row.cached && <span className="flag-badge cache" title="Cache hit">⚡ cache</span>}
              {!!row.redactions && <span className="flag-badge pii" title="PII Redacted">🔒 {row.redactions}</span>}
              {!!row.flagged && <span className="flag-badge alert" title="Injection flagged">⚠ flag</span>}
            </span>
            <span className="num-mono">{row.latency_ms.toFixed(0)}ms</span>
            <span className="num-mono">${row.cost_usd.toFixed(5)}</span>
            <span className="muted">{timeAgo(row.ts)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
