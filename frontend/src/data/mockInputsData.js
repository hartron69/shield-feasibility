/**
 * Mock Inputs Data for C5AI+ Inputs Page
 *
 * Consistent with C5AI_MOCK (c5ai_mock.js) and MOCK_ALERTS (mockAlertsData.js).
 * Three sites: Kornstad (KH_S01), Leite (KH_S02), Hogsnes (KH_S03) — Kornstad Havbruk AS.
 */

// ── 1. Site Profiles ──────────────────────────────────────────────────────────
export const MOCK_SITE_PROFILES = [
  {
    site_id:             'KH_S01',
    site_name:           'Kornstad',
    region:              'Møre og Romsdal, Norway',
    species:             'Atlantic Salmon (Salmo salar)',
    biomass_tonnes:      3000,
    biomass_value_nok:   195_000_000,
    equipment_value_nok:  48_000_000,
    infra_value_nok:      35_000_000,
    annual_revenue_nok:  270_000_000,
    exposure_factor:     1.15,   // 1.0=sheltered, 1.5=open coast
    operational_factor:  1.10,   // 1.0=standard, higher = stressed operations
    fjord_exposure:      'semi_exposed',
    lice_pressure_factor: 1.15,
    hab_risk_factor:     1.10,
    years_in_operation:  7,
    license_number:      'NOR-MR-1842',
    nis_certification:   true,
    data_source:         'simulated',
  },
  {
    site_id:             'KH_S02',
    site_name:           'Leite',
    region:              'Møre og Romsdal, Norway',
    species:             'Atlantic Salmon (Salmo salar)',
    biomass_tonnes:      2500,
    biomass_value_nok:   162_500_000,
    equipment_value_nok:  42_000_000,
    infra_value_nok:      30_000_000,
    annual_revenue_nok:  225_000_000,
    exposure_factor:     1.15,
    operational_factor:  1.00,
    fjord_exposure:      'semi_exposed',
    lice_pressure_factor: 1.10,
    hab_risk_factor:     0.90,
    years_in_operation:  11,
    license_number:      'NOR-MR-2201',
    nis_certification:   true,
    data_source:         'simulated',
  },
  {
    site_id:             'KH_S03',
    site_name:           'Hogsnes',
    region:              'Møre og Romsdal, Norway',
    species:             'Atlantic Salmon (Salmo salar)',
    biomass_tonnes:      2800,
    biomass_value_nok:   182_000_000,
    equipment_value_nok:  45_000_000,
    infra_value_nok:      32_000_000,
    annual_revenue_nok:  252_000_000,
    exposure_factor:     0.85,
    operational_factor:  0.95,
    fjord_exposure:      'sheltered',
    lice_pressure_factor: 0.85,
    hab_risk_factor:     0.70,
    years_in_operation:  12,
    license_number:      'NOR-MR-2398',
    nis_certification:   true,
    data_source:         'simulated',
  },
]

