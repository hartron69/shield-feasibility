import React from 'react'

export default function StrategySettings({ values, onChange }) {
  return (
    <div>
      <div className="field">
        <label>Primary Strategy</label>
        <select value={values.strategy}
          onChange={(e) => onChange({ ...values, strategy: e.target.value })}>
          <option value="pcc_captive">PCC Captive Cell (recommended)</option>
          <option value="full_insurance">Full Insurance (baseline)</option>
          <option value="hybrid">Hybrid</option>
          <option value="self_insurance">Self-Insurance</option>
        </select>
      </div>
      <div className="field">
        <label>Custom Retention (NOK, leave blank for auto)</label>
        <input type="number" min="0"
          value={values.retention_nok ?? ''}
          placeholder="Auto-calculated"
          onChange={(e) =>
            onChange({ ...values, retention_nok: e.target.value ? parseFloat(e.target.value) : null })
          }
        />
      </div>
    </div>
  )
}
