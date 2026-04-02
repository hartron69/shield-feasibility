import React, { useState, useEffect, useMemo } from 'react'
import ConfidenceBadge from './ConfidenceBadge.jsx'
import { fetchLiveRiskFeed } from '../../api/client.js'

const ILA_VARSEL_STYLE = {
  'GRØNN': { bg: '#e6f4ea', color: '#2e7d32' },
  'ILA01': { bg: '#fff8e1', color: '#e65100' },
  'ILA02': { bg: '#fff3e0', color: '#bf360c' },
  'ILA03': { bg: '#fce4ec', color: '#b71c1c' },
  'ILA04': { bg: '#ede7f6', color: '#4a148c' },
}

function IlaBadge({ varselniva }) {
  if (!varselniva) return <span style={{ color: '#9ca3af', fontSize: 11 }}>—</span>
  const s = ILA_VARSEL_STYLE[varselniva] || ILA_VARSEL_STYLE['GRØNN']
  return (
    <span style={{
      background: s.bg, color: s.color,
      border: `1px solid ${s.color}44`,
      borderRadius: 10, padding: '2px 8px',
      fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
    }}>
      {varselniva}
    </span>
  )
}

// Overview page showing live risk feed for all monitored localities

const FRESHNESS_CONFIG = {
  fresh:   { bg: '#e8f5e9', color: '#2e7d32', label: 'Fersk' },
  stale:   { bg: '#fff8e1', color: '#f57f17', label: 'Forsinket' },
  old:     { bg: '#fdecea', color: '#c62828', label: 'Gammel' },
  failed:  { bg: '#fdecea', color: '#c62828', label: 'Feilet' },
}

const DOMAIN_COLORS = {
  biological:    '#3A86FF',
  structural:    '#FF6B6B',
  environmental: '#36A271',
  operational:   '#F4A620',
}

const DOMAIN_LABELS = {
  biological:    'Biologisk',
  structural:    'Strukturell',
  environmental: 'Miljø',
  operational:   'Operasjonell',
}

const SORT_OPTIONS = [
  { value: 'risk_change', label: 'Største endring' },
  { value: 'risk_score',  label: 'Høyeste risiko' },
  { value: 'name',        label: 'Navn A–Å' },
  { value: 'freshness',   label: 'Nyeste data' },
]

function formatSyncTime(isoStr) {
  if (!isoStr) return '—'
  const d = new Date(isoStr)
  return d.toLocaleString('nb-NO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function FreshnessChip({ freshness }) {
  const cfg = FRESHNESS_CONFIG[freshness] || FRESHNESS_CONFIG.old
  return (
    <span style={{
      background: cfg.bg,
      color: cfg.color,
      border: `1px solid ${cfg.color}33`,
      borderRadius: 10,
      padding: '1px 7px',
      fontSize: 11,
      fontWeight: 600,
    }}>
      {cfg.label}
    </span>
  )
}

function DomainChip({ domain }) {
  const color = DOMAIN_COLORS[domain] || '#6b7280'
  const label = DOMAIN_LABELS[domain] || domain
  return (
    <span style={{
      background: `${color}18`,
      color,
      border: `1px solid ${color}44`,
      borderRadius: 10,
      padding: '1px 7px',
      fontSize: 11,
      fontWeight: 600,
    }}>
      {label}
    </span>
  )
}

function RiskBar({ score }) {
  const pct = Math.max(0, Math.min(100, score || 0))
  const barColor = pct >= 70 ? '#dc2626' : pct >= 40 ? '#f59e0b' : '#16a34a'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ width: 60, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: barColor, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color: '#111827' }}>{Math.round(pct)}</span>
    </div>
  )
}

function DeltaBadge({ delta }) {
  if (delta == null) return <span style={{ color: '#9ca3af' }}>—</span>
  const isIncrease = delta > 0
  const color = isIncrease ? '#c62828' : delta < 0 ? '#2e7d32' : '#6b7280'
  const arrow = isIncrease ? '▲' : delta < 0 ? '▼' : '●'
  return (
    <span style={{ color, fontWeight: 700, whiteSpace: 'nowrap', fontSize: 12 }}>
      {arrow} {isIncrease ? '+' : ''}{delta.toFixed(1)}
    </span>
  )
}

