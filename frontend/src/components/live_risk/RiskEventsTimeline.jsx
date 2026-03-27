import React from 'react'

// Vertical timeline of risk events, most recent first

const SEVERITY_CONFIG = {
  info:     { bg: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe', label: 'Info' },
  warning:  { bg: '#fffbeb', color: '#b45309', border: '#fde68a', label: 'Advarsel' },
  critical: { bg: '#fef2f2', color: '#b91c1c', border: '#fecaca', label: 'Kritisk' },
}

const DOMAIN_COLORS = {
  biological:    '#3A86FF',
  structural:    '#FF6B6B',
  environmental: '#36A271',
  operational:   '#F4A620',
}

const DOMAIN_LABELS = {
  biological:    'Biologisk',
  structural:    'Strukturell',
  environmental: 'Miljø',
  operational:   'Operasjonell',
}

function formatEventDate(isoStr) {
  if (!isoStr) return '—'
  const d = new Date(isoStr)
  const dd = String(d.getDate()).padStart(2, '0')
  const mon = d.toLocaleString('nb-NO', { month: 'short' })
  const yyyy = d.getFullYear()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${dd}. ${mon} ${yyyy} ${hh}:${mm}`
}

function SeverityChip({ severity }) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info
  return (
    <span style={{
      background: cfg.bg,
      color: cfg.color,
      border: `1px solid ${cfg.border}`,
      borderRadius: 10,
      padding: '1px 8px',
      fontSize: 11,
      fontWeight: 700,
    }}>
      {cfg.label}
    </span>
  )
}

function DomainChip({ domain }) {
  const color = DOMAIN_COLORS[domain] || '#6b7280'
  const label = DOMAIN_LABELS[domain] || domain
  return (
    <span style={{
      background: `${color}18`,
      color,
      border: `1px solid ${color}44`,
      borderRadius: 10,
      padding: '1px 8px',
      fontSize: 11,
      fontWeight: 600,
    }}>
      {label}
    </span>
  )
}

function RiskImpactBadge({ impact }) {
  if (impact == null) return null
  const isPositive = impact > 0
  const color = isPositive ? '#c62828' : '#2e7d32'
  return (
    <span style={{ color, fontWeight: 700, fontSize: 12, marginLeft: 6 }}>
      {isPositive ? '+' : ''}{impact.toFixed(1)} pkt
    </span>
  )
}

export default function RiskEventsTimeline({ events = [] }) {
  if (!events || events.length === 0) {
    return (
      <div className="lr-events-empty" style={{ padding: 24, color: '#6b7280', fontStyle: 'italic', textAlign: 'center' }}>
        Ingen hendelser i valgt periode
      </div>
    )
  }

  // Sort most recent first
  const sorted = [...events].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))

  return (
    <div className="lr-events-timeline" style={{ position: 'relative' }}>
      {/* Vertical line */}
      <div style={{
        position: 'absolute',
        left: 15,
        top: 8,
        bottom: 8,
        width: 2,
        background: '#e5e7eb',
        borderRadius: 1,
      }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, paddingLeft: 36 }}>
        {sorted.map((ev, i) => {
          const svCfg = SEVERITY_CONFIG[ev.severity] || SEVERITY_CONFIG.info
          const dotColor = svCfg.color
          return (
            <div key={ev.event_id || i} style={{ position: 'relative' }}>
              {/* Timeline dot */}
              <div style={{
                position: 'absolute',
                left: -28,
                top: 14,
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: dotColor,
                border: '2px solid white',
                boxShadow: `0 0 0 2px ${dotColor}44`,
              }} />

              {/* Event card */}
              <div style={{
                background: 'white',
                border: '1px solid #e5e7eb',
                borderLeft: `3px solid ${dotColor}`,
                borderRadius: 8,
                padding: '10px 14px',
              }}>
                {/* Top row: timestamp + chips */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, color: '#9ca3af', whiteSpace: 'nowrap' }}>
                    {formatEventDate(ev.timestamp)}
                  </span>
                  <SeverityChip severity={ev.severity} />
                  {ev.domain && <DomainChip domain={ev.domain} />}
                  {ev.risk_impact != null && <RiskImpactBadge impact={ev.risk_impact} />}
                </div>

                {/* Title */}
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 3, color: '#111827' }}>
                  {ev.title}
                </div>

                {/* Description */}
                {ev.description && (
                  <div style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.5 }}>
                    {ev.description}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
