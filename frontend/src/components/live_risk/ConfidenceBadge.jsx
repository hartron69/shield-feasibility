import React from 'react'

// Display confidence level as a colored badge with optional percentage score
const LEVEL_CONFIG = {
  high:   { bg: '#e8f5e9', color: '#2e7d32', label: 'Høy tillit' },
  medium: { bg: '#fff8e1', color: '#f57f17', label: 'Moderat tillit' },
  low:    { bg: '#fdecea', color: '#c62828', label: 'Lav tillit' },
}

export default function ConfidenceBadge({ level, score, showScore = false }) {
  const cfg = LEVEL_CONFIG[level] || LEVEL_CONFIG.medium

  return (
    <span
      className="lr-confidence-badge"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        background: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.color}33`,
        borderRadius: 12,
        padding: '2px 8px',
        fontSize: 12,
        fontWeight: 600,
        whiteSpace: 'nowrap',
      }}
    >
      {cfg.label}
      {showScore && score != null && (
        <span style={{ fontWeight: 400, opacity: 0.85 }}>
          {' '}({Math.round(score * 100)}%)
        </span>
      )}
    </span>
  )
}
