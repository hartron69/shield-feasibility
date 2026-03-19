import React, { useState } from 'react'
import { SmoltBIWidget } from './SmoltBIWidget.jsx'

/**
 * SmoltTIVPanel
 * Viser ett akkordeon-kort per anlegg med bygg, maskiner, biomasse og BI.
 * Live TIV-beregning ved alle endringer.
 */

const FACILITY_TYPES = [
  { value: 'smolt_ras',    label: 'RAS (lukket system)'  },
  { value: 'smolt_flow',   label: 'Gjennomstrøm'         },
  { value: 'smolt_hybrid', label: 'Hybrid RAS/gjennomstrøm' },
]

function fmt(n) {
  if (!n && n !== 0) return '—'
  return (n / 1_000_000).toFixed(1) + ' M'
}

function computeFacilityTIV(f) {
  const buildingTotal = (f.building_components || []).reduce(
    (s, c) => s + (parseFloat(c.area_sqm) || 0) * (parseFloat(c.value_per_sqm_nok) || 0),
    0,
  ) + (parseFloat(f.site_clearance_nok) || 0)
  return (
    buildingTotal +
    (parseFloat(f.machinery_nok)                 || 0) +
    (parseFloat(f.avg_biomass_insured_value_nok) || 0) +
    (parseFloat(f.bi_sum_insured_nok)            || 0)
  )
}

function numInput(label, value, onChange, placeholder) {
  return (
    <div className="smolt-field-row">
      <label>{label}</label>
      <input
        type="number"
        value={value === 0 ? '' : value}
        onChange={e => onChange(parseFloat(e.target.value) || 0)}
        placeholder={placeholder || '0'}
        className="smolt-input"
      />
    </div>
  )
}

