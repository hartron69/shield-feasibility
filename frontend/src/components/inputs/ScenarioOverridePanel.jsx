import React, { useState } from 'react'
import { SCENARIO_BASELINE, SCENARIO_PRESETS } from '../../data/mockInputsData.js'
import { runScenario } from '../../api/client.js'

const SEA_FIELD_CONFIG = [
  { key: 'biomass_tonnes',     label: 'Total Biomass',       unit: 't',      min: 1000, max: 50000, step: 100  },
  { key: 'oxygen_mg_l',        label: 'Dissolved Oxygen',    unit: 'mg/L',   min: 3,    max: 12,    step: 0.1  },
  { key: 'nitrate_umol_l',     label: 'Nitrate',             unit: 'µmol/L', min: 0,    max: 40,    step: 0.5  },
  { key: 'lice_pressure',      label: 'Lice Pressure Index', unit: 'index',  min: 0.5,  max: 4,     step: 0.1  },
  { key: 'exposure_factor',    label: 'Exposure Factor',     unit: 'x',      min: 0.5,  max: 2.0,   step: 0.05 },
  { key: 'operational_factor', label: 'Operational Factor',  unit: 'x',      min: 0.5,  max: 2.0,   step: 0.05 },
]

const SMOLT_FIELD_CONFIG = [
  { key: 'oxygen_mg_l',          label: 'O₂-nivå',             unit: 'mg/L',  min: 3,   max: 12,  step: 0.1 },
  { key: 'power_backup_hours',   label: 'Backup-strøm',         unit: 'timer', min: 0,   max: 72,  step: 1   },
  { key: 'ras_failure_multiplier', label: 'RAS-feilmultiplikator', unit: 'x', min: 0.5, max: 10,  step: 0.1 },
]

const SMOLT_BASELINE = {
  oxygen_mg_l:            8.5,
  power_backup_hours:     24,
  ras_failure_multiplier: 1.0,
}

// Demo smolt facilities — matches SMOLT_SITE_RISK in mockSmoltSiteRiskData.js
const FACILITY_OPTIONS = [
  { label: 'Alle anlegg',        value: null },
  { label: 'Agaqua Jelsa',       value: 0 },
  { label: 'Agaqua Tau',         value: 1 },
  { label: 'Nordic Smolt Fjord', value: 2 },
  { label: 'SalmoSet Ryfylke',   value: 3 },
  { label: 'AquaGen Sunnfjord',  value: 4 },
]

function deltaFromBaseline(key, value, baseline) {
  const base = baseline[key]
  if (base == null || base === 0) return null
  return ((value - base) / base) * 100
}

function fmtNOK(v) {
  if (v == null) return '—'
  if (Math.abs(v) >= 1_000_000) return `NOK ${(v / 1_000_000).toFixed(1)} M`
  if (Math.abs(v) >= 1_000)     return `NOK ${(v / 1_000).toFixed(0)} k`
  return `NOK ${v.toFixed(0)}`
}

function ChangePct({ pct }) {
  if (pct == null) return null
  const color = pct > 0 ? '#DC2626' : '#16A34A'
  const arrow = pct > 0 ? '▲' : '▼'
  return (
    <span style={{ color, fontWeight: 700 }}>
      {arrow} {pct > 0 ? '+' : ''}{pct.toFixed(1)} %
    </span>
  )
}

