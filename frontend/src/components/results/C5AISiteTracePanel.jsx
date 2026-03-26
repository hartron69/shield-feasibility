import React, { useState } from 'react'

// ── Domain display config ─────────────────────────────────────────────────────
const DOMAIN_CONFIG = {
  biological:    { label: 'Biologisk',    color: '#16a34a' },
  structural:    { label: 'Strukturell',  color: '#1d4ed8' },
  environmental: { label: 'Miljø',        color: '#0891b2' },
  operational:   { label: 'Operasjonell', color: '#9333ea' },
}

// ── Source badge config ───────────────────────────────────────────────────────
const SOURCE_CONFIG = {
  c5ai_plus: { label: 'C5AI+',    bg: '#dcfce7', color: '#166534', title: 'Beregnet fra C5AI+-prognose' },
  estimated: { label: 'Estimert', bg: '#fef3c7', color: '#92400e', title: 'Estimert fra stub-modell (ekspertprioritet, ikke lokalitetsspesifikk)' },
}

// ── Confidence display ────────────────────────────────────────────────────────
const CONFIDENCE_CONFIG = {
  'Middels':     { bg: '#fef3c7', color: '#92400e' },
  'Lav–Middels': { bg: '#fff7ed', color: '#9a3412' },
  'Lav':         { bg: '#fee2e2', color: '#991b1b' },
}

function fmt(nok) {
  if (nok >= 1_000_000) return `NOK ${(nok / 1_000_000).toFixed(1)}M`
  if (nok >= 1_000) return `NOK ${(nok / 1_000).toFixed(0)}k`
  return `NOK ${Math.round(nok)}`
}

function SourceBadge({ source }) {
  const cfg = SOURCE_CONFIG[source] || SOURCE_CONFIG.estimated
  return (
    <span
      className="transparency-source-badge"
      style={{ background: cfg.bg, color: cfg.color }}
      title={cfg.title}
    >
      {cfg.label}
    </span>
  )
}

function ConfidencePill({ score, label }) {
  const cfg = CONFIDENCE_CONFIG[label] || CONFIDENCE_CONFIG['Lav']
  const pct = Math.round((score || 0) * 100)
  return (
    <span
      className="transparency-confidence-pill"
      style={{ background: cfg.bg, color: cfg.color }}
      title={`Konfidenspoeng: ${pct}/100. Basert på datakilde og modellbegrensninger.`}
    >
      {label} ({pct}%)
    </span>
  )
}

function DomainSourceRow({ domain, source }) {
  const dcfg = DOMAIN_CONFIG[domain] || { label: domain, color: '#6b7280' }
  return (
    <div className="domain-source-row">
      <span className="domain-dot" style={{ background: dcfg.color }} />
      <span className="domain-source-label">{dcfg.label}</span>
      <SourceBadge source={source} />
    </div>
  )
}

