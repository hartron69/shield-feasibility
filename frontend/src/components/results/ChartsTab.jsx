import React from 'react'

const CHART_LABELS = {
  loss_distribution: 'Loss Distribution',
  cumulative_costs: 'Cumulative 5-Year Costs',
  annual_comparison: 'Annual Cost Comparison',
  scr_comparison: 'SCR Comparison',
  risk_return_frontier: 'Risk-Return Frontier',
  suitability_radar: 'Suitability Radar',
  cost_box_whisker: 'Cost Box & Whisker',
  domain_corr_heatmap: 'Domain Correlation Heatmap',
  scenario_domain_stacks: 'Scenario Domain Stacks',
  tail_domain_composition: 'Tail Domain Composition',
}

export default function ChartsTab({ charts }) {
  const entries = Object.entries(charts || {})
  if (!entries.length) {
    return <div className="result-placeholder"><p>No charts available.</p></div>
  }
  return (
    <div className="chart-grid">
      {entries.map(([key, b64]) => (
        <div key={key} className="chart-card">
          <h4>{CHART_LABELS[key] || key}</h4>
          <img src={`data:image/png;base64,${b64}`} alt={key} />
        </div>
      ))}
    </div>
  )
}
