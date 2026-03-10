import React, { useState } from 'react'
import { SCENARIO_BASELINE, SCENARIO_PRESETS } from '../../data/mockInputsData.js'

const FIELD_CONFIG = [
  { key: 'biomass_tonnes',     label: 'Total Biomass',       unit: 't',     min: 1000, max: 50000, step: 100   },
  { key: 'oxygen_mg_l',        label: 'Dissolved Oxygen',    unit: 'mg/L',  min: 3,    max: 12,    step: 0.1   },
  { key: 'nitrate_umol_l',     label: 'Nitrate',             unit: 'µmol/L',min: 0,    max: 40,    step: 0.5   },
  { key: 'lice_pressure',      label: 'Lice Pressure Index', unit: 'index', min: 0.5,  max: 4,     step: 0.1   },
  { key: 'exposure_factor',    label: 'Exposure Factor',     unit: 'x',     min: 0.5,  max: 2.0,   step: 0.05  },
  { key: 'operational_factor', label: 'Operational Factor',  unit: 'x',     min: 0.5,  max: 2.0,   step: 0.05  },
]

function deltaFromBaseline(key, value) {
  const base = SCENARIO_BASELINE[key]
  if (base == null) return null
  const d = ((value - base) / base) * 100
  return d
}

export default function ScenarioOverridePanel() {
  const [values, setValues]       = useState({ ...SCENARIO_BASELINE })
  const [scenarioResult, setResult] = useState(null)
  const [running, setRunning]     = useState(false)

  function applyPreset(preset) {
    setValues({ ...SCENARIO_BASELINE, ...preset.overrides })
    setResult(null)
  }

  function handleChange(key, raw) {
    const v = parseFloat(raw)
    if (!isNaN(v)) setValues(prev => ({ ...prev, [key]: v }))
  }

  function reset() {
    setValues({ ...SCENARIO_BASELINE })
    setResult(null)
  }

  function runScenario() {
    setRunning(true)
    // Stub: simulate a 1s "run" then show placeholder result
    setTimeout(() => {
      const scaleFactor = (values.lice_pressure * 0.15 + values.exposure_factor * 0.25 +
                          values.operational_factor * 0.10 + (values.nitrate_umol_l > 10 ? 0.12 : 0)) + 0.80
      setResult({
        scenario_scale_factor: parseFloat(scaleFactor.toFixed(2)),
        estimated_annual_loss_change_pct: parseFloat(((scaleFactor - 1.0) * 100).toFixed(1)),
        highest_risk_driver: values.lice_pressure > 1.5 ? 'Sea Lice Pressure' : values.nitrate_umol_l > 10 ? 'HAB (Nitrate)' : 'Exposure',
        note: 'Scenario estimate — connect /api/c5ai/scenario for full Monte Carlo output.',
      })
      setRunning(false)
    }, 900)
  }

  return (
    <div>
      {/* Preset buttons */}
      <div className="scenario-presets">
        <span className="scenario-preset-label">Presets:</span>
        {SCENARIO_PRESETS.map(p => (
          <button key={p.id} className="scenario-preset-btn" onClick={() => applyPreset(p)}
                  title={p.description}>
            {p.label}
          </button>
        ))}
      </div>

      {/* Override inputs */}
      <div className="scenario-fields-grid">
        {FIELD_CONFIG.map(({ key, label, unit, min, max, step }) => {
          const base  = SCENARIO_BASELINE[key]
          const delta = deltaFromBaseline(key, values[key])
          const sign  = delta > 0 ? '+' : ''
          const color = delta > 5 ? '#DC2626' : delta < -5 ? '#16A34A' : 'var(--dark-grey)'
          return (
            <div key={key} className="scenario-field-card">
              <label className="scenario-field-label">{label}</label>
              <div className="scenario-field-row">
                <input
                  type="number"
                  className="scenario-input"
                  value={values[key]}
                  min={min}
                  max={max}
                  step={step}
                  onChange={e => handleChange(key, e.target.value)}
                />
                <span className="scenario-unit">{unit}</span>
              </div>
              <div className="scenario-baseline-row">
                <span style={{ color:'var(--dark-grey)', fontSize:11 }}>Baseline: {base}</span>
                {delta != null && Math.abs(delta) > 0.5 && (
                  <span style={{ color, fontSize: 11, fontWeight: 600 }}>
                    {sign}{delta.toFixed(1)}%
                  </span>
                )}
              </div>
              <input
                type="range"
                className="scenario-slider"
                value={values[key]}
                min={min}
                max={max}
                step={step}
                onChange={e => handleChange(key, e.target.value)}
              />
            </div>
          )
        })}
      </div>

      {/* Action buttons */}
      <div className="scenario-actions">
        <button className="btn-run-scenario" onClick={runScenario} disabled={running}>
          {running ? 'Running…' : 'Run Scenario'}
        </button>
        <button className="btn-reset-scenario" onClick={reset}>Reset to Baseline</button>
      </div>

      {/* Result */}
      {scenarioResult && (
        <div className="scenario-result card">
          <div className="section-title" style={{ marginBottom: 10 }}>Scenario Result (Estimate)</div>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-label">Scale Factor</div>
              <div className="kpi-value" style={{ color: '#7C3AED' }}>{scenarioResult.scenario_scale_factor}×</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Annual Loss Change</div>
              <div className="kpi-value" style={{ color: scenarioResult.estimated_annual_loss_change_pct > 0 ? '#DC2626' : '#16A34A' }}>
                {scenarioResult.estimated_annual_loss_change_pct > 0 ? '+' : ''}{scenarioResult.estimated_annual_loss_change_pct}%
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Highest Risk Driver</div>
              <div className="kpi-value" style={{ fontSize: 14 }}>{scenarioResult.highest_risk_driver}</div>
            </div>
          </div>
          <div className="info-note" style={{ marginTop: 10 }}>{scenarioResult.note}</div>
        </div>
      )}
    </div>
  )
}