export default function C5AISiteTracePanel({ siteTrace, onNavigateToRisk }) {
  const [open, setOpen] = useState(false)
  const [expandedSite, setExpandedSite] = useState(null)

  if (!siteTrace || siteTrace.length === 0) return null

  // All sites share the same domain_sources (model is portfolio-level)
  const sharedDomainSources = siteTrace[0]?.domain_sources || {}
  const allDomainsEstimated = Object.values(sharedDomainSources).every(s => s === 'estimated')
  const hasC5AIBio = sharedDomainSources['biological'] === 'c5ai_plus'

  return (
    <div className="site-trace-panel">
      {/* ── Toggle header ─────────────────────────────────────────────────── */}
      <button className="site-trace-toggle" onClick={() => setOpen(o => !o)}>
        <span>Anlegg i analysen ({siteTrace.length})</span>
        <span className="site-trace-chevron">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="site-trace-body">

          {/* ── Portfolio-level disclaimer ──────────────────────────────────── */}
          <div className="transparency-disclaimer">
            <span className="transparency-disclaimer-icon">ℹ</span>
            <div>
              <strong>Domenebryting er porteføljebasert, ikke lokalitetsspesifikk.</strong>
              {' '}Alle anlegg er tildelt samme domenemix, vektet etter anleggets tapsbidrag.
              Per-anlegg domenefordeling er en proporsjonal approksimering.
            </div>
          </div>

          {/* ── Domain source legend ────────────────────────────────────────── */}
          <div className="transparency-legend">
            <div className="transparency-legend-title">Datakilde per domene</div>
            <div className="transparency-legend-grid">
              {Object.entries(sharedDomainSources).map(([domain, source]) => (
                <DomainSourceRow key={domain} domain={domain} source={source} />
              ))}
            </div>
            {hasC5AIBio && (
              <div className="transparency-legend-note">
                Biologisk domene er informert av C5AI+-prognose.
                Strukturell, miljø og operasjonell bruker stub-estimater (ekspertprioritet).
              </div>
            )}
            {allDomainsEstimated && (
              <div className="transparency-legend-note transparency-legend-note--warn">
                Ingen C5AI+-prognose ble aktivert. Alle domener er estimert fra
                static template-modell.
              </div>
            )}
          </div>

          {/* ── Per-site table ──────────────────────────────────────────────── */}
          <table className="site-trace-table">
            <thead>
              <tr>
                <th>Anlegg</th>
                <th>Domene</th>
                <th>Forv. tap/år</th>
                <th>SCR-bidrag</th>
                <th>Konfidens</th>
              </tr>
            </thead>
            <tbody>
              {siteTrace.map(s => {
                const isExpanded = expandedSite === s.site_id
                const dcfg = DOMAIN_CONFIG[s.dominant_domain] || { label: s.dominant_domain, color: '#6b7280' }
                return (
                  <React.Fragment key={s.site_id}>
                    <tr
                      className={`site-trace-row ${isExpanded ? 'site-trace-row--expanded' : ''}`}
                      onClick={() => setExpandedSite(isExpanded ? null : s.site_id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>
                        <div style={{ fontWeight: 600, fontSize: 12 }}>{s.site_name}</div>
                        <div style={{ fontSize: 10, color: '#6b7280' }}>{s.site_id}</div>
                        {s.locality_no && (
                          <div style={{ fontSize: 9, color: '#9ca3af' }}>BW: {s.locality_no}</div>
                        )}
                      </td>
                      <td>
                        <span className="domain-pill" style={{ background: dcfg.color }}>
                          {dcfg.label || s.dominant_domain || '—'}
                        </span>
                        <span style={{ fontSize: 9, color: '#9ca3af', display: 'block', marginTop: 2 }}>
                          {sharedDomainSources[s.dominant_domain] === 'c5ai_plus' ? 'C5AI+' : 'Estimert'}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, textAlign: 'right' }}>{fmt(s.expected_annual_loss_nok)}</td>
                      <td style={{ fontSize: 12, textAlign: 'right', color: '#6b7280' }}>
                        {fmt(s.scr_contribution_nok)}
                        <span style={{ fontSize: 9, display: 'block', color: '#9ca3af' }}>approks.</span>
                      </td>
                      <td>
                        <ConfidencePill score={s.confidence_score} label={s.confidence_label} />
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="site-trace-detail-row">
                        <td colSpan={5}>
                          <div className="site-trace-detail">
                            <div className="site-trace-detail-title">Domenefordeling for {s.site_name}</div>
                            <div className="site-trace-detail-grid">
                              {Object.entries(sharedDomainSources).map(([domain, source]) => {
                                const dcfg2 = DOMAIN_CONFIG[domain] || { label: domain, color: '#6b7280' }
                                return (
                                  <div key={domain} className="site-trace-detail-cell">
                                    <span className="domain-dot" style={{ background: dcfg2.color }} />
                                    <span style={{ fontSize: 11, fontWeight: 500 }}>{dcfg2.label}</span>
                                    <SourceBadge source={source} />
                                  </div>
                                )
                              })}
                            </div>
                            <div className="site-trace-detail-note">
                              Domenevektene er porteføljens gjennomsnitt fordelt proporsjonalt til dette anlegget.
                              Anleggets faktiske eksponering kan avvike, særlig for åpen kyst vs. skjermet fjord.
                            </div>
                            {s.locality_no && (
                              <div style={{ marginTop: 8, fontSize: 11, color: '#475569' }}>
                                BarentsWatch lokalitet: <code style={{ fontFamily: 'monospace', background: '#f1f5f9', padding: '1px 5px', borderRadius: 3 }}>{s.locality_no}</code>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>

          {/* ── Footer ──────────────────────────────────────────────────────── */}
          <div className="site-trace-footer">
            <div className="site-trace-note">
              <strong>EAL:</strong> eksakt (Monte Carlo, TIV-vektet).
              {' '}<strong>SCR-bidrag:</strong> proporsjonal approksimering av portefølje-SCR.
              {' '}<strong>Domenebryting:</strong> porteføljebasert approksimering — ikke lokalitetsspesifikk.
            </div>
            {onNavigateToRisk && (
              <button className="site-trace-cta" onClick={() => onNavigateToRisk('risk', 'risiko')}>
                Se anlegg i C5AI+ Risiko →
              </button>
            )}
          </div>

        </div>
      )}
    </div>
  )
}
