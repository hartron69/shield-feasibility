import React from 'react'

const FRESHNESS_CONFIG = {
  fresh:   { label: 'C5AI+ oppdatert',     color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0', dot: '#22c55e' },
  stale:   { label: 'C5AI+ ikke oppdatert', color: '#b45309', bg: '#fffbeb', border: '#fde68a', dot: '#f59e0b' },
  missing: { label: 'C5AI+ ikke kjørt',    color: '#b91c1c', bg: '#fef2f2', border: '#fecaca', dot: '#ef4444' },
}

function formatTs(isoString) {
  if (!isoString) return null
  try {
    const d = new Date(isoString)
    return d.toLocaleString('nb-NO', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return isoString
  }
}

export default function C5AIStatusBar({ status, loading, onRun }) {
  const freshness = status?.freshness || 'missing'
  const cfg = FRESHNESS_CONFIG[freshness] || FRESHNESS_CONFIG.missing
  const lastRun = formatTs(status?.c5ai_last_run_at)

  return (
    <div className="c5ai-status-bar" style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
      <div className="c5ai-status-left">
        <span className="c5ai-status-dot" style={{ background: cfg.dot }} />
        <span className="c5ai-status-label" style={{ color: cfg.color }}>
          {loading ? 'Oppdaterer C5AI+...' : cfg.label}
        </span>
        {lastRun && !loading && (
          <span className="c5ai-status-ts">{lastRun}</span>
        )}
      </div>
      <button
        className="c5ai-run-btn"
        onClick={onRun}
        disabled={loading}
        title="Kjør C5AI+ analyse"
      >
        {loading
          ? <><span className="c5ai-spinner" /> Kjører...</>
          : 'Oppdater C5AI+'}
      </button>
    </div>
  )
}
