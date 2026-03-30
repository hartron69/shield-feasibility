import React, { useState, useEffect } from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'
import BioLineChart from './BioLineChart.jsx'
import { BIO_READING_LABELS } from '../../data/mockInputsData.js'
import {
  MOCK_BIO_TIMESERIES,
  PARAM_THRESHOLDS,
  PARAM_COLORS,
} from '../../data/mockBioTimeseries.js'
import { fetchLiveRiskTimeseries } from '../../api/client.js'

// Parameters that exist in the Live Risk timeseries feed
// key = Live Risk series parameter name, value = bio panel parameter key
const LR_PARAM_MAP = {
  temperature: 'surface_temp_c',
  oxygen:      'dissolved_oxygen_mg_l',
  salinity:    'salinity_ppt',
  lice:        'lice_count_per_fish',
  treatment:   'treatments_last_90d',
}

// Parameters that are NOT in Live Risk — kept as mock
const MOCK_ONLY_PARAMS = new Set([
  'nitrate_umol_l',
  'chlorophyll_a_ug_l',
  'hab_alert_count',
  'jellyfish_sightings',
  'pathogen_obs_count',
  'neighbor_lice_pressure',
])

const CHART_GROUPS = [
  { label: 'Temperatur & oksygen',  params: ['surface_temp_c', 'dissolved_oxygen_mg_l'] },
  { label: 'Næringsstoffer & alger', params: ['nitrate_umol_l', 'chlorophyll_a_ug_l'] },
  { label: 'Salinitet',              params: ['salinity_ppt'] },
  { label: 'Lus & behandlinger',    params: ['lice_count_per_fish', 'treatments_last_90d', 'neighbor_lice_pressure'] },
  { label: 'Biologiske hendelser',  params: ['hab_alert_count', 'jellyfish_sightings', 'pathogen_obs_count'] },
]

const ALL_PARAMS = CHART_GROUPS.flatMap(g => g.params)

const PARAM_UNITS = {
  surface_temp_c:         '°C',
  dissolved_oxygen_mg_l:  'mg/L',
  nitrate_umol_l:         'µmol/L',
  salinity_ppt:           'ppt',
  chlorophyll_a_ug_l:     'µg/L',
  lice_count_per_fish:    'lus/fisk',
  hab_alert_count:        'varsler',
  jellyfish_sightings:    'obs.',
  pathogen_obs_count:     'hendelser',
  treatments_last_90d:    'beh.',
  neighbor_lice_pressure: 'indeks',
}

const KH_SITES = ['KH_S01', 'KH_S02', 'KH_S03']

function deltaClass(key, delta) {
  const lowerIsBad = ['dissolved_oxygen_mg_l', 'salinity_ppt']
  if (lowerIsBad.includes(key)) {
    if (delta < -0.5) return 'delta-bad'
    if (delta > 0.5)  return 'delta-good'
  } else {
    if (delta > 0)    return 'delta-warn'
    if (delta < 0)    return 'delta-good'
  }
  return ''
}

function fmtDelta(delta) {
  const sign = delta > 0 ? '+' : ''
  return `${sign}${delta.toFixed(2)}`
}

