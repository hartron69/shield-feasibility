/**
 * Biological / Environmental Time Series – 12 månedlige målinger per parameter per lokasjon.
 * Periode: April 2025 – Mars 2026.
 * Verdiene er simulerte men realistiske for norsk lakseoppdrett.
 */

// Månedsmerker (ISO YYYY-MM)
const MONTHS = [
  '2025-04','2025-05','2025-06','2025-07','2025-08','2025-09',
  '2025-10','2025-11','2025-12','2026-01','2026-02','2026-03',
]

function series(values) {
  return MONTHS.map((date, i) => ({ date, value: values[i] }))
}

// ─────────────────────────────────────────────────────────────────────────────
// S01 – Frohavet North (åpen kyst, varmest, høyest risiko)
// ─────────────────────────────────────────────────────────────────────────────
const S01 = {
  surface_temp_c: series([
     7.4,  9.8, 12.6, 15.4, 16.5, 14.8,
    11.2,  7.9,  5.4,  4.7,  4.5,  5.8,
  ]),
  dissolved_oxygen_mg_l: series([
    10.1,  9.4,  8.5,  7.8,  7.1,  7.6,
     8.4,  9.2,  9.8, 10.4, 10.6,  9.9,
  ]),
  nitrate_umol_l: series([
    14.2, 22.1, 18.4, 10.2,  6.8,  5.4,
     4.8,  5.2,  6.1,  7.4,  8.8, 18.4,
  ]),
  salinity_ppt: series([
    30.8, 30.2, 31.4, 32.6, 33.2, 33.4,
    33.1, 32.8, 32.4, 32.1, 31.8, 32.1,
  ]),
  chlorophyll_a_ug_l: series([
     2.1,  5.8,  4.2,  3.1,  2.4,  1.8,
     1.2,  0.9,  0.8,  0.9,  1.1,  3.8,
  ]),
  lice_count_per_fish: series([
     0.4,  0.9,  1.8,  2.8,  3.2,  2.1,
     1.4,  0.8,  0.5,  0.4,  0.6,  2.4,
  ]),
  hab_alert_count: series([
     0,  0,  0,  1,  2,  1,
     0,  0,  0,  0,  0,  1,
  ]),
  jellyfish_sightings: series([
     0,  0,  1,  3,  4,  2,
     1,  0,  0,  0,  0,  3,
  ]),
  pathogen_obs_count: series([
     0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  1,  0,
  ]),
  treatments_last_90d: series([
     0,  0,  1,  2,  2,  1,
     0,  0,  0,  0,  1,  2,
  ]),
  neighbor_lice_pressure: series([
     1.0,  1.2,  1.5,  1.8,  2.0,  1.9,
     1.6,  1.3,  1.1,  1.0,  1.1,  1.8,
  ]),
}

// ─────────────────────────────────────────────────────────────────────────────
// S02 – Sunndalsfjord (semi-eksponert, litt kjøligere vinter)
// ─────────────────────────────────────────────────────────────────────────────
const S02 = {
  surface_temp_c: series([
     6.8,  9.1, 11.8, 14.5, 15.6, 13.9,
    10.6,  7.4,  5.0,  4.4,  4.2,  5.4,
  ]),
  dissolved_oxygen_mg_l: series([
    10.3,  9.7,  8.9,  8.2,  7.5,  8.0,
     8.8,  9.5, 10.1, 10.6, 10.8, 10.2,
  ]),
  nitrate_umol_l: series([
    11.4, 18.6, 14.2,  8.4,  5.2,  4.1,
     3.8,  4.4,  5.2,  6.2,  7.1,  6.2,
  ]),
  salinity_ppt: series([
    29.8, 29.2, 30.6, 31.8, 32.4, 32.6,
    32.2, 31.9, 31.5, 31.1, 30.8, 30.8,
  ]),
  chlorophyll_a_ug_l: series([
     1.8,  4.6,  3.4,  2.6,  2.0,  1.6,
     1.1,  0.8,  0.7,  0.8,  1.0,  1.9,
  ]),
  lice_count_per_fish: series([
     0.3,  0.7,  1.2,  2.0,  2.4,  1.8,
     1.1,  0.6,  0.4,  0.3,  0.5,  1.6,
  ]),
  hab_alert_count: series([
     0,  0,  0,  0,  1,  0,
     0,  0,  0,  0,  0,  0,
  ]),
  jellyfish_sightings: series([
     0,  0,  0,  1,  2,  1,
     0,  0,  0,  0,  0,  0,
  ]),
  pathogen_obs_count: series([
     0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,
  ]),
  treatments_last_90d: series([
     0,  0,  1,  1,  2,  1,
     0,  0,  0,  0,  0,  1,
  ]),
  neighbor_lice_pressure: series([
     1.0,  1.1,  1.3,  1.6,  1.8,  1.7,
     1.4,  1.2,  1.0,  0.9,  1.0,  1.4,
  ]),
}

