import React from 'react'

function fmtM(n) {
  if (n == null) return '—'
  return `NOK ${(n / 1e6).toFixed(1)} M`
}

function pct(n, decimals = 1) {
  if (n == null) return '—'
  return `${n.toFixed(decimals)} %`
}

function DeltaBadge({ value, lowerIsBetter = true, suffix = '' }) {
  if (value == null) return null
  const improved = lowerIsBetter ? value > 0 : value > 0
  const colour = improved ? '#2e7d32' : '#c62828'
  const sign = value > 0 ? '▼ ' : '▲ '
  return (
    <span style={{ color: colour, fontWeight: 700, fontSize: 12 }}>
      {sign}{Math.abs(value).toFixed(1)}{suffix}
    </span>
  )
}

export default function PoolingTab({ pooling }) {
  if (!pooling) {
    return (
      <div className="tab-content" style={{ color: '#888', padding: 24 }}>
        Enable "Pooled PCC scenario" in the Pooling settings and re-run.
      </div>
    )
  }

  if (!pooling.enabled) {
    return (
      <div className="tab-content" style={{ color: '#888', padding: 24 }}>
        Pooling is disabled. Enable it in the Pooling settings panel.
      </div>
    )
  }

  const {
    n_members, pooled_cv, standalone_cv, cv_reduction_pct,
    pooled_var_995, standalone_var_995, var_reduction_pct,
    pooled_ri_premium_annual, standalone_ri_premium_annual, ri_premium_reduction_pct,
    pooled_scr, standalone_scr, scr_reduction_pct,
    operator_5yr_tcor_standalone, operator_5yr_tcor_pooled, tcor_improvement_pct,
    pooled_mean_annual_loss,
    members = [], viable, verdict_narrative, known_simplifications = [],
  } = pooling

  const verdictColour = viable ? '#2e7d32' : '#e65100'
  const verdictBg = viable ? '#e8f5e9' : '#fff3e0'
  const verdictBorder = viable ? '#a5d6a7' : '#ffcc80'

  return (
    <div className="tab-content">

      {/* ── Verdict banner ─────────────────────────────────────────── */}
      <div style={{
        background: verdictBg, border: `2px solid ${verdictBorder}`,
        borderRadius: 8, padding: '12px 18px', marginBottom: 24,
      }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: verdictColour, marginBottom: 4 }}>
          {viable ? '✓ Pooled PCC: VIABLE' : '⚠ Pooled PCC: Limited benefit in this scenario'}
        </div>
        <div style={{ fontSize: 12, color: '#444', lineHeight: 1.5 }}>
          {verdict_narrative}
        </div>
      </div>

      {/* ── A. Diversification benefit ─────────────────────────────── */}
      <h4 style={{ margin: '0 0 10px', fontSize: 13, color: '#555' }}>
        Diversification benefit ({n_members}-member pool)
      </h4>
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <div className="kpi-card">
          <div className="kpi-label">Standalone CV</div>
          <div className="kpi-value" style={{ fontSize: 22 }}>
            {standalone_cv != null ? standalone_cv.toFixed(3) : '—'}
          </div>
          <div className="kpi-sub">Loss coefficient of variation</div>
        </div>
        <div className="kpi-card" style={{ borderColor: '#a5d6a7' }}>
          <div className="kpi-label">Pooled CV (operator share)</div>
          <div className="kpi-value" style={{ fontSize: 22, color: '#2e7d32' }}>
            {pooled_cv != null ? pooled_cv.toFixed(3) : '—'}
          </div>
          <div className="kpi-sub">
            <DeltaBadge value={cv_reduction_pct} suffix="% reduction" />
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Standalone VaR 99.5%</div>
          <div className="kpi-value" style={{ fontSize: 18 }}>
            {fmtM(standalone_var_995)}
          </div>
          <div className="kpi-sub">Standalone annual</div>
        </div>
        <div className="kpi-card" style={{ borderColor: '#a5d6a7' }}>
          <div className="kpi-label">Pooled VaR 99.5% (operator share)</div>
          <div className="kpi-value" style={{ fontSize: 18, color: '#2e7d32' }}>
            {fmtM(pooled_var_995 * (members[0]?.allocation_weight ?? 1))}
          </div>
          <div className="kpi-sub">
            <DeltaBadge value={var_reduction_pct} suffix="% reduction" />
          </div>
        </div>
      </div>

      {/* ── B. Economics comparison ────────────────────────────────── */}
      <h4 style={{ margin: '0 0 10px', fontSize: 13, color: '#555' }}>
        Operator economics: standalone PCC vs pooled PCC
      </h4>
      <div style={{ overflowX: 'auto', marginBottom: 24 }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse', fontSize: 12, minWidth: 560,
        }}>
          <thead>
            <tr style={{ background: '#f0f4f8', textAlign: 'left' }}>
              {['Metric', 'Standalone PCC', 'Pooled PCC', 'Reduction'].map(h => (
                <th key={h} style={{ padding: '6px 12px', borderBottom: '2px solid #ddd' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              {
                label: 'Annual RI premium',
                standalone: fmtM(standalone_ri_premium_annual),
                pooled: fmtM(pooled_ri_premium_annual),
                delta: ri_premium_reduction_pct,
              },
              {
                label: 'SCR (net)',
                standalone: fmtM(standalone_scr),
                pooled: fmtM(pooled_scr * (members[0]?.allocation_weight ?? 1)),
                delta: scr_reduction_pct,
              },
              {
                label: '5-year TCOR (economics)',
                standalone: fmtM(operator_5yr_tcor_standalone),
                pooled: fmtM(operator_5yr_tcor_pooled),
                delta: tcor_improvement_pct,
              },
            ].map(row => (
              <tr key={row.label} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '5px 12px', fontWeight: 600 }}>{row.label}</td>
                <td style={{ padding: '5px 12px' }}>{row.standalone}</td>
                <td style={{ padding: '5px 12px', color: '#2e7d32' }}>{row.pooled}</td>
                <td style={{ padding: '5px 12px' }}>
                  <DeltaBadge value={row.delta} suffix="%" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── C. Pool member breakdown ───────────────────────────────── */}
      {members.length > 0 && (
        <>
          <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#555' }}>
            Pool member breakdown
          </h4>
          <div style={{ overflowX: 'auto', marginBottom: 20 }}>
            <table style={{
              width: '100%', borderCollapse: 'collapse', fontSize: 12, minWidth: 620,
            }}>
              <thead>
                <tr style={{ background: '#f0f4f8', textAlign: 'left' }}>
                  {['Member', 'Exp. annual loss', 'Weight', 'Standalone CV', 'Pooled CV', 'Alloc. RI/yr', 'Alloc. SCR', '5yr TCOR'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {members.map((m, i) => (
                  <tr
                    key={m.member_id}
                    style={{
                      borderBottom: '1px solid #eee',
                      background: m.member_id === 0 ? '#f0f8ff' : 'white',
                    }}
                  >
                    <td style={{ padding: '5px 10px', fontWeight: m.member_id === 0 ? 700 : 400 }}>
                      {m.label}
                    </td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(m.expected_annual_loss)}</td>
                    <td style={{ padding: '5px 10px' }}>{pct(m.allocation_weight * 100)}</td>
                    <td style={{ padding: '5px 10px' }}>{m.standalone_cv?.toFixed(3) ?? '—'}</td>
                    <td style={{ padding: '5px 10px', color: '#2e7d32' }}>
                      {m.pooled_cv?.toFixed(3) ?? '—'}
                    </td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(m.allocated_ri_premium_annual)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(m.allocated_scr)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(m.allocated_5yr_tcor)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ── D. Known simplifications (transparency) ───────────────── */}
      {known_simplifications.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary style={{ fontSize: 11, color: '#888', cursor: 'pointer' }}>
            v2.1 model assumptions &amp; known simplifications
          </summary>
          <ul style={{ fontSize: 10, color: '#999', margin: '6px 0 0 16px', lineHeight: 1.6 }}>
            {known_simplifications.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </details>
      )}
    </div>
  )
}
