/**
 * Mock data for Structural, Environmental, and Operational input panels.
 * Three demo sites: DEMO_OP_S01 (Frohavet North), DEMO_OP_S02 (Sunndalsfjord),
 * DEMO_OP_S03 (Storfjorden South).
 */

// ── Structural ─────────────────────────────────────────────────────────────────

export const MOCK_STRUCTURAL_INPUTS = {
  DEMO_OP_S01: {
    site_id: 'DEMO_OP_S01',
    site_name: 'Frohavet North',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'real',
    readings: [
      { parameter: 'Net Age', value: 3.5, baseline: 2.0, unit: 'years', adverse: true,
        description: 'Age of active net pen above recommended 3-year replacement cycle' },
      { parameter: 'Net Strength Residual', value: 72.0, baseline: 90.0, unit: '%', adverse: true,
        description: 'Remaining tensile strength vs. new net baseline' },
      { parameter: 'Mooring Inspection Score', value: 0.55, baseline: 0.80, unit: 'score', adverse: true,
        description: 'Composite score from most recent mooring inspection (1 = passed fully)' },
      { parameter: 'Deformation Load Index', value: 0.62, baseline: 0.35, unit: 'index', adverse: true,
        description: 'Fraction of design deformation load currently experienced' },
      { parameter: 'Anchor Line Condition', value: 0.58, baseline: 0.85, unit: 'score', adverse: true,
        description: 'Visual and tensile condition score of anchor lines (1 = new)' },
      { parameter: 'Last Inspection', value: 210, baseline: 90, unit: 'days ago', adverse: true,
        description: 'Days since last formal structural inspection' },
    ],
  },
  DEMO_OP_S02: {
    site_id: 'DEMO_OP_S02',
    site_name: 'Sunndalsfjord',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'real',
    readings: [
      { parameter: 'Net Age', value: 1.8, baseline: 2.0, unit: 'years', adverse: false },
      { parameter: 'Net Strength Residual', value: 88.0, baseline: 90.0, unit: '%', adverse: false },
      { parameter: 'Mooring Inspection Score', value: 0.78, baseline: 0.80, unit: 'score', adverse: false },
      { parameter: 'Deformation Load Index', value: 0.38, baseline: 0.35, unit: 'index', adverse: false },
      { parameter: 'Anchor Line Condition', value: 0.80, baseline: 0.85, unit: 'score', adverse: false },
      { parameter: 'Last Inspection', value: 95, baseline: 90, unit: 'days ago', adverse: false },
    ],
  },
  DEMO_OP_S03: {
    site_id: 'DEMO_OP_S03',
    site_name: 'Storfjorden South',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'real',
    readings: [
      { parameter: 'Net Age', value: 0.9, baseline: 2.0, unit: 'years', adverse: false },
      { parameter: 'Net Strength Residual', value: 96.0, baseline: 90.0, unit: '%', adverse: false },
      { parameter: 'Mooring Inspection Score', value: 0.92, baseline: 0.80, unit: 'score', adverse: false },
      { parameter: 'Deformation Load Index', value: 0.18, baseline: 0.35, unit: 'index', adverse: false },
      { parameter: 'Anchor Line Condition', value: 0.94, baseline: 0.85, unit: 'score', adverse: false },
      { parameter: 'Last Inspection', value: 42, baseline: 90, unit: 'days ago', adverse: false },
    ],
  },
}

export const STRUCTURAL_SITE_IDS = Object.keys(MOCK_STRUCTURAL_INPUTS)

// ── Environmental ──────────────────────────────────────────────────────────────

