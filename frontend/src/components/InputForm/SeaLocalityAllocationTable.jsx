import React, { useState } from 'react'
import CagePortfolioPanel from './CagePortfolioPanel'

/**
 * SeaLocalityAllocationTable
 *
 * Props:
 *   sites         – array of { site_id, locality_no, site_name, biomass_tonnes, biomass_value_nok, cages? }
 *   onChange      – (updatedSites) => void
 *   appliedValue  – NOK/tonne used for auto-derivation
 */
export default function SeaLocalityAllocationTable({ sites = [], onChange, appliedValue = 64800 }) {
  const [expandedCages, setExpandedCages] = useState({})  // site_id → boolean

  function toggleCages(siteId) {
    setExpandedCages(prev => ({ ...prev, [siteId]: !prev[siteId] }))
  }

  function handleCagesChange(siteIdx, updatedCages) {
    const next = sites.map((s, i) => i === siteIdx ? { ...s, cages: updatedCages } : s)
    onChange(next)
  }
  const totalBiomass = sites.reduce((s, x) => s + (parseFloat(x.biomass_tonnes) || 0), 0)

  function updateSite(idx, field, value) {
    const next = sites.map((s, i) => {
      if (i !== idx) return s
      const updated = { ...s, [field]: value }
      // When biomass_tonnes changes and value was auto, keep auto flag
      if (field === 'biomass_tonnes') {
        if (!s.biomass_value_manual) {
          updated.biomass_value_nok = null  // will be auto-derived
        }
        // Recompute cage biomass_tonnes from stored biomass_pct
        if (s.cages && s.cages.length > 0) {
          const newTotal = parseFloat(value) || 0
          updated.cages = s.cages.map(c => ({
            ...c,
            biomass_tonnes: (parseFloat(c.biomass_pct) || 0) * newTotal / 100,
          }))
        }
      }
      if (field === 'biomass_value_nok') {
        updated.biomass_value_manual = value !== null && value !== ''
      }
      return updated
    })
    onChange(next)
  }

  function autoDistributeBiomass() {
    if (sites.length === 0) return
    const perSite = Math.round(totalBiomass / sites.length) || 3000
    onChange(sites.map(s => ({ ...s, biomass_tonnes: perSite })))
  }

  function clearValueOverride(idx) {
    const next = sites.map((s, i) =>
      i === idx ? { ...s, biomass_value_nok: null, biomass_value_manual: false } : s
    )
    onChange(next)
  }

  if (sites.length === 0) {
    return (
      <div style={{ color: 'var(--dark-grey)', fontSize: 12, padding: '8px 0' }}>
        Velg lokaliteter ovenfor for å fordele biomasse og verdi.
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>
          Total biomasse: <strong>{totalBiomass.toLocaleString('nb-NO')} t</strong>
        </div>
        <button
          type="button"
          onClick={autoDistributeBiomass}
          style={{ fontSize: 10, padding: '2px 8px', borderRadius: 3,
            border: '1px solid #b8d0e8', background: '#f4f8fb',
            cursor: 'pointer', color: '#2c6e9c' }}
        >
          Fordel biomasse jevnt
        </button>
      </div>

      <div style={{ border: '1px solid #e5e7eb', borderRadius: 6, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
              <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--dark-grey)' }}>Lokalitet</th>
              <th style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 600, color: 'var(--dark-grey)' }}>Biomasse (t)</th>
              <th style={{ textAlign: 'right', padding: '6px 8px', fontWeight: 600, color: 'var(--dark-grey)' }}>Verdi (NOK)</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--dark-grey)' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {sites.map((site, i) => {
              const bv = site.biomass_value_manual
                ? site.biomass_value_nok
                : (parseFloat(site.biomass_tonnes) || 0) * appliedValue
              const isAuto = !site.biomass_value_manual
              const cagesExpanded = expandedCages[site.site_id]
              const cageCount = (site.cages || []).length

              return (
                <React.Fragment key={site.site_id}>
                  <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                    <td style={{ padding: '6px 8px' }}>
                      <div style={{ fontWeight: 600 }}>{site.site_name}</div>
                      <div style={{ fontSize: 10, color: 'var(--dark-grey)', fontFamily: 'monospace' }}>
                        BW {site.locality_no}
                      </div>
                      <button
                        type="button"
                        onClick={() => toggleCages(site.site_id)}
                        style={{ fontSize: 9, marginTop: 3, padding: '1px 6px',
                          borderRadius: 3, border: '1px solid #b8d0e8',
                          background: cagesExpanded ? '#e3f2fd' : '#f4f8fb',
                          cursor: 'pointer', color: '#2c6e9c' }}
                      >
                        {cagesExpanded ? '▾' : '▸'} Merder {cageCount > 0 ? `(${cageCount})` : ''}
                      </button>
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>
                      <input
                        type="number"
                        min="1"
                        value={site.biomass_tonnes || ''}
                        onChange={e => updateSite(i, 'biomass_tonnes', parseFloat(e.target.value) || 0)}
                        style={{ width: 80, textAlign: 'right', fontSize: 12,
                          border: '1px solid #d1d5db', borderRadius: 4, padding: '3px 6px' }}
                      />
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>
                      <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <input
                          type="number"
                          min="1"
                          value={isAuto ? Math.round(bv) : (site.biomass_value_nok || '')}
                          onChange={e => updateSite(i, 'biomass_value_nok', parseFloat(e.target.value) || null)}
                          style={{
                            width: 110, textAlign: 'right', fontSize: 12,
                            border: '1px solid #d1d5db', borderRadius: 4, padding: '3px 6px',
                            background: isAuto ? 'rgba(27,138,122,0.06)' : 'white',
                            color: isAuto ? '#1B5E50' : 'inherit',
                          }}
                        />
                        {!isAuto && (
                          <button
                            type="button"
                            title="Tilbakestill til auto"
                            onClick={() => clearValueOverride(i)}
                            style={{ fontSize: 10, padding: '1px 5px', borderRadius: 3,
                              border: '1px solid #ffc107', background: '#fffdf0',
                              cursor: 'pointer', color: '#856404' }}
                          >
                            ×
                          </button>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '6px 8px' }}>
                      {isAuto ? (
                        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.3px',
                          background: 'rgba(27,138,122,0.12)', color: '#1B8A7A',
                          borderRadius: 3, padding: '1px 5px' }}>
                          Auto-fordelt
                        </span>
                      ) : (
                        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.3px',
                          background: '#fff3cd', color: '#856404',
                          border: '1px solid #ffc107', borderRadius: 3, padding: '1px 5px' }}>
                          Manuell
                        </span>
                      )}
                    </td>
                  </tr>
                  {cagesExpanded && (
                    <tr>
                      <td colSpan={4} style={{ padding: 0, background: '#f8fafd', borderBottom: '1px solid #e5e7eb' }}>
                        <div style={{ padding: '8px 12px' }}>
                          <CagePortfolioPanel
                            siteId={site.site_id}
                            siteName={site.site_name}
                            totalSiteBiomass={parseFloat(site.biomass_tonnes) || 0}
                            cages={site.cages || []}
                            onChange={updated => handleCagesChange(i, updated)}
                          />
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 6, fontSize: 10, color: 'var(--dark-grey)', lineHeight: 1.5 }}>
        Verdi = biomasse &times; NOK/t når «Auto-fordelt». Klikk verdi-feltet for manuell overstyring.
        NOK/t-sats: {appliedValue.toLocaleString('nb-NO')} NOK/t.
      </div>
    </div>
  )
}