function rowBackground(loc) {
  const freshness = loc.sync_freshness || 'old'
  const score = loc.risk_score || 0
  if (freshness === 'failed') return '#fff5f5'
  if (score >= 70) return '#fff5f5'
  if (freshness === 'stale' || score >= 40) return '#fffdf0'
  return 'white'
}

function FilterPill({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '4px 12px',
        borderRadius: 16,
        border: active ? '1.5px solid var(--navy)' : '1px solid #d1d5db',
        background: active ? 'var(--navy)' : 'white',
        color: active ? 'white' : '#374151',
        fontSize: 12,
        fontWeight: active ? 700 : 400,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  )
}

function SummaryChip({ label, value, color }) {
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      background: 'white',
      border: `1px solid ${color}44`,
      borderRadius: 20,
      padding: '4px 14px',
    }}>
      <span style={{ fontWeight: 700, fontSize: 15, color }}>{value}</span>
      <span style={{ fontSize: 12, color: '#6b7280' }}>{label}</span>
    </div>
  )
}

export default function LiveRiskFeedPage({ onSelectLocality, onFeedRefreshed }) {
  const [data, setData]               = useState(null)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [refreshing, setRefreshing]   = useState(false)
  const [sortBy, setSortBy]           = useState('risk_change')
  const [sortDir, setSortDir]         = useState('desc')
  const [filterFreshness, setFilterFreshness]       = useState('all')
  const [filterRiskDirection, setFilterRiskDirection] = useState('all')
  const [selectedRegion, setSelectedRegion]         = useState('all')
  const [ilaByLocality, setIlaByLocality]           = useState({})

  const load = (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)
    setError(null)
    fetchLiveRiskFeed()
      .then(d => {
        setData(d)
        setLoading(false)
        setRefreshing(false)
        if (isRefresh && onFeedRefreshed) onFeedRefreshed()
      })
      .catch(e => { setError(e.message); setLoading(false); setRefreshing(false) })
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    fetch('/api/ila/portfolio')
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (!d) return
        const map = {}
        ;(d.lokaliteter || []).forEach(l => { map[l.locality_id] = l.varselniva })
        setIlaByLocality(map)
      })
      .catch(() => {})
  }, [])

  const localities = data?.localities || []

  // Unique regions for filter
  const regions = useMemo(() => {
    const rs = [...new Set(localities.map(l => l.region).filter(Boolean))]
    return rs.sort()
  }, [localities])

  // Apply filters and sort
  const filtered = useMemo(() => {
    let locs = [...localities]
    if (filterFreshness !== 'all') locs = locs.filter(l => l.sync_freshness === filterFreshness)
    if (filterRiskDirection !== 'all') {
      if (filterRiskDirection === 'up')   locs = locs.filter(l => (l.risk_change_30d || 0) > 0)
      if (filterRiskDirection === 'down') locs = locs.filter(l => (l.risk_change_30d || 0) < 0)
    }
    if (selectedRegion !== 'all') locs = locs.filter(l => l.region === selectedRegion)

    locs.sort((a, b) => {
      let av, bv
      if (sortBy === 'risk_change') { av = Math.abs(a.risk_change_30d || 0); bv = Math.abs(b.risk_change_30d || 0) }
      else if (sortBy === 'risk_score') { av = a.risk_score || 0; bv = b.risk_score || 0 }
      else if (sortBy === 'name') { return sortDir === 'asc' ? (a.locality_name || '').localeCompare(b.locality_name || '') : (b.locality_name || '').localeCompare(a.locality_name || '') }
      else if (sortBy === 'freshness') { av = new Date(a.last_sync || 0).getTime(); bv = new Date(b.last_sync || 0).getTime() }
      else { av = 0; bv = 0 }
      return sortDir === 'desc' ? bv - av : av - bv
    })

    return locs
  }, [localities, filterFreshness, filterRiskDirection, selectedRegion, sortBy, sortDir])

  if (loading) {
    return (
      <div className="lr-feed-page" style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>
        <div style={{ fontSize: 20, marginBottom: 8 }}>&#8987;</div>
        Laster sanntidsdata...
      </div>
    )
  }

  if (error) {
    return (
      <div className="lr-feed-page" style={{ padding: 32 }}>
        <div style={{ color: '#c62828', background: '#fdecea', padding: '12px 16px', borderRadius: 8, marginBottom: 12 }}>
          Feil ved lasting: {error}
        </div>
        <button
          onClick={() => load(false)}
          style={{ padding: '8px 18px', borderRadius: 6, border: '1px solid #d1d5db', background: 'white', cursor: 'pointer', fontWeight: 600 }}
        >
          Prøv igjen
        </button>
      </div>
    )
  }

  return (
    <div className="lr-feed-page" style={{ padding: '20px 24px' }}>
      {/* Page header */}
      <div style={{ marginBottom: 20, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>
            Live Risk Intelligence &mdash; Datafeed
          </h2>
          <p style={{ color: '#6b7280', fontSize: 13 }}>
            Sanntidsstatus for alle overvåkede lokaliteter
          </p>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          title="Hent oppdaterte data fra alle kilder"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '7px 14px',
            borderRadius: 7,
            border: '1px solid #d1d5db',
            background: refreshing ? '#f1f5f9' : 'white',
            color: refreshing ? '#94a3b8' : '#374151',
            fontWeight: 600,
            fontSize: 13,
            cursor: refreshing ? 'not-allowed' : 'pointer',
            transition: 'background 0.15s',
          }}
        >
          <span className={refreshing ? 'lr-spin' : ''} style={{ fontSize: 14 }}>↻</span>
          {refreshing ? 'Oppdaterer...' : 'Oppdater feed'}
        </button>
      </div>

      {/* Summary chips */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
        <SummaryChip label="lokaliteter" value={data?.total_count ?? localities.length} color="#374151" />
        <SummaryChip label="friske" value={data?.healthy_count ?? 0} color="#2e7d32" />
        <SummaryChip label="varsler" value={data?.warning_count ?? 0} color="#f57f17" />
        <SummaryChip label="kritiske" value={data?.critical_count ?? 0} color="#c62828" />
        {data?.last_updated && (
          <span style={{ fontSize: 11, color: '#9ca3af', alignSelf: 'center', marginLeft: 4 }}>
            Oppdatert: {formatSyncTime(data.last_updated)}
          </span>
        )}
      </div>

      {/* Filter row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginBottom: 16 }}>
        {/* Freshness filter pills */}
        <div style={{ display: 'flex', gap: 6 }}>
          {[
            { value: 'all',    label: 'Alle' },
            { value: 'fresh',  label: 'Fersk' },
            { value: 'stale',  label: 'Forsinket' },
            { value: 'failed', label: 'Feilet' },
          ].map(f => (
            <FilterPill key={f.value} label={f.label} active={filterFreshness === f.value} onClick={() => setFilterFreshness(f.value)} />
          ))}
        </div>

        <div style={{ width: 1, height: 24, background: '#e5e7eb' }} />

        {/* Risk direction filter */}
        <div style={{ display: 'flex', gap: 6 }}>
          {[
            { value: 'all',  label: 'Alle retninger' },
            { value: 'up',   label: '▲ Stigende' },
            { value: 'down', label: '▼ Fallende' },
          ].map(f => (
            <FilterPill key={f.value} label={f.label} active={filterRiskDirection === f.value} onClick={() => setFilterRiskDirection(f.value)} />
          ))}
        </div>

        {/* Sort selector */}
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          style={{ marginLeft: 'auto', padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 12 }}
        >
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <button
          onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}
          title="Bytt sorteringsretning"
          style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #d1d5db', background: 'white', cursor: 'pointer', fontSize: 13 }}
        >
          {sortDir === 'desc' ? '↓' : '↑'}
        </button>
      </div>

      {/* Refresh-in-progress banner */}
      {refreshing && (
        <div className="lr-refresh-banner">
          <span className="lr-spin">↻</span>
          Henter oppdaterte data fra alle kilder...
        </div>
      )}

      {/* Table */}
      {filtered.length === 0 ? (
        <p style={{ color: '#6b7280', fontStyle: 'italic', textAlign: 'center', padding: 32 }}>
          Ingen lokaliteter matcher filteret
        </p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                {[
                  'Lokalitet', 'Siste sync', 'Aktive kilder',
                  'Nye datapunkter', 'Risikopoeng', 'Endring 30d',
                  'Dominant domene', 'ILA', 'Tillit', '',
                ].map(h => (
                  <th key={h} style={{ padding: '9px 10px', textAlign: 'left', fontWeight: 600, color: '#374151', whiteSpace: 'nowrap' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((loc, i) => (
                <tr
                  key={loc.locality_id || i}
                  style={{ background: rowBackground(loc), borderBottom: '1px solid #f3f4f6', cursor: 'pointer' }}
                  onClick={() => onSelectLocality && onSelectLocality(loc.locality_id)}
                >
                  {/* Lokalitet */}
                  <td style={{ padding: '9px 10px' }}>
                    <div style={{ fontWeight: 700 }}>{loc.locality_name}</div>
                    {loc.locality_no && <div style={{ fontSize: 11, color: '#9ca3af' }}>BW {loc.locality_no}</div>}
                    {loc.operator && <div style={{ fontSize: 11, color: '#9ca3af' }}>{loc.operator}</div>}
                  </td>

                  {/* Siste sync */}
                  <td style={{ padding: '9px 10px', whiteSpace: 'nowrap' }}>
                    <div style={{ fontSize: 12, marginBottom: 3 }}>{formatSyncTime(loc.last_sync)}</div>
                    <FreshnessChip freshness={loc.sync_freshness} />
                  </td>

                  {/* Aktive kilder */}
                  <td style={{ padding: '9px 10px', textAlign: 'center' }}>
                    <span style={{ fontWeight: 600 }}>{Array.isArray(loc.active_sources) ? loc.active_sources.length : (loc.active_sources ?? '—')}</span>
                  </td>

                  {/* Nye datapunkter */}
                  <td style={{ padding: '9px 10px', textAlign: 'center' }}>
                    <span style={{ fontWeight: 600 }}>{loc.new_data_points ?? '—'}</span>
                  </td>

                  {/* Risikopoeng */}
                  <td style={{ padding: '9px 10px' }}>
                    <RiskBar score={loc.risk_score} />
                  </td>

                  {/* Endring 30d */}
                  <td style={{ padding: '9px 10px' }}>
                    <DeltaBadge delta={loc.risk_change_30d} />
                  </td>

                  {/* Dominant domene */}
                  <td style={{ padding: '9px 10px' }}>
                    {loc.dominant_domain ? <DomainChip domain={loc.dominant_domain} /> : <span style={{ color: '#9ca3af' }}>—</span>}
                  </td>

                  {/* ILA varselnivå */}
                  <td style={{ padding: '9px 10px' }}>
                    <IlaBadge varselniva={ilaByLocality[loc.locality_id]} />
                  </td>

                  {/* Tillit */}
                  <td style={{ padding: '9px 10px' }}>
                    {loc.confidence
                      ? <ConfidenceBadge level={loc.confidence} score={loc.confidence_score} showScore />
                      : <span style={{ color: '#9ca3af' }}>—</span>
                    }
                  </td>

                  {/* Action button */}
                  <td style={{ padding: '9px 10px' }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); onSelectLocality && onSelectLocality(loc.locality_id) }}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 6,
                        border: '1px solid #d1d5db',
                        background: 'white',
                        cursor: 'pointer',
                        fontWeight: 600,
                        fontSize: 14,
                      }}
                      title="Åpne detaljer"
                    >
                      &#8594;
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
