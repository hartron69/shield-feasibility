import React from 'react'

/**
 * OperatorTypeSelector
 * Vises øverst i venstre panel. Lar bruker velge mellom:
 *   - Sjøoppdrett (eksisterende flyt)
 *   - Settefisk / RAS (ny flyt)
 */
export function OperatorTypeSelector({ value, onChange }) {
  return (
    <div className="operator-type-selector">
      <button
        className={`type-btn ${value === 'sea' ? 'active' : ''}`}
        onClick={() => onChange('sea')}
      >
        Sjooppdrett
      </button>
      <button
        className={`type-btn ${value === 'smolt' ? 'active' : ''}`}
        onClick={() => onChange('smolt')}
      >
        Settefisk / RAS
      </button>
    </div>
  )
}
