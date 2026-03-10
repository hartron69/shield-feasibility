import React from 'react'

const STEPS = [
  'Validate',
  'Monte Carlo',
  'Strategies',
  'SCR / Cost',
  'Suitability',
  'Report',
]

export default function StatusBar({ loading, currentStep, error }) {
  if (!loading && !error && currentStep === 0) return null

  return (
    <div className="status-bar">
      {error ? (
        <div className="error-msg">{error}</div>
      ) : (
        <>
          <div>
            {loading && <span className="spinner">⟳</span>}
            {loading ? `Step ${currentStep} of ${STEPS.length}: ${STEPS[currentStep - 1] || ''}` : 'Complete'}
          </div>
          <div className="status-steps">
            {STEPS.map((s, i) => {
              const stepNum = i + 1
              const cls = !loading ? 'done'
                : stepNum < currentStep ? 'done'
                : stepNum === currentStep ? 'active'
                : ''
              return (
                <span key={s} className={`status-step ${cls}`}>{s}</span>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
