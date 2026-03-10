/**
 * Mock Inputs Data for C5AI+ Inputs Page
 *
 * Consistent with C5AI_MOCK (c5ai_mock.js) and MOCK_ALERTS (mockAlertsData.js).
 * Three sites: Frohavet North (S01), Sunndalsfjord (S02), Storfjorden South (S03).
 */

// ── 1. Site Profiles ──────────────────────────────────────────────────────────
export const MOCK_SITE_PROFILES = [
  {
    site_id:             'DEMO_OP_S01',
    site_name:           'Frohavet North',
    region:              'Møre og Romsdal, Norway',
    species:             'Atlantic Salmon (Salmo salar)',
    biomass_tonnes:      3200,
    biomass_value_nok:   207_360_000,
    equipment_value_nok:  52_000_000,
    infra_value_nok:      38_000_000,
    annual_revenue_nok:  288_000_000,
    exposure_factor:     1.40,   // 1.0=sheltered, 1.5=open coast
    operational_factor:  1.10,   // 1.0=standard, higher = stressed operations
    fjord_exposure:      'open_coast',
    years_in_operation:  7,
    license_number:      'NOR-MR-1842',
    nis_certification:   true,
    data_source:         'simulated',
  },
  {
    site_id:             'DEMO_OP_S02',
    site_name:           'Sunndalsfjord',
    region:              'Møre og Romsdal, Norway',
    species:             'Atlantic Salmon (Salmo salar)',
    biomass_tonnes:      3500,
    biomass_value_nok:   226_800_000,
    equipment_value_nok:  58_000_000,
    infra_value_nok:      42_000_000,
    annual_revenue_nok:  315_000_000,
    exposure_factor:     1.15,
    operational_factor:  1.00,
    fjord_exposure:      'semi_exposed',
    years_in_operation:  11,
    license_number:      'NOR-MR-2201',
    nis_certification:   true,
    data_source:         'simulated',
  },
  {
    site_id:             'DEMO_OP_S03',
    site_name:           'Storfjorden South',
    region:              'Møre og Romsdal, Norway',
    species:             'Atlantic Salmon (Salmo salar)',
    biomass_tonnes:      2500,
    biomass_value_nok:   162_000_000,
    equipment_value_nok:  40_000_000,
    infra_value_nok:      29_000_000,
    annual_revenue_nok:  225_000_000,
    exposure_factor:     0.85,
    operational_factor:  0.95,
    fjord_exposure:      'sheltered',
    years_in_operation:  12,
    license_number:      'NOR-MR-2398',
    nis_certification:   true,
    data_source:         'simulated',
  },
]

// ── 2. Biological / Environmental Inputs ──────────────────────────────────────
export const MOCK_BIOLOGICAL_INPUTS = [
  {
    site_id:    'DEMO_OP_S01',
    site_name:  'Frohavet North',
    recorded_at: '2026-03-09T12:00:00Z',
    data_source: 'simulated',
    readings: {
      surface_temp_c:          { value: 15.2, unit: '°C',       baseline: 13.0,  source: 'simulated' },
      dissolved_oxygen_mg_l:   { value:  6.8, unit: 'mg/L',     baseline:  8.5,  source: 'simulated' },
      nitrate_umol_l:          { value: 18.4, unit: 'µmol/L',   baseline:  5.0,  source: 'simulated' },
      salinity_ppt:            { value: 32.1, unit: 'ppt',      baseline: 33.5,  source: 'simulated' },
      chlorophyll_a_ug_l:      { value:  3.8, unit: 'µg/L',     baseline:  1.5,  source: 'simulated' },
      lice_count_per_fish:     { value:  2.4, unit: 'lice/fish',baseline:  0.5,  source: 'simulated' },
      hab_alert_count:         { value:  1,   unit: 'alerts',   baseline:  0,    source: 'simulated' },
      jellyfish_sightings:     { value:  3,   unit: 'obs',      baseline:  0,    source: 'simulated' },
      pathogen_obs_count:      { value:  0,   unit: 'events',   baseline:  0,    source: 'simulated' },
      treatments_last_90d:     { value:  2,   unit: 'events',   baseline:  0.5,  source: 'simulated' },
      neighbor_lice_pressure:  { value:  1.8, unit: 'index',    baseline:  1.0,  source: 'estimated' },
    },
  },
  {
    site_id:    'DEMO_OP_S02',
    site_name:  'Sunndalsfjord',
    recorded_at: '2026-03-09T12:00:00Z',
    data_source: 'simulated',
    readings: {
      surface_temp_c:          { value: 12.4, unit: '°C',       baseline: 12.0,  source: 'simulated' },
      dissolved_oxygen_mg_l:   { value:  8.1, unit: 'mg/L',     baseline:  8.5,  source: 'simulated' },
      nitrate_umol_l:          { value:  6.2, unit: 'µmol/L',   baseline:  5.0,  source: 'simulated' },
      salinity_ppt:            { value: 30.8, unit: 'ppt',      baseline: 32.0,  source: 'simulated' },
      chlorophyll_a_ug_l:      { value:  1.9, unit: 'µg/L',     baseline:  1.5,  source: 'simulated' },
      lice_count_per_fish:     { value:  1.6, unit: 'lice/fish',baseline:  0.5,  source: 'simulated' },
      hab_alert_count:         { value:  0,   unit: 'alerts',   baseline:  0,    source: 'simulated' },
      jellyfish_sightings:     { value:  0,   unit: 'obs',      baseline:  0,    source: 'simulated' },
      pathogen_obs_count:      { value:  0,   unit: 'events',   baseline:  0,    source: 'simulated' },
      treatments_last_90d:     { value:  1,   unit: 'events',   baseline:  0.5,  source: 'simulated' },
      neighbor_lice_pressure:  { value:  1.4, unit: 'index',    baseline:  1.0,  source: 'estimated' },
    },
  },
  {
    site_id:    'DEMO_OP_S03',
    site_name:  'Storfjorden South',
    recorded_at: '2026-03-09T12:00:00Z',
    data_source: 'simulated',
    readings: {
      surface_temp_c:          { value: 11.2, unit: '°C',       baseline: 11.5,  source: 'simulated' },
      dissolved_oxygen_mg_l:   { value:  8.9, unit: 'mg/L',     baseline:  8.5,  source: 'simulated' },
      nitrate_umol_l:          { value:  4.5, unit: 'µmol/L',   baseline:  5.0,  source: 'simulated' },
      salinity_ppt:            { value: 33.8, unit: 'ppt',      baseline: 33.0,  source: 'simulated' },
      chlorophyll_a_ug_l:      { value:  1.2, unit: 'µg/L',     baseline:  1.5,  source: 'simulated' },
      lice_count_per_fish:     { value:  0.9, unit: 'lice/fish',baseline:  0.5,  source: 'simulated' },
      hab_alert_count:         { value:  0,   unit: 'alerts',   baseline:  0,    source: 'simulated' },
      jellyfish_sightings:     { value:  0,   unit: 'obs',      baseline:  0,    source: 'simulated' },
      pathogen_obs_count:      { value:  0,   unit: 'events',   baseline:  0,    source: 'simulated' },
      treatments_last_90d:     { value:  0,   unit: 'events',   baseline:  0.5,  source: 'simulated' },
      neighbor_lice_pressure:  { value:  1.1, unit: 'index',    baseline:  1.0,  source: 'estimated' },
    },
  },
]

