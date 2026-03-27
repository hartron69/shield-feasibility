import React from 'react'

// Panel showing how risk changed over the period, broken down by domain and factor

const DOMAIN_LABELS = {
  biological:    'Biologisk',
  structural:    'Strukturell',
  environmental: 'Miljø',
  operational:   'Operasjonell',
}

const DOMAIN_COLORS = {
  biological:    '#3A86FF',
  structural:    '#FF6B6B',
  environmental: '#36A271',
  operational:   '#F4A620',
}

function DeltaChip({ delta }) {
  if (delta == null) return <span style={{ color: '#9ca3af' }}>—</span>
  const isIncrease = delta > 0
  const isDecrease = delta < 0
  const color = isIncrease ? '#c62828' : isDecrease ? '#2e7d32' : '#6b7280'
  const arrow = isIncrease ? '▲' : isDecrease ? '▼' : '●'
  return (
    <span style={{ color, fontWeight: 700, whiteSpace: 'nowrap' }}>
      {arrow} {isIncrease ? '+' : ''}{delta.toFixed(1)} pkt
    </span>
  )
}

function formatDate(isoStr) {
  if (!isoStr) return '—'
  return new Date(isoStr).toLocaleDateString('nb-NO', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function RiskChangeBreakdownPanel({ breakdown }) {
  if (!breakdown) {
    return <p style={{ color: '#6b7280', fontStyle: 'italic' }}>Ingen endringsdata tilgjengelig</p>
  }

  const {
    period_days,
    from_date,
    to_date,
    risk_at_start,
    risk_at_end,
    total_delta,
    domain_deltas = {},
    factor_deltas = [],
    explanation_summary = [],
    confidence_note,
    data_limited = false,
    data_available_days,
  } = breakdown

  const totalIncrease = total_delta > 0
  const totalDecrease = total_delta < 0
  const totalColor = totalIncrease ? '#c62828' : totalDecrease ? '#2e7d32' : '#6b7280'
  const totalArrow = totalIncrease ? '▲' : totalDecrease ? '▼' : '●'

  return (
    <div className="lr-breakdown-panel">
      {/* Summary header */}
      <div style={{
        background: '#f9fafb',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: '14px 16px',
        marginBottom: 16,
      }}>
        <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
          Risikoen endret seg{' '}
          <span style={{ color: totalColor }}>
            {totalArrow} {total_delta != null ? `${total_delta > 0 ? '+' : ''}${total_delta.toFixed(1)} poeng` : '—'}
          </span>
          {' '}over {period_days != null ? `${period_days} dager` : '—'}
        </div>
        <div style={{ fontSize: 12, color: '#6b7280' }}>
          {formatDate(from_date)} til {formatDate(to_date)}
          {risk_at_start != null && risk_at_end != null && (
            <span style={{ marginLeft: 8 }}>
              ({Math.round(risk_at_start)} → {Math.round(risk_at_end)} pkt)
            </span>
          )}
        </div>
      </div>

      {/* Data limitation notice */}
      {data_limited && (
        <div style={{
          background: '#fffbeb',
          border: '1px solid #fcd34d',
          borderRadius: 6,
          padding: '8px 12px',
          marginBottom: 14,
          fontSize: 12,
          color: '#92400e',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{ fontSize: 14 }}>⚠</span>
          <span>
            Historikk begrenser seg til {data_available_days} dager.
            12 måneder er ikke tilgjengelig i nåværende datakilde.
          </span>
        </div>
      )}

      {/* Domain delta cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, marginBottom: 16 }}>
        {Object.entries(DOMAIN_LABELS).map(([domain, label]) => {
          const delta = domain_deltas[domain]
          const color = DOMAIN_COLORS[domain]
          const isIncrease = delta > 0
          const isDecrease = delta < 0
          const deltaColor = isIncrease ? '#c62828' : isDecrease ? '#2e7d32' : '#6b7280'
          const arrow = isIncrease ? '▲' : isDecrease ? '▼' : '●'
          return (
            <div key={domain} style={{
              border: `1px solid ${color}33`,
              borderLeft: `3px solid ${color}`,
              borderRadius: 6,
              padding: '10px 12px',
              background: 'white',
            }}>
              <div style={{ fontSize: 11, color: '#6b7280', fontWeight: 600, marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: deltaColor }}>
                {delta != null ? `${arrow} ${delta > 0 ? '+' : ''}${delta.toFixed(1)}` : '—'}
              </div>
              <div style={{ fontSize: 10, color: '#9ca3af' }}>poeng</div>
            </div>
          )
        })}
      </div>

      {/* Factor breakdown — grouped by domain */}
      {factor_deltas.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#374151' }}>
            Faktorbidrag per risikogruppe
          </div>
          {Object.entries(DOMAIN_LABELS).map(([domain, domainLabel]) => {
            const domainFactors = factor_deltas.filter(f => f.domain === domain)
            if (domainFactors.length === 0) return null
            const color = DOMAIN_COLORS[domain]
            const domainDelta = domain_deltas[domain]
            const deltaColor = domainDelta > 0 ? '#c62828' : domainDelta < 0 ? '#2e7d32' : '#6b7280'
            return (
              <div key={domain} style={{
                marginBottom: 10,
                border: `1px solid ${color}33`,
                borderLeft: `3px solid ${color}`,
                borderRadius: 6,
                overflow: 'hidden',
              }}>
                {/* Domain header row */}
                <div style={{
                  background: `${color}10`,
                  padding: '6px 10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}>
                  <span style={{ fontWeight: 700, fontSize: 12, color }}>
                    {domainLabel}
                  </span>
                  {domainDelta != null && (
                    <span style={{ fontWeight: 700, fontSize: 12, color: deltaColor }}>
                      {domainDelta > 0 ? '▲ +' : domainDelta < 0 ? '▼ ' : '● '}
                      {domainDelta.toFixed(1)} pkt
                    </span>
                  )}
                </div>
                {/* Factor rows */}
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <tbody>
                    {domainFactors.map((f, i) => (
                      <tr key={i} style={{
                        borderTop: '1px solid #f3f4f6',
                        background: i % 2 === 0 ? 'white' : '#fafafe',
                      }}>
                        <td style={{ padding: '6px 10px', fontWeight: 600, width: '22%' }}>
                          {f.factor}
                        </td>
                        <td style={{ padding: '6px 10px', width: '16%' }}>
                          <DeltaChip delta={f.delta} />
                        </td>
                        <td style={{ padding: '6px 10px', color: '#6b7280' }}>
                          {f.explanation || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          })}
        </div>
      )}

      {/* Explanation summary */}
      {explanation_summary.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6, color: '#374151' }}>Oppsummering</div>
          <ul style={{ paddingLeft: 18, color: '#374151', fontSize: 13, lineHeight: 1.7 }}>
            {explanation_summary.map((line, i) => <li key={i}>{line}</li>)}
          </ul>
        </div>
      )}

      {/* Confidence note */}
      {confidence_note && (
        <p style={{ fontSize: 11, color: '#9ca3af', fontStyle: 'italic', marginTop: 8 }}>
          {confidence_note}
        </p>
      )}
    </div>
  )
}