// ── 2. Biological / Environmental Inputs ──────────────────────────────────────
export const MOCK_BIOLOGICAL_INPUTS = [
  {
    site_id:    'KH_S01',
    site_name:  'Kornstad',
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
    site_id:    'KH_S02',
    site_name:  'Leite',
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
    site_id:    'KH_S03',
    site_name:  'Hogsnes',
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
  // Kornstad (S01) — HAB signals
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'hab',
    signal_name:'hab_warm_surface',   current_value:15.2, baseline_value:13.0, delta:2.2, threshold:15.0, unit:'°C',       triggered:true  },
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'hab',
    signal_name:'hab_low_oxygen',     current_value: 6.8, baseline_value: 8.5, delta:-1.7,threshold: 7.0, unit:'mg/L',    triggered:true  },
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'hab',
    signal_name:'hab_high_nitrate',   current_value:18.4, baseline_value: 5.0, delta:13.4,threshold:12.0, unit:'µmol/L', triggered:true  },
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'hab',
    signal_name:'hab_high_prior',     current_value: 0.22,baseline_value: 0.12,delta:0.10,threshold: 0.15,unit:'prob',   triggered:true  },
  // Kornstad — Lice signals
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'lice',
    signal_name:'lice_warm_water',    current_value:15.2, baseline_value:10.0, delta:5.2, threshold:10.0, unit:'°C',      triggered:true  },
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'lice',
    signal_name:'lice_elevated_counts',current_value:2.4, baseline_value:0.5,  delta:1.9, threshold: 1.0, unit:'lice/fish',triggered:true },
  // Kornstad — Jellyfish signals
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'jellyfish',
    signal_name:'jellyfish_warm_seasonal',current_value:1.09,baseline_value:0.08,delta:1.01,threshold:0.5,unit:'index',  triggered:true  },
  { site_id:'KH_S01', site_name:'Kornstad', risk_type:'jellyfish',
    signal_name:'jellyfish_prior_sightings',current_value:3,baseline_value:0.5,delta:2.5,threshold:2.0,unit:'obs',       triggered:true  },
  // Leite (S02) — Lice signals
  { site_id:'KH_S02', site_name:'Leite',  risk_type:'lice',
    signal_name:'lice_warm_water',    current_value:12.4, baseline_value:10.0, delta:2.4, threshold:10.0, unit:'°C',      triggered:true  },
  { site_id:'KH_S02', site_name:'Leite',  risk_type:'lice',
    signal_name:'lice_elevated_counts',current_value:1.6, baseline_value:0.5,  delta:1.1, threshold: 1.0, unit:'lice/fish',triggered:true },
  // Hogsnes (S03) — Pathogen signals
  { site_id:'KH_S03', site_name:'Hogsnes',risk_type:'pathogen',
    signal_name:'pathogen_neighbor_outbreak',current_value:0.20,baseline_value:0.10,delta:0.10,threshold:0.15,unit:'index',triggered:true},
  // Hogsnes — not triggered
  { site_id:'KH_S03', site_name:'Hogsnes',risk_type:'lice',
    signal_name:'lice_warm_water',    current_value:11.2, baseline_value:10.0, delta:1.2, threshold:10.0, unit:'°C',      triggered:false },
]

