import React, { useState } from 'react'

// ── Formatting helpers ────────────────────────────────────────────────────────

function fmtNOK(v) {
  if (v == null || isNaN(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1_000_000) return `NOK ${(v / 1_000_000).toFixed(1)} M`
  if (abs >= 1_000)     return `NOK ${(v / 1_000).toFixed(0)} k`
  return `NOK ${Number(v).toFixed(0)}`
}

function fmtDelta(v) {
  if (v == null || isNaN(v)) return '—'
  const abs = Math.abs(v)
  const sign = v < 0 ? '▼ ' : v > 0 ? '▲ ' : ''
  const color = v < 0 ? 'var(--success)' : v > 0 ? 'var(--danger)' : 'var(--dark-grey)'
  const label = abs >= 1_000_000
    ? `${sign}NOK ${(abs / 1_000_000).toFixed(1)} M`
    : abs >= 1_000
      ? `${sign}NOK ${(abs / 1_000).toFixed(0)} k`
      : `${sign}NOK ${abs.toFixed(0)}`
  return { label, color }
}

// ── Domain colours & labels ───────────────────────────────────────────────────

const DOMAIN_COLORS = {
  biological:   '#1A6B6B',
  environmental:'#2E6EA6',
  structural:   '#C0392B',
  operational:  '#E67E22',
}

const DOMAIN_LABELS = {
  biological:   'Biologisk',
  environmental:'Miljø',
  structural:   'Strukturell',
  operational:  'Operasjonell',
}

function DomainBadge({ domain }) {
  const c = DOMAIN_COLORS[domain] || '#666'
  const l = DOMAIN_LABELS[domain] || domain
  return (
    <span style={{
      background: c + '22', border: `1px solid ${c}55`, color: c,
      borderRadius: 4, padding: '1px 6px', fontSize: 11, fontWeight: 600,
    }}>
      {l}
    </span>
  )
}

// ── Mini horizontal bar (pure SVG) ───────────────────────────────────────────

function MiniBar({ value, max, color }) {
  const pct = max > 0 ? Math.min(value / max, 1) * 100 : 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ flex: 1, background: 'var(--mid-grey)', borderRadius: 3, height: 6, minWidth: 60 }}>
        <div style={{ width: `${pct}%`, height: 6, borderRadius: 3, background: color || 'var(--teal)' }} />
      </div>
      <span style={{ fontSize: 11, minWidth: 60, textAlign: 'right' }}>{fmtNOK(value)}</span>
    </div>
  )
}

// ── Stacked domain bar ────────────────────────────────────────────────────────

function DomainBar({ breakdown, total }) {
  if (!breakdown || total <= 0) return null
  const domains = ['biological', 'environmental', 'structural', 'operational']
  let x = 0
  const segments = domains
    .filter(d => breakdown[d] > 0)
    .map(d => {
      const w = (breakdown[d] / total) * 100
      const seg = { d, w, x }
      x += w
      return seg
    })
  return (
    <div style={{ position: 'relative', height: 8, borderRadius: 4, overflow: 'hidden', background: '#eee', width: '100%', minWidth: 80 }}>
      {segments.map(({ d, w, x: sx }) => (
        <div key={d} style={{
          position: 'absolute', left: `${sx}%`, width: `${w}%`, height: '100%',
          background: DOMAIN_COLORS[d] || '#aaa',
        }} title={`${DOMAIN_LABELS[d] || d}: ${w.toFixed(0)}%`} />
      ))}
    </div>
  )
}

