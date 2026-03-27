import React from 'react'

const RISK_TYPES = ['hab', 'lice', 'jellyfish', 'pathogen']
const RISK_LABELS = {
  hab:       'Skadelig algeblomst (HAB)',
  lice:      'Lakselus',
  jellyfish: 'Manetoppblomst',
  pathogen:  'Patogen / sykdom',
}

function brierClass(v) {
  if (v == null) return ''
  if (v < 0.10) return 'brier-good'
  if (v < 0.20) return 'brier-ok'
  return 'brier-warn'
}

function calClass(v) {
  if (v == null) return ''
  if (v >= 0.90) return 'cal-good'
  if (v >= 0.70) return 'cal-ok'
  return 'cal-warn'
}

function calLabel(v) {
  if (v == null) return '—'
  if (v >= 0.90) return `${v.toFixed(2)} ✓`
  if (v >= 0.70) return `${v.toFixed(2)} ≈`
  return `${v.toFixed(2)} ⚠`
}

function fmtK(v) {
  if (v == null) return '—'
  return `NOK ${(v / 1_000).toFixed(0)}k`
}

function fmtPct(v) {
  if (v == null) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${(v * 100).toFixed(1)}%`
}

function biasPctStyle(v) {
  if (Math.abs(v) > 0.08) return { color: 'var(--danger)', fontWeight: 700 }
  if (Math.abs(v) > 0.03) return { color: '#D97706', fontWeight: 600 }
  return { color: 'var(--success)' }
}

export default function LearningStatusTab({ data }) {
  const L = data.learning
  const status = L.status
  const n = L.cycles_completed
  const toActive = L.cycles_to_active

  // Meter: 10 dots, filled = cycles completed
  const dots = Array.from({ length: toActive }, (_, i) => i < n)

  return (
    <div>
      {/* ── Status overview ──────────────────────────────────────────────── */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <div className="section-title" style={{ margin: 0 }}>Strategiske mønstre — læringsmodell</div>
              <span className={`c5ai-status-pill c5ai-status-${status}`}>
                {status.toUpperCase()}
              </span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 10, fontStyle: 'italic' }}>
              Langsiktige mønstre i risikobildet og utvikling over tid — ikke enkelthendelser.
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
              <div className="learning-meter">
                {dots.map((filled, i) => (
                  <div key={i} className={`meter-dot ${filled ? `filled-${status}` : ''}`} />
                ))}
              </div>
              <span style={{ fontSize: 12, color: 'var(--dark-grey)' }}>
                Syklus {n} av {toActive} for å nå AKTIV status
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
              <div>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)' }}>Treningskilde</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>
                  {L.training_source === 'simulated' ? '⚙ Simulerte data' : '✓ Operatørrapportert'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)' }}>Sist oppdatert</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{L.last_retrain_at?.slice(0, 10) || '—'}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)' }}>Sykluser fullført</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{n}</div>
              </div>
            </div>
          </div>

          {/* Model versions */}
          <div style={{ background: 'var(--light-grey)', borderRadius: 8, padding: 14, minWidth: 180 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)', marginBottom: 8 }}>
              Modellversjoner
            </div>
            {RISK_TYPES.map(rt => (
              <div key={rt} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
                <span style={{ fontSize: 12, color: 'var(--navy)' }}>{RISK_LABELS[rt]}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#7C3AED' }}>
                  {L.model_versions[rt] || '—'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {L.training_source === 'simulated' && (
          <div className="warn-note" style={{ marginTop: 12, marginBottom: 0 }}>
            <strong>Simulerte treningsdata:</strong> Modellene er trent på syntetiske observasjoner generert
            av C5AI+ EventSimulator. Strategiske mønstre vil bli mer presise etter hvert som reelle
            operatørrapporterte observasjoner legges inn via API-et.
          </div>
        )}
      </div>

      {/* ── Brier score history ──────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Historisk modellnøyaktighet</div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12 }}>
          Brier-skår = E[(p − y)²]. Lavere er bedre. Referanse: <strong>0.25</strong> = ikke-informativ prior.
          Skår <strong>0.0</strong> = perfekt prediksjon. Viser om modellen forbedres over tid.
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Syklus</th>
              <th>År</th>
              {RISK_TYPES.map(rt => <th key={rt}>{RISK_LABELS[rt]}</th>)}
              <th>Utvikling</th>
            </tr>
          </thead>
          <tbody>
            {L.brier_history.map((row, i) => {
              const prev = L.brier_history[i - 1]
              const avg     = RISK_TYPES.reduce((s, rt) => s + row[rt], 0) / RISK_TYPES.length
              const prevAvg = prev ? RISK_TYPES.reduce((s, rt) => s + prev[rt], 0) / RISK_TYPES.length : null
              const improving = prevAvg != null && avg < prevAvg
              return (
                <tr key={row.cycle}>
                  <td style={{ fontWeight: 600 }}>{row.cycle}</td>
                  <td>{row.year}</td>
                  {RISK_TYPES.map(rt => (
                    <td key={rt} className={brierClass(row[rt])}>{row[rt].toFixed(3)}</td>
                  ))}
                  <td>
                    {prevAvg == null ? <span style={{ color: 'var(--dark-grey)' }}>—</span> :
                      improving
                        ? <span style={{ color: 'var(--success)', fontWeight: 700 }}>↓ Bedre</span>
                        : <span style={{ color: 'var(--danger)', fontWeight: 700 }}>↑ Svakere</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── Current evaluation metrics ───────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Nåværende modellevaluering</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Risikotype</th>
              <th>Brier</th>
              <th>Log-loss</th>
              <th>Systematisk avvik</th>
              <th>Alvorlighets-MAE</th>
              <th>Kalibrering</th>
              <th>Observasjoner</th>
            </tr>
          </thead>
          <tbody>
            {RISK_TYPES.map(rt => {
              const m = L.evaluation_metrics[rt]
              if (!m) return null
              return (
                <tr key={rt}>
                  <td style={{ fontWeight: 600 }}>{RISK_LABELS[rt]}</td>
                  <td className={brierClass(m.brier_score)}>{m.brier_score.toFixed(3)}</td>
                  <td>{m.log_loss.toFixed(3)}</td>
                  <td style={biasPctStyle(m.mean_probability_error)}>{fmtPct(m.mean_probability_error)}</td>
                  <td>{fmtK(m.severity_mae_nok)}</td>
                  <td className={calClass(m.calibration_slope)}>{calLabel(m.calibration_slope)}</td>
                  <td>{m.n_samples}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <div style={{ marginTop: 12, fontSize: 12, color: 'var(--dark-grey)', lineHeight: 1.7 }}>
          <strong>Fargeindikator Brier:</strong>{' '}
          <span className="brier-good">grønn &lt; 0.10</span> ·{' '}
          <span className="brier-ok">gul 0.10–0.20</span> ·{' '}
          <span className="brier-warn">rød &gt; 0.20</span>
          {'  |  '}
          <strong>Kalibrering:</strong> 1.00 = perfekt · ✓ ≥ 0.90 · ≈ ≥ 0.70 · ⚠ &lt; 0.70
        </div>
      </div>

      {/* ── Neste steg ────────────────────────────────────────────────────── */}
      <div className="info-note">
        <strong>Neste steg:</strong> Etter {toActive - n} ytterligere observasjonssyklus{toActive - n !== 1 ? 'er' : ''},
        vil læringsmodellen nå <strong>AKTIV</strong> status. RandomForest-modellen (n ≥ 20) kan da
        fremmes for risikotyper med tilstrekkelig datagrunnlag. Legg inn operatørrapporterte hendelser
        via lærings-API-et for å akselerere konvergensen og styrke de strategiske mønstrene.
      </div>
    </div>
  )
}
