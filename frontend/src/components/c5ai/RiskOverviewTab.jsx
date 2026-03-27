import React from 'react'

// Strategic portfolio & captive dashboard.
// Operational detail (raw measurements, alerts, BW sync) lives in Live Risk.

const DOMAIN_COLORS = {
  biological:    '#059669',
  structural:    '#2563EB',
  environmental: '#D97706',
  operational:   '#7C3AED',
}

const DOMAIN_LABELS = {
  biological:    'Biologisk',
  structural:    'Strukturell',
  environmental: 'Miljø',
  operational:   'Operasjonell',
}

const RISK_TYPE_LABELS = {
  biological:    'Biologisk risiko',
  structural:    'Strukturell risiko',
  environmental: 'Miljørisiko',
  operational:   'Operasjonell risiko',
}

const EXPOSURE_LABELS = {
  open_coast:   'Eksponert',
  semi_exposed: 'Semi-eksponert',
  sheltered:    'Skjermet',
}

function fmtM(v) {
  if (v == null) return '—'
  return `NOK ${(v / 1_000_000).toFixed(1)}M`
}

function scoreClass(s) {
  if (s >= 65) return 'high'
  if (s >= 40) return 'medium'
  return 'low'
}

// Herfindahl–Hirschman Index from share array (values 0–1); returns 0–10000
function hhi(shares) {
  return Math.round(shares.reduce((sum, s) => sum + (s * 100) ** 2, 0))
}

