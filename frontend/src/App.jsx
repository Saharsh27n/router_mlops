import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { Navbar } from './components/Navbar'
import { LandingHero } from './components/LandingHero'
import { ChatPanel } from './components/ChatPanel'
import { HeroStrip } from './components/HeroStrip'
import { RequestFeed } from './components/RequestFeed'
import {
  CostSavedChart,
  DriftChart,
  LatencyByModelChart,
  RoutingDistributionChart,
} from './components/Charts'
import { ControlPanel } from './components/ControlPanel'
import { useInterval } from './useInterval'
import './App.css'

const POLL_MS = 2500

export default function App() {
  const [tab, setTab] = useState('landing') // 'landing' | 'dashboard' | 'chat'
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [health, setHealth] = useState(null)
  const [driftHistory, setDriftHistory] = useState([])
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [statsRes, recentRes, healthRes] = await Promise.all([
        api.stats(),
        api.recent(30),
        api.health(),
      ])
      setStats(statsRes)
      setRecent(recentRes)
      setHealth(healthRes)
      setError(null)
    } catch (err) {
      setError(String(err.message ?? err))
    }
  }, [])

  const refreshDrift = useCallback(async () => {
    try {
      const drift = await api.drift()
      setDriftHistory((prev) => [...prev, { psi: drift.max_psi ?? drift.psi ?? 0 }].slice(-40))
    } catch {
      // /drift endpoint fallback
    }
  }, [])

  useEffect(() => {
    refresh()
    refreshDrift()
  }, [refresh, refreshDrift])

  useInterval(refresh, POLL_MS)
  useInterval(refreshDrift, POLL_MS * 2)

  return (
    <div className="app-shell">
      <Navbar
        activeTab={tab}
        onSelectTab={setTab}
        health={health}
        error={error}
      />

      {tab === 'landing' && (
        <div className="page">
          <LandingHero
            onLaunchChat={() => setTab('chat')}
            onOpenDashboard={() => setTab('dashboard')}
          />
        </div>
      )}

      {tab === 'dashboard' && (
        <div className="page">
          <HeroStrip stats={stats} modelInfo={health?.model} />

          <div className="dash-grid">
            <RequestFeed rows={recent} />
            <ControlPanel onRequestServed={refresh} onRefreshDrift={refreshDrift} />
          </div>

          <div className="charts-row">
            <CostSavedChart timeline={stats?.timeline ?? []} />
            <LatencyByModelChart byModel={stats?.by_model ?? []} />
            <RoutingDistributionChart byLabel={stats?.by_label ?? []} />
            <DriftChart history={driftHistory} />
          </div>
        </div>
      )}

      {tab === 'chat' && (
        <ChatPanel onRequestServed={refresh} />
      )}

      <footer className="app-footer">
        SmartRoute Gateway · Provider: <strong style={{ color: 'var(--text)' }}>{health?.provider ?? 'Groq'}</strong> · Active Policy: <strong style={{ color: 'var(--text)' }}>Hybrid (ML + SLM)</strong> · Model:{' '}
        <strong style={{ color: 'var(--text)' }}>
          {health?.model ? `${health.model.alias} v${health.model.version}` : 'LinearSVC-v1'}
        </strong>
      </footer>
    </div>
  )
}
