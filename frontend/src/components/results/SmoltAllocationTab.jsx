import React from 'react'

/**
 * SmoltAllocationTab
 * TIV-fordeling spesifikk for settefisk.
 * Vises i stedet for generisk AllocationTab når operator_type == "smolt".
 */

function fmt(n, dec = 0) {
  if (n == null) return '—'
  return n.toLocaleString('nb-NO', { maximumFractionDigits: dec })
}
function fmtM(n) {
  if (n == null) return '—'
  return `NOK ${(n / 1e6).toFixed(1)} M`
}
function pct(n) {
  if (n == null) return '—'
  return `${(n * 100).toFixed(1)} %`
}

// ── SVG donut chart (4 segmenter, stroke-dasharray metode) ───────────────────
const DONUT_COLORS  = ['#0D1B2A', '#4B5563', '#1B8A7A', '#F4A820']
const DONUT_LABELS  = ['Bygg', 'Maskiner', 'Biomasse', 'BI']
const DONUT_KEYS    = ['buildings', 'machinery', 'biomass', 'bi']

function DonutChart({ shares }) {
  const r           = 38
  const cx          = 50
  const cy          = 50
  const circumf     = 2 * Math.PI * r
  let   dashOffset  = 0   // starts at 12 o'clock (rotation -90 below)

  const segments = DONUT_KEYS.map((key, i) => {
    const share = shares[key] || 0
    const len   = share * circumf
    const seg   = (
      <circle
        key={key}
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={DONUT_COLORS[i]}
        strokeWidth={18}
        strokeDasharray={`${len} ${circumf - len}`}
        strokeDashoffset={-dashOffset}
        style={{ transform: `rotate(-90deg)`, transformOrigin: `${cx}px ${cy}px` }}
      />
    )
    dashOffset += len
    return seg
  })

  return (
    <svg viewBox="0 0 100 100" width={140} height={140}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f0f0f0" strokeWidth={18} />
      {segments}
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize={8} fill="#555">Total</text>
      <text x={cx} y={cy + 8} textAnchor="middle" fontSize={8} fill="#555">TIV</text>
    </svg>
  )
}

function DonutLegend({ shares }) {
  return (
    <div className="smolt-donut-legend">
      {DONUT_KEYS.map((key, i) => (
        <div key={key} className="smolt-legend-row">
          <span className="smolt-legend-dot" style={{ background: DONUT_COLORS[i] }} />
          <span className="smolt-legend-label">{DONUT_LABELS[i]}</span>
          <span className="smolt-legend-pct">{pct(shares[key])}</span>
        </div>
      ))}
    </div>
  )
}

