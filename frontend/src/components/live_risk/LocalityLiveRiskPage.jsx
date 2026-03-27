import React, { useState, useEffect } from 'react'
import ConfidenceBadge from './ConfidenceBadge.jsx'
import RawDataChart from './RawDataChart.jsx'
import RiskHistoryChart from './RiskHistoryChart.jsx'
import RiskChangeBreakdownPanel from './RiskChangeBreakdownPanel.jsx'
import SourceStatusPanel from './SourceStatusPanel.jsx'
import RiskEventsTimeline from './RiskEventsTimeline.jsx'
import EconomicsTab from './EconomicsTab.jsx'
import {
  fetchLiveRiskLocality,
  fetchLiveRiskTimeseries,
  fetchLiveRiskHistory,
  fetchLiveRiskSources,
  fetchLiveRiskBreakdown,
  fetchLiveRiskEvents,
  fetchLiveRiskConfidence,
  fetchLiveRiskCageImpact,
  fetchLiveRiskEconomics,
} from '../../api/client.js'

// Detail page for a single monitored locality — all data tabs with period selector

const PERIOD_OPTIONS = [
  { value: '7d',  label: '7 dager' },
  { value: '30d', label: '30 dager' },
  { value: '90d', label: '90 dager' },
  { value: '12m', label: '12 måneder' },
]

const TABS = [
  { key: 'timeseries', label: 'Rådata' },
  { key: 'risk',       label: 'Risikoutvikling' },
  { key: 'change',     label: 'Hva endret risikoen?' },
  { key: 'sources',    label: 'Datakilder' },
  { key: 'events',     label: 'Hendelser' },
  { key: 'confidence', label: 'Tillit' },
  { key: 'economics',  label: 'Økonomi' },
]

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