// ── 4. Data Quality — all four domains ───────────────────────────────────────
// Risk type keys match c5ai_mock.js exactly:
//   biological:    hab, lice, jellyfish, pathogen
//   structural:    mooring_failure, net_integrity, cage_structural, deformation, anchor_deterioration
//   environmental: oxygen_stress, temperature_extreme, current_storm, ice, exposure_anomaly
//   operational:   human_error, procedure_failure, equipment_failure, incident, maintenance_backlog
export const MOCK_DATA_QUALITY = [
  {
    site_id:    'KH_S01',
    site_name:  'Kornstad',
    overall_completeness: 0.61,
    overall_confidence:   'medium',
    risk_types: {
      // Biological
      hab:                   { source:'simulated', completeness:0.72, confidence:'medium', flag:'LIMITED',    n_obs:12, missing_fields:['chlorophyll_history','algae_species'] },
      lice:                  { source:'simulated', completeness:0.85, confidence:'high',   flag:'SUFFICIENT', n_obs:15, missing_fields:[] },
      jellyfish:             { source:'simulated', completeness:0.45, confidence:'low',    flag:'POOR',       n_obs: 8, missing_fields:['current_data','bloom_index','species_id'] },
      pathogen:              { source:'simulated', completeness:0.61, confidence:'medium', flag:'LIMITED',    n_obs:11, missing_fields:['pcr_results','mortality_records'] },
      // Structural
      mooring_failure:       { source:'real',      completeness:0.58, confidence:'medium', flag:'LIMITED',    n_obs: 9, missing_fields:['anchor_tensile_test','corrosion_survey'] },
      net_integrity:         { source:'real',      completeness:0.80, confidence:'high',   flag:'SUFFICIENT', n_obs:14, missing_fields:[] },
      cage_structural:       { source:'estimated', completeness:0.42, confidence:'low',    flag:'POOR',       n_obs: 6, missing_fields:['deformation_log','load_cell_data'] },
      deformation:           { source:'estimated', completeness:0.45, confidence:'low',    flag:'POOR',       n_obs: 7, missing_fields:['load_cell_data','deformation_log'] },
      anchor_deterioration:  { source:'real',      completeness:0.55, confidence:'medium', flag:'LIMITED',    n_obs: 8, missing_fields:['tensile_test'] },
      // Environmental
      oxygen_stress:         { source:'real',      completeness:0.78, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      temperature_extreme:   { source:'simulated', completeness:0.88, confidence:'high',   flag:'SUFFICIENT', n_obs:20, missing_fields:[] },
      current_storm:         { source:'real',      completeness:0.65, confidence:'medium', flag:'LIMITED',    n_obs:10, missing_fields:['wave_buoy_data'] },
      ice:                   { source:'estimated', completeness:0.40, confidence:'low',    flag:'POOR',       n_obs: 5, missing_fields:['sea_level_gauge','ice_forecast'] },
      exposure_anomaly:      { source:'estimated', completeness:0.38, confidence:'low',    flag:'POOR',       n_obs: 4, missing_fields:['current_meter','exposure_model'] },
      // Operational
      human_error:           { source:'estimated', completeness:0.45, confidence:'low',    flag:'POOR',       n_obs: 5, missing_fields:['incident_reports','training_records'] },
      procedure_failure:     { source:'estimated', completeness:0.50, confidence:'medium', flag:'LIMITED',    n_obs: 7, missing_fields:['procedure_audit_log'] },
      equipment_failure:     { source:'estimated', completeness:0.55, confidence:'medium', flag:'LIMITED',    n_obs: 8, missing_fields:['maintenance_log','failure_history'] },
      incident:              { source:'estimated', completeness:0.52, confidence:'medium', flag:'LIMITED',    n_obs: 8, missing_fields:['near_miss_reports'] },
      maintenance_backlog:   { source:'real',      completeness:0.72, confidence:'medium', flag:'SUFFICIENT', n_obs:12, missing_fields:[] },
    },
  },
  {
    site_id:    'KH_S02',
    site_name:  'Leite',
    overall_completeness: 0.74,
    overall_confidence:   'medium',
    risk_types: {
      // Biological
      hab:                   { source:'simulated', completeness:0.78, confidence:'high',   flag:'SUFFICIENT', n_obs:14, missing_fields:['algae_species'] },
      lice:                  { source:'simulated', completeness:0.88, confidence:'high',   flag:'SUFFICIENT', n_obs:16, missing_fields:[] },
      jellyfish:             { source:'simulated', completeness:0.42, confidence:'low',    flag:'POOR',       n_obs: 7, missing_fields:['current_data','bloom_index','species_id'] },
      pathogen:              { source:'simulated', completeness:0.65, confidence:'medium', flag:'LIMITED',    n_obs:12, missing_fields:['pcr_results'] },
      // Structural
      mooring_failure:       { source:'real',      completeness:0.78, confidence:'high',   flag:'SUFFICIENT', n_obs:14, missing_fields:[] },
      net_integrity:         { source:'real',      completeness:0.90, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      cage_structural:       { source:'real',      completeness:0.72, confidence:'medium', flag:'SUFFICIENT', n_obs:12, missing_fields:['load_cell_data'] },
      deformation:           { source:'real',      completeness:0.75, confidence:'high',   flag:'SUFFICIENT', n_obs:13, missing_fields:[] },
      anchor_deterioration:  { source:'real',      completeness:0.80, confidence:'high',   flag:'SUFFICIENT', n_obs:15, missing_fields:[] },
      // Environmental
      oxygen_stress:         { source:'simulated', completeness:0.82, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      temperature_extreme:   { source:'simulated', completeness:0.85, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      current_storm:         { source:'simulated', completeness:0.70, confidence:'medium', flag:'SUFFICIENT', n_obs:12, missing_fields:[] },
      ice:                   { source:'estimated', completeness:0.62, confidence:'medium', flag:'LIMITED',    n_obs: 9, missing_fields:['ice_forecast'] },
      exposure_anomaly:      { source:'estimated', completeness:0.58, confidence:'medium', flag:'LIMITED',    n_obs: 8, missing_fields:['current_meter'] },
      // Operational
      human_error:           { source:'real',      completeness:0.75, confidence:'medium', flag:'SUFFICIENT', n_obs:13, missing_fields:['training_records'] },
      procedure_failure:     { source:'real',      completeness:0.78, confidence:'high',   flag:'SUFFICIENT', n_obs:14, missing_fields:[] },
      equipment_failure:     { source:'real',      completeness:0.80, confidence:'high',   flag:'SUFFICIENT', n_obs:15, missing_fields:[] },
      incident:              { source:'real',      completeness:0.78, confidence:'high',   flag:'SUFFICIENT', n_obs:14, missing_fields:[] },
      maintenance_backlog:   { source:'real',      completeness:0.82, confidence:'high',   flag:'SUFFICIENT', n_obs:16, missing_fields:[] },
    },
  },
  {
    site_id:    'KH_S03',
    site_name:  'Hogsnes',
    overall_completeness: 0.83,
    overall_confidence:   'high',
    risk_types: {
      // Biological
      hab:                   { source:'simulated', completeness:0.82, confidence:'high',   flag:'SUFFICIENT', n_obs:15, missing_fields:[] },
      lice:                  { source:'simulated', completeness:0.90, confidence:'high',   flag:'SUFFICIENT', n_obs:17, missing_fields:[] },
      jellyfish:             { source:'simulated', completeness:0.48, confidence:'low',    flag:'POOR',       n_obs: 9, missing_fields:['bloom_index','species_id'] },
      pathogen:              { source:'simulated', completeness:0.70, confidence:'medium', flag:'LIMITED',    n_obs:13, missing_fields:['pcr_results'] },
      // Structural
      mooring_failure:       { source:'real',      completeness:0.92, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      net_integrity:         { source:'real',      completeness:0.95, confidence:'high',   flag:'SUFFICIENT', n_obs:20, missing_fields:[] },
      cage_structural:       { source:'real',      completeness:0.88, confidence:'high',   flag:'SUFFICIENT', n_obs:16, missing_fields:[] },
      deformation:           { source:'real',      completeness:0.88, confidence:'high',   flag:'SUFFICIENT', n_obs:16, missing_fields:[] },
      anchor_deterioration:  { source:'real',      completeness:0.90, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      // Environmental
      oxygen_stress:         { source:'real',      completeness:0.92, confidence:'high',   flag:'SUFFICIENT', n_obs:22, missing_fields:[] },
      temperature_extreme:   { source:'real',      completeness:0.90, confidence:'high',   flag:'SUFFICIENT', n_obs:22, missing_fields:[] },
      current_storm:         { source:'real',      completeness:0.80, confidence:'high',   flag:'SUFFICIENT', n_obs:15, missing_fields:[] },
      ice:                   { source:'estimated', completeness:0.72, confidence:'medium', flag:'SUFFICIENT', n_obs:12, missing_fields:[] },
      exposure_anomaly:      { source:'estimated', completeness:0.68, confidence:'medium', flag:'LIMITED',    n_obs:10, missing_fields:['current_meter'] },
      // Operational
      human_error:           { source:'real',      completeness:0.88, confidence:'high',   flag:'SUFFICIENT', n_obs:16, missing_fields:[] },
      procedure_failure:     { source:'real',      completeness:0.90, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      equipment_failure:     { source:'real',      completeness:0.92, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
      incident:              { source:'real',      completeness:0.88, confidence:'high',   flag:'SUFFICIENT', n_obs:16, missing_fields:[] },
      maintenance_backlog:   { source:'real',      completeness:0.90, confidence:'high',   flag:'SUFFICIENT', n_obs:18, missing_fields:[] },
    },
  },
]

// ── 5. Scenario Baselines ─────────────────────────────────────────────────────
export const SCENARIO_BASELINE = {
  biomass_tonnes:      8300,
  oxygen_mg_l:          8.5,
  nitrate_umol_l:       5.0,
  lice_pressure:        1.0,
  exposure_factor:      1.05,   // weighted average across 3 sites
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

// ── 6. Shared site registry ───────────────────────────────────────────────────
// Single source of truth for site_id → display name mapping.
// Import this instead of hardcoding SITE_NAMES in individual panels.
export const SITE_REGISTRY = Object.fromEntries(
  MOCK_SITE_PROFILES.map(s => [s.site_id, s.site_name])
)
// e.g. { KH_S01: 'Kornstad', KH_S02: 'Leite', ... }

// ── 7. Canonical risk-type → domain mapping ───────────────────────────────────
// Single source of truth used by alerts, forecasts, data-quality and overview
// widgets. Keep in sync with RISK_TYPE_DOMAIN in alert_models.py.
export const RISK_TYPE_TO_DOMAIN = {
  // biological
  hab:                'biological',
  lice:               'biological',
  jellyfish:          'biological',
  pathogen:           'biological',
  // structural
  mooring_failure:    'structural',
  net_integrity:      'structural',
  cage_structural:    'structural',
  deformation:        'structural',
  anchor_deterioration: 'structural',
  // environmental
  oxygen_stress:      'environmental',
  temperature_extreme: 'environmental',
  current_storm:      'environmental',
  ice:                'environmental',
  exposure_anomaly:   'environmental',
  // operational
  human_error:        'operational',
  procedure_failure:  'operational',
  equipment_failure:  'operational',
  incident:           'operational',
  maintenance_backlog: 'operational',
}