const BIO_READING_LABELS = {
  surface_temp_c:         'Surface Temperature',
  dissolved_oxygen_mg_l:  'Dissolved Oxygen',
  nitrate_umol_l:         'Nitrate Concentration',
  salinity_ppt:           'Salinity',
  chlorophyll_a_ug_l:     'Chlorophyll-a',
  lice_count_per_fish:    'Lice Count / Fish',
  hab_alert_count:        'HAB Alerts',
  jellyfish_sightings:    'Jellyfish Sightings',
  pathogen_obs_count:     'Pathogen Observations',
  treatments_last_90d:    'Treatments (90d)',
  neighbor_lice_pressure: 'Neighbour Lice Pressure',
}
export { BIO_READING_LABELS }

// ── 3. Alert Signals (precursor signals from pattern detector) ────────────────
export const MOCK_ALERT_SIGNALS = [
  // Frohavet North (S01) — HAB signals
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'hab',
    signal_name:'hab_warm_surface',   current_value:15.2, baseline_value:13.0, delta:2.2, threshold:15.0, unit:'°C',       triggered:true  },
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'hab',
    signal_name:'hab_low_oxygen',     current_value: 6.8, baseline_value: 8.5, delta:-1.7,threshold: 7.0, unit:'mg/L',    triggered:true  },
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'hab',
    signal_name:'hab_high_nitrate',   current_value:18.4, baseline_value: 5.0, delta:13.4,threshold:12.0, unit:'µmol/L', triggered:true  },
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'hab',
    signal_name:'hab_high_prior',     current_value: 0.22,baseline_value: 0.12,delta:0.10,threshold: 0.15,unit:'prob',   triggered:true  },
  // Frohavet North — Lice signals
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'lice',
    signal_name:'lice_warm_water',    current_value:15.2, baseline_value:10.0, delta:5.2, threshold:10.0, unit:'°C',      triggered:true  },
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'lice',
    signal_name:'lice_elevated_counts',current_value:2.4, baseline_value:0.5,  delta:1.9, threshold: 1.0, unit:'lice/fish',triggered:true },
  // Frohavet North — Jellyfish signals
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'jellyfish',
    signal_name:'jellyfish_warm_seasonal',current_value:1.09,baseline_value:0.08,delta:1.01,threshold:0.5,unit:'index',  triggered:true  },
  { site_id:'DEMO_OP_S01', site_name:'Frohavet North', risk_type:'jellyfish',
    signal_name:'jellyfish_prior_sightings',current_value:3,baseline_value:0.5,delta:2.5,threshold:2.0,unit:'obs',       triggered:true  },
  // Sunndalsfjord (S02) — Lice signals
  { site_id:'DEMO_OP_S02', site_name:'Sunndalsfjord',  risk_type:'lice',
    signal_name:'lice_warm_water',    current_value:12.4, baseline_value:10.0, delta:2.4, threshold:10.0, unit:'°C',      triggered:true  },
  { site_id:'DEMO_OP_S02', site_name:'Sunndalsfjord',  risk_type:'lice',
    signal_name:'lice_elevated_counts',current_value:1.6, baseline_value:0.5,  delta:1.1, threshold: 1.0, unit:'lice/fish',triggered:true },
  // Storfjorden South (S03) — Pathogen signals
  { site_id:'DEMO_OP_S03', site_name:'Storfjorden South',risk_type:'pathogen',
    signal_name:'pathogen_neighbor_outbreak',current_value:0.20,baseline_value:0.10,delta:0.10,threshold:0.15,unit:'index',triggered:true},
  // Storfjorden South — not triggered
  { site_id:'DEMO_OP_S03', site_name:'Storfjorden South',risk_type:'lice',
    signal_name:'lice_warm_water',    current_value:11.2, baseline_value:10.0, delta:1.2, threshold:10.0, unit:'°C',      triggered:false },
]