// ─────────────────────────────────────────────────────────────────────────────
// S03 – Storfjorden South (ly, kjøligst, lavest risiko)
// ─────────────────────────────────────────────────────────────────────────────
const S03 = {
  surface_temp_c: series([
     5.9,  8.2, 10.8, 13.4, 14.6, 12.8,
     9.8,  6.8,  4.6,  3.9,  3.8,  4.6,
  ]),
  dissolved_oxygen_mg_l: series([
    10.8, 10.2,  9.5,  8.8,  8.2,  8.6,
     9.2,  9.8, 10.4, 10.9, 11.1, 10.5,
  ]),
  nitrate_umol_l: series([
     9.2, 14.8, 11.4,  6.8,  4.2,  3.4,
     3.2,  3.8,  4.4,  5.2,  6.0,  4.5,
  ]),
  salinity_ppt: series([
    32.4, 32.0, 32.8, 33.4, 33.8, 34.0,
    33.6, 33.4, 33.2, 32.9, 32.6, 33.8,
  ]),
  chlorophyll_a_ug_l: series([
     1.4,  3.8,  2.8,  2.0,  1.5,  1.2,
     0.9,  0.7,  0.6,  0.7,  0.8,  1.2,
  ]),
  lice_count_per_fish: series([
     0.2,  0.5,  0.8,  1.4,  1.6,  1.2,
     0.8,  0.5,  0.3,  0.2,  0.3,  0.9,
  ]),
  hab_alert_count: series([
     0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,
  ]),
  jellyfish_sightings: series([
     0,  0,  0,  0,  1,  0,
     0,  0,  0,  0,  0,  0,
  ]),
  pathogen_obs_count: series([
     0,  0,  0,  0,  0,  0,
     0,  0,  0,  0,  0,  0,
  ]),
  treatments_last_90d: series([
     0,  0,  0,  1,  1,  1,
     0,  0,  0,  0,  0,  0,
  ]),
  neighbor_lice_pressure: series([
     0.9,  1.0,  1.1,  1.3,  1.4,  1.3,
     1.2,  1.0,  0.9,  0.9,  1.0,  1.1,
  ]),
}

// ─────────────────────────────────────────────────────────────────────────────
// Eksportert tidsserie-map: { site_id → { param → [{date, value}] } }
// ─────────────────────────────────────────────────────────────────────────────
export const MOCK_BIO_TIMESERIES = {
  'DEMO_OP_S01': S01,
  'DEMO_OP_S02': S02,
  'DEMO_OP_S03': S03,
}

// Terskelverdier for risikoparametere (vises som rød stiplet linje i grafene)
export const PARAM_THRESHOLDS = {
  surface_temp_c:          { value: 15.0, direction: 'above', label: 'HAB-terskel' },
  dissolved_oxygen_mg_l:   { value:  7.0, direction: 'below', label: 'Oksygentrigger' },
  nitrate_umol_l:          { value: 12.0, direction: 'above', label: 'HAB-indikator' },
  lice_count_per_fish:     { value:  1.0, direction: 'above', label: 'Behandlingstrigger' },
  chlorophyll_a_ug_l:      { value:  3.0, direction: 'above', label: 'Algeinndikator' },
  neighbor_lice_pressure:  { value:  1.5, direction: 'above', label: 'Nettverksvarsling' },
}

// Farger per parameter-gruppe
export const PARAM_COLORS = {
  surface_temp_c:         '#DC2626',   // rød – temperatur
  dissolved_oxygen_mg_l:  '#2563EB',   // blå – oksygen
  nitrate_umol_l:         '#D97706',   // gul – næringsstoffer
  salinity_ppt:           '#0891B2',   // cyan – salinitet
  chlorophyll_a_ug_l:     '#16A34A',   // grønn – klorofyll
  lice_count_per_fish:    '#7C3AED',   // lilla – lus
  hab_alert_count:        '#DC2626',   // rød – HAB
  jellyfish_sightings:    '#0891B2',   // cyan – maneter
  pathogen_obs_count:     '#B45309',   // brun – patogen
  treatments_last_90d:    '#6B7280',   // grå – behandlinger
  neighbor_lice_pressure: '#7C3AED',   // lilla – naboluspress
}
