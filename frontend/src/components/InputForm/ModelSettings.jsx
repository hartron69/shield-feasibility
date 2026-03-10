import React from 'react'

export default function ModelSettings({ values, onChange }) {
  const set = (field) => (e) => onChange({ ...values, [field]: e.target.value })

  return (
    <div>
      <div className="field">
        <label>Simulations</label>
        <select value={values.n_simulations}
          onChange={(e) => onChange({ ...values, n_simulations: parseInt(e.target.value) })}>
          <option value={1000}>1 000 (fast)</option>
          <option value={5000}>5 000 (recommended)</option>
          <option value={10000}>10 000 (accurate)</option>
          <option value={20000}>20 000 (high precision)</option>
        </select>
      </div>
      <div className="field">
        <label>Domain Correlation Model</label>
        <select value={values.domain_correlation} onChange={set('domain_correlation')}>
          <option value="independent">Independent (no correlation)</option>
          <option value="low">Low correlation</option>
          <option value="expert_default">Expert default (recommended)</option>
          <option value="moderate">Moderate correlation</option>
        </select>
      </div>
      <div className="field" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <input type="checkbox" id="gen-pdf" checked={values.generate_pdf}
          onChange={(e) => onChange({ ...values, generate_pdf: e.target.checked })} />
        <label htmlFor="gen-pdf" style={{ marginBottom: 0, cursor: 'pointer' }}>
          Generate board PDF report
        </label>
      </div>
      <div className="field" style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
        <input type="checkbox" id="use-history" checked={values.use_history_calibration ?? false}
          onChange={(e) => onChange({ ...values, use_history_calibration: e.target.checked })} />
        <label htmlFor="use-history" style={{ marginBottom: 0, cursor: 'pointer' }}>
          Calibrate risk parameters from loss history
          <span style={{
            display: 'block', fontSize: 10, color: '#888', fontWeight: 400, marginTop: 1,
          }}>
            When on, uses observed loss records to set severity and frequency instead of TIV scaling
          </span>
        </label>
      </div>
    </div>
  )
}
