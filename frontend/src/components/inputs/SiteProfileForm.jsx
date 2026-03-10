import React from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'

const EXPOSURE_LABELS = {
  open_coast:   'Open Coast',
  semi_exposed: 'Semi-Exposed',
  sheltered:    'Sheltered',
}

function fmtM(v) { return `NOK ${(v / 1_000_000).toFixed(1)}M` }
function fmtPct(v) { return `${(v * 100).toFixed(0)}%` }

function FieldRow({ label, value, highlight }) {
  return (
    <tr className={highlight ? 'sp-row-highlight' : ''}>
      <td className="sp-field-label">{label}</td>
      <td className="sp-field-value">{value}</td>
    </tr>
  )
}

export default function SiteProfileForm({ sites }) {
  if (!sites || sites.length === 0) return <div className="inputs-empty">No site profiles available.</div>

  return (
    <div className="site-profile-grid">
      {sites.map(site => (
        <div key={site.site_id} className="site-profile-card card">
          <div className="site-profile-header">
            <div>
              <div className="site-profile-name">{site.site_name}</div>
              <div className="site-profile-id">{site.site_id}</div>
            </div>
            <InputSourceBadge source={site.data_source} />
          </div>

          <table className="sp-table">
            <tbody>
              <FieldRow label="Region"         value={site.region} />
              <FieldRow label="Species"        value={site.species} />
              <FieldRow label="Exposure"       value={EXPOSURE_LABELS[site.fjord_exposure] || site.fjord_exposure} />
              <FieldRow label="Yrs in Operation" value={site.years_in_operation} />
              <FieldRow label="Licence"        value={site.license_number} />
              <FieldRow label="NIS Certified"  value={site.nis_certification ? 'Yes' : 'No'} />
            </tbody>
          </table>

          <div className="sp-divider" />

          <table className="sp-table">
            <tbody>
              <FieldRow label="Biomass"        value={`${site.biomass_tonnes.toLocaleString()} t`} highlight />
              <FieldRow label="Biomass Value"  value={fmtM(site.biomass_value_nok)} />
              <FieldRow label="Equipment"      value={fmtM(site.equipment_value_nok)} />
              <FieldRow label="Infrastructure" value={fmtM(site.infra_value_nok)} />
              <FieldRow label="Annual Revenue" value={fmtM(site.annual_revenue_nok)} />
            </tbody>
          </table>

          <div className="sp-divider" />

          <table className="sp-table">
            <tbody>
              <FieldRow label="Exposure Factor"     value={site.exposure_factor.toFixed(2)} highlight />
              <FieldRow label="Operational Factor"  value={site.operational_factor.toFixed(2)} />
            </tbody>
          </table>

          <div className="sp-note">
            Exposure factor scales structural and environmental risk loadings.
            Operational factor scales ops domain losses.
          </div>
        </div>
      ))}
    </div>
  )
}
