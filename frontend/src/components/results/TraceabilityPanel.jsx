import React, { useState } from 'react'

const DOMAIN_COLORS = {
  biological:    '#059669',
  structural:    '#2563EB',
  environmental: '#D97706',
  operational:   '#7C3AED',
}

const RISK_TYPE_LABELS = {
  hab: 'HAB (algeoppblomstring)', lice: 'Lakselus', jellyfish: 'Manet-invasjon',
  pathogen: 'Sykdomsutbrudd', biosecurity: 'Biosikkerhet',
  mooring_failure: 'Fortøyningssvikt', net_integrity: 'Not-integritet',
  cage_structural: 'Merdestruktur', deformation: 'Deformasjon',
  anchor_deterioration: 'Anker-svekkelse',
  oxygen_stress: 'Oksygenstress', temperature_extreme: 'Temperaturekstrem',
  current_storm: 'Strøm/storm', ice: 'Is-hendelse', exposure_anomaly: 'Eksponeringsanomal',
  human_error: 'Menneskelig feil', procedure_failure: 'Prosedyresvikt',
  equipment_failure: 'Utstyrsvikt', incident: 'Hendelse',
  maintenance_backlog: 'Vedlikeholdsefterslep',
}

function fmtM(v) { return v >= 1_000_000 ? `NOK ${(v/1_000_000).toFixed(2)}M` : `NOK ${Math.round(v).toLocaleString('nb-NO')}` }

function DataModeBadge({ mode }) {
  const map = {
    static_model:            { label: 'Statisk modell', bg: '#F3F4F6', color: '#374151', border: '#D1D5DB' },
    c5ai_forecast:           { label: 'C5AI+ prognose', bg: '#ECFDF5', color: '#065F46', border: '#6EE7B7' },
    c5ai_forecast_mitigated: { label: 'C5AI+ mitigert', bg: '#EFF6FF', color: '#1E40AF', border: '#BFDBFE' },
  }
  const s = map[mode] || map.static_model
  return (
    <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 9px', borderRadius: 4,
      border: `1px solid ${s.border}`, background: s.bg, color: s.color, letterSpacing: '0.3px' }}>
      {s.label}
    </span>
  )
}

function DomainPill({ domain }) {
  const color = DOMAIN_COLORS[domain] || '#6B7280'
  const labels = { biological: 'Biologisk', structural: 'Strukturell', environmental: 'Miljø', operational: 'Operasjonell' }
  return (
    <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 12,
      background: `${color}18`, color, border: `1px solid ${color}40` }}>
      {labels[domain] || domain}
    </span>
  )
}

