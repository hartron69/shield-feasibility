import React from 'react'

const LEVEL_LABELS = {
  CRITICAL: 'CRITICAL',
  WARNING:  'WARNING',
  WATCH:    'WATCH',
  NORMAL:   'NORMAL',
}

export default function AlertLevelBadge({ level }) {
  return (
    <span className={`alert-level-badge alert-level-${level}`}>
      {LEVEL_LABELS[level] || level}
    </span>
  )
}