export default function BiologicalInputsPanel({ bioInputs, snapshots = {} }) {
  const [selectedSite, setSelectedSite]     = useState(bioInputs?.[0]?.site_id || 'KH_S01')
  const [viewMode, setViewMode]             = useState('charts')
  const [selectedGroup, setSelectedGroup]   = useState('Alle')
  // Live Risk timeseries: { KH_S01: { surface_temp_c: [{date, value}], ... }, ... }
  const [liveTs, setLiveTs] = useState({})

  useEffect(() => {
    Promise.all(
      KH_SITES.map(id =>
        fetchLiveRiskTimeseries(id, '90d')
          .then(data => {
            const byParam = {}
            for (const series of data.raw_data) {
              const panelKey = LR_PARAM_MAP[series.parameter]
              if (panelKey) {
                byParam[panelKey] = series.points
                  .filter(p => p.value !== null && p.value !== undefined)
                  .map(p => ({ date: p.timestamp.slice(0, 10), value: p.value }))
              }
            }
            return { id, byParam }
          })
          .catch(() => ({ id, byParam: {} }))
      )
    ).then(results => {
      const map = {}
      results.forEach(({ id, byParam }) => { map[id] = byParam })
      setLiveTs(map)
    })
  }, [])

  if (!bioInputs || bioInputs.length === 0) {
    return <div className="inputs-empty">Ingen biologiske data tilgjengelig.</div>
  }

  const site     = bioInputs.find(s => s.site_id === selectedSite) || bioInputs[0]
  const readings = site.readings
  const mockTs   = MOCK_BIO_TIMESERIES[site.site_id] || {}
  const siteSnap = snapshots[site.site_id]

  // Merge: Live Risk for overlapping params, mock for the rest
  const getChartData = (param) => {
    const lr = liveTs[site.site_id]?.[param]
    if (lr && lr.length > 0) return lr
    return mockTs[param] || []
  }

  const getParamSource = (param) =>
    (liveTs[site.site_id]?.[param]?.length > 0) ? 'derived' : 'simulated'

  // Override snapshot values for table view where Live Risk has current data
  const getReadingValue = (key) => {
    if (siteSnap) {
      if (key === 'surface_temp_c') {
        const r = siteSnap.environmental?.readings?.find(r => r.parameter === 'Overflatetemperatur')
        if (r?.value != null) return r.value
      }
      if (key === 'dissolved_oxygen_mg_l') {
        const r = siteSnap.environmental?.readings?.find(r => r.parameter === 'Løst O₂')
        if (r?.value != null) return r.value
      }
      if (key === 'lice_count_per_fish') {
        if (siteSnap.biological?.lice_now != null) return siteSnap.biological.lice_now
      }
      if (key === 'treatments_last_90d') {
        if (siteSnap.biological?.treatment_30d != null) return siteSnap.biological.treatment_30d
      }
    }
    return readings[key]?.value
  }

  const visibleParams = selectedGroup === 'Alle'
    ? ALL_PARAMS
    : (CHART_GROUPS.find(g => g.label === selectedGroup)?.params || ALL_PARAMS)

  return (
    <div>
      {/* ── Site-selector + visningsveksler ──────────────────────────────── */}
      <div className="bio-toolbar">
        <div className="bio-site-selector">
          {bioInputs.map(s => (
            <button
              key={s.site_id}
              className={`bio-site-btn ${selectedSite === s.site_id ? 'active' : ''}`}
              onClick={() => setSelectedSite(s.site_id)}
            >
              {s.site_name}
            </button>
          ))}
          <span className="bio-recorded-at">
            Registrert:{' '}
            {site.recorded_at
              ? new Date(site.recorded_at).toLocaleString('nb-NO', { dateStyle: 'short', timeStyle: 'short' })
              : '—'}
          </span>
          <InputSourceBadge source={site.data_source} />
        </div>

        <div className="bio-view-toggle">
          <button
            className={`bio-toggle-btn ${viewMode === 'charts' ? 'active' : ''}`}
            onClick={() => setViewMode('charts')}
          >
            Grafer
          </button>
          <button
            className={`bio-toggle-btn ${viewMode === 'table' ? 'active' : ''}`}
            onClick={() => setViewMode('table')}
          >
            Tabell
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* GRAFVISNING                                                       */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {viewMode === 'charts' && (
        <div>
          <div className="bio-group-filter">
            {['Alle', ...CHART_GROUPS.map(g => g.label)].map(g => (
              <button
                key={g}
                className={`bio-group-btn ${selectedGroup === g ? 'active' : ''}`}
                onClick={() => setSelectedGroup(g)}
              >
                {g}
              </button>
            ))}
          </div>

          <div className="bio-chart-grid">
            {visibleParams.map(param => {
              const data      = getChartData(param)
              const reading   = readings[param]
              const baseline  = reading?.baseline
              const threshold = PARAM_THRESHOLDS[param] || null
              const color     = PARAM_COLORS[param] || '#2563EB'
              const unit      = PARAM_UNITS[param] || reading?.unit || ''
              const label     = BIO_READING_LABELS[param] || param
              const source    = getParamSource(param)

              if (data.length === 0) return null

              const lastVal  = data[data.length - 1]?.value
              const breached = threshold && (
                (threshold.direction === 'above' && lastVal > threshold.value) ||
                (threshold.direction === 'below' && lastVal < threshold.value)
              )

              return (
                <div
                  key={param}
                  className={`bio-chart-card${breached ? ' bio-chart-card-alert' : ''}`}
                >
                  <div className="bio-chart-card-header">
                    <span className="bio-chart-card-title">{label}</span>
                    {breached && (
                      <span className="bio-chart-threshold-badge">Terskel nådd</span>
                    )}
                    {!MOCK_ONLY_PARAMS.has(param) && (
                      <InputSourceBadge source={source} />
                    )}
                    {reading && (
                      <span className="bio-chart-current-val" style={{ color }}>
                        {typeof lastVal === 'number'
                          ? (lastVal < 10 ? lastVal.toFixed(2) : lastVal.toFixed(1))
                          : lastVal}{' '}{unit}
                      </span>
                    )}
                  </div>
                  <BioLineChart
                    data={data}
                    baseline={baseline}
                    threshold={threshold}
                    color={color}
                    unit={unit}
                    height={165}
                  />
                </div>
              )
            })}
          </div>

          <div className="inputs-note">
            Stiplet grå linje = baseline. Stiplet rød linje = risikoterskel. Siste datapunkt uthevet.
            Temp / O₂ / salinitet / lus / behandlinger: Live Risk-tidsserie (siste 90 dager, daglig oppløsning).
            Nitrat / klorofyll / HAB / manet / nabolus: separat mock-tidsserie (12 månedlige punkter, apr 2025–mar 2026).
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* TABELLVISNING                                                     */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {viewMode === 'table' && (
        <>
          <table className="bio-table">
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Nåværende</th>
                <th>Baseline</th>
                <th>Delta</th>
                <th>Enhet</th>
                <th>Kilde</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(readings).map(([key, r]) => {
                const currentVal = getReadingValue(key) ?? r.value
                const delta      = currentVal - r.baseline
                const cls        = deltaClass(key, delta)
                const src        = MOCK_ONLY_PARAMS.has(key) ? r.source : getParamSource(key)
                return (
                  <tr key={key}>
                    <td className="bio-param-name">{BIO_READING_LABELS[key] || key}</td>
                    <td className="bio-current">
                      <strong>
                        {typeof currentVal === 'number'
                          ? currentVal.toFixed(currentVal < 10 ? 2 : 1)
                          : currentVal}
                      </strong>
                    </td>
                    <td className="bio-baseline" style={{ color: 'var(--dark-grey)' }}>
                      {typeof r.baseline === 'number'
                        ? r.baseline.toFixed(r.baseline < 10 ? 2 : 1)
                        : r.baseline}
                    </td>
                    <td className={`bio-delta ${cls}`}>{fmtDelta(delta)}</td>
                    <td className="bio-unit">{r.unit}</td>
                    <td><InputSourceBadge source={src} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div className="inputs-note">
            Delta = Nåværende − Baseline. Live Risk-parametere (temp, O₂, salinitet, lus, behandlinger)
            oppdateres fra Live Risk-feedet. Øvrige parametere er simulerte.
          </div>
        </>
      )}
    </div>
  )
}
