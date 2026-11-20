import { useState } from 'react'
import { api } from '../api'

export function ControlPanel({ onRequestServed, onRefreshDrift }) {
  const [query, setQuery] = useState(
    'How many clips did Natalia sell altogether if she sold 48 in April and half as many in May?',
  )
  const [threshold, setThreshold] = useState(0.6)
  const [strategy, setStrategy] = useState('hybrid')
  const [busy, setBusy] = useState(null)
  const [latestAnswer, setLatestAnswer] = useState(null)
  const [log, setLog] = useState([])

  function note(text, tone = 'info') {
    setLog((prev) => [{ text, tone, id: Date.now() }, ...prev].slice(0, 5))
  }

  async function sendQuery() {
    if (!query.trim()) return
    setBusy('chat')
    try {
      const result = await api.chat(query, { threshold, strategy })
      const { routing, usage, answer } = result
      setLatestAnswer({
        answer,
        model: routing.model,
        strategy: routing.strategy ?? strategy,
        slm_consulted: routing.slm_consulted,
        latency_ms: usage.latency_ms,
        routing_latency_ms: routing.routing_latency_ms,
        cost_usd: usage.cost_usd,
        saved_usd: usage.saved_usd,
        label: routing.predicted_label,
        confidence: routing.confidence,
        escalated: routing.escalated,
      })
      note(
        `[${routing.strategy?.toUpperCase() ?? 'HYBRID'}] ${routing.model.split('/').pop()} ` +
          `(${routing.predicted_label}, conf ${routing.confidence.toFixed(2)}) ` +
          `[${routing.slm_consulted ? 'SLM Tier-2' : 'ML Tier-1'}] — $${usage.cost_usd.toFixed(5)}`,
        'ok',
      )
      onRequestServed?.()
    } catch (err) {
      note(String(err.message ?? err), 'error')
    } finally {
      setBusy(null)
    }
  }

  async function simulateDrift() {
    setBusy('drift')
    try {
      const result = await api.simulateDrift()
      note(`Drift traffic injected (${result.injected ?? '?'} queries)`, 'ok')
      onRefreshDrift?.()
    } catch (err) {
      note('simulate-drift failed', 'error')
    } finally {
      setBusy(null)
    }
  }

  async function retrain() {
    setBusy('retrain')
    try {
      const result = await api.retrain()
      note(
        result.promoted
          ? `MLflow: Retrained & Promoted v${result.version} to @champion`
          : `MLflow: Retrained v${result.version} (did not beat champion)`,
        'ok',
      )
    } catch (err) {
      note('retrain endpoint failed', 'error')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="card control-panel">
      <h2>Routing Operations Control</h2>

      <div className="field-group">
        <label className="field-label">Routing Strategy</label>
        <div className="strategy-selector">
          <button
            type="button"
            className={`strategy-btn ${strategy === 'hybrid' ? 'active' : ''}`}
            onClick={() => setStrategy('hybrid')}
          >
            <strong>Hybrid</strong>
            <span>ML &lt;3ms + SLM Fallback</span>
          </button>
          <button
            type="button"
            className={`strategy-btn ${strategy === 'ml_fast' ? 'active' : ''}`}
            onClick={() => setStrategy('ml_fast')}
          >
            <strong>Fast ML</strong>
            <span>Sub-millisecond</span>
          </button>
          <button
            type="button"
            className={`strategy-btn ${strategy === 'llm_semantic' ? 'active' : ''}`}
            onClick={() => setStrategy('llm_semantic')}
          >
            <strong>SLM Judge</strong>
            <span>Zero-shot Semantic</span>
          </button>
        </div>
      </div>

      <div className="field-group">
        <label className="field-label" htmlFor="query">
          Test Query
        </label>
        <textarea
          id="query"
          rows={2}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question or enter code..."
        />
      </div>

      <div className="row">
        <label className="field-label" htmlFor="threshold">
          Confidence threshold: <strong>{threshold.toFixed(2)}</strong>
        </label>
        <input
          id="threshold"
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
        />
      </div>

      <div className="button-row">
        <button className="primary-btn" onClick={sendQuery} disabled={busy !== null}>
          {busy === 'chat' ? 'Routing...' : 'Route & Execute'}
        </button>
        <button onClick={simulateDrift} disabled={busy !== null} className="secondary">
          {busy === 'drift' ? 'Injecting...' : 'Simulate Drift'}
        </button>
        <button onClick={retrain} disabled={busy !== null} className="secondary">
          {busy === 'retrain' ? 'Retraining...' : 'MLflow Retrain'}
        </button>
      </div>

      {latestAnswer && (
        <div className="response-preview">
          <div className="response-header">
            <span className="badge badge-model">{latestAnswer.model.split('/').pop()}</span>
            <span className="badge badge-tier">
              {latestAnswer.slm_consulted ? 'Tier-2 (SLM)' : 'Tier-1 (Fast ML)'}
            </span>
            {latestAnswer.routing_latency_ms && (
              <span className="badge badge-latency">
                Route: {latestAnswer.routing_latency_ms.toFixed(1)}ms
              </span>
            )}
            <span className="badge badge-saved">
              Saved: ${(latestAnswer.saved_usd ?? 0).toFixed(5)}
            </span>
          </div>
          <div className="response-body">{latestAnswer.answer}</div>
        </div>
      )}

      {log.length > 0 && (
        <ul className="log">
          {log.map((entry) => (
            <li key={entry.id} className={`log-${entry.tone}`}>
              {entry.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
