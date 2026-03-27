import React, { useState } from 'react'

const RISK_TYPES = ['hab', 'lice', 'jellyfish', 'pathogen']

const RISK_META = {
  hab:       { label: 'Skadelig algeblomst (HAB)', abbr: 'HAB',    emoji: '🟡', desc: 'Chrysochromulina, Karenia og beslektede arter' },
  lice:      { label: 'Lakselusinfeksjon',          abbr: 'Lus',    emoji: '🟢', desc: 'Lepeophtheirus salmonis og Caligus spp.' },
  jellyfish: { label: 'Manetoppblomst',             abbr: 'Manet',  emoji: '🔵', desc: 'Aurelia, Cyanea og Pelagia-blomster' },
  pathogen:  { label: 'Patogen / sykdom',           abbr: 'Patogen',emoji: '🔴', desc: 'ILA, PD, Moritella, Aeromonas og beslektede' },
}

const TREND_LABELS = {
  increasing: 'Stigende',
  decreasing: 'Synkende',
  stable:     'Stabil',
}

function fmtM(v) {
  if (v == null || v === 0) return '—'
  if (v >= 1_000_000) return `NOK ${(v / 1_000_000).toFixed(1)}M`
  return `NOK ${(v / 1_000).toFixed(0)}k`
}

function pctStr(v) {
  return `${(v * 100).toFixed(0)}%`
}

function probClass(p) {
  if (p >= 0.30) return 'high'
  if (p >= 0.15) return 'medium'
  return 'low'
}

function probBarClass(p) {
  if (p >= 0.30) return 'prob-high'
  if (p >= 0.15) return 'prob-medium'
  return 'prob-low'
}

function ProbBar({ p }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div className="prob-bar-outer" style={{ flex: 1 }}>
        <div className={`prob-bar-inner ${probBarClass(p)}`} style={{ width: `${p * 100}%` }} />
      </div>
      <span style={{ fontWeight: 700, fontSize: 13, width: 36, textAlign: 'right' }}>{pctStr(p)}</span>
    </div>
  )
}

function modelBadgeClass(model) {
  if (model && model.startsWith('ml_')) return 'model-ml'
  if (model === 'prior_fallback') return 'model-prior_fallback'
  return 'model-prior'
}

function modelBadgeLabel(model) {
  if (!model) return 'prior'
  if (model.startsWith('ml_')) return 'ML-modell'
  if (model === 'prior_fallback') return 'prior (reserve)'
  return 'prior'
}

// Aggregate a field across sites for a given risk type
function aggregate(forecast, riskType, field) {
  const vals = forecast.map(sf => sf[riskType][field]).filter(v => v != null)
  if (!vals.length) return null
  return vals.reduce((a, b) => a + b, 0) / vals.length
}

function sumField(forecast, riskType, field) {
  return forecast.map(sf => sf[riskType][field] || 0).reduce((a, b) => a + b, 0)
}

