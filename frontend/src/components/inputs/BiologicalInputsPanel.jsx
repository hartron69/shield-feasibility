import React, { useState } from 'react'
import InputSourceBadge from './InputSourceBadge.jsx'
import BioLineChart from './BioLineChart.jsx'
import { BIO_READING_LABELS } from '../../data/mockInputsData.js'
import {
  MOCK_BIO_TIMESERIES,
  PARAM_THRESHOLDS,
  PARAM_COLORS,
} from '../../data/mockBioTimeseries.js'

// Parametre som vises i grafvisningen (gruppert)
const CHART_GROUPS = [
  {
    label: 'Temperatur & oksygen',
    params: ['surface_temp_c', 'dissolved_oxygen_mg_l'],
  },
  {
    label: 'Næringsstoffer & alger',
    params: ['nitrate_umol_l', 'chlorophyll_a_ug_l'],
  },
  {
    label: 'Salinitet',
    params: ['salinity_ppt'],
  },
  {
    label: 'Lus & behandlinger',
    params: ['lice_count_per_fish', 'treatments_last_90d', 'neighbor_lice_pressure'],
  },
  {
    label: 'Biologiske hendelser',
    params: ['hab_alert_count', 'jellyfish_sightings', 'pathogen_obs_count'],
  },
]

const ALL_PARAMS = CHART_GROUPS.flatMap(g => g.params)

// Enhetskart
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

export default function BiologicalInputsPanel({ bioInputs }) {
  const [selectedSite, setSelectedSite] = useState(bioInputs?.[0]?.site_id || '')
  const [viewMode, setViewMode]         = useState('charts')   // 'table' | 'charts'
  const [selectedGroup, setSelectedGroup] = useState('Alle')

  if (!bioInputs || bioInputs.length === 0) {
    return <div className="inputs-empty">Ingen biologiske data tilgjengelig.</div>
  }

  const site     = bioInputs.find(s => s.site_id === selectedSite) || bioInputs[0]
  const readings = site.readings
  const ts       = MOCK_BIO_TIMESERIES[site.site_id] || {}

  // Parametre som skal vises i valgt gruppe
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

        {/* Tabell / Graf toggle */}
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
          {/* Gruppefilter */}
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

          {/* Graf-rutenett */}
          <div className="bio-chart-grid">
            {visibleParams.map(param => {
              const data      = ts[param] || []
              const reading   = readings[param]
              const baseline  = reading?.baseline
              const threshold = PARAM_THRESHOLDS[param] || null
              const color     = PARAM_COLORS[param] || '#2563EB'
              const unit      = PARAM_UNITS[param] || reading?.unit || ''
              const label     = BIO_READING_LABELS[param] || param

              if (data.length === 0) return null

              // Fremhev grafer med aktiv terskelbrudd
              const lastVal   = data[data.length - 1]?.value
              const breached  = threshold && (
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
            Stiplet grå linje = baseline. Stiplet rød linje = risikoterskel.
            Siste datapunkt (Mars 2026) er uthevet. Tidsserie: April 2025 – Mars 2026 (simulert).
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* TABELLVISNING (uendret fra original)                             */}
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
                const delta = r.value - r.baseline
                const cls   = deltaClass(key, delta)
                return (
                  <tr key={key}>
                    <td className="bio-param-name">{BIO_READING_LABELS[key] || key}</td>
                    <td className="bio-current">
                      <strong>
                        {typeof r.value === 'number'
                          ? r.value.toFixed(r.value < 10 ? 2 : 1)
                          : r.value}
                      </strong>
                    </td>
                    <td className="bio-baseline" style={{ color: 'var(--dark-grey)' }}>
                      {typeof r.baseline === 'number'
                        ? r.baseline.toFixed(r.baseline < 10 ? 2 : 1)
                        : r.baseline}
                    </td>
                    <td className={`bio-delta ${cls}`}>{fmtDelta(delta)}</td>
                    <td className="bio-unit">{r.unit}</td>
                    <td><InputSourceBadge source={r.source} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div className="inputs-note">
            Delta = Nåværende − Baseline. Rød = ugunstig avvik; grønn = forbedring.
            Datakilden er simulert for alle avlesninger i demomodus.
          </div>
        </>
      )}
    </div>
  )
}
