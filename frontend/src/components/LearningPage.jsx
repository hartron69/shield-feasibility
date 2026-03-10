import React from 'react'
import LearningStatusTab from './c5ai/LearningStatusTab.jsx'
import { C5AI_MOCK } from '../data/c5ai_mock.js'
import { MOCK_DATA_QUALITY } from '../data/mockInputsData.js'

export default function LearningPage() {
  const avgCompleteness = MOCK_DATA_QUALITY.reduce((s, d) => s + d.overall_completeness, 0) / MOCK_DATA_QUALITY.length

  return (
    <div style={{ maxWidth: 900 }}>
      <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>Learning Status</div>
      <div style={{ fontSize: 13, color:'var(--dark-grey)', marginBottom: 16 }}>
        Bayesian learning loop status, model versions, and evaluation metrics.
      </div>

      {/* Data context banner */}
      <div className="info-note" style={{ marginBottom: 16 }}>
        Training source: <strong>{C5AI_MOCK.learning.training_source === 'simulated' ? 'Simulated data' : 'Operator-reported data'}</strong>.
        Portfolio input completeness: <strong>{Math.round(avgCompleteness * 100)}%</strong>.
        {C5AI_MOCK.learning.training_source === 'simulated' && (
          <span style={{ color:'#92400E' }}>
            {' '}Upload real environmental records to accelerate model promotion to ACTIVE status.
          </span>
        )}
      </div>

      <LearningStatusTab data={C5AI_MOCK} />
    </div>
  )
}