export const MOCK_ENVIRONMENTAL_INPUTS = {
  DEMO_OP_S01: {
    site_id: 'DEMO_OP_S01',
    site_name: 'Frohavet North',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'real',
    readings: [
      { parameter: 'Dissolved O2', value: 6.8, baseline: 8.5, unit: 'mg/L', adverse: true,
        description: 'Below safe minimum of 7 mg/L — stress risk active' },
      { parameter: 'O2 Saturation', value: 78.0, baseline: 95.0, unit: '%', adverse: true,
        description: 'Below 80% saturation threshold' },
      { parameter: 'Surface Temperature', value: 16.2, baseline: 12.0, unit: 'C', adverse: true,
        description: 'Above safe high (16C) — HAB and pathogen risk elevated' },
      { parameter: 'Current Speed', value: 0.72, baseline: 0.40, unit: 'm/s', adverse: true,
        description: 'Exceeds design limit of 0.60 m/s' },
      { parameter: 'Significant Wave Height', value: 2.8, baseline: 1.5, unit: 'm', adverse: true,
        description: 'Above 2.0 m design limit' },
      { parameter: 'Ice Risk Score', value: 0.02, baseline: 0.05, unit: 'score', adverse: false },
      { parameter: 'Exposure Class', value: 'open', baseline: 'semi', unit: '', adverse: true },
    ],
  },
  DEMO_OP_S02: {
    site_id: 'DEMO_OP_S02',
    site_name: 'Sunndalsfjord',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'simulated',
    readings: [
      { parameter: 'Dissolved O2', value: 8.2, baseline: 8.5, unit: 'mg/L', adverse: false },
      { parameter: 'O2 Saturation', value: 92.0, baseline: 95.0, unit: '%', adverse: false },
      { parameter: 'Surface Temperature', value: 12.4, baseline: 12.0, unit: 'C', adverse: false },
      { parameter: 'Current Speed', value: 0.38, baseline: 0.40, unit: 'm/s', adverse: false },
      { parameter: 'Significant Wave Height', value: 1.1, baseline: 1.5, unit: 'm', adverse: false },
      { parameter: 'Ice Risk Score', value: 0.05, baseline: 0.05, unit: 'score', adverse: false },
      { parameter: 'Exposure Class', value: 'semi', baseline: 'semi', unit: '', adverse: false },
    ],
  },
  DEMO_OP_S03: {
    site_id: 'DEMO_OP_S03',
    site_name: 'Storfjorden South',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'real',
    readings: [
      { parameter: 'Dissolved O2', value: 9.5, baseline: 8.5, unit: 'mg/L', adverse: false },
      { parameter: 'O2 Saturation', value: 106.0, baseline: 95.0, unit: '%', adverse: false },
      { parameter: 'Surface Temperature', value: 9.8, baseline: 12.0, unit: 'C', adverse: false },
      { parameter: 'Current Speed', value: 0.18, baseline: 0.40, unit: 'm/s', adverse: false },
      { parameter: 'Significant Wave Height', value: 0.4, baseline: 1.5, unit: 'm', adverse: false },
      { parameter: 'Ice Risk Score', value: 0.10, baseline: 0.05, unit: 'score', adverse: true,
        description: 'Slight ice risk — fjord sheltered but higher latitude effect' },
      { parameter: 'Exposure Class', value: 'sheltered', baseline: 'semi', unit: '', adverse: false },
    ],
  },
}

export const ENVIRONMENTAL_SITE_IDS = Object.keys(MOCK_ENVIRONMENTAL_INPUTS)

// ── Operational ────────────────────────────────────────────────────────────────

export const MOCK_OPERATIONAL_INPUTS = {
  DEMO_OP_S01: {
    site_id: 'DEMO_OP_S01',
    site_name: 'Frohavet North',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'estimated',
    readings: [
      { parameter: 'Staffing Score', value: 0.55, baseline: 0.75, unit: 'score', adverse: true,
        description: 'Below safe minimum (0.60) — shift gaps identified' },
      { parameter: 'Training Compliance', value: 72.0, baseline: 90.0, unit: '%', adverse: true,
        description: 'Below 80% compliance requirement for high-risk procedures' },
      { parameter: 'Incident Rate (12m)', value: 1.4, baseline: 0.5, unit: '/month', adverse: true,
        description: 'Above baseline of 1.0 incidents/month' },
      { parameter: 'Maintenance Backlog', value: 0.48, baseline: 0.20, unit: 'score', adverse: true,
        description: 'Backlog score above safe threshold (0.30)' },
      { parameter: 'Critical Ops Frequency', value: 6.5, baseline: 4.0, unit: '/month', adverse: true,
        description: 'High-risk operations above guideline frequency' },
      { parameter: 'Equipment Readiness', value: 0.65, baseline: 0.80, unit: 'score', adverse: true,
        description: 'Below operational minimum (0.70)' },
    ],
  },
  DEMO_OP_S02: {
    site_id: 'DEMO_OP_S02',
    site_name: 'Sunndalsfjord',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'real',
    readings: [
      { parameter: 'Staffing Score', value: 0.78, baseline: 0.75, unit: 'score', adverse: false },
      { parameter: 'Training Compliance', value: 88.0, baseline: 90.0, unit: '%', adverse: false },
      { parameter: 'Incident Rate (12m)', value: 0.6, baseline: 0.5, unit: '/month', adverse: false },
      { parameter: 'Maintenance Backlog', value: 0.22, baseline: 0.20, unit: 'score', adverse: false },
      { parameter: 'Critical Ops Frequency', value: 3.8, baseline: 4.0, unit: '/month', adverse: false },
      { parameter: 'Equipment Readiness', value: 0.82, baseline: 0.80, unit: 'score', adverse: false },
    ],
  },
  DEMO_OP_S03: {
    site_id: 'DEMO_OP_S03',
    site_name: 'Storfjorden South',
    recorded_at: '2026-03-10T06:00:00Z',
    source: 'real',
    readings: [
      { parameter: 'Staffing Score', value: 0.92, baseline: 0.75, unit: 'score', adverse: false },
      { parameter: 'Training Compliance', value: 97.0, baseline: 90.0, unit: '%', adverse: false },
      { parameter: 'Incident Rate (12m)', value: 0.2, baseline: 0.5, unit: '/month', adverse: false },
      { parameter: 'Maintenance Backlog', value: 0.08, baseline: 0.20, unit: 'score', adverse: false },
      { parameter: 'Critical Ops Frequency', value: 2.1, baseline: 4.0, unit: '/month', adverse: false },
      { parameter: 'Equipment Readiness', value: 0.95, baseline: 0.80, unit: 'score', adverse: false },
    ],
  },
}

export const OPERATIONAL_SITE_IDS = Object.keys(MOCK_OPERATIONAL_INPUTS)
