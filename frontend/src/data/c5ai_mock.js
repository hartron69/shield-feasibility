/**
 * C5AI+ Risk Intelligence – Mock Data
 *
 * Calibrated against Kornstad Havbruk AS (8 300 t, 3 sites, Møre og Romsdal).
 * Brier score history from the 5-cycle demo run (run_learning_loop_demo.py).
 * Replace with live API call when /api/c5ai/* routes are ready.
 */

export const C5AI_MOCK = {
  metadata: {
    operator_id:             'KORNSTAD_HAVBRUK',
    operator_name:           'Kornstad Havbruk AS',
    model_version:           '5.0.0',
    generated_at:            '2026-03-10T08:14:22Z',
    forecast_horizon_years:  5,
    overall_confidence:      'medium',
    overall_data_quality:    'LIMITED',
    learning_status:         'warming',
    cycles_completed:        5,
    last_retrain_at:         '2026-03-10T08:00:00Z',
    probability_model_versions: {
      hab:       'v1.15',
      lice:      'v1.15',
      jellyfish: 'v1.15',
      pathogen:  'v1.15',
    },
    sites_included: ['KH_S01', 'KH_S02', 'KH_S03'],
    warnings: [],
  },

  // ── A. Risk Overview ──────────────────────────────────────────────────────

  overall_risk_score: 62,   // 0–100 composite

  sites: [
    {
      site_id:       'KH_S01',
      site_name:     'Kornstad',
      biomass_tonnes: 3000,
      biomass_value_nok: 195_000_000,
      fjord_exposure: 'semi_exposed',
      risk_score:     62,
      dominant_risks: ['hab', 'lice'],
    },
    {
      site_id:       'KH_S02',
      site_name:     'Leite',
      biomass_tonnes: 2500,
      biomass_value_nok: 162_500_000,
      fjord_exposure: 'semi_exposed',
      risk_score:     58,
      dominant_risks: ['lice'],
    },
    {
      site_id:       'KH_S03',
      site_name:     'Hogsnes',
      biomass_tonnes: 2800,
      biomass_value_nok: 182_000_000,
      fjord_exposure: 'sheltered',
      risk_score:     41,
      dominant_risks: ['pathogen'],
    },
  ],

  domain_breakdown: {
    biological:    { fraction: 0.52, annual_loss_nok: 11_800_000 },
    structural:    { fraction: 0.22, annual_loss_nok:  5_000_000 },
    environmental: { fraction: 0.17, annual_loss_nok:  3_900_000 },
    operational:   { fraction: 0.09, annual_loss_nok:  2_000_000 },
  },

  // ── B. Biological Forecast ─────────────────────────────────────────────────

  biological_forecast: [
    {
      site_id:   'KH_S01',
      site_name: 'Kornstad',
      hab: {
        probability:         0.22,
        baseline_probability: 0.12,
        adjusted_probability: 0.22,
        expected_loss_mean:  3_200_000,
        expected_loss_p50:   1_800_000,
        expected_loss_p90:   7_100_000,
        confidence_score:    0.62,
        data_quality_flag:   'LIMITED',
        model_used:          'prior',
        trend:               'increasing',
      },
      lice: {
        probability:         0.41,
        baseline_probability: 0.30,
        adjusted_probability: 0.41,
        expected_loss_mean:  1_100_000,
        expected_loss_p50:     650_000,
        expected_loss_p90:   2_300_000,
        confidence_score:    0.71,
        data_quality_flag:   'SUFFICIENT',
        model_used:          'ml_lice',
        trend:               'stable',
      },
      jellyfish: {
        probability:         0.09,
        baseline_probability: 0.08,
        adjusted_probability: 0.09,
        expected_loss_mean:    320_000,
        expected_loss_p50:     150_000,
        expected_loss_p90:     780_000,
        confidence_score:    0.48,
        data_quality_flag:   'POOR',
        model_used:          'prior',
        trend:               'stable',
      },
      pathogen: {
        probability:         0.14,
        baseline_probability: 0.10,
        adjusted_probability: 0.14,
        expected_loss_mean:  1_500_000,
        expected_loss_p50:     800_000,
        expected_loss_p90:   3_800_000,
        confidence_score:    0.55,
        data_quality_flag:   'LIMITED',
        model_used:          'prior',
        trend:               'stable',
      },
    },
    {
      site_id:   'KH_S02',
      site_name: 'Leite',
      hab: {
        probability:         0.12,
        baseline_probability: 0.12,
        adjusted_probability: 0.12,
        expected_loss_mean:  1_600_000,
        expected_loss_p50:     900_000,
        expected_loss_p90:   3_800_000,
        confidence_score:    0.65,
        data_quality_flag:   'SUFFICIENT',
        model_used:          'prior',
        trend:               'stable',
      },
      lice: {
        probability:         0.35,
        baseline_probability: 0.30,
        adjusted_probability: 0.35,
        expected_loss_mean:    900_000,
        expected_loss_p50:     520_000,
        expected_loss_p90:   2_100_000,
        confidence_score:    0.72,
        data_quality_flag:   'SUFFICIENT',
        model_used:          'ml_lice',
        trend:               'decreasing',
      },
      jellyfish: {
        probability:         0.07,
        baseline_probability: 0.08,
        adjusted_probability: 0.07,
        expected_loss_mean:    250_000,
        expected_loss_p50:     120_000,
        expected_loss_p90:     600_000,
        confidence_score:    0.45,
        data_quality_flag:   'POOR',
        model_used:          'prior',
        trend:               'stable',
      },
      pathogen: {
        probability:         0.10,
        baseline_probability: 0.10,
        adjusted_probability: 0.10,
        expected_loss_mean:  1_100_000,
        expected_loss_p50:     600_000,
        expected_loss_p90:   2_900_000,
        confidence_score:    0.58,
        data_quality_flag:   'LIMITED',
        model_used:          'prior',
        trend:               'stable',
      },
    },
    {
      site_id:   'KH_S03',
      site_name: 'Hogsnes',
      hab: {
        probability:         0.06,
        baseline_probability: 0.12,
        adjusted_probability: 0.06,
        expected_loss_mean:    750_000,
        expected_loss_p50:     400_000,
        expected_loss_p90:   1_900_000,
        confidence_score:    0.70,
        data_quality_flag:   'SUFFICIENT',
        model_used:          'prior',
        trend:               'stable',
      },
      lice: {
        probability:         0.28,
        baseline_probability: 0.30,
        adjusted_probability: 0.28,
        expected_loss_mean:    680_000,
        expected_loss_p50:     380_000,
        expected_loss_p90:   1_600_000,
        confidence_score:    0.75,
        data_quality_flag:   'SUFFICIENT',
        model_used:          'ml_lice',
        trend:               'decreasing',
      },
      jellyfish: {
        probability:         0.04,
        baseline_probability: 0.08,
        adjusted_probability: 0.04,
        expected_loss_mean:    180_000,
        expected_loss_p50:      80_000,
        expected_loss_p90:     450_000,
        confidence_score:    0.50,
        data_quality_flag:   'POOR',
        model_used:          'prior',
        trend:               'stable',
      },
      pathogen: {
        probability:         0.08,
        baseline_probability: 0.10,
        adjusted_probability: 0.08,
        expected_loss_mean:    820_000,
        expected_loss_p50:     440_000,
        expected_loss_p90:   2_100_000,
        confidence_score:    0.60,
        data_quality_flag:   'LIMITED',
        model_used:          'prior',
        trend:               'stable',
      },
    },
  ],

  // ── C. Risk Drivers ────────────────────────────────────────────────────────

  risk_drivers: [
    {
      rank:        1,
      driver:      'Sea Surface Temperature',
      site:        'Kornstad',
      risk_type:   'hab',
      importance:  0.38,
      direction:   'positive',
      description: 'Summer SST > 14°C elevates HAB risk. Mean summer temp this site: 15.2°C. Model assigns 38% of HAB probability weight to this feature.',
    },
    {
      rank:        2,
      driver:      'Fjord Circulation Pattern',
      site:        'Kornstad',
      risk_type:   'hab',
      importance:  0.27,
      direction:   'positive',
      description: 'Semi-exposed coastal position with prevailing current patterns from the open sea associated with 1.4× elevated HAB transport risk relative to inner-fjord sites.',
    },
    {
      rank:        3,
      driver:      'Lice Treatment Lag',
      site:        'All sites',
      risk_type:   'lice',
      importance:  0.24,
      direction:   'positive',
      description: 'Spring lice peak (weeks 12–20). Treatment delay > 2 weeks significantly amplifies peak louse count and associated loss. Treatment effectiveness: bath 65%, in-feed 72%.',
    },
    {
      rank:        4,
      driver:      'Chlorophyll-a Concentration',
      site:        'Kornstad',
      risk_type:   'hab',
      importance:  0.22,
      direction:   'positive',
      description: 'Elevated chlorophyll-a (> 3 µg/L) in April–May is a leading indicator of HAB formation. Current mean: 3.8 µg/L at this site.',
    },
    {
      rank:        5,
      driver:      'Network Proximity',
      site:        'Leite',
      risk_type:   'lice',
      importance:  0.19,
      direction:   'positive',
      description: '2 neighbouring sites within 35 km. Lice dispersal model applies a 1.12× network risk multiplier to this site.',
    },
    {
      rank:        6,
      driver:      'Years in Operation',
      site:        'Hogsnes',
      risk_type:   'pathogen',
      importance:  0.15,
      direction:   'negative',
      description: '12 years in operation at this site. Established biosecurity protocols and historical pathogen surveillance reduce residual pathogen risk by approximately 20%.',
    },
    {
      rank:        7,
      driver:      'Salinity Variability',
      site:        'Leite',
      risk_type:   'jellyfish',
      importance:  0.11,
      direction:   'positive',
      description: 'Freshwater inflow from snowmelt in April–June reduces mean salinity (29–31 ppt). Low salinity windows are associated with increased jellyfish bloom incidence.',
    },
  ],

  // ── D. Learning Status ────────────────────────────────────────────────────

  learning: {
    status:              'warming',
    cycles_completed:    5,
    cycles_to_active:    10,
    last_retrain_at:     '2026-03-10T08:00:00Z',
    training_source:     'simulated',   // 'simulated' | 'operator_reported'
    model_versions: {
      hab:       'v1.15',
      lice:      'v1.15',
      jellyfish: 'v1.15',
      pathogen:  'v1.15',
    },
    brier_history: [
      { cycle: 1, year: 2020, hab: 0.268, lice: 0.090, jellyfish: 0.286, pathogen: 0.810 },
      { cycle: 2, year: 2021, hab: 0.254, lice: 0.063, jellyfish: 0.267, pathogen: 0.563 },
      { cycle: 3, year: 2022, hab: 0.188, lice: 0.048, jellyfish: 0.256, pathogen: 0.431 },
      { cycle: 4, year: 2023, hab: 0.150, lice: 0.039, jellyfish: 0.207, pathogen: 0.349 },
      { cycle: 5, year: 2024, hab: 0.171, lice: 0.033, jellyfish: 0.174, pathogen: 0.325 },
    ],
    evaluation_metrics: {
      hab: {
        brier_score:            0.171,
        log_loss:               0.412,
        mean_probability_error: 0.038,
        severity_mae_nok:       380_000,
        calibration_slope:      0.82,
        n_samples:              12,
      },
      lice: {
        brier_score:            0.033,
        log_loss:               0.198,
        mean_probability_error: -0.012,
        severity_mae_nok:       120_000,
        calibration_slope:      0.96,
        n_samples:              15,
      },
      jellyfish: {
        brier_score:            0.174,
        log_loss:               0.428,
        mean_probability_error: 0.021,
        severity_mae_nok:        85_000,
        calibration_slope:      0.79,
        n_samples:              10,
      },
      pathogen: {
        brier_score:            0.325,
        log_loss:               0.681,
        mean_probability_error: 0.124,
        severity_mae_nok:       640_000,
        calibration_slope:      0.61,
        n_samples:              11,
      },
    },
  },

  // ── E. Structural Forecast ─────────────────────────────────────────────────

  structural_forecast: [
    {
      site_id: 'KH_S01', site_name: 'Kornstad',
      risks: {
        mooring_failure:      { probability: 0.22, expected_loss_mean: 1_980_000, expected_loss_p50: 1_050_000, expected_loss_p90: 4_200_000, confidence: 0.48, drivers: ['Mooring inspection score 0.55 < 0.60', 'Inspection overdue (210d > 180d)'] },
        net_integrity:        { probability: 0.27, expected_loss_mean: 2_700_000, expected_loss_p50: 1_440_000, expected_loss_p90: 5_600_000, confidence: 0.42, drivers: ['Net strength 72% below 70% threshold', 'Net age 3.5y > 3-year guideline'] },
        cage_structural:      { probability: 0.18, expected_loss_mean: 3_600_000, expected_loss_p50: 1_860_000, expected_loss_p90: 7_200_000, confidence: 0.52, drivers: ['Deformation load index 0.62 above threshold'] },
        deformation:          { probability: 0.22, expected_loss_mean: 2_160_000, expected_loss_p50: 1_140_000, expected_loss_p90: 4_500_000, confidence: 0.45, drivers: ['Load index 0.62 > 0.40', 'Monitoring overdue 210d'] },
        anchor_deterioration: { probability: 0.14, expected_loss_mean:   960_000, expected_loss_p50:   540_000, expected_loss_p90: 2_040_000, confidence: 0.55, drivers: ['Anchor condition 0.58 < 0.50 approaching critical'] },
      },
    },
    {
      site_id: 'KH_S02', site_name: 'Leite',
      risks: {
        mooring_failure:      { probability: 0.05, expected_loss_mean:   450_000, expected_loss_p50:   240_000, expected_loss_p90:   960_000, confidence: 0.68, drivers: ['Mooring within normal parameters'] },
        net_integrity:        { probability: 0.08, expected_loss_mean:   800_000, expected_loss_p50:   430_000, expected_loss_p90: 1_660_000, confidence: 0.70, drivers: ['Net condition normal'] },
        cage_structural:      { probability: 0.04, expected_loss_mean:   720_000, expected_loss_p50:   380_000, expected_loss_p90: 1_500_000, confidence: 0.72, drivers: ['Structural loads within design range'] },
        deformation:          { probability: 0.06, expected_loss_mean:   600_000, expected_loss_p50:   320_000, expected_loss_p90: 1_250_000, confidence: 0.70, drivers: ['Load index 0.38 within normal range'] },
        anchor_deterioration: { probability: 0.04, expected_loss_mean:   320_000, expected_loss_p50:   180_000, expected_loss_p90:   680_000, confidence: 0.72, drivers: ['Anchor lines recently inspected'] },
      },
    },
    {
      site_id: 'KH_S03', site_name: 'Hogsnes',
      risks: {
        mooring_failure:      { probability: 0.05, expected_loss_mean:   450_000, expected_loss_p50:   240_000, expected_loss_p90:   960_000, confidence: 0.72, drivers: ['Mooring score 0.92 — excellent'] },
        net_integrity:        { probability: 0.08, expected_loss_mean:   800_000, expected_loss_p50:   430_000, expected_loss_p90: 1_660_000, confidence: 0.75, drivers: ['New net — 0.9 years, 96% residual strength'] },
        cage_structural:      { probability: 0.04, expected_loss_mean:   720_000, expected_loss_p50:   380_000, expected_loss_p90: 1_500_000, confidence: 0.78, drivers: ['Load index 0.18 — well below design limit'] },
        deformation:          { probability: 0.06, expected_loss_mean:   600_000, expected_loss_p50:   320_000, expected_loss_p90: 1_250_000, confidence: 0.75, drivers: ['Recently inspected (42d), load minimal'] },
        anchor_deterioration: { probability: 0.04, expected_loss_mean:   320_000, expected_loss_p50:   180_000, expected_loss_p90:   680_000, confidence: 0.78, drivers: ['Anchor condition 0.94 — near new'] },
      },
    },
  ],

  // ── F. Environmental Forecast ──────────────────────────────────────────────

  environmental_forecast: [
    {
      site_id: 'KH_S01', site_name: 'Kornstad',
      risks: {
        oxygen_stress:      { probability: 0.26, expected_loss_mean: 2_080_000, expected_loss_p50: 1_100_000, expected_loss_p90: 4_300_000, confidence: 0.45, drivers: ['DO 6.8 mg/L below 7.0 mg/L safe limit', 'O2 saturation 78% below 80%'] },
        temperature_extreme:{ probability: 0.22, expected_loss_mean: 1_320_000, expected_loss_p50:   700_000, expected_loss_p90: 2_700_000, confidence: 0.50, drivers: ['Surface temp 16.2C above safe high (16C)'] },
        current_storm:      { probability: 0.27, expected_loss_mean: 3_780_000, expected_loss_p50: 1_960_000, expected_loss_p90: 7_800_000, confidence: 0.42, drivers: ['Current 0.72 m/s exceeds design limit (0.60)', 'Wave height 2.8m > 2.0m limit'] },
        ice:                { probability: 0.03, expected_loss_mean:   300_000, expected_loss_p50:   154_000, expected_loss_p90:   650_000, confidence: 0.68, drivers: ['Ice risk score negligible (0.02)'] },
        exposure_anomaly:   { probability: 0.14, expected_loss_mean:   980_000, expected_loss_p50:   522_000, expected_loss_p90: 2_100_000, confidence: 0.52, drivers: ['Open coast + high current + elevated wave height'] },
      },
    },
    {
      site_id: 'KH_S02', site_name: 'Leite',
      risks: {
        oxygen_stress:      { probability: 0.10, expected_loss_mean:   800_000, expected_loss_p50:   425_000, expected_loss_p90: 1_650_000, confidence: 0.65, drivers: ['Oxygen within normal range'] },
        temperature_extreme:{ probability: 0.08, expected_loss_mean:   480_000, expected_loss_p50:   256_000, expected_loss_p90:   980_000, confidence: 0.68, drivers: ['Temperature 12.4C — within safe range'] },
        current_storm:      { probability: 0.07, expected_loss_mean:   980_000, expected_loss_p50:   520_000, expected_loss_p90: 2_050_000, confidence: 0.70, drivers: ['Current and wave within design limits'] },
        ice:                { probability: 0.03, expected_loss_mean:   300_000, expected_loss_p50:   154_000, expected_loss_p90:   650_000, confidence: 0.70, drivers: ['Low ice risk (0.05)'] },
        exposure_anomaly:   { probability: 0.05, expected_loss_mean:   350_000, expected_loss_p50:   186_000, expected_loss_p90:   730_000, confidence: 0.72, drivers: ['Semi-exposed, environmental loading normal'] },
      },
    },
    {
      site_id: 'KH_S03', site_name: 'Hogsnes',
      risks: {
        oxygen_stress:      { probability: 0.10, expected_loss_mean:   800_000, expected_loss_p50:   425_000, expected_loss_p90: 1_650_000, confidence: 0.68, drivers: ['DO 9.5 mg/L — optimal'] },
        temperature_extreme:{ probability: 0.08, expected_loss_mean:   480_000, expected_loss_p50:   256_000, expected_loss_p90:   980_000, confidence: 0.70, drivers: ['Temp 9.8C — within safe range'] },
        current_storm:      { probability: 0.07, expected_loss_mean:   980_000, expected_loss_p50:   520_000, expected_loss_p90: 2_050_000, confidence: 0.72, drivers: ['Current 0.18 m/s — calm sheltered site'] },
        ice:                { probability: 0.07, expected_loss_mean:   700_000, expected_loss_p50:   364_000, expected_loss_p90: 1_500_000, confidence: 0.65, drivers: ['Ice score 0.10 — fjord sheltered but high latitude'] },
        exposure_anomaly:   { probability: 0.05, expected_loss_mean:   350_000, expected_loss_p50:   186_000, expected_loss_p90:   730_000, confidence: 0.75, drivers: ['Sheltered site — minimal combined loading'] },
      },
    },
  ],

  // ── G. Operational Forecast ────────────────────────────────────────────────

  operational_forecast: [
    {
      site_id: 'KH_S01', site_name: 'Kornstad',
      risks: {
        human_error:         { probability: 0.27, expected_loss_mean: 1_350_000, expected_loss_p50:   700_000, expected_loss_p90: 2_800_000, confidence: 0.48, drivers: ['Staffing score 0.55 < 0.60', 'High-risk ops 6.5/month'] },
        procedure_failure:   { probability: 0.22, expected_loss_mean: 1_320_000, expected_loss_p50:   700_000, expected_loss_p90: 2_700_000, confidence: 0.50, drivers: ['Training compliance 72% < 80% requirement'] },
        equipment_failure:   { probability: 0.25, expected_loss_mean: 1_750_000, expected_loss_p50:   920_000, expected_loss_p90: 3_600_000, confidence: 0.45, drivers: ['Equipment readiness 0.65 < 0.70 minimum', 'Maintenance backlog 0.48 > 0.30'] },
        incident:            { probability: 0.18, expected_loss_mean:   720_000, expected_loss_p50:   386_000, expected_loss_p90: 1_550_000, confidence: 0.52, drivers: ['Incident rate 1.4/month > baseline 1.0/month'] },
        maintenance_backlog: { probability: 0.22, expected_loss_mean: 1_100_000, expected_loss_p50:   586_000, expected_loss_p90: 2_300_000, confidence: 0.48, drivers: ['Backlog score 0.48 > safe level 0.30'] },
      },
    },
    {
      site_id: 'KH_S02', site_name: 'Leite',
      risks: {
        human_error:         { probability: 0.12, expected_loss_mean:   600_000, expected_loss_p50:   310_000, expected_loss_p90: 1_250_000, confidence: 0.68, drivers: ['Staffing within normal range'] },
        procedure_failure:   { probability: 0.08, expected_loss_mean:   480_000, expected_loss_p50:   256_000, expected_loss_p90:   980_000, confidence: 0.70, drivers: ['Training compliance 88% — adequate'] },
        equipment_failure:   { probability: 0.10, expected_loss_mean:   700_000, expected_loss_p50:   374_000, expected_loss_p90: 1_500_000, confidence: 0.68, drivers: ['Equipment readiness 0.82 — good'] },
        incident:            { probability: 0.06, expected_loss_mean:   240_000, expected_loss_p50:   128_000, expected_loss_p90:   510_000, confidence: 0.72, drivers: ['Incident rate 0.6/month — below baseline'] },
        maintenance_backlog: { probability: 0.09, expected_loss_mean:   450_000, expected_loss_p50:   240_000, expected_loss_p90:   940_000, confidence: 0.70, drivers: ['Backlog score 0.22 within acceptable range'] },
      },
    },
    {
      site_id: 'KH_S03', site_name: 'Hogsnes',
      risks: {
        human_error:         { probability: 0.12, expected_loss_mean:   600_000, expected_loss_p50:   310_000, expected_loss_p90: 1_250_000, confidence: 0.72, drivers: ['Staffing 0.92 — excellent'] },
        procedure_failure:   { probability: 0.08, expected_loss_mean:   480_000, expected_loss_p50:   256_000, expected_loss_p90:   980_000, confidence: 0.75, drivers: ['Training 97% — best in class'] },
        equipment_failure:   { probability: 0.10, expected_loss_mean:   700_000, expected_loss_p50:   374_000, expected_loss_p90: 1_500_000, confidence: 0.72, drivers: ['Equipment readiness 0.95 — excellent'] },
        incident:            { probability: 0.06, expected_loss_mean:   240_000, expected_loss_p50:   128_000, expected_loss_p90:   510_000, confidence: 0.75, drivers: ['Incident rate 0.2/month — lowest of all sites'] },
        maintenance_backlog: { probability: 0.09, expected_loss_mean:   450_000, expected_loss_p50:   240_000, expected_loss_p90:   940_000, confidence: 0.72, drivers: ['Backlog 0.08 — minimal'] },
      },
    },
  ],

  // ── PCC Integration ────────────────────────────────────────────────────────

  pcc_integration: {
    enriched:                  true,
    scale_factor:              1.18,
    scale_factor_static:       1.00,
    biological_loss_fraction:  0.52,
    mitigation_impact: {
      hab_monitoring:  { probability_reduction: 0.15, loss_reduction: 0.12 },
      lice_treatment:  { probability_reduction: 0.28, loss_reduction: 0.22 },
    },
    suitability_impact: {
      bio_criterion_score:   68,
      bio_criterion_weight:  0.25,
      bio_criterion_finding: 'C5AI+ detects elevated HAB risk at Kornstad (semi-eksponert, SST 14.8°C). Biologisk skalfaktor 1.18× påført Monte Carlo-simulering.',
    },
  },
}