function ConcentrationBadge({ value }) {
  if (value >= 2500) return (
    <span style={{ background: '#fee2e2', color: '#991b1b', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
      HØY
    </span>
  )
  if (value >= 1500) return (
    <span style={{ background: '#fef9c3', color: '#854d0e', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
      MODERAT
    </span>
  )
  return (
    <span style={{ background: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
      LAV
    </span>
  )
}

export default function RiskOverviewTab({ data, feasibilityResult, onNavigateToLiveRisk }) {
  const overall = data.overall_risk_score
  const sites   = data.sites
  const domains = data.domain_breakdown
  const pcc     = data.pcc_integration

  const totalBioLoss = Object.values(data.biological_forecast).reduce((sum, sf) => {
    return sum + (sf.hab.expected_loss_mean + sf.lice.expected_loss_mean +
                  sf.jellyfish.expected_loss_mean + sf.pathogen.expected_loss_mean)
  }, 0)

  // Concentration analysis
  const totalBiomass = sites.reduce((s, x) => s + x.biomass_tonnes, 0)
  const biomassShares = sites.map(s => s.biomass_tonnes / (totalBiomass || 1))
  const portfolioHHI  = hhi(biomassShares)
  const sortedByRisk  = [...sites].sort((a, b) => b.risk_score - a.risk_score)
  const topSite       = sortedByRisk[0]
  const topShare      = topSite ? Math.round((topSite.biomass_tonnes / (totalBiomass || 1)) * 100) : 0

  const siteRiskWeights = sites.map(s => ({
    ...s,
    biomassShare: Math.round((s.biomass_tonnes / (totalBiomass || 1)) * 100),
  }))

  return (
    <div>

      {/* ── Strategic clarification banner ──────────────────────────────── */}
      <div style={{
        background: '#f0f9ff', border: '1px solid #bae6fd',
        borderRadius: 8, padding: '12px 16px', marginBottom: 16,
        fontSize: 13, color: '#0c4a6e', lineHeight: 1.6,
      }}>
        <div style={{ fontWeight: 700, marginBottom: 3 }}>Strategisk analyse</div>
        Strategisk analyse av selskapets samlede risikobilde.
        Denne modulen viser hvilke lokaliteter og risikotyper som betyr mest for forventet tap,
        kapitalbehov og captive-vurdering.{' '}
        <span style={{ fontStyle: 'italic' }}>
          For operativ status, siste endringer og datadetaljer, bruk Live Risk.
        </span>
      </div>

      {/* ── Selskapets risikobilde — hero card ──────────────────────────── */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <div className={`risk-score-ring ${scoreClass(overall)}`}>
          <span className="ring-value">{overall}</span>
          <span className="ring-label">/ 100</span>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>
            Selskapets risikobilde
          </div>
          <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 2, fontStyle: 'italic' }}>
            Strategisk risikonivå — samlet modellert vurdering for captive-egnethet og kapitalplanlegging
          </div>
          <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginBottom: 8 }}>
            {overall >= 65 ? 'HØY — Betydelig biologisk risikoeksponering trekker opp forventet tap og svekker captive-egnetheten.' :
             overall >= 40 ? 'MODERAT — Risikobildet er håndterbart, men krever oppfølging i biologisk domene.' :
                             'LAV — Risikobildet støtter captive-egnethet og gir gunstig premieindikasjon.'}
          </div>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Anlegg</div>
              <div style={{ fontWeight: 700 }}>{sites.length}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Total biomasse</div>
              <div style={{ fontWeight: 700 }}>{totalBiomass.toLocaleString()} t</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Forv. biologisk tap/år</div>
              <div style={{ fontWeight: 700 }}>{fmtM(totalBioLoss)}</div>
            </div>
            {pcc.enriched && (
              <div>
                <div style={{ fontSize: 11, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>Skalafaktor</div>
                <div style={{ fontWeight: 700, color: '#7C3AED' }}>{pcc.scale_factor.toFixed(2)}×</div>
              </div>
            )}
          </div>
        </div>
        {pcc.enriched && (
          <div style={{ textAlign: 'center', padding: '8px 12px', background: '#F5F3FF', borderRadius: 8, border: '1px solid #C4B5FD' }}>
            <div className="c5ai-pill" style={{ marginBottom: 4 }}>C5AI+</div>
            <div style={{ fontSize: 11, color: '#6D28D9', fontWeight: 600 }}>Beriket</div>
          </div>
        )}
      </div>

      {/* ── Tap fordelt på risikotype ────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Tap fordelt på risikotype</div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12, fontStyle: 'italic' }}>
          Viser hvilke risikotyper som driver størst andel av forventet årlig tap i analysegrunnlaget.
        </div>
        {Object.entries(domains).map(([domain, d]) => (
          <div key={domain} className="domain-bar-row">
            <div className="domain-bar-label">{RISK_TYPE_LABELS[domain] || DOMAIN_LABELS[domain] || domain}</div>
            <div className="domain-bar-track">
              <div
                className="domain-bar-fill"
                style={{ width: `${d.fraction * 100}%`, background: DOMAIN_COLORS[domain] }}
              />
            </div>
            <div className="domain-bar-pct" style={{ color: DOMAIN_COLORS[domain] }}>
              {(d.fraction * 100).toFixed(0)}% av forv. årstap
            </div>
            <div className="domain-bar-nok">{fmtM(d.annual_loss_nok)}/år</div>
          </div>
        ))}
      </div>

      {/* ── Viktigste lokaliteter ────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Viktigste lokaliteter</div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12, fontStyle: 'italic' }}>
          Lokalitetene er prioritert etter samlet betydning for selskapets forventede tap og risikobilde —
          ikke siste operative endring. For operativ utvikling per lokalitet, åpne i Live Risk.
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Lokalitet</th>
              <th>Eksponering</th>
              <th>Biomasse</th>
              <th>Strategisk risikonivå</th>
              <th>Viktigste risikotyper</th>
              {onNavigateToLiveRisk && <th>Handling</th>}
            </tr>
          </thead>
          <tbody>
            {sortedByRisk.map((site, i) => {
              const sc = scoreClass(site.risk_score)
              return (
                <tr key={site.site_id}>
                  <td style={{ color: 'var(--dark-grey)', fontWeight: 600 }}>{i + 1}</td>
                  <td style={{ fontWeight: 600 }}>
                    <div>{site.site_name}</div>
                    <div style={{ fontSize: 10, color: 'var(--dark-grey)', fontFamily: 'monospace' }}>{site.site_id}</div>
                  </td>
                  <td>{EXPOSURE_LABELS[site.fjord_exposure] || site.fjord_exposure}</td>
                  <td>{site.biomass_tonnes.toLocaleString()} t</td>
                  <td>
                    <span
                      className={`site-score-bar site-score-${sc}`}
                      style={{ width: site.risk_score * 0.9 }}
                    />
                    <strong>{site.risk_score}</strong>/100
                  </td>
                  <td>
                    {site.dominant_risks.map(r => (
                      <span key={r} className="badge badge-biological"
                        style={{
                          marginRight: 4,
                          background: DOMAIN_COLORS[r] ? DOMAIN_COLORS[r] + '22' : undefined,
                          color: DOMAIN_COLORS[r] || undefined,
                          borderColor: DOMAIN_COLORS[r] || undefined,
                        }}>
                        {DOMAIN_LABELS[r] || r}
                      </span>
                    ))}
                  </td>
                  {onNavigateToLiveRisk && (
                    <td>
                      <button
                        onClick={() => onNavigateToLiveRisk(site.site_id)}
                        style={{
                          background: 'none', border: '1px solid #d1d5db',
                          borderRadius: 4, padding: '3px 8px',
                          fontSize: 11, color: '#374151', cursor: 'pointer',
                          fontWeight: 600, whiteSpace: 'nowrap',
                        }}
                        title={`Åpne ${site.site_name} i Live Risk`}
                      >
                        Åpne i Live Risk
                      </button>
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── Konsentrasjon i risikobildet ─────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Konsentrasjon i risikobildet</div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12, fontStyle: 'italic' }}>
          Viser om forventet tap og risiko er bredt fordelt eller konsentrert i få lokaliteter.
          Høy konsentrasjon kan gi svakere diversifisering i captive-strukturen.
        </div>

        {/* Biomass distribution bar */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 6, fontWeight: 600 }}>
            Biomassfordeling per anlegg
          </div>
          <div style={{ display: 'flex', height: 20, borderRadius: 4, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
            {siteRiskWeights.map((s, i) => {
              const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444']
              return (
                <div
                  key={s.site_id}
                  style={{ width: `${s.biomassShare}%`, background: colors[i % colors.length] }}
                  title={`${s.site_name}: ${s.biomassShare}%`}
                />
              )
            })}
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 6, flexWrap: 'wrap' }}>
            {siteRiskWeights.map((s, i) => {
              const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444']
              return (
                <div key={s.site_id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: colors[i % colors.length] }} />
                  <span>{s.site_name} {s.biomassShare}%</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* HHI summary */}
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: '8px 14px', minWidth: 160 }}>
            <div style={{ fontSize: 10, color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 2 }}>
              HHI — konsentrasjonsindeks
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#111827', lineHeight: 1.2 }}>{portfolioHHI}</div>
            <div style={{ marginTop: 4 }}><ConcentrationBadge value={portfolioHHI} /></div>
          </div>
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 6, padding: '8px 14px', minWidth: 200 }}>
            <div style={{ fontSize: 10, color: '#9ca3af', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 2 }}>
              Høyest prioritert anlegg
            </div>
            {topSite && (
              <>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#111827' }}>{topSite.site_name}</div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                  {topShare}% av biomasse · Strategisk risikonivå {topSite.risk_score}/100
                </div>
              </>
            )}
          </div>
          <div style={{ flex: 1, minWidth: 200, fontSize: 12, color: '#6b7280', lineHeight: 1.6, paddingTop: 4 }}>
            HHI viser hvor konsentrert eksponeringen er i analysegrunnlaget.
            Under 1500 = lav · 1500–2500 = moderat · over 2500 = høy konsentrasjon.
          </div>
        </div>
      </div>

      {/* ── Konsekvens for captive og feasibility ───────────────────────── */}
      <div className="card" style={{ borderLeft: '4px solid #7C3AED' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div className="c5ai-pill">C5AI+</div>
          <div className="section-title" style={{ margin: 0 }}>Konsekvens for captive og feasibility</div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12, fontStyle: 'italic' }}>
          Viser hvordan risikobildet påvirker forventet tap, kapitalbehov og egnethet for captive-struktur.
        </div>
        <div className="kpi-grid" style={{ marginBottom: 12 }}>
          <div className="kpi-card">
            <div className="kpi-label">C5AI+ skalafaktor</div>
            <div className="kpi-value" style={{ color: '#7C3AED' }}>{pcc.scale_factor.toFixed(2)}×</div>
            <div className="kpi-sub">vs. statisk {pcc.scale_factor_static.toFixed(2)}×</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Biologisk tapandel</div>
            <div className="kpi-value">{(pcc.biological_loss_fraction * 100).toFixed(0)}%</div>
            <div className="kpi-sub">av forventet årstap</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Biologisk kriteriescore</div>
            <div className="kpi-value">{pcc.suitability_impact.bio_criterion_score}/100</div>
            <div className="kpi-sub">vekt {(pcc.suitability_impact.bio_criterion_weight * 100).toFixed(0)}% av kompositt</div>
          </div>
        </div>
        <div className="info-note" style={{ marginBottom: 8 }}>
          {pcc.suitability_impact.bio_criterion_finding}
        </div>
        {!feasibilityResult ? (
          <div style={{ fontSize: 12, color: 'var(--dark-grey)' }}>
            Kjør PCC Feasibility-analysen for å se hvordan C5AI+ skalafaktoren påvirker
            forventet tap, SCR-kravet og den samlede captive-egnetheten.
          </div>
        ) : (
          <div style={{ fontSize: 12, color: '#065F46', fontWeight: 600 }}>
            Feasibility-resultat tilgjengelig — C5AI+-berikelse er anvendt. Gå til PCC Feasibility for full egnethetsvurdering, kapitalkrav og premieindikasjon.
          </div>
        )}
      </div>

      {/* ── Footer disclaimer ────────────────────────────────────────────── */}
      <div style={{
        fontSize: 11, color: '#9ca3af', fontStyle: 'italic',
        padding: '10px 4px', borderTop: '1px solid #e5e7eb', marginTop: 4, lineHeight: 1.6,
      }}>
        Dette er en strategisk, modellert visning basert på analysegrunnlaget.
        For operativ sannhet, siste endringer og datakilder, bruk Live Risk.
      </div>

    </div>
  )
}