export default function TraceabilityPanel({ traceability, onNavigateToRisk }) {
  const [noteExpanded, setNoteExpanded] = useState(false)

  if (!traceability) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: 'var(--dark-grey)', fontSize: 13 }}>
        Ingen sporbarhetsinformasjon tilgjengelig for dette kjøret.
      </div>
    )
  }

  const t = traceability
  let ts = '—'
  try { ts = new Date(t.generated_at).toLocaleString('nb-NO') } catch {}

  return (
    <div style={{ maxWidth: 920 }}>

      {/* Header */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
              Datagrunnlag — C5AI+ → Gjennomførbarhetsanalyse
            </div>
            <div style={{ fontSize: 12, color: 'var(--dark-grey)' }}>
              Analyse-ID: <code style={{ fontFamily: 'monospace', background: '#F3F4F6', padding: '1px 5px', borderRadius: 3 }}>{t.analysis_id}</code>
              &nbsp;·&nbsp;Kjørt: {ts}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <DataModeBadge mode={t.data_mode} />
            {t.mitigated_forecast_used && (
              <span style={{ fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 4,
                background: '#ECFDF5', color: '#065F46', border: '1px solid #6EE7B7' }}>
                Mitigert
              </span>
            )}
            {t.applied_mitigations && t.applied_mitigations.length > 0 && (
              <span style={{ fontSize: 11, color: 'var(--dark-grey)' }}>
                {t.applied_mitigations.length} tiltak valgt
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Flow diagram */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 12, color: 'var(--dark-grey)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Datapipeline
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {[
            {
              label: t.c5ai_enriched ? 'C5AI+ prognose' : 'Statisk risikomodell',
              sub: t.c5ai_enriched
                ? `Skaleringsfaktor: ${t.c5ai_scale_factor?.toFixed(3) ?? '—'}`
                : 'TIV-kalibrert Compound Poisson',
              color: t.c5ai_enriched ? '#059669' : '#6B7280',
              exact: t.c5ai_enriched,
            },
            null,
            {
              label: 'Monte Carlo',
              sub: 'LogNormal-alvorlighetsgrad',
              color: '#2563EB',
              exact: true,
            },
            null,
            {
              label: 'Tapsanalyse',
              sub: 'EAL eksakt · SCR tilnærmet',
              color: '#7C3AED',
              exact: null,
            },
            null,
            {
              label: 'PCC-egnethetsanalyse',
              sub: '6-kriterium egnethetsscore',
              color: '#D97706',
              exact: true,
            },
          ].map((node, i) => {
            if (node === null) {
              return <div key={i} style={{ color: '#9CA3AF', fontSize: 18, lineHeight: 1 }}>→</div>
            }
            return (
              <div key={i} style={{
                background: '#FAFAFA',
                border: `2px solid ${node.color}40`,
                borderRadius: 8, padding: '10px 14px',
                minWidth: 130, textAlign: 'center', flex: '1 1 130px',
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: node.color, marginBottom: 3 }}>{node.label}</div>
                <div style={{ fontSize: 10, color: 'var(--dark-grey)', lineHeight: 1.4 }}>{node.sub}</div>
                {node.exact === true && (
                  <div style={{ fontSize: 9, color: '#059669', fontWeight: 700, marginTop: 4 }}>EKSAKT</div>
                )}
                {node.exact === false && (
                  <div style={{ fontSize: 9, color: '#D97706', fontWeight: 700, marginTop: 4 }}>TILNÆRMET</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Summary KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        {[
          { label: 'Simulerte anlegg', value: t.site_count, sub: 'i PCC-kjøret' },
          { label: 'Risikodomener', value: t.domain_count, sub: 'biologisk, strukturell, miljø, ops' },
          { label: 'Risikotyper', value: t.risk_type_count, sub: 'sub-typer modellert' },
          { label: 'Mitigering', value: t.applied_mitigations?.length || 0, sub: 'tiltak inkludert' },
        ].map(({ label, value, sub }) => (
          <div key={label} className="dashboard-kpi-card">
            <div className="dashboard-kpi-label">{label}</div>
            <div className="dashboard-kpi-value" style={{ fontSize: 26 }}>{value}</div>
            <div className="dashboard-kpi-sub">{sub}</div>
          </div>
        ))}
      </div>

      {/* Site trace table */}
      {t.site_trace && t.site_trace.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>Anlegg inkludert i analysen</div>
            {onNavigateToRisk && (
              <button
                className="overview-link-btn"
                style={{ margin: 0 }}
                onClick={() => onNavigateToRisk('risk', 'risiko')}
              >
                Se anlegg i C5AI+ Risiko →
              </button>
            )}
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--mid-grey)', textAlign: 'left' }}>
                <th style={{ padding: '6px 10px', fontWeight: 600, color: 'var(--dark-grey)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px' }}>Anlegg</th>
                <th style={{ padding: '6px 10px', fontWeight: 600, color: 'var(--dark-grey)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px' }}>BW-lokalitet</th>
                <th style={{ padding: '6px 10px', fontWeight: 600, color: 'var(--dark-grey)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', textAlign: 'right' }}>EAL (eksakt)</th>
                <th style={{ padding: '6px 10px', fontWeight: 600, color: 'var(--dark-grey)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', textAlign: 'right' }}>SCR-bidrag (tilnærmet)</th>
                <th style={{ padding: '6px 10px', fontWeight: 600, color: 'var(--dark-grey)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px' }}>Topp domener</th>
              </tr>
            </thead>
            <tbody>
              {t.site_trace.map((s, i) => (
                <tr key={s.site_id} style={{ borderBottom: '1px solid var(--mid-grey)', background: i % 2 === 0 ? 'transparent' : 'var(--light-grey)' }}>
                  <td style={{ padding: '8px 10px', fontWeight: 600 }}>
                    <div>{s.site_name}</div>
                    <div style={{ fontSize: 10, color: 'var(--dark-grey)', fontFamily: 'monospace' }}>{s.site_id}</div>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    {s.locality_no
                      ? <code style={{ fontFamily: 'monospace', fontSize: 11, background: '#f1f5f9', padding: '1px 5px', borderRadius: 3 }}>{s.locality_no}</code>
                      : <span style={{ color: 'var(--dark-grey)', fontSize: 11 }}>—</span>
                    }
                  </td>
                  <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600 }}>{fmtM(s.eal_nok)}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right', color: 'var(--dark-grey)' }}>
                    {fmtM(s.scr_contribution_nok)}
                    <div style={{ fontSize: 10, color: '#D97706' }}>prop. tilnærming</div>
                  </td>
                  <td style={{ padding: '8px 10px' }}>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {s.top_domains.map(d => <DomainPill key={d} domain={d} />)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Domains and risk types */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <div className="card">
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--dark-grey)' }}>Risikodomener modellert</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {(t.domains_used || []).map(d => <DomainPill key={d} domain={d} />)}
          </div>
        </div>
        <div className="card">
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--dark-grey)' }}>Risikotyper inkludert ({t.risk_type_count})</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {(t.risk_types_used || []).slice(0, 12).map(rt => (
              <span key={rt} style={{ fontSize: 10, padding: '2px 7px', borderRadius: 10,
                background: '#F3F4F6', color: '#374151', border: '1px solid #E5E7EB' }}>
                {RISK_TYPE_LABELS[rt] || rt.replace(/_/g, ' ')}
              </span>
            ))}
            {(t.risk_types_used || []).length > 12 && (
              <span style={{ fontSize: 10, color: 'var(--dark-grey)' }}>+{t.risk_types_used.length - 12} til</span>
            )}
          </div>
        </div>
      </div>

      {/* Mapping / method note */}
      <div className="card">
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700,
            textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--dark-grey)',
            display: 'flex', gap: 6, alignItems: 'center', padding: 0, width: '100%', textAlign: 'left' }}
          onClick={() => setNoteExpanded(e => !e)}
        >
          <span>{noteExpanded ? '▼' : '▶'}</span>
          Metodenotat og koblingsforklaring
        </button>
        {noteExpanded && (
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--dark-grey)', lineHeight: 1.7, borderTop: '1px solid var(--mid-grey)', paddingTop: 10 }}>
            {t.mapping_note}
          </div>
        )}
      </div>
    </div>
  )
}
