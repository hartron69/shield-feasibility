import React from 'react'
import SeaLocalitySelector from './SeaLocalitySelector.jsx'
import SeaLocalityAllocationTable from './SeaLocalityAllocationTable.jsx'

// Inline styles for auto-calculated fields
const AUTO_INPUT_STYLE = {
  background: 'rgba(27,138,122,0.06)',
  borderColor: 'rgba(27,138,122,0.35)',
  color: '#1B5E50',
}

function AutoChip() {
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: '0.4px',
      textTransform: 'uppercase', background: 'rgba(27,138,122,0.12)',
      color: '#1B8A7A', borderRadius: 4, padding: '1px 5px',
      marginLeft: 6, verticalAlign: 'middle',
    }}>auto</span>
  )
}

// Suggested = reference_price × 1000 × realisation × (1 − haircut)
function computeSuggested(ref, realisation, haircut) {
  return Math.round(ref * 1000 * realisation * (1 - haircut))
}

export default function OperatorProfile({
  values,
  onChange,
  derived = new Set(),
  siteSelectionMode = 'generic',
  onSiteModeChange,
  selectedSites = [],
  onSelectedSitesChange,
}) {
  const set = (field) => (e) => onChange({ ...values, [field]: e.target.value })
  const setNum = (field) => (e) => onChange({ ...values, [field]: parseFloat(e.target.value) || 0 })
  const setInt = (field) => (e) => onChange({ ...values, [field]: parseInt(e.target.value) || 1 })

  // Mill NOK ↔ NOK converters for revenue / premium fields
  const setMillNok = (field) => (e) => {
    const mill = parseFloat(e.target.value) || 0
    onChange({ ...values, [field]: Math.round(mill * 1_000_000) })
  }
  const toMillNok = (nok) => parseFloat((nok / 1_000_000).toFixed(2))

  const inputStyle = (field) => derived.has(field) ? AUTO_INPUT_STYLE : {}

  // ── Biomass valuation helpers ──────────────────────────────────────────────
  const ref = values.reference_price_per_kg ?? 80
  const realisation = values.realisation_factor ?? 0.90
  const haircut = values.prudence_haircut ?? 0.10
  const suggested = computeSuggested(ref, realisation, haircut)
  const isOverridden = values.biomass_value_per_tonne_override != null

  function handleAppliedChange(e) {
    const val = Math.round(parseFloat(e.target.value) || 0)
    onChange({
      ...values,
      biomass_value_per_tonne: val,
      biomass_value_per_tonne_override: val,   // mark as manual override
    })
  }

  function handleUseSuggested() {
    onChange({
      ...values,
      biomass_value_per_tonne: suggested,
      biomass_value_per_tonne_override: null,  // clear override
    })
  }

  // ── Specific locality mode handlers ───────────────────────────────────────
  function handleSiteSelectionIds(newIds, registrySites) {
    // Keep existing allocation data for already-selected sites; initialise new ones
    const existing = {}
    for (const s of selectedSites) existing[s.site_id] = s

    const next = registrySites
      .filter(r => newIds.has(r.site_id))
      .map(r => existing[r.site_id] || {
        site_id: r.site_id,
        locality_no: r.locality_no,
        site_name: r.site_name,
        biomass_tonnes: 3000,
        biomass_value_nok: null,        // auto-derive
        biomass_value_manual: false,
        fjord_exposure: r.fjord_exposure || 'semi_exposed',
        lice_pressure_factor: 1.0,
        hab_risk_factor: 1.0,
      })
    onSelectedSitesChange(next)
  }

  const appliedValue = values.biomass_value_per_tonne || suggested || 64800
  const isSpecific = siteSelectionMode === 'specific'
  const selectedIdSet = new Set(selectedSites.map(s => s.site_id))

  return (
    <div>
      {/* ── Identity ───────────────────────────────────────────────── */}
      <div className="field">
        <label>Operator Name</label>
        <input value={values.name} onChange={set('name')} placeholder="e.g. Nordic Aqua Partners AS" />
      </div>

      <div className="field">
        <label>Country</label>
        <input value={values.country} onChange={set('country')} placeholder="e.g. Norge" />
      </div>

      {/* ── Sea-site mode selector ─────────────────────────────────── */}
      {onSiteModeChange && (
        <div style={{ marginTop: 10, marginBottom: 8 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#667', letterSpacing: '0.5px',
            textTransform: 'uppercase', marginBottom: 6 }}>
            Porteføljemodus
          </div>
          <div className="sea-mode-selector">
            <button
              type="button"
              className={`sea-mode-btn ${!isSpecific ? 'active' : ''}`}
              onClick={() => onSiteModeChange('generic')}
            >
              Generisk portefølje
            </button>
            <button
              type="button"
              className={`sea-mode-btn ${isSpecific ? 'active' : ''}`}
              onClick={() => onSiteModeChange('specific')}
            >
              Spesifikke lokaliteter
            </button>
          </div>
        </div>
      )}

      {/* ── Generic mode: n_sites + total biomass ─────────────────── */}
      {!isSpecific && (
        <div className="field-row">
          <div className="field">
            <label>Number of Sites</label>
            <input type="number" min="1" max="20" value={values.n_sites} onChange={setInt('n_sites')} />
          </div>
          <div className="field">
            <label>Total Biomass (t)</label>
            <input type="number" min="1" value={values.total_biomass_tonnes} onChange={setNum('total_biomass_tonnes')} />
          </div>
        </div>
      )}

      {/* ── Specific mode: locality selector + allocation ─────────── */}
      {isSpecific && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#667', letterSpacing: '0.5px',
            textTransform: 'uppercase', marginBottom: 6 }}>
            Velg lokaliteter fra C5AI+ / BarentsWatch
          </div>
          <SeaLocalitySelector
            selectedIds={selectedIdSet}
            onChange={handleSiteSelectionIds}
          />

          {selectedSites.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#667', letterSpacing: '0.5px',
                textTransform: 'uppercase', marginBottom: 6 }}>
                Fordel biomasse og verdi
              </div>
              <SeaLocalityAllocationTable
                sites={selectedSites}
                onChange={onSelectedSitesChange}
                appliedValue={appliedValue}
              />
            </div>
          )}

          {selectedSites.length > 0 && (
            <div style={{
              marginTop: 8, fontSize: 11, padding: '6px 10px',
              background: '#ecfdf5', border: '1px solid #6ee7b7',
              borderRadius: 5, color: '#065f46', lineHeight: 1.5,
            }}>
              Denne analysen er basert p&#229; {selectedSites.length} valgte lokaliteter fra C5AI+ / BarentsWatch.
              BW-lokalitetsnummer: {selectedSites.map(s => s.locality_no).join(', ')}.
            </div>
          )}
        </div>
      )}

      {/* ── Biomass Valuation ──────────────────────────────────────── */}
      <div style={{
        borderTop: '1px solid #e8ecf0', marginTop: 12, paddingTop: 10,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#667', letterSpacing: '0.5px',
          textTransform: 'uppercase', marginBottom: 8 }}>
          Biomass Valuation
        </div>

        <div className="field-row">
          <div className="field">
            <label>Reference Price (NOK/kg)</label>
            <input
              type="number" min="1" step="1"
              value={values.reference_price_per_kg ?? 80}
              onChange={setNum('reference_price_per_kg')}
            />
          </div>
          <div className="field">
            <label>Realisation Factor</label>
            <input
              type="number" min="0.5" max="1.2" step="0.01"
              value={values.realisation_factor ?? 0.90}
              onChange={setNum('realisation_factor')}
            />
          </div>
        </div>

        <div className="field">
          <label>Prudence Haircut</label>
          <input
            type="number" min="0" max="0.5" step="0.01"
            value={values.prudence_haircut ?? 0.10}
            onChange={setNum('prudence_haircut')}
          />
        </div>

        {/* Suggested value — read-only with formula explanation */}
        <div style={{
          background: '#f4f8fb', border: '1px solid #d5e3ee',
          borderRadius: 6, padding: '7px 10px', marginBottom: 8, fontSize: 12,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#556', fontWeight: 600 }}>Suggested value</span>
            <span style={{ fontWeight: 700, color: '#1B5E50', fontSize: 14 }}>
              {suggested.toLocaleString('nb-NO')} NOK/t
            </span>
          </div>
          <div style={{ color: '#889', fontSize: 11, marginTop: 3 }}>
            {ref} &times; 1&#8239;000 &times; {realisation} &times; (1 &minus; {haircut})
            {' '}= {suggested.toLocaleString('nb-NO')} NOK/t
          </div>
        </div>

        {/* Applied value — editable, shows override state */}
        <div className="field">
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            Applied Value / Tonne (NOK)
            {isOverridden && (
              <span style={{
                fontSize: 10, fontWeight: 700, background: '#fff3cd',
                color: '#856404', border: '1px solid #ffc107',
                borderRadius: 4, padding: '1px 5px',
              }}>Manual override</span>
            )}
          </label>
          <input
            type="number"
            min="1"
            value={values.biomass_value_per_tonne}
            onChange={handleAppliedChange}
            style={isOverridden ? { borderColor: '#ffc107', background: '#fffdf0' } : {}}
          />
          {isOverridden && (
            <button
              type="button"
              onClick={handleUseSuggested}
              style={{
                marginTop: 4, fontSize: 11, padding: '3px 8px',
                background: '#f4f8fb', border: '1px solid #b8d0e8',
                borderRadius: 4, cursor: 'pointer', color: '#2c6e9c',
              }}
            >
              Use suggested ({suggested.toLocaleString('nb-NO')} NOK/t)
            </button>
          )}
        </div>
      </div>

      {/* ── Revenue / Premium ──────────────────────────────────────── */}
      <div style={{ borderTop: '1px solid #e8ecf0', marginTop: 12, paddingTop: 10 }}>
        <div className="field">
          <label>
            Annual Revenue (Mill NOK)
            {derived.has('annual_revenue_nok') && <AutoChip />}
          </label>
          <input
            type="number" min="0.1" step="0.1"
            value={toMillNok(values.annual_revenue_nok)}
            onChange={setMillNok('annual_revenue_nok')}
            style={inputStyle('annual_revenue_nok')}
          />
        </div>

        <div className="field">
          <label>
            Annual Insurance Premium (Mill NOK)
            {derived.has('annual_premium_nok') && <AutoChip />}
          </label>
          <input
            type="number" min="0.01" step="0.1"
            value={toMillNok(values.annual_premium_nok)}
            onChange={setMillNok('annual_premium_nok')}
            style={inputStyle('annual_premium_nok')}
          />
        </div>
      </div>
    </div>
  )
}