// ── KPI cards ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, delta, color }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ fontSize: 16, color: color || 'var(--dark-grey)' }}>
        {fmtNOK(value)}
      </div>
      {delta != null && (() => {
        const d = fmtDelta(delta)
        return (
          <div style={{ fontSize: 11, color: d.color, fontWeight: 600, marginTop: 2 }}>
            {d.label}
          </div>
        )
      })()}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SeaSiteLossTable({ lossAnalysis, baseline, mitigated }) {
  const [expandedSite, setExpandedSite] = useState(null)

  if (!lossAnalysis || !lossAnalysis.per_site || lossAnalysis.per_site.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', color: '#888', padding: 32 }}>
        Ingen tapsanalyse tilgjengelig ennå. Kjør analyse på nytt eller kontroller backend loss_analysis-respons.
      </div>
    )
  }

  const { per_site, per_domain, top_drivers, mitigated: mit_block, method_note } = lossAnalysis

  const totalEAL = per_site.reduce((s, r) => s + (r.expected_annual_loss_nok || 0), 0)
  const totalSCR = per_site.reduce((s, r) => s + (r.scr_contribution_nok || 0), 0)
  const maxEAL   = Math.max(...per_site.map(r => r.expected_annual_loss_nok || 0), 1)

  const hasMit = !!mit_block && (mit_block.per_site || []).length > 0
  const mitTotalEAL = hasMit ? (mit_block.per_site || []).reduce((s, r) => s + (r.expected_annual_loss_nok || 0), 0) : null

  // Build mitigated EAL map for per-site delta column
  const mitEALMap = {}
  if (hasMit) {
    for (const r of mit_block.per_site) {
      mitEALMap[r.site_id] = r.expected_annual_loss_nok
    }
  }

  const domainOrder = ['biological', 'environmental', 'structural', 'operational']
  const domainTotal = domainOrder.reduce((s, d) => s + (per_domain[d] || 0), 0)

  return (
    <div>
      {/* ── KPI summary row ─────────────────────────────────────────────── */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', marginBottom: 16 }}>
        <KpiCard
          label="Forv. tap/år (EAL)"
          value={totalEAL}
          delta={hasMit ? mit_block.delta_total_eal_nok : null}
        />
        <KpiCard
          label="SCR (portefølje)"
          value={totalSCR}
          delta={hasMit ? mit_block.delta_total_scr_nok : null}
        />
        {hasMit && (
          <KpiCard
            label="EAL med tiltak"
            value={mitTotalEAL}
            color="var(--teal)"
          />
        )}
        <div className="kpi-card">
          <div className="kpi-label">Antall anlegg</div>
          <div className="kpi-value" style={{ fontSize: 16 }}>{per_site.length}</div>
        </div>
      </div>

      {/* ── Domain breakdown bar ─────────────────────────────────────────── */}
      {domainTotal > 0 && (
        <div className="card">
          <div className="section-title">Domenefordeling</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
            <div style={{ flex: 1 }}>
              <DomainBar breakdown={per_domain} total={domainTotal} />
            </div>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 12 }}>
            {domainOrder.filter(d => per_domain[d] > 0).map(d => (
              <div key={d} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: DOMAIN_COLORS[d] }} />
                <span style={{ color: 'var(--dark-grey)' }}>{DOMAIN_LABELS[d]}</span>
                <span style={{ fontWeight: 700 }}>{fmtNOK(per_domain[d])}</span>
                <span style={{ color: '#aaa' }}>({domainTotal > 0 ? ((per_domain[d] / domainTotal) * 100).toFixed(0) : 0}%)</span>
                {hasMit && mit_block.per_domain[d] != null && (() => {
                  const delta = mit_block.per_domain[d] - per_domain[d]
                  const df = fmtDelta(delta)
                  return <span style={{ fontSize: 11, color: df.color, fontWeight: 600 }}>{df.label}</span>
                })()}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Per-site table ───────────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Per-anlegg tapsbidrag</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Lokalitet</th>
                <th>EAL/år</th>
                <th>EAL andel</th>
                <th>SCR-bidrag</th>
                <th>SCR-andel</th>
                <th>Dom. risiko</th>
                <th>Domenemix</th>
                {hasMit && <th>Med tiltak</th>}
              </tr>
            </thead>
            <tbody>
              {per_site.map((fr, i) => {
                const isExpanded = expandedSite === i
                const hasBreakdown = fr.domain_breakdown && Object.keys(fr.domain_breakdown).some(k => fr.domain_breakdown[k] > 0)
                const mitEAL = mitEALMap[fr.site_id]
                const mitDelta = mitEAL != null ? mitEAL - fr.expected_annual_loss_nok : null
                const df = mitDelta != null ? fmtDelta(mitDelta) : null

                return (
                  <React.Fragment key={fr.site_id}>
                    <tr
                      style={{ cursor: hasBreakdown ? 'pointer' : 'default' }}
                      onClick={() => hasBreakdown && setExpandedSite(isExpanded ? null : i)}
                    >
                      <td style={{ fontWeight: 600 }}>
                        {hasBreakdown && (
                          <span style={{ marginRight: 6, color: '#94a3b8', fontSize: 10 }}>
                            {isExpanded ? '▼' : '▶'}
                          </span>
                        )}
                        {fr.site_name}
                      </td>
                      <td>
                        <MiniBar value={fr.expected_annual_loss_nok} max={maxEAL} color={DOMAIN_COLORS[fr.dominant_domain]} />
                      </td>
                      <td style={{ color: 'var(--dark-grey)', fontSize: 12 }}>
                        {totalEAL > 0 ? ((fr.expected_annual_loss_nok / totalEAL) * 100).toFixed(1) : 0}%
                      </td>
                      <td>{fmtNOK(fr.scr_contribution_nok)}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ flex: 1, background: 'var(--mid-grey)', borderRadius: 3, height: 6, minWidth: 60 }}>
                            <div style={{ width: `${fr.scr_share_pct}%`, height: 6, borderRadius: 3, background: '#7c3aed' }} />
                          </div>
                          <span style={{ fontSize: 11 }}>{fr.scr_share_pct?.toFixed(1)}%</span>
                        </div>
                      </td>
                      <td><DomainBadge domain={fr.dominant_domain} /></td>
                      <td style={{ minWidth: 90 }}>
                        {hasBreakdown && <DomainBar breakdown={fr.domain_breakdown} total={fr.expected_annual_loss_nok} />}
                      </td>
                      {hasMit && (
                        <td style={{ fontWeight: 700, color: df ? df.color : 'var(--dark-grey)', fontSize: 12 }}>
                          {df ? df.label : '—'}
                        </td>
                      )}
                    </tr>
                    {isExpanded && hasBreakdown && (
                      <tr>
                        <td colSpan={hasMit ? 8 : 7} style={{ padding: '4px 10px 10px 28px', background: '#f8fafc' }}>
                          <table style={{ width: '100%', fontSize: 11 }}>
                            <tbody>
                              {domainOrder.filter(d => fr.domain_breakdown[d] > 0).map(d => {
                                const mitDomRow = hasMit && mit_block.per_site.find(s => s.site_id === fr.site_id)
                                const mitDomVal = mitDomRow?.domain_breakdown?.[d]
                                const dDelta = mitDomVal != null ? fmtDelta(mitDomVal - fr.domain_breakdown[d]) : null
                                return (
                                  <tr key={d}>
                                    <td style={{ padding: '2px 8px', color: DOMAIN_COLORS[d] }}>
                                      └ {DOMAIN_LABELS[d]}
                                    </td>
                                    <td style={{ padding: '2px 8px', textAlign: 'right' }}>
                                      {fmtNOK(fr.domain_breakdown[d])}
                                    </td>
                                    {dDelta && (
                                      <td style={{ padding: '2px 8px', textAlign: 'right', color: dDelta.color, fontWeight: 600, fontSize: 11 }}>
                                        {dDelta.label}
                                      </td>
                                    )}
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
            <tfoot>
              <tr style={{ background: '#f0f4f8', fontWeight: 700, borderTop: '2px solid #ddd' }}>
                <td style={{ padding: '7px 10px' }}>TOTAL</td>
                <td style={{ padding: '7px 10px' }}>{fmtNOK(totalEAL)}</td>
                <td style={{ padding: '7px 10px' }}>100%</td>
                <td style={{ padding: '7px 10px' }}>{fmtNOK(totalSCR)}</td>
                <td style={{ padding: '7px 10px' }}>100%</td>
                <td colSpan={hasMit ? 3 : 2} />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* ── Top risk drivers ─────────────────────────────────────────────── */}
      {top_drivers && top_drivers.length > 0 && (
        <div className="card">
          <div className="section-title">Topp risikodrivere (portefølje)</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Driver</th>
                <th>Domene</th>
                <th>EAL-bidrag</th>
                <th>Andel</th>
              </tr>
            </thead>
            <tbody>
              {top_drivers.map((d, i) => (
                <tr key={d.risk_type || i}>
                  <td style={{ color: '#aaa', fontWeight: 600 }}>{i + 1}</td>
                  <td style={{ fontWeight: 600 }}>{d.label}</td>
                  <td><DomainBadge domain={d.domain} /></td>
                  <td>{fmtNOK(d.impact_nok)}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ flex: 1, background: 'var(--mid-grey)', borderRadius: 3, height: 5, minWidth: 60 }}>
                        <div style={{ width: `${d.impact_share_pct}%`, height: 5, borderRadius: 3, background: DOMAIN_COLORS[d.domain] || '#888' }} />
                      </div>
                      <span style={{ fontSize: 11 }}>{d.impact_share_pct?.toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Method note ──────────────────────────────────────────────────── */}
      {method_note && (
        <div style={{
          padding: '8px 12px', borderRadius: 6, fontSize: 11,
          background: '#F9FAFB', border: '1px solid #E5E7EB', color: '#6B7280',
          marginTop: 8, lineHeight: 1.6,
        }}>
          <strong>Metode:</strong> {method_note}
        </div>
      )}
    </div>
  )
}
