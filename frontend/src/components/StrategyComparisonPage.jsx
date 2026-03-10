import React from 'react'

const STRATEGIES = [
  {
    id: 'pcc_captive',
    name: 'PCC Captive Cell',
    description: 'Protected cell company structure with dedicated cell for the operator. Capital held within cell; reinsurance purchased to cap tail exposure.',
    tcor_5yr_m: 64,
    solvency_ratio: 1.0,
    pros: ['Lower long-run TCOR vs. FI', 'Capital control', 'RI structure limits catastrophic exposure'],
    cons: ['Requires NOK 25M cell reserve', 'Regulatory oversight', 'Fronting fee 3–5%'],
    verdict: 'RECOMMENDED',
  },
  {
    id: 'full_insurance',
    name: 'Full Insurance (FI)',
    description: 'Traditional market placement. Premiums ceded to insurer; claims recovered on event. Market pricing applies.',
    tcor_5yr_m: 97,
    solvency_ratio: null,
    pros: ['Simplest structure', 'No capital requirement', 'Immediate cover'],
    cons: ['Highest long-run cost', 'Market cycle risk', 'Coverage gaps at renewal'],
    verdict: 'BASELINE',
  },
  {
    id: 'pooling',
    name: 'Mutual Pooling',
    description: 'Group of 4 similar operators pool risk. Shared administration savings. RI purchased at portfolio level.',
    tcor_5yr_m: 74,
    solvency_ratio: null,
    pros: ['Admin savings ~20%', 'Diversification benefit', 'Shared RI buying power'],
    cons: ['Requires 4+ members', 'Inter-member correlation risk', 'Governance complexity'],
    verdict: 'ALTERNATIVE',
  },
]

const VERDICT_STYLE = {
  RECOMMENDED: { bg:'#D1FAE5', color:'#065F46' },
  BASELINE:    { bg:'#F3F4F6', color:'#374151' },
  ALTERNATIVE: { bg:'#DBEAFE', color:'#1D4ED8' },
}

export default function StrategyComparisonPage({ result }) {
  const hasResult = !!result

  return (
    <div style={{ maxWidth: 1000 }}>
      <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>Strategy Comparison</div>
      <div style={{ fontSize: 13, color:'var(--dark-grey)', marginBottom: 20 }}>
        Side-by-side comparison of PCC Captive, Full Insurance, and Mutual Pooling structures.
        {!hasResult && ' Run a Feasibility analysis first for operator-specific TCOR values.'}
      </div>

      {!hasResult && (
        <div className="info-note" style={{ marginBottom: 20 }}>
          Showing illustrative values based on Nordic Aqua Partners AS demo data.
          Switch to PCC Feasibility, load the example, and run analysis for precise figures.
        </div>
      )}

      <div className="strategy-comparison-grid">
        {STRATEGIES.map(s => {
          const vstyle = VERDICT_STYLE[s.verdict] || {}
          return (
            <div key={s.id} className="strategy-card card" style={{ borderTop: `4px solid ${vstyle.color || '#666'}` }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:10 }}>
                <div style={{ fontWeight:700, fontSize:15 }}>{s.name}</div>
                <span style={{ background:vstyle.bg, color:vstyle.color, padding:'2px 10px', borderRadius:12, fontSize:11, fontWeight:700 }}>
                  {s.verdict}
                </span>
              </div>
              <div style={{ fontSize:13, color:'var(--dark-grey)', marginBottom:14, lineHeight:1.5 }}>{s.description}</div>

              <div className="kpi-grid" style={{ marginBottom:14 }}>
                <div className="kpi-card">
                  <div className="kpi-label">5yr TCOR (illustrative)</div>
                  <div className="kpi-value">NOK {s.tcor_5yr_m}M</div>
                </div>
                {s.solvency_ratio != null && (
                  <div className="kpi-card">
                    <div className="kpi-label">Solvency Ratio</div>
                    <div className="kpi-value">{s.solvency_ratio.toFixed(1)}×</div>
                  </div>
                )}
              </div>

              <div style={{ marginBottom:8 }}>
                <div style={{ fontSize:11, fontWeight:700, color:'#16A34A', marginBottom:4 }}>Advantages</div>
                <ul style={{ paddingLeft:16, fontSize:12, lineHeight:1.8 }}>
                  {s.pros.map((p,i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
              <div>
                <div style={{ fontSize:11, fontWeight:700, color:'#DC2626', marginBottom:4 }}>Drawbacks</div>
                <ul style={{ paddingLeft:16, fontSize:12, lineHeight:1.8 }}>
                  {s.cons.map((c,i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
