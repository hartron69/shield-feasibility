import React from 'react'

const SOURCE_CONFIG = {
  real:      { label: 'Real',      cls: 'source-real'      },
  simulated: { label: 'Simulated', cls: 'source-simulated' },
  estimated: { label: 'Estimated', cls: 'source-estimated' },
  missing:   { label: 'Missing',   cls: 'source-missing'   },
}

export default function InputSourceBadge({ source }) {
  const cfg = SOURCE_CONFIG[source] || SOURCE_CONFIG.missing
  return (
    <span className={`input-source-badge ${cfg.cls}`}>{cfg.label}</span>
  )
}