// ── 4. Data Quality ───────────────────────────────────────────────────────────
export const MOCK_DATA_QUALITY = [
  {
    site_id:    'DEMO_OP_S01',
    site_name:  'Frohavet North',
    overall_completeness: 0.68,
    overall_confidence:   'medium',
    risk_types: {
      hab:       { source:'simulated', completeness:0.72, confidence:'medium',  flag:'LIMITED',    n_obs:12, missing_fields:['chlorophyll_history','algae_species'] },
      lice:      { source:'simulated', completeness:0.85, confidence:'high',    flag:'SUFFICIENT', n_obs:15, missing_fields:[] },
      jellyfish: { source:'simulated', completeness:0.45, confidence:'low',     flag:'POOR',       n_obs: 8, missing_fields:['current_data','bloom_index','species_id'] },
      pathogen:  { source:'simulated', completeness:0.61, confidence:'medium',  flag:'LIMITED',    n_obs:11, missing_fields:['pcr_results','mortality_records'] },
    },
  },
  {
    site_id:    'DEMO_OP_S02',
    site_name:  'Sunndalsfjord',
    overall_completeness: 0.74,
    overall_confidence:   'medium',
    risk_types: {
      hab:       { source:'simulated', completeness:0.78, confidence:'high',    flag:'SUFFICIENT', n_obs:14, missing_fields:['algae_species'] },
      lice:      { source:'simulated', completeness:0.88, confidence:'high',    flag:'SUFFICIENT', n_obs:16, missing_fields:[] },
      jellyfish: { source:'simulated', completeness:0.42, confidence:'low',     flag:'POOR',       n_obs: 7, missing_fields:['current_data','bloom_index','species_id'] },
      pathogen:  { source:'simulated', completeness:0.65, confidence:'medium',  flag:'LIMITED',    n_obs:12, missing_fields:['pcr_results'] },
    },
  },
  {
    site_id:    'DEMO_OP_S03',
    site_name:  'Storfjorden South',
    overall_completeness: 0.78,
    overall_confidence:   'medium',
    risk_types: {
      hab:       { source:'simulated', completeness:0.82, confidence:'high',    flag:'SUFFICIENT', n_obs:15, missing_fields:[] },
      lice:      { source:'simulated', completeness:0.90, confidence:'high',    flag:'SUFFICIENT', n_obs:17, missing_fields:[] },
      jellyfish: { source:'simulated', completeness:0.48, confidence:'low',     flag:'POOR',       n_obs: 9, missing_fields:['bloom_index','species_id'] },
      pathogen:  { source:'simulated', completeness:0.70, confidence:'medium',  flag:'LIMITED',    n_obs:13, missing_fields:['pcr_results'] },
    },
  },
]

// ── 5. Scenario Baselines ─────────────────────────────────────────────────────
export const SCENARIO_BASELINE = {
  biomass_tonnes:      9200,
  oxygen_mg_l:          8.5,
  nitrate_umol_l:       5.0,
  lice_pressure:        1.0,
  exposure_factor:      1.13,   // weighted average across 3 sites
  operational_factor:   1.02,
}

export const SCENARIO_PRESETS = [
  {
    id: 'baseline',
    label: 'Baseline',
    description: 'Current modelled conditions.',
    overrides: {},
  },
  {
    id: 'warm_summer',
    label: 'Warm Summer',
    description: 'SST +3°C above baseline; increased HAB and lice risk.',
    overrides: { oxygen_mg_l: 6.5, nitrate_umol_l: 14.0, lice_pressure: 1.5 },
  },
  {
    id: 'lice_outbreak',
    label: 'Lice Outbreak',
    description: 'Elevated ambient lice pressure from neighbouring sites.',
    overrides: { lice_pressure: 2.5, operational_factor: 1.25 },
  },
  {
    id: 'adverse_weather',
    label: 'Adverse Weather',
    description: 'Storm damage increases structural and operational stress.',
    overrides: { exposure_factor: 1.60, operational_factor: 1.40 },
  },
]