function FacilityCard({ facility, index, expanded, onToggle, onChange, onRemove }) {
  const tiv = computeFacilityTIV(facility)

  function update(field, value) {
    onChange(index, { ...facility, [field]: value })
  }

  function updateComponent(ci, field, value) {
    const updated = facility.building_components.map((c, i) =>
      i === ci ? { ...c, [field]: value } : c,
    )
    onChange(index, { ...facility, building_components: updated })
  }

  function addComponent() {
    onChange(index, {
      ...facility,
      building_components: [
        ...facility.building_components,
        { name: '', area_sqm: 0, value_per_sqm_nok: 27000 },
      ],
    })
  }

  function removeComponent(ci) {
    onChange(index, {
      ...facility,
      building_components: facility.building_components.filter((_, i) => i !== ci),
    })
  }

  return (
    <div className="smolt-facility-card">
      {/* Header */}
      <div className="smolt-facility-header" onClick={onToggle}>
        <div style={{ flex: 1 }}>
          <span className="smolt-facility-name">
            {facility.facility_name || `Anlegg ${index + 1}`}
          </span>
          <span className="smolt-facility-type-badge">
            {facility.facility_type}
          </span>
        </div>
        <span className="smolt-tiv-badge">TIV {fmt(tiv)}</span>
        <span style={{ marginLeft: 8, fontSize: 11, color: '#888' }}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {expanded && (
        <div className="smolt-facility-body">
          {/* Anleggsnavn og type */}
          <div className="smolt-field-row">
            <label>Anleggnavn</label>
            <input
              type="text"
              value={facility.facility_name}
              onChange={e => update('facility_name', e.target.value)}
              className="smolt-input"
              placeholder="f.eks. Villa Smolt AS"
            />
          </div>
          <div className="smolt-field-row">
            <label>Kommune</label>
            <input
              type="text"
              value={facility.municipality || ''}
              onChange={e => update('municipality', e.target.value)}
              className="smolt-input"
              placeholder="f.eks. Herøy"
            />
          </div>
          <div className="smolt-field-row">
            <label>Anleggstype</label>
            <select
              value={facility.facility_type}
              onChange={e => update('facility_type', e.target.value)}
              className="smolt-input"
            >
              {FACILITY_TYPES.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* Bygningskomponenter */}
          <div className="smolt-section-label">Bygningskomponenter</div>
          {facility.building_components.map((c, ci) => (
            <div key={ci} className="smolt-component-row">
              <input
                type="text"
                value={c.name}
                onChange={e => updateComponent(ci, 'name', e.target.value)}
                className="smolt-input smolt-input-name"
                placeholder="Navn"
              />
              <input
                type="number"
                value={c.area_sqm || ''}
                onChange={e => updateComponent(ci, 'area_sqm', parseFloat(e.target.value) || 0)}
                className="smolt-input smolt-input-sqm"
                placeholder="m²"
              />
              <input
                type="number"
                value={c.value_per_sqm_nok || ''}
                onChange={e => updateComponent(ci, 'value_per_sqm_nok', parseFloat(e.target.value) || 0)}
                className="smolt-input smolt-input-sqm"
                placeholder="NOK/m²"
              />
              <span className="smolt-comp-value">
                {fmt((c.area_sqm || 0) * (c.value_per_sqm_nok || 0))}
              </span>
              <button className="smolt-remove-btn" onClick={() => removeComponent(ci)}>–</button>
            </div>
          ))}
          <button className="smolt-add-btn" onClick={addComponent}>+ Legg til bygning</button>

          {/* Maskiner, tomt, biomasse, BI */}
          {numInput('Branntomt/rydding (NOK)', facility.site_clearance_nok,
            v => update('site_clearance_nok', v))}
          {numInput('Maskiner/RAS (NOK)', facility.machinery_nok,
            v => update('machinery_nok', v))}
          {numInput('Biomasse gjennomsnitt (NOK)', facility.avg_biomass_insured_value_nok,
            v => update('avg_biomass_insured_value_nok', v))}
          {numInput('BI sum forsikret (NOK)', facility.bi_sum_insured_nok,
            v => update('bi_sum_insured_nok', v))}

          <div className="smolt-field-row">
            <label>Indemnitetperiode</label>
            <select
              value={facility.bi_indemnity_months}
              onChange={e => update('bi_indemnity_months', Number(e.target.value))}
              className="smolt-input"
            >
              <option value={12}>12 måneder</option>
              <option value={24}>24 måneder</option>
              <option value={36}>36 måneder</option>
            </select>
          </div>

          {/* BI-kalkulator */}
          <SmoltBIWidget
            facilityName={facility.facility_name}
            onApply={bi => update('bi_sum_insured_nok', bi)}
          />

          {/* TIV-sammendrag */}
          <div className="smolt-tiv-summary">
            <div className="smolt-tiv-row">
              <span>Bygg + tomt</span>
              <span>{fmt(
                (facility.building_components || []).reduce(
                  (s, c) => s + (c.area_sqm || 0) * (c.value_per_sqm_nok || 0), 0,
                ) + (facility.site_clearance_nok || 0),
              )}</span>
            </div>
            <div className="smolt-tiv-row">
              <span>Maskiner/RAS</span>
              <span>{fmt(facility.machinery_nok)}</span>
            </div>
            <div className="smolt-tiv-row">
              <span>Biomasse</span>
              <span>{fmt(facility.avg_biomass_insured_value_nok)}</span>
            </div>
            <div className="smolt-tiv-row">
              <span>BI</span>
              <span>{fmt(facility.bi_sum_insured_nok)}</span>
            </div>
            <div className="smolt-tiv-row smolt-tiv-total">
              <span>Total TIV</span>
              <span>NOK {fmt(tiv)}</span>
            </div>
          </div>

          {onRemove && (
            <button
              className="smolt-remove-facility-btn"
              onClick={() => onRemove(index)}
            >
              Fjern anlegg
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export function SmoltTIVPanel({ facilities, onChange, onAddFacility, onRemoveFacility }) {
  const [expanded, setExpanded] = useState(0)

  const totalTIV = facilities.reduce((s, f) => s + computeFacilityTIV(f), 0)

  function handleChange(index, updated) {
    const next = facilities.map((f, i) => i === index ? updated : f)
    onChange(next)
  }

  return (
    <div className="smolt-tiv-panel">
      <div className="smolt-panel-header">
        <span>Anlegg ({facilities.length})</span>
        <span className="smolt-total-tiv">Total TIV: NOK {fmt(totalTIV)}</span>
      </div>

      {facilities.map((f, i) => (
        <FacilityCard
          key={i}
          facility={f}
          index={i}
          expanded={expanded === i}
          onToggle={() => setExpanded(expanded === i ? -1 : i)}
          onChange={handleChange}
          onRemove={facilities.length > 1 ? onRemoveFacility : null}
        />
      ))}

      <button className="smolt-add-facility-btn" onClick={onAddFacility}>
        + Legg til anlegg
      </button>
    </div>
  )
}
