import React from 'react'

function fmt(v, prefix = 'NOK ') {
  if (v == null) return '—'
  const abs = Math.abs(v)
  if (abs >= 1_000_000_000) return `${prefix}${(v / 1_000_000_000).toFixed(2)}B`
  if (abs >= 1_000_000) return `${prefix}${(v / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `${prefix}${(v / 1_000).toFixed(0)}k`
  return `${prefix}${v.toFixed(0)}`
}

function KPICard({ label, baseline, mitigated, formatFn = fmt, lowerIsBetter = true }) {
  const delta = mitigated != null ? mitigated - baseline : null
  const isImprovement = delta != null && (lowerIsBetter ? delta < 0 : delta > 0)
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{formatFn(baseline)}</div>
      {mitigated != null && (
        <>
          <div className="kpi-sub">Mitigated: {formatFn(mitigated)}</div>
          <div className={`kpi-delta ${isImprovement ? 'pos' : 'neg'}`}>
            {delta >= 0 ? '+' : ''}{formatFn(delta, '')}
          </div>
        </>
      )}
    </div>
  )
}

// C5AI+ enrichment indicator shown when biological scale factor differs from 1.0
function C5AIEnrichmentBar({ scaleFactor }) {
  if (!scaleFactor || Math.abs(scaleFactor - 1.0) < 0.01) return null
  return (
    <div className="c5ai-enrichment-bar">
      <span className="c5ai-pill">C5AI+</span>
      <span>
        <strong>Biological risk intelligence applied.</strong>
        {' '}Scale factor <strong>{scaleFactor.toFixed(2)}×</strong> from C5AI+ model
        (static baseline = 1.00×). Switch to the{' '}
        <strong>C5AI+ Risk Intelligence</strong> page for full biological forecast,
        risk drivers, and learning status.
      </span>
    </div>
  )
}

export default function SummaryTab({ baseline, mitigated }) {
  const b = baseline.summary
  const m = mitigated?.summary
  // c5ai_scale_factor may be present if backend enriches the response
  const c5aiScale = baseline.c5ai_scale_factor

  return (
    <div>
      <C5AIEnrichmentBar scaleFactor={c5aiScale} />
      <div className="section-title">Key Risk Metrics</div>
      <div className="kpi-grid">
        <KPICard label="Expected Annual Loss" baseline={b.expected_annual_loss} mitigated={m?.expected_annual_loss} />
        <KPICard label="P95 Loss" baseline={b.p95_loss} mitigated={m?.p95_loss} />
        <KPICard label="P99 Loss" baseline={b.p99_loss} mitigated={m?.p99_loss} />
        <KPICard label="SCR (Net)" baseline={b.scr} mitigated={m?.scr} />
        <KPICard
          label="Composite Score"
          baseline={b.composite_score}
          mitigated={m?.composite_score}
          formatFn={(v) => v != null ? `${v.toFixed(1)}/100` : '—'}
          lowerIsBetter={false}
        />
      </div>

      <div className="section-title">Verdict</div>
      <div className={`verdict-banner ${b.verdict.startsWith('STRONGLY') ? 'verdict-STRONGLY' : b.verdict.startsWith('RECOMMENDED') ? 'verdict-RECOMMENDED' : b.verdict.startsWith('POTENTIALLY') ? 'verdict-POTENTIALLY' : 'verdict-NOT'}`}>
        {b.verdict}
        <span style={{ fontSize: 14, fontWeight: 400, marginLeft: 12 }}>
          Confidence: {b.confidence_level}
        </span>
      </div>
    </div>
  )
}