function formatTimestamp(isoStr) {
  if (!isoStr) return '—'
  const d = new Date(isoStr)
  return d.toLocaleString('nb-NO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function LoadingBlock({ label }) {
  return (
    <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>
      <div style={{ fontSize: 20, marginBottom: 6 }}>&#8987;</div>
      Laster {label}...
    </div>
  )
}

function ErrorBlock({ label, error, onRetry }) {
  return (
    <div style={{ padding: 16 }}>
      <div style={{ background: '#fdecea', color: '#c62828', padding: '10px 14px', borderRadius: 8, marginBottom: 10 }}>
        Feil ved lasting av {label}: {error}
      </div>
      {onRetry && (
        <button onClick={onRetry} style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #d1d5db', background: 'white', cursor: 'pointer' }}>
          Prøv igjen
        </button>
      )}
    </div>
  )
}

// ── Confidence detail view ───────────────────────────────────────────────────
function ConfidenceDetailView({ confidence }) {
  if (!confidence) return <p style={{ color: '#6b7280', fontStyle: 'italic' }}>Ingen tillitsdata tilgjengelig</p>

  const components = confidence.components || []
  const level = confidence.level || 'medium'
  const score = confidence.score

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <ConfidenceBadge level={level} score={score} showScore />
        {confidence.explanation && (
          <p style={{ color: '#6b7280', fontSize: 13 }}>{confidence.explanation}</p>
        )}
      </div>

      {components.length > 0 && (
        <div>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>Tillitskomponenter</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                {['Komponent', 'Score', 'Vekt', 'Forklaring'].map(h => (
                  <th key={h} style={{ padding: '7px 10px', textAlign: 'left', fontWeight: 600, color: '#374151' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {components.map((c, i) => {
                const pct = c.score != null ? Math.round(c.score * 100) : null
                const barColor = pct >= 70 ? '#2e7d32' : pct >= 40 ? '#f57f17' : '#c62828'
                return (
                  <tr key={i} style={{ borderBottom: '1px solid #f3f4f6', background: i % 2 === 0 ? 'white' : '#fafafa' }}>
                    <td style={{ padding: '7px 10px', fontWeight: 600 }}>{c.name || c.component}</td>
                    <td style={{ padding: '7px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 60, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ width: `${pct ?? 0}%`, height: '100%', background: barColor, borderRadius: 3 }} />
                        </div>
                        <span style={{ fontWeight: 700, color: barColor }}>{pct != null ? `${pct}%` : '—'}</span>
                      </div>
                    </td>
                    <td style={{ padding: '7px 10px', color: '#6b7280' }}>
                      {c.weight != null ? `${(c.weight * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td style={{ padding: '7px 10px', color: '#6b7280' }}>{c.explanation || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {confidence.data_coverage != null && (
        <p style={{ marginTop: 12, fontSize: 12, color: '#9ca3af' }}>
          Datadekning: {Math.round(confidence.data_coverage * 100)}%
          {confidence.computed_at && ` — beregnet ${formatTimestamp(confidence.computed_at)}`}
        </p>
      )}
    </div>
  )
}

// ── Cage impact section ─────────────────────────────────────────────────────
function CageImpactSection({ cageImpact }) {
  if (!cageImpact) return null
  const cages = cageImpact.cages || []
  if (cages.length === 0) return null

  return (
    <div style={{
      marginTop: 20,
      padding: '14px 16px',
      background: '#f9fafb',
      border: '1px solid #e5e7eb',
      borderRadius: 8,
    }}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>Merdeksponering</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
        {cages.map((cage, i) => (
          <div key={cage.cage_id || i} style={{
            background: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: 6,
            padding: '8px 12px',
            minWidth: 120,
          }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{cage.cage_id || `Merd ${i + 1}`}</div>
            {cage.risk_score != null && (
              <div style={{ fontSize: 12, color: '#6b7280' }}>Risiko: <b>{Math.round(cage.risk_score)}</b></div>
            )}
            {cage.biomass_kg != null && (
              <div style={{ fontSize: 11, color: '#9ca3af' }}>{(cage.biomass_kg / 1000).toFixed(1)} tonn</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function LocalityLiveRiskPage({ localityId, onBack }) {
  const [activeTab, setActiveTab] = useState('timeseries')
  const [period, setPeriod]       = useState('30d')

  // Data states
  const [locality, setLocality]       = useState(null)
  const [timeseries, setTimeseries]   = useState(null)
  const [riskHistory, setRiskHistory] = useState(null)
  const [sources, setSources]         = useState(null)
  const [breakdown, setBreakdown]     = useState(null)
  const [events, setEvents]           = useState(null)
  const [confidence, setConfidence]   = useState(null)
  const [cageImpact, setCageImpact]   = useState(null)
  const [economics, setEconomics]     = useState(null)

  // Loading states per endpoint
  const [loading, setLoading] = useState({
    locality: true, timeseries: true, riskHistory: true,
    sources: true, breakdown: true, events: true, confidence: true, economics: true,
  })
  // Error states per endpoint
  const [errors, setErrors] = useState({})

  const setEndpointLoading = (key, val) => setLoading(prev => ({ ...prev, [key]: val }))
  const setEndpointError   = (key, val) => setErrors(prev => ({ ...prev, [key]: val }))

  // Fetch static data (period-independent) on mount or localityId change
  useEffect(() => {
    if (!localityId) return

    setEndpointLoading('locality', true)
    fetchLiveRiskLocality(localityId)
      .then(d => { setLocality(d); setEndpointLoading('locality', false) })
      .catch(e => { setEndpointError('locality', e.message); setEndpointLoading('locality', false) })

    setEndpointLoading('sources', true)
    fetchLiveRiskSources(localityId)
      .then(d => { setSources(d); setEndpointLoading('sources', false) })
      .catch(e => { setEndpointError('sources', e.message); setEndpointLoading('sources', false) })

    setEndpointLoading('confidence', true)
    fetchLiveRiskConfidence(localityId)
      .then(d => { setConfidence(d); setEndpointLoading('confidence', false) })
      .catch(e => { setEndpointError('confidence', e.message); setEndpointLoading('confidence', false) })

    // Cage impact is optional — silent 404
    fetchLiveRiskCageImpact(localityId)
      .then(d => { setCageImpact(d) })
      .catch(() => { setCageImpact(null) })
  }, [localityId])

  // Fetch period-dependent data whenever period or locality changes
  useEffect(() => {
    if (!localityId) return

    setEndpointLoading('timeseries', true)
    setEndpointError('timeseries', null)
    fetchLiveRiskTimeseries(localityId, period)
      .then(d => { setTimeseries(d); setEndpointLoading('timeseries', false) })
      .catch(e => { setEndpointError('timeseries', e.message); setEndpointLoading('timeseries', false) })

    setEndpointLoading('riskHistory', true)
    setEndpointError('riskHistory', null)
    fetchLiveRiskHistory(localityId, period)
      .then(d => { setRiskHistory(d); setEndpointLoading('riskHistory', false) })
      .catch(e => { setEndpointError('riskHistory', e.message); setEndpointLoading('riskHistory', false) })

    setEndpointLoading('breakdown', true)
    setEndpointError('breakdown', null)
    fetchLiveRiskBreakdown(localityId, period)
      .then(d => { setBreakdown(d); setEndpointLoading('breakdown', false) })
      .catch(e => { setEndpointError('breakdown', e.message); setEndpointLoading('breakdown', false) })

    setEndpointLoading('events', true)
    setEndpointError('events', null)
    fetchLiveRiskEvents(localityId, period)
      .then(d => { setEvents(d); setEndpointLoading('events', false) })
      .catch(e => { setEndpointError('events', e.message); setEndpointLoading('events', false) })

    setEndpointLoading('economics', true)
    setEndpointError('economics', null)
    fetchLiveRiskEconomics(localityId, period)
      .then(d => { setEconomics(d); setEndpointLoading('economics', false) })
      .catch(e => { setEndpointError('economics', e.message); setEndpointLoading('economics', false) })
  }, [localityId, period])

  // ── Render helpers ─────────────────────────────────────────────────────────

  function renderTabContent() {
    switch (activeTab) {
      case 'timeseries':
        if (loading.timeseries) return <LoadingBlock label="rådata" />
        if (errors.timeseries) return <ErrorBlock label="rådata" error={errors.timeseries} onRetry={() => { setEndpointLoading('timeseries', true); fetchLiveRiskTimeseries(localityId, period).then(d => { setTimeseries(d); setEndpointLoading('timeseries', false) }).catch(e => { setEndpointError('timeseries', e.message); setEndpointLoading('timeseries', false) }) }} />
        return <RawDataChart series={timeseries?.raw_data || []} period={period} height={240} />

      case 'risk':
        if (loading.riskHistory) return <LoadingBlock label="risikohistorikk" />
        if (errors.riskHistory) return <ErrorBlock label="risikohistorikk" error={errors.riskHistory} />
        return <RiskHistoryChart history={riskHistory?.risk_history || []} period={period} />

      case 'change':
        if (loading.breakdown) return <LoadingBlock label="endringsdata" />
        if (errors.breakdown) return <ErrorBlock label="endringsdata" error={errors.breakdown} />
        return <RiskChangeBreakdownPanel breakdown={breakdown} />

      case 'sources':
        if (loading.sources) return <LoadingBlock label="datakilder" />
        if (errors.sources) return <ErrorBlock label="datakilder" error={errors.sources} />
        return <SourceStatusPanel sources={sources?.sources || sources || []} healthSummary={sources?.health_summary || 'ok'} />

      case 'events':
        if (loading.events) return <LoadingBlock label="hendelser" />
        if (errors.events) return <ErrorBlock label="hendelser" error={errors.events} />
        return <RiskEventsTimeline events={events?.events || events || []} />

      case 'confidence':
        if (loading.confidence) return <LoadingBlock label="tillitsdata" />
        if (errors.confidence) return <ErrorBlock label="tillitsdata" error={errors.confidence} />
        return <ConfidenceDetailView confidence={confidence} />

      case 'economics':
        if (loading.economics) return <LoadingBlock label="økonomidata" />
        if (errors.economics) return <ErrorBlock label="økonomidata" error={errors.economics} />
        return <EconomicsTab economics={economics} />

      default:
        return null
    }
  }

  // ── Main render ──────────────────────────────────────────────────────────
  return (
    <div className="lr-locality-page" style={{ padding: '16px 24px' }}>
      {/* Back button */}
      <button
        onClick={onBack}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--navy)',
          fontSize: 13,
          cursor: 'pointer',
          fontWeight: 600,
          marginBottom: 12,
          padding: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
        }}
      >
        &#8592; Tilbake til oversikt
      </button>

      {/* Locality header */}
      {loading.locality ? (
        <div style={{ color: '#9ca3af', fontSize: 13, marginBottom: 16 }}>Laster lokalitetsinfo...</div>
      ) : errors.locality ? (
        <div style={{ color: '#c62828', marginBottom: 16 }}>Feil: {errors.locality}</div>
      ) : locality ? (
        <div style={{
          background: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: 10,
          padding: '14px 18px',
          marginBottom: 16,
          display: 'flex',
          flexWrap: 'wrap',
          gap: 12,
          alignItems: 'center',
        }}>
          <div style={{ flex: 1, minWidth: 180 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 2 }}>{locality.locality_name}</h2>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              {locality.locality_no && <span>BW {locality.locality_no}</span>}
              {locality.operator && <span style={{ marginLeft: 8 }}>{locality.operator}</span>}
              {locality.region && <span style={{ marginLeft: 8, color: '#9ca3af' }}>{locality.region}</span>}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
            {locality.confidence && (
              <ConfidenceBadge level={locality.confidence} score={locality.confidence_score} showScore />
            )}
            {locality.last_sync && (
              <span style={{ fontSize: 11, color: '#9ca3af' }}>
                Sist oppdatert: {formatTimestamp(locality.last_sync)}
              </span>
            )}
          </div>
        </div>
      ) : null}

      {/* Period selector */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {PERIOD_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => setPeriod(opt.value)}
            style={{
              padding: '5px 14px',
              borderRadius: 20,
              border: period === opt.value ? '1.5px solid var(--navy)' : '1px solid #d1d5db',
              background: period === opt.value ? 'var(--navy)' : 'white',
              color: period === opt.value ? 'white' : '#374151',
              fontWeight: period === opt.value ? 700 : 400,
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Sub-tabs */}
      <div style={{
        display: 'flex',
        gap: 0,
        borderBottom: '2px solid #e5e7eb',
        marginBottom: 20,
        overflowX: 'auto',
      }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className="lr-tab"
            style={{
              padding: '8px 16px',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2.5px solid var(--navy)' : '2.5px solid transparent',
              background: 'none',
              fontWeight: activeTab === tab.key ? 700 : 400,
              color: activeTab === tab.key ? 'var(--navy)' : '#6b7280',
              fontSize: 13,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              marginBottom: -2,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content panel */}
      <div style={{
        background: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: 10,
        padding: '16px 18px',
        minHeight: 280,
      }}>
        {renderTabContent()}
      </div>

      {/* Optional cage impact section */}
      <CageImpactSection cageImpact={cageImpact} />
    </div>
  )
}
