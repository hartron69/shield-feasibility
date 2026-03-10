import React from 'react'

const RISK_TYPES = ['hab', 'lice', 'jellyfish', 'pathogen']
const RISK_LABELS = { hab: 'HAB', lice: 'Lice', jellyfish: 'Jellyfish', pathogen: 'Pathogen' }

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
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <div className="section-title" style={{ margin: 0 }}>Learning Loop Status</div>
              <span className={`c5ai-status-pill c5ai-status-${status}`}>
                {status.toUpperCase()}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
              <div className="learning-meter">
                {dots.map((filled, i) => (
                  <div key={i} className={`meter-dot ${filled ? `filled-${status}` : ''}`} />
                ))}
              </div>
              <span style={{ fontSize: 12, color: 'var(--dark-grey)' }}>
                Cycle {n} of {toActive} to reach ACTIVE
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
              <div>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)' }}>Training Source</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>
                  {L.training_source === 'simulated' ? '⚙ Simulated data' : '✓ Operator reported'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)' }}>Last Retrained</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{L.last_retrain_at?.slice(0, 10) || '—'}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)' }}>Cycles Completed</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{n}</div>
              </div>
            </div>
          </div>

          {/* Model versions */}
          <div style={{ background: 'var(--light-grey)', borderRadius: 8, padding: 14, minWidth: 180 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--dark-grey)', marginBottom: 8 }}>
              Model Versions
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
            <strong>Simulated training data:</strong> Models have been trained on synthetic observations generated
            by the C5AI+ EventSimulator. Provide real operator-reported observations via the API to improve calibration.
          </div>
        )}
      </div>

      {/* ── Brier score history ──────────────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Brier Score History</div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12 }}>
          Brier score = E[(p − y)²]. Lower is better. Reference: <strong>0.25</strong> = uninformative prior.
          A score of <strong>0.0</strong> is perfect prediction.
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Cycle</th>
              <th>Year</th>
              {RISK_TYPES.map(rt => <th key={rt}>{RISK_LABELS[rt]}</th>)}
              <th>Trend</th>
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
                        ? <span style={{ color: 'var(--success)', fontWeight: 700 }}>↓ Better</span>
                        : <span style={{ color: 'var(--danger)', fontWeight: 700 }}>↑ Worse</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── Current evaluation metrics ───────────────────────────────────── */}
      <div className="card">
        <div className="section-title">Current Evaluation Metrics</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Risk Type</th>
              <th>Brier</th>
              <th>Log-Loss</th>
              <th>Bias</th>
              <th>Severity MAE</th>
              <th>Cal. Slope</th>
              <th>Samples</th>
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
          <strong>Brier colour key:</strong>{' '}
          <span className="brier-good">green &lt; 0.10</span> ·{' '}
          <span className="brier-ok">amber 0.10–0.20</span> ·{' '}
          <span className="brier-warn">red &gt; 0.20</span>
          {'  |  '}
          <strong>Calibration slope:</strong> 1.00 = perfect · ✓ ≥ 0.90 · ≈ ≥ 0.70 · ⚠ &lt; 0.70
        </div>
      </div>

      {/* ── What happens next ─────────────────────────────────────────────── */}
      <div className="info-note">
        <strong>Next step:</strong> After {toActive - n} more observation cycle{toActive - n !== 1 ? 's' : ''},
        the learning loop will reach <strong>ACTIVE</strong> status. At that point the RandomForest model
        (n ≥ 20) can be promoted for risk types with sufficient data. Provide operator-reported events
        via the learning API to accelerate convergence.
      </div>
    </div>
  )
}
