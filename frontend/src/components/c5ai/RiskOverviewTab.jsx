import React from 'react'

// Two-block layout:
//   Block A — Oppdatert strategisk bilde  (source: Live Risk)
//   Block B — Siste feasibility-resultat  (source: latest completed run)
//
// Rule: if a number looks like EAL / SCR / scale factor / bio-fraction / score,
//       it must come from (A) live risk snapshot or (B) latest feasibility run.
//       Mock/fallback values are never displayed as real KPIs.

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

function fmtNok(v) {
  if (v == null) return '—'
  const m = v / 1_000_000
  return m >= 1 ? `NOK ${m.toFixed(1)}M` : `NOK ${Math.round(v / 1_000)}k`
}

function scoreClass(s) {
  if (s >= 65) return 'high'
  if (s >= 40) return 'medium'
  return 'low'
}

function hhi(shares) {
  return Math.round(shares.reduce((sum, s) => sum + (s * 100) ** 2, 0))
}

function ConcentrationBadge({ value }) {
  if (value >= 2500) return (
    <span style={{ background: '#fee2e2', color: '#991b1b', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>HØY</span>
  )
  if (value >= 1500) return (
    <span style={{ background: '#fef9c3', color: '#854d0e', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>MODERAT</span>
  )
  return (
    <span style={{ background: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 }}>LAV</span>
  )
}

function SourcePill({ label, color = '#374151', bg = '#f3f4f6', border = '#e5e7eb' }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: '0.05em',
      background: bg, color, border: `1px solid ${border}`,
      borderRadius: 4, padding: '2px 8px', textTransform: 'uppercase',
    }}>
      {label}
    </span>
  )
}

function BlockHeader({ title, subtitle, sourceLabel, sourceBg, sourceBorder, sourceColor }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
      <div>
        <div style={{ fontWeight: 700, fontSize: 15, color: '#111827', marginBottom: 2 }}>{title}</div>
        <div style={{ fontSize: 12, color: '#6b7280', fontStyle: 'italic' }}>{subtitle}</div>
      </div>
      <SourcePill label={sourceLabel} bg={sourceBg} border={sourceBorder} color={sourceColor} />
    </div>
  )
}

function verdictColor(v) {
  if (!v) return 'var(--dark-grey)'
  const u = v.toUpperCase()
  if (u.includes('SUITABLE') || u.includes('ANBEFALT')) return '#059669'
  if (u.includes('POTENTIALLY') || u.includes('MULIG')) return '#D97706'
  return '#DC2626'
}

function verdictNorwegian(v) {
  if (!v) return '—'
  const u = v.toUpperCase()
  if (u === 'SUITABLE') return 'Egnet'
  if (u.includes('POTENTIALLY')) return 'Potensielt egnet'
  if (u.includes('NOT') || u.includes('IKKE')) return 'Ikke anbefalt'
  return v
}

// ── Main component ────────────────────────────────────────────────────────────

