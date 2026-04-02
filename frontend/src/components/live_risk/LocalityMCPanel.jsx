import React, { useState, useEffect } from 'react'
import { fetchLocalityMC } from '../../api/client.js'

// Monte Carlo simulation panel — EAL, SCR, domain breakdown for a single locality

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

const DOMAINS = ['biological', 'structural', 'environmental', 'operational']

function fmt(nok) {
  if (nok == null) return '—'
  if (nok >= 1_000_000) return `${(nok / 1_000_000).toFixed(1)} MNOK`
  if (nok >= 1_000)     return `${(nok / 1_000).toFixed(0)} kNOK`
  return `${Math.round(nok)} NOK`
}

// ── Pure SVG stacked bar for domain fractions ────────────────────────────────
function DomainBar({ fractions, width = 420, height = 28 }) {
  if (!fractions) return null
  const total = DOMAINS.reduce((s, d) => s + (fractions[d] ?? 0), 0)
  if (total < 1e-9) return null

  let x = 0
  return (
    <svg width={width} height={height} style={{ display: 'block', borderRadius: 4, overflow: 'hidden' }}>
      {DOMAINS.map(d => {
        const pct = (fractions[d] ?? 0) / total
        const w   = pct * width
        const rect = (
          <rect key={d} x={x} y={0} width={w} height={height} fill={DOMAIN_COLORS[d]} />
        )
        x += w
        return rect
      })}
    </svg>
  )
}

// ── KPI card ────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, highlight }) {
  return (
    <div style={{
      background: highlight ? '#f0f4ff' : '#f9fafb',
      border: `1px solid ${highlight ? '#bfcdff' : '#e5e7eb'}`,
      borderRadius: 8,
      padding: '12px 16px',
      minWidth: 130,
      flex: '1 1 130px',
    }}>
      <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: highlight ? '#1e3a8a' : '#111827' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

// ── Transparency table ───────────────────────────────────────────────────────
function TransparencyTable({ mc }) {
  const rows = [
    ['Base frekvens',          mc.base_expected_events?.toFixed(4),    'hendelser/år'],
    ['Frekvens-multiplier',    mc.frequency_multiplier?.toFixed(4),    '(score-drevet)'],
    ['Effektiv frekvens',      mc.effective_expected_events?.toFixed(4),'hendelser/år'],
    ['Base alvorlighet',       fmt(mc.base_mean_severity_nok),         ''],
    ['Alvorlighet-multiplier', mc.severity_multiplier?.toFixed(4),     '(score-drevet)'],
    ['Effektiv alvorlighet',   fmt(mc.effective_mean_severity_nok),    ''],
    ['Total risikoscore',      mc.total_risk_score?.toFixed(1),        '/100'],
    ['Simuleringer',           mc.n_simulations?.toLocaleString('nb'), ''],
    ['Domenekorreler',         mc.domain_correlation_applied ? 'Ja' : 'Nei', ''],
  ]

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, marginTop: 8 }}>
      <tbody>
        {rows.map(([label, value, unit]) => (
          <tr key={label} style={{ borderBottom: '1px solid #f3f4f6' }}>
            <td style={{ padding: '5px 10px', color: '#6b7280', width: '42%' }}>{label}</td>
            <td style={{ padding: '5px 10px', fontWeight: 600, color: '#111827' }}>{value ?? '—'}</td>
            <td style={{ padding: '5px 10px', color: '#9ca3af' }}>{unit}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ── Domain breakdown table ───────────────────────────────────────────────────
function DomainBreakdownTable({ domainEal, domainFractions }) {
  if (!domainEal || !domainFractions) return null

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>Domenebidrag</div>
      <DomainBar fractions={domainFractions} />
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
        {DOMAINS.map(d => (
          <div key={d} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: DOMAIN_COLORS[d] }} />
            <span style={{ color: '#374151' }}>{DOMAIN_LABELS[d]}</span>
            <span style={{ fontWeight: 700 }}>{fmt(domainEal[d])}</span>
            <span style={{ color: '#9ca3af' }}>({((domainFractions[d] ?? 0) * 100).toFixed(1)}%)</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main panel ───────────────────────────────────────────────────────────────
export default function LocalityMCPanel({ localityId }) {
  const [mc,      setMc]      = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [nSims,   setNSims]   = useState(5000)
  const [showTransparency, setShowTransparency] = useState(false)

  function run() {
    setLoading(true)
    setError(null)
    setMc(null)
    fetchLocalityMC(localityId, nSims)
      .then(d => { setMc(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }

  useEffect(() => {
    if (localityId) run()
  }, [localityId]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      {/* Controls row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <label style={{ fontSize: 13, color: '#374151' }}>
          Simuleringer:
          <select
            value={nSims}
            onChange={e => setNSims(Number(e.target.value))}
            style={{ marginLeft: 8, padding: '3px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 13 }}
          >
            {[1000, 2000, 5000, 10000].map(n => (
              <option key={n} value={n}>{n.toLocaleString('nb')}</option>
            ))}
          </select>
        </label>
        <button
          onClick={run}
          disabled={loading}
          style={{
            padding: '5px 16px',
            borderRadius: 6,
            border: '1px solid var(--navy)',
            background: loading ? '#e5e7eb' : 'var(--navy)',
            color: loading ? '#6b7280' : 'white',
            fontWeight: 600,
            fontSize: 13,
            cursor: loading ? 'default' : 'pointer',
          }}
        >
          {loading ? 'Kjører...' : 'Kjør simulering'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ background: '#fdecea', color: '#c62828', padding: '10px 14px', borderRadius: 8, marginBottom: 12, fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af', fontSize: 13 }}>
          &#8987; Kjører Monte Carlo ({nSims.toLocaleString('nb')} simuleringer)...
        </div>
      )}

      {/* Results */}
      {mc && !loading && (
        <div>
          {/* KPI row */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
            <KpiCard
              label="Forventet årlig tap (EAL)"
              value={fmt(mc.eal_nok)}
              sub="E[annual loss]"
              highlight
            />
            <KpiCard
              label="Kapitalankre (SCR)"
              value={fmt(mc.scr_nok)}
              sub="VaR 99.5%"
              highlight
            />
            <KpiCard
              label="VaR 99%"
              value={fmt(mc.var_99_nok)}
            />
            <KpiCard
              label="VaR 95%"
              value={fmt(mc.var_95_nok)}
            />
            <KpiCard
              label="Std. avvik"
              value={fmt(mc.std_nok)}
              sub="årlig tap"
            />
            <KpiCard
              label="TVaR 95%"
              value={fmt(mc.tvar_95_nok)}
              sub="halesensitivitet"
            />
          </div>

          {/* Domain breakdown */}
          <DomainBreakdownTable
            domainEal={mc.domain_eal_nok}
            domainFractions={mc.domain_fractions}
          />

          {/* Transparency toggle */}
          <div style={{ marginTop: 16 }}>
            <button
              onClick={() => setShowTransparency(v => !v)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--navy)',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                padding: 0,
              }}
            >
              {showTransparency ? '▲ Skjul simuleringsdetaljer' : '▼ Vis simuleringsdetaljer'}
            </button>
            {showTransparency && <TransparencyTable mc={mc} />}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!mc && !loading && !error && (
        <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af', fontSize: 13 }}>
          Klikk «Kjør simulering» for å beregne stokastisk tapsfordeling
        </div>
      )}
    </div>
  )
}