export default function BiologicalForecastTab({ data }) {
  const { biological_forecast: forecast } = data
  const [selectedSite, setSelectedSite] = useState('all')

  const sites = forecast.map(sf => ({ id: sf.site_id, name: sf.site_name }))
  const displayForecast = selectedSite === 'all' ? forecast : forecast.filter(sf => sf.site_id === selectedSite)

  return (
    <div>
      {/* ── Site filter ──────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        <button
          className={`tab-btn ${selectedSite === 'all' ? 'active' : ''}`}
          style={{ borderRadius: 6, border: '1px solid var(--mid-grey)', padding: '6px 14px' }}
          onClick={() => setSelectedSite('all')}
        >Alle anlegg</button>
        {sites.map(s => (
          <button
            key={s.id}
            className={`tab-btn ${selectedSite === s.id ? 'active' : ''}`}
            style={{ borderRadius: 6, border: '1px solid var(--mid-grey)', padding: '6px 14px' }}
            onClick={() => setSelectedSite(s.id)}
          >{s.name}</button>
        ))}
      </div>

      {/* ── Risk type cards ──────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16, marginBottom: 24 }}>
        {RISK_TYPES.map(rt => {
          const meta = RISK_META[rt]
          const avgP      = aggregate(displayForecast, rt, 'probability')
          const totalLoss = sumField(displayForecast, rt, 'expected_loss_mean')
          const sumP90    = sumField(displayForecast, rt, 'expected_loss_p90')
          const trend     = displayForecast[0]?.[rt]?.trend || 'stable'
          const model     = displayForecast[0]?.[rt]?.model_used || 'prior'
          const conf      = aggregate(displayForecast, rt, 'confidence_score')
          const pc = probClass(avgP)

          return (
            <div key={rt} className={`risk-type-card ${rt}`}>
              <div className="risk-type-header">
                <div>
                  <div className="risk-type-name">{meta.emoji} {meta.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginTop: 2 }}>{meta.desc}</div>
                </div>
                <span className={`trend-badge trend-${trend}`}>
                  {trend === 'increasing' ? '↑' : trend === 'decreasing' ? '↓' : '→'}{' '}
                  {TREND_LABELS[trend] || trend}
                </span>
              </div>

              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--dark-grey)', marginBottom: 4 }}>
                  Årlig hendelsessannsynlighet
                  <span style={{
                    marginLeft: 8, fontWeight: 700,
                    color: pc === 'high' ? 'var(--danger)' : pc === 'medium' ? '#92400E' : 'var(--success)'
                  }}>
                    {pc === 'high' ? 'HØY' : pc === 'medium' ? 'MODERAT' : 'LAV'}
                  </span>
                </div>
                <ProbBar p={avgP || 0} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>Forv. tap/år</div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{fmtM(totalLoss)}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>P90-tap</div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{fmtM(sumP90)}</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                <span className={`model-badge ${modelBadgeClass(model)}`}>{modelBadgeLabel(model)}</span>
                {conf != null && (
                  <span className="badge badge-cost">Modellsikkerhet {(conf * 100).toFixed(0)}%</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Per-site breakdown table ─────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Fordeling per anlegg</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Anlegg</th>
              {RISK_TYPES.map(rt => (
                <th key={rt}>{RISK_META[rt].abbr} sannsynl.</th>
              ))}
              {RISK_TYPES.map(rt => (
                <th key={rt + '_loss'}>{RISK_META[rt].abbr} forv. tap</th>
              ))}
              <th>Sum forventet tap</th>
            </tr>
          </thead>
          <tbody>
            {displayForecast.map(sf => {
              const siteTotalLoss = RISK_TYPES.reduce((s, rt) => s + (sf[rt].expected_loss_mean || 0), 0)
              return (
                <tr key={sf.site_id}>
                  <td style={{ fontWeight: 600 }}>{sf.site_name}</td>
                  {RISK_TYPES.map(rt => {
                    const p  = sf[rt].probability
                    const pc = probClass(p)
                    return (
                      <td key={rt}>
                        <span style={{
                          fontWeight: 700,
                          color: pc === 'high' ? 'var(--danger)' : pc === 'medium' ? '#92400E' : 'var(--success)'
                        }}>
                          {pctStr(p)}
                        </span>
                      </td>
                    )
                  })}
                  {RISK_TYPES.map(rt => (
                    <td key={rt + '_loss'}>{fmtM(sf[rt].expected_loss_mean)}</td>
                  ))}
                  <td style={{ fontWeight: 700 }}>{fmtM(siteTotalLoss)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── Bayesian enrichment note ─────────────────────────────────────── */}
      <div className="info-note">
        <strong>Bayesiansk berikelse:</strong> Sannsynlighetene er posterior-estimater fra C5AI+-læringsmodellen.
        Der <em>justert sannsynlighet</em> avviker fra den statiske prioren, har modellen tatt inn
        historiske observasjoner fra dette anlegget og justert det strategiske risikobildet tilsvarende.
        Gå til Læringsmodell-fanen for å se Brier-skår-konvergens over treningssykluser.
      </div>
    </div>
  )
}