export default function ScenarioOverridePanel({ operatorType = 'sea', operator, smoltInput }) {
  const isSmolt      = operatorType === 'smolt'
  const fieldConfig  = isSmolt ? SMOLT_FIELD_CONFIG : SEA_FIELD_CONFIG
  const baselineData = isSmolt ? SMOLT_BASELINE : SCENARIO_BASELINE

  const [values, setValues]           = useState({ ...baselineData })
  const [scenarioResult, setResult]   = useState(null)
  const [running, setRunning]         = useState(false)
  const [error, setError]             = useState(null)
  const [selectedFacilityIndex, setFacilityIndex] = useState(null)

  function applyPreset(preset) {
    setValues({ ...baselineData, ...preset.overrides })
    setResult(null)
    setError(null)
  }

  function handleChange(key, raw) {
    const v = parseFloat(raw)
    if (!isNaN(v)) setValues(prev => ({ ...prev, [key]: v }))
  }

  function reset() {
    setValues({ ...baselineData })
    setResult(null)
    setError(null)
  }

  async function handleRunScenario() {
    setRunning(true)
    setError(null)
    try {
      const payload = {
        facility_type:           operatorType,
        preset_id:               'custom',
        operator:                !isSmolt ? (operator || null) : null,
        smolt_operator:          isSmolt  ? (smoltInput || null) : null,
        // Sea parameters from sliders
        dissolved_oxygen_mg_l:   !isSmolt ? (values.oxygen_mg_l ?? null)        : null,
        lice_pressure_index:     !isSmolt ? (values.lice_pressure ?? null)       : null,
        exposure_factor:         !isSmolt ? (values.exposure_factor ?? null)     : null,
        operational_factor:      !isSmolt ? (values.operational_factor ?? null)  : null,
        total_biomass_override:  !isSmolt ? (values.biomass_tonnes ?? null)      : null,
        nitrate_umol_l:          !isSmolt ? (values.nitrate_umol_l ?? null)      : null,
        // Smolt / RAS parameters
        ras_failure_multiplier:  isSmolt  ? (values.ras_failure_multiplier ?? null) : null,
        power_backup_hours:      isSmolt  ? (values.power_backup_hours ?? null)     : null,
        oxygen_level_mg_l:       isSmolt  ? (values.oxygen_mg_l ?? null)            : null,
        affected_facility_index: selectedFacilityIndex,
      }
      const result = await runScenario(payload)
      setResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      {/* Preset buttons */}
      {!isSmolt && (
        <div className="scenario-presets">
          <span className="scenario-preset-label">Presets:</span>
          {SCENARIO_PRESETS.map(p => (
            <button key={p.id} className="scenario-preset-btn" onClick={() => applyPreset(p)}
                    title={p.description}>
              {p.label}
            </button>
          ))}
        </div>
      )}

      {/* Smolt: affected facility selector */}
      {isSmolt && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--dark-grey)', marginRight: 8 }}>
            Berørt anlegg:
          </label>
          <select
            value={selectedFacilityIndex ?? ''}
            onChange={e => setFacilityIndex(e.target.value === '' ? null : Number(e.target.value))}
            style={{ fontSize: 12, padding: '3px 8px', borderRadius: 4, border: '1px solid #d1d5db' }}
          >
            {FACILITY_OPTIONS.map(opt => (
              <option key={String(opt.value)} value={opt.value ?? ''}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Sea: affected site selector (when sites are configured) */}
      {!isSmolt && operator?.sites && operator.sites.length > 1 && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--dark-grey)', marginRight: 8 }}>
            Berørt lokalitet:
          </label>
          <select
            value={selectedFacilityIndex ?? ''}
            onChange={e => setFacilityIndex(e.target.value === '' ? null : Number(e.target.value))}
            style={{ fontSize: 12, padding: '3px 8px', borderRadius: 4, border: '1px solid #d1d5db' }}
          >
            <option value="">Alle lokaliteter</option>
            {operator.sites.map((s, idx) => (
              <option key={idx} value={idx}>{s.site_name || s.name || `Lokalitet ${idx + 1}`}</option>
            ))}
          </select>
        </div>
      )}

      {/* Slider inputs */}
      <div className="scenario-fields-grid">
        {fieldConfig.map(({ key, label, unit, min, max, step }) => {
          const delta = deltaFromBaseline(key, values[key], baselineData)
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
                <span style={{ color: 'var(--dark-grey)', fontSize: 11 }}>
                  Baseline: {baselineData[key]}
                </span>
                {delta != null && Math.abs(delta) > 0.5 && (
                  <span style={{ color, fontSize: 11, fontWeight: 600 }}>
                    {sign}{delta.toFixed(1)} %
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
        <button className="btn-run-scenario" onClick={handleRunScenario} disabled={running}>
          {running ? 'Kjører…' : 'Kjør scenario'}
        </button>
        <button className="btn-reset-scenario" onClick={reset}>Tilbakestill</button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ marginTop: 10, padding: '8px 12px', background: '#fef2f2',
                      border: '1px solid #fca5a5', borderRadius: 6, fontSize: 12, color: '#dc2626' }}>
          {error}
        </div>
      )}

      {/* Result */}
      {scenarioResult && (
        <div className="scenario-result card">
          <div className="section-title" style={{ marginBottom: 10 }}>Scenario-resultat</div>

          {/* Per-facility table for smolt; single row for sea */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: '#f0f4f8', textAlign: 'left' }}>
                  <th style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>Anlegg</th>
                  <th style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>Baseline/år</th>
                  <th style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>Scenario</th>
                  <th style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>Endring</th>
                </tr>
              </thead>
              <tbody>
                {scenarioResult.facility_results.map((fr, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '5px 10px', fontWeight: 600 }}>{fr.facility_name}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtNOK(fr.baseline_expected_loss)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtNOK(fr.scenario_expected_loss)}</td>
                    <td style={{ padding: '5px 10px' }}><ChangePct pct={fr.change_pct} /></td>
                  </tr>
                ))}
              </tbody>
              {isSmolt && scenarioResult.facility_results.length > 1 && (
                <tfoot>
                  <tr style={{ background: '#f7f9fb', fontWeight: 700 }}>
                    <td style={{ padding: '6px 10px' }}>KONSERN TOTAL<br/>
                      <span style={{ fontWeight: 400, fontSize: 10 }}>(etter diversif.)</span>
                    </td>
                    <td style={{ padding: '6px 10px' }}>{fmtNOK(scenarioResult.baseline_total_loss)}</td>
                    <td style={{ padding: '6px 10px' }}>{fmtNOK(scenarioResult.scenario_total_loss)}</td>
                    <td style={{ padding: '6px 10px' }}><ChangePct pct={scenarioResult.total_change_pct} /></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>

          {/* KPI row */}
          <div className="kpi-grid" style={{ marginTop: 12 }}>
            <div className="kpi-card">
              <div className="kpi-label">Tapendring totalt</div>
              <div className="kpi-value" style={{
                color: scenarioResult.total_change_pct > 0 ? '#DC2626' : '#16A34A',
                fontSize: 20,
              }}>
                {scenarioResult.total_change_pct > 0 ? '+' : ''}
                {scenarioResult.total_change_pct.toFixed(1)} %
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Høyeste risikofaktor</div>
              <div className="kpi-value" style={{ fontSize: 14 }}>
                {scenarioResult.highest_risk_driver}
              </div>
            </div>
          </div>

          {/* Narrative */}
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--dark-grey)',
                        background: '#f9fafb', borderRadius: 6, padding: '8px 12px',
                        border: '1px solid #e5e7eb' }}>
            {scenarioResult.narrative}
          </div>
        </div>
      )}
    </div>
  )
}