export default function RiskOverviewTab({ data, feasibilityResult, onNavigateToLiveRisk }) {
  const overall = data.overall_risk_score
  const sites   = data.sites
  const domains = data.domain_breakdown

  // ── Block A: data derived from Live Risk ──────────────────────────────────
  const totalBiomass  = sites.reduce((s, x) => s + x.biomass_tonnes, 0)
  const biomassShares = sites.map(s => s.biomass_tonnes / (totalBiomass || 1))
  const portfolioHHI  = hhi(biomassShares)
  const sortedByRisk  = [...sites].sort((a, b) => b.risk_score - a.risk_score)
  const topSite       = sortedByRisk[0]
  const topShare      = topSite ? Math.round((topSite.biomass_tonnes / (totalBiomass || 1)) * 100) : 0
  const siteRiskWeights = sites.map(s => ({
    ...s,
    biomassShare: Math.round((s.biomass_tonnes / (totalBiomass || 1)) * 100),
  }))

  // ── Block B: data derived only from completed feasibility run ─────────────
  const feas         = feasibilityResult?.baseline?.summary ?? null
  const traceability = feasibilityResult?.traceability ?? null
  const c5aiMeta     = feasibilityResult?.c5ai_meta ?? null
  const scaleFactor  = traceability?.c5ai_scale_factor ?? null
  const c5aiEnriched = traceability?.c5ai_enriched ?? false
  const perDomain    = feasibilityResult?.loss_analysis?.per_domain ?? null
  const domainTotal  = perDomain ? Object.values(perDomain).reduce((s, v) => s + v, 0) : 0
  const bioFraction  = (perDomain && domainTotal > 0) ? (perDomain.biological ?? 0) / domainTotal : null
  const runAt        = traceability?.generated_at ?? null

  return (
    <div>

      {/* ── Navigation guidance banner ─────────────────────────────────────── */}
      <div style={{
        background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8,
        padding: '10px 16px', marginBottom: 20, fontSize: 12,
        display: 'flex', gap: 32, flexWrap: 'wrap', color: '#475569',
      }}>
        <div>
          <span style={{ fontWeight: 700, color: '#1e40af' }}>Live Risk</span>
          {' — operativ status, siste endringer, datakilder, hendelser per lokalitet'}
        </div>
        <div>
          <span style={{ fontWeight: 700, color: '#111827' }}>Risk Intelligence</span>
          {' — strategisk risikobilde, lokaltitetsprioritering, feasibility-resultater, captive-vurdering'}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          BLOCK A — Oppdatert strategisk bilde
          Source: Live Risk feed (updated every time the feed is refreshed)
          ═══════════════════════════════════════════════════════════════════ */}
      <div style={{ marginBottom: 28 }}>

        <BlockHeader
          title="Oppdatert strategisk bilde"
          subtitle="Basert på oppdaterte risikosignaler fra Live Risk"
          sourceLabel="Kilde: Live Risk"
          sourceBg="#eff6ff"
          sourceBorder="#bfdbfe"
          sourceColor="#1d4ed8"
        />

        {/* Hero — overall risk score */}
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
              {overall >= 65
                ? 'HØY — Betydelig biologisk risikoeksponering trekker opp forventet tap og svekker captive-egnetheten.'
                : overall >= 40
                  ? 'MODERAT — Risikobildet er håndterbart, men krever oppfølging i biologisk domene.'
                  : 'LAV — Risikobildet støtter captive-egnethet og gir gunstig premieindikasjon.'}
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
            </div>
          </div>
        </div>

        {/* Tap fordelt på risikotype */}
        <div className="card">
          <div className="section-title">Tap fordelt på risikotype</div>
          <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12, fontStyle: 'italic' }}>
            Viser hvilke risikotyper som driver størst andel av forventet tap — basert på Live Risk-signaler.
            For absolutte NOK-beløp, kjør feasibility-analysen.
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
                {(d.fraction * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </div>

        {/* Viktigste lokaliteter */}
        <div className="card">
          <div className="section-title">Viktigste lokaliteter</div>
          <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12, fontStyle: 'italic' }}>
            Prioritert etter samlet strategisk betydning for risikobilde — ikke siste operative endring.
            For operativ utvikling per lokalitet, åpne i Live Risk.
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
                      <span className={`site-score-bar site-score-${sc}`} style={{ width: site.risk_score * 0.9 }} />
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

        {/* Konsentrasjon i risikobildet */}
        <div className="card">
          <div className="section-title">Konsentrasjon i risikobildet</div>
          <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12, fontStyle: 'italic' }}>
            Viser om risikoen er bredt fordelt eller konsentrert i få lokaliteter.
            Høy konsentrasjon kan svekke diversifisering i captive-strukturen.
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 6, fontWeight: 600 }}>Biomassfordeling per anlegg</div>
            <div style={{ display: 'flex', height: 20, borderRadius: 4, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
              {siteRiskWeights.map((s, i) => {
                const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444']
                return (
                  <div key={s.site_id}
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
                    {topShare}% av biomasse · Risikonivå {topSite.risk_score}/100
                  </div>
                </>
              )}
            </div>
            <div style={{ flex: 1, minWidth: 200, fontSize: 12, color: '#6b7280', lineHeight: 1.6, paddingTop: 4 }}>
              Under 1500 = lav · 1500–2500 = moderat · over 2500 = høy konsentrasjon.
            </div>
          </div>
        </div>

      </div>{/* end Block A */}

      {/* ═══════════════════════════════════════════════════════════════════
          BLOCK B — Siste feasibility-resultat
          Source: latest completed feasibility run only.
          No mock/fallback values — empty state shown when no run exists.
          ═══════════════════════════════════════════════════════════════════ */}
      <div style={{ borderTop: '2px solid #e5e7eb', paddingTop: 20 }}>

        <BlockHeader
          title="Siste feasibility-resultat"
          subtitle="Vises når en feasibility-analyse er kjørt"
          sourceLabel="Kilde: Siste feasibility-kjøring"
          sourceBg="#f5f3ff"
          sourceBorder="#c4b5fd"
          sourceColor="#6d28d9"
        />

        {!feas ? (

          /* ── Pre-run: clean empty state ─────────────────────────────── */
          <div className="card" style={{ textAlign: 'center', padding: '32px 24px', color: 'var(--dark-grey)' }}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>📋</div>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8, color: '#374151' }}>
              Ingen feasibility-analyse er kjørt ennå
            </div>
            <div style={{ fontSize: 13, maxWidth: 480, margin: '0 auto', lineHeight: 1.7 }}>
              Kjør analysen i <strong>PCC Feasibility</strong> for å se forventet tap, SCR,
              egnethet og captive-konsekvens basert på selskapets faktiske portefølje.
            </div>
          </div>

        ) : (

          /* ── Post-run: real results only ────────────────────────────── */
          <div className="card" style={{ borderLeft: '4px solid #7C3AED' }}>

            {/* Run metadata */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
              <div className="c5ai-pill">C5AI+</div>
              <span style={{ fontSize: 12, color: '#6b7280' }}>Basert på siste kjøring</span>
              {c5aiMeta?.data_mode === 'real' && (
                <span style={{ fontSize: 11, background: '#dcfce7', color: '#166534', border: '1px solid #bbf7d0', borderRadius: 4, padding: '1px 7px', fontWeight: 600 }}>
                  BarentsWatch-data
                </span>
              )}
              {runAt && (
                <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 'auto' }}>
                  {new Date(runAt).toLocaleString('nb-NO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>

            {/* KPI row 1: suitability + EAL + SCR */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
              <div className="kpi-card" style={{ flex: 1, minWidth: 140 }}>
                <div className="kpi-label">Egnethet</div>
                <div className="kpi-value" style={{ fontSize: 14, fontWeight: 700, color: verdictColor(feas.verdict) }}>
                  {verdictNorwegian(feas.verdict)}
                </div>
                <div className="kpi-sub">Score {feas.composite_score?.toFixed(1)} / 100</div>
              </div>
              <div className="kpi-card" style={{ flex: 1, minWidth: 140 }}>
                <div className="kpi-label">Forventet årstap</div>
                <div className="kpi-value">{fmtNok(feas.expected_annual_loss)}</div>
                <div className="kpi-sub">E[L] Monte Carlo</div>
              </div>
              <div className="kpi-card" style={{ flex: 1, minWidth: 140 }}>
                <div className="kpi-label">SCR (VaR 99,5%)</div>
                <div className="kpi-value">{fmtNok(feas.scr)}</div>
                <div className="kpi-sub">kapitalkrav</div>
              </div>
            </div>

            {/* KPI row 2: C5AI enrichment details */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
              <div className="kpi-card" style={{ flex: 1, minWidth: 140 }}>
                <div className="kpi-label">C5AI+ brukt i analysen</div>
                <div className="kpi-value" style={{ fontSize: 14, color: c5aiEnriched ? '#7C3AED' : '#6b7280' }}>
                  {c5aiEnriched ? 'Ja' : 'Nei'}
                </div>
                <div className="kpi-sub">
                  {c5aiEnriched ? 'biologisk berikelse anvendt' : 'statisk modell brukt'}
                </div>
              </div>
              {scaleFactor != null && (
                <div className="kpi-card" style={{ flex: 1, minWidth: 140 }}>
                  <div className="kpi-label">C5AI+ skalafaktor</div>
                  <div className="kpi-value" style={{ color: '#7C3AED' }}>{scaleFactor.toFixed(2)}×</div>
                  <div className="kpi-sub">fra siste kjøring</div>
                </div>
              )}
              {bioFraction != null && (
                <div className="kpi-card" style={{ flex: 1, minWidth: 140 }}>
                  <div className="kpi-label">Biologisk tapandel</div>
                  <div className="kpi-value">{(bioFraction * 100).toFixed(0)}%</div>
                  <div className="kpi-sub">av forventet årstap</div>
                </div>
              )}
            </div>

            {/* Bridge interpretation — derived from real run data */}
            <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.7, borderTop: '1px solid #ede9fe', paddingTop: 10 }}>
              {(() => {
                const score = feas.composite_score ?? 0
                const eal   = feas.expected_annual_loss ?? 0
                const bio   = bioFraction ?? 0
                if (score >= 65 || bio >= 0.55 || eal > 25_000_000) {
                  return '⚠️ Økt biologisk risiko trekker opp forventet årstap og svekker captive-egnetheten i siste analyse. Vurder tiltak i Mitigation-panelet og kjør ny analyse.'
                }
                if (score >= 40) {
                  return '✓ Risikobildet er håndterbart. Captive-struktur kan være aktuelt med riktig retensjons- og risikovektnivå.'
                }
                return '✓ Risikobildet støtter captive-egnethet. Lavt forventet tap og akseptabel SCR-belastning.'
              })()}
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: '#9ca3af', fontStyle: 'italic' }}>
              Ikke oppdatert automatisk — gjelder siste fullførte kjøring. Kjør ny analyse i PCC Feasibility for å oppdatere.
            </div>
          </div>

        )}
      </div>{/* end Block B */}

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <div style={{
        fontSize: 11, color: '#9ca3af', fontStyle: 'italic',
        padding: '10px 4px', borderTop: '1px solid #e5e7eb', marginTop: 16, lineHeight: 1.6,
      }}>
        Block A: strategisk bilde oppdateres fra Live Risk-feed. Block B: viser kun resultater fra fullført feasibility-analyse.
      </div>

    </div>
  )
}
