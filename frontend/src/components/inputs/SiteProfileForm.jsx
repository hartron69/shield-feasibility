import React, { useState, useEffect } from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'
import { fetchSiteProfile } from '../../api/client.js'

const KH_SITES = ['KH_S01', 'KH_S02', 'KH_S03']

function fmtM(v)   { return v != null ? `NOK ${(v / 1_000_000).toFixed(1)}M` : '—' }
function fmtCoord(v, dec) { return v != null ? v.toFixed(dec) : '—' }

function Section({ children }) {
  return (
    <>
      <div className="sp-divider" />
      <table className="sp-table"><tbody>{children}</tbody></table>
    </>
  )
}

function Row({ label, value, highlight, badge }) {
  return (
    <tr className={highlight ? 'sp-row-highlight' : ''}>
      <td className="sp-field-label">{label}</td>
      <td className="sp-field-value">
        <span style={{ marginRight: badge ? 6 : 0 }}>{value ?? '—'}</span>
        {badge && <InputSourceBadge source={badge} />}
      </td>
    </tr>
  )
}

const EXPOSURE_LABELS = {
  open:      'Eksponert kyst',
  semi:      'Semi-eksponert',
  sheltered: 'Skjermet',
}

export default function SiteProfileForm() {
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading]   = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all(KH_SITES.map(id => fetchSiteProfile(id)))
      .then(results => setProfiles(results))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="inputs-empty">Laster lokasjonsprofiler fra Live Risk…</div>
  }

  if (profiles.length === 0) {
    return <div className="inputs-empty">Ingen lokasjonsprofiler tilgjengelig. Start backend for å laste Live Risk-data.</div>
  }

  return (
    <div className="site-profile-grid">
      {profiles.map(site => {
        const utilPct = site.biomass_utilisation_pct
        const utilColor = utilPct >= 90 ? '#DC2626' : utilPct >= 75 ? '#D97706' : '#16A34A'

        const src = site.sources || {}
        const regSrc = src.registration || 'derived'

        return (
          <div key={site.locality_id} className="site-profile-card card">
            {/* Header */}
            <div className="site-profile-header">
              <div>
                <div className="site-profile-name">{site.site_name}</div>
                <div className="site-profile-id">{site.locality_id}</div>
              </div>
              <InputSourceBadge source={regSrc} />
            </div>

            {/* Registration (BW Akvakulturregisteret) */}
            <table className="sp-table">
              <tbody>
                <Row label="Lok.nr. (BW)"   value={site.locality_no}  badge={regSrc} />
                <Row label="Operatør"        value={site.operator}     badge={regSrc} />
                {site.org_number && (
                  <Row label="Org.nr."       value={site.org_number}   badge={regSrc} />
                )}
                <Row label="Region"          value={site.region} />
                <Row label="Art"             value={site.species}      badge={regSrc} />
                <Row label="Konsesjon"       value={site.license_number} badge={regSrc} />
                <Row label="Driftsstart"     value={site.start_year
                  ? `${site.start_year}  (${site.years_in_operation} år)`
                  : '—'} />
                <Row label="NIS-sertifisert" value={site.nis_certified ? 'Ja' : 'Nei'} />
                {site.bw_status && (
                  <Row label="Driftsstatus"  value={site.bw_status}    badge={regSrc} />
                )}
              </tbody>
            </table>

            {/* Position */}
            <Section>
              <Row label="Breddegrad" value={`${fmtCoord(site.lat, 5)}° N`} badge={src.position || regSrc} />
              <Row label="Lengdegrad" value={`${fmtCoord(site.lon, 5)}° Ø`} badge={src.position || regSrc} />
            </Section>

            {/* Biomass / MTB */}
            <Section>
              <Row
                label="MTB (maks tillatt)"
                value={`${site.mtb_tonnes?.toLocaleString('nb-NO')} t`}
                highlight
                badge={src.mtb || regSrc}
              />
              <Row
                label="Stående biomasse"
                value={`${site.current_biomass_tonnes?.toLocaleString('nb-NO')} t`}
                highlight
                badge="derived"
              />
              <Row
                label="MTB-utnyttelse"
                value={
                  utilPct != null
                    ? <span style={{ color: utilColor, fontWeight: 700 }}>{utilPct} %</span>
                    : '—'
                }
              />
              <Row label="Biomasseverdi"  value={fmtM(site.biomass_value_nok)} badge="derived" />
            </Section>

            {/* Operator-reported financials */}
            <Section>
              <Row label="Utstyr"          value={fmtM(site.equipment_value_nok)} badge={src.financials || 'operator'} />
              <Row label="Infrastruktur"   value={fmtM(site.infra_value_nok)}     badge={src.financials || 'operator'} />
              <Row label="Årsomsetning"    value={fmtM(site.annual_revenue_nok)}  badge={src.financials || 'operator'} />
            </Section>

            {/* Risk factors */}
            <Section>
              <Row
                label="Eksponering"
                value={`${site.exposure_factor?.toFixed(2)}  — ${EXPOSURE_LABELS[site.exposure_class] || site.exposure_class}`}
                highlight
                badge={src.exposure || 'derived'}
              />
              <Row
                label="Operasjonell faktor"
                value={site.operational_factor?.toFixed(2)}
                badge={src.financials || 'operator'}
              />
            </Section>

            <div className="sp-note">
              {site.bw_live
                ? 'Lok.nr., operatør, org.nr., GPS, MTB og art: live fra BarentsWatch Akvakulturregisteret.'
                : 'Lok.nr., operatør, GPS, MTB og art: Live Risk (kilde: konfigurasjon). Sett BW_CLIENT_ID og BW_CLIENT_SECRET for live BarentsWatch-data.'
              }
              {' '}Stående biomasse og biomasseverdi: Live Risk-modell.
              Utstyr, infrastruktur og omsetning er operatørrapporterte estimater.
              MTB-utnyttelse &gt; 90 % er markert rødt.
            </div>
          </div>
        )
      })}
    </div>
  )
}