export default function SmoltAllocationTab({ allocationSummary, facilities }) {
  if (!allocationSummary) {
    return (
      <div className="tab-content" style={{ color: '#888', padding: 24 }}>
        Allocation-data ikke tilgjengelig. Kjør analysen først.
      </div>
    )
  }

  const {
    total_tiv_nok,
    biomass_share,
    property_share,
    bi_share,
    machinery_share,
    building_share,
    n_facilities,
    facility_names,
    scr_capacity_ratio,
    liquidity_post_scr_nok,
  } = allocationSummary

  // Shares for donut — fall back to zeros if not available
  const shares = {
    buildings: building_share  ?? (property_share - (machinery_share ?? 0)),
    machinery: machinery_share ?? 0,
    biomass:   biomass_share   ?? 0,
    bi:        bi_share        ?? 0,
  }

  // Normalise to sum=1 in case of floating point drift
  const total = Object.values(shares).reduce((a, b) => a + b, 0)
  if (total > 0) {
    Object.keys(shares).forEach(k => { shares[k] = shares[k] / total })
  }

  return (
    <div className="tab-content">

      {/* ── TIV-oversikt med donut ──────────────────────────────────── */}
      <h4 style={{ margin: '0 0 12px', fontSize: 14, color: '#0D1B2A' }}>
        TIV-fordeling — {n_facilities} anlegg
      </h4>

      <div className="smolt-donut-section">
        <DonutChart shares={shares} />
        <DonutLegend shares={shares} />
        <div className="kpi-card" style={{ minWidth: 160 }}>
          <div className="kpi-label">Total TIV</div>
          <div className="kpi-value">{fmtM(total_tiv_nok)}</div>
          <div className="kpi-sub">{n_facilities} anlegg</div>
        </div>
      </div>

      {/* ── Nøkkel-KPI-er ─────────────────────────────────────────── */}
      <div className="kpi-grid" style={{ marginBottom: 20, marginTop: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">Bygg-andel</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>{pct(building_share)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Maskiner/RAS</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>{pct(machinery_share)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Biomasse-andel</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>{pct(biomass_share)}</div>
          <div className="kpi-sub">Lav (typisk 6–9 % for RAS)</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">BI-andel</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>{pct(bi_share)}</div>
          <div className="kpi-sub">Dominerende post</div>
        </div>
      </div>

      {/* ── SCR-kapasitetsanalyse ──────────────────────────────────── */}
      <h4 style={{ margin: '16px 0 8px', fontSize: 13, color: '#555' }}>
        SCR-kapasitetsanalyse
      </h4>
      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        <div className="kpi-card" style={
          scr_capacity_ratio != null && scr_capacity_ratio < 1.0
            ? { borderColor: '#DC2626', background: '#FEF2F2' } : {}
        }>
          <div className="kpi-label">SCR-kapasitetsratio</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>
            {scr_capacity_ratio != null ? scr_capacity_ratio.toFixed(2) : '—'}
          </div>
          <div className="kpi-sub">Likvider / SCR</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Likvider etter SCR</div>
          <div className="kpi-value" style={{ fontSize: 18 }}>
            {fmtM(liquidity_post_scr_nok)}
          </div>
          <div className="kpi-sub">Buffer etter reservekrav</div>
        </div>
      </div>

      {/* ── Per-anlegg tabell ──────────────────────────────────────── */}
      {facilities && facilities.length > 0 && (
        <>
          <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#555' }}>
            Per-anlegg TIV-detaljer
          </h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%', borderCollapse: 'collapse',
              fontSize: 12, minWidth: 560,
            }}>
              <thead>
                <tr style={{ background: '#f0f4f8', textAlign: 'left' }}>
                  {['Anlegg', 'Type', 'Maskiner', 'Biomasse', 'BI', 'Måneder', 'Total TIV'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {facilities.map((f, i) => {
                  const buildingTotal = (f.building_components || []).reduce(
                    (s, c) => s + (c.area_sqm || 0) * (c.value_per_sqm_nok || 0), 0,
                  ) + (f.site_clearance_nok || 0)
                  const tiv = buildingTotal + (f.machinery_nok || 0) +
                    (f.avg_biomass_insured_value_nok || 0) + (f.bi_sum_insured_nok || 0)
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '5px 10px', fontWeight: 600 }}>{f.facility_name}</td>
                      <td style={{ padding: '5px 10px', color: '#666' }}>{f.facility_type}</td>
                      <td style={{ padding: '5px 10px' }}>{fmtM(f.machinery_nok)}</td>
                      <td style={{ padding: '5px 10px' }}>{fmtM(f.avg_biomass_insured_value_nok)}</td>
                      <td style={{ padding: '5px 10px' }}>{fmtM(f.bi_sum_insured_nok)}</td>
                      <td style={{ padding: '5px 10px' }}>{f.bi_indemnity_months} mnd</td>
                      <td style={{ padding: '5px 10px', fontWeight: 600 }}>{fmtM(tiv)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ── Nøkkelobservasjoner ───────────────────────────────────── */}
      <div className="smolt-observations">
        <div style={{ fontSize: 12, color: '#555', fontWeight: 600, marginBottom: 6 }}>
          Nøkkelobservasjoner
        </div>
        {biomass_share != null && biomass_share < 0.10 && (
          <div className="smolt-obs-row">
            Biomasse-andel ({pct(biomass_share)}) er lav — typisk for RAS. BI og maskiner dominerer TIV.
          </div>
        )}
        {bi_share != null && bi_share > 0.30 && (
          <div className="smolt-obs-row">
            BI-andel ({pct(bi_share)}) er dominerende — indemnitetperiode og salgspris er kritiske
            forsikringsparametere.
          </div>
        )}
        {scr_capacity_ratio != null && scr_capacity_ratio < 1.5 && (
          <div className="smolt-obs-row smolt-obs-warning">
            SCR-kapasitetsratio ({scr_capacity_ratio.toFixed(2)}) er lav. Vurder økt egenkapital
            eller lavere PCC-egenandel.
          </div>
        )}
      </div>
    </div>
  )
}
