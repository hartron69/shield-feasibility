// Mock site-level smolt / RAS risk data
// 3 real Agaqua AS facilities — same names as PCC Feasibility smolt example
// + 2 additional demo settefisk sites for portfolio context
// All NOK values, risk scores 0–100

export const SMOLT_SITE_RISK = [
  {
    site_id: 'SMOLT_S01',
    site_name: 'Villa Smolt AS',
    municipality: 'Herøy',
    production_type: 'RAS',
    capacity_msmolt: 3.2,
    total_risk_score: 68,
    dominant_domain: 'ras_failure',
    expected_annual_loss_nok: 7_240_000,
    scr_contribution_nok: 19_100_000,
    scr_share_pct: 28.4,
    alerts_open: 2,
    alert_level: 'WARNING',
    domain_breakdown: {
      ras_failure:  0.38,
      oxygen_event: 0.24,
      power_outage: 0.13,
      biological:   0.16,
      operational:  0.09,
    },
    top_drivers: [
      {
        driver: 'Biofilterkapasitet',
        severity: 'high',
        description: 'Biofiltervolum under anbefalt 350 m³/kg tilvekst/dag',
      },
      {
        driver: 'Oksygensystem redundans',
        severity: 'high',
        description: 'Kun én O₂-kilde — backup ikke testet siste 90 dager',
      },
      {
        driver: 'Strømsikring',
        severity: 'medium',
        description: 'UPS-kapasitet dekker < 4 timer ved fullt anlegg',
      },
    ],
    data_confidence: 0.74,
  },
  {
    site_id: 'SMOLT_S02',
    site_name: 'Olden Oppdrettsanlegg AS',
    municipality: 'Stryn',
    production_type: 'flow-through',
    capacity_msmolt: 1.5,
    total_risk_score: 52,
    dominant_domain: 'oxygen_event',
    expected_annual_loss_nok: 4_180_000,
    scr_contribution_nok: 11_200_000,
    scr_share_pct: 16.6,
    alerts_open: 1,
    alert_level: 'WARNING',
    domain_breakdown: {
      ras_failure:  0.12,
      oxygen_event: 0.36,
      power_outage: 0.14,
      biological:   0.22,
      operational:  0.16,
    },
    top_drivers: [
      {
        driver: 'Oksygenmåler kalibrering',
        severity: 'high',
        description: 'Tre sensorer ute av kalibreringsintervall',
      },
      {
        driver: 'Vannkildesikring',
        severity: 'medium',
        description: 'Enkelt inntakspunkt uten reserveløsning',
      },
      {
        driver: 'Ansattkompetanse',
        severity: 'low',
        description: 'Én nøkkelperson mangler sertifisering',
      },
    ],
    data_confidence: 0.80,
  },
  {
    site_id: 'SMOLT_S03',
    site_name: 'Setran Settefisk AS',
    municipality: 'Osen',
    production_type: 'flow-through',
    capacity_msmolt: 1.1,
    total_risk_score: 44,
    dominant_domain: 'biological',
    expected_annual_loss_nok: 2_840_000,
    scr_contribution_nok: 7_400_000,
    scr_share_pct: 11.0,
    alerts_open: 0,
    alert_level: 'WATCH',
    domain_breakdown: {
      ras_failure:  0.10,
      oxygen_event: 0.15,
      power_outage: 0.12,
      biological:   0.38,
      operational:  0.25,
    },
    top_drivers: [
      {
        driver: 'AGD-risiko',
        severity: 'medium',
        description: 'Amøbisk gjellesykdom registrert i regionen',
      },
      {
        driver: 'Tetthetsstyring',
        severity: 'low',
        description: 'To kar over anbefalt tetthet (> 80 kg/m³)',
      },
    ],
    data_confidence: 0.86,
  },
  {
    site_id: 'SMOLT_S04',
    site_name: 'SalmoSet Ryfylke',
    municipality: 'Sauda',
    production_type: 'flow-through',
    capacity_msmolt: 2.5,
    total_risk_score: 35,
    dominant_domain: 'operational',
    expected_annual_loss_nok: 1_920_000,
    scr_contribution_nok: 5_200_000,
    scr_share_pct: 7.4,
    alerts_open: 0,
    alert_level: 'WATCH',
    domain_breakdown: {
      ras_failure:  0.08,
      oxygen_event: 0.11,
      power_outage: 0.14,
      biological:   0.28,
      operational:  0.39,
    },
    top_drivers: [
      {
        driver: 'Vannkildesikring',
        severity: 'low',
        description: 'Enkelt inntakspunkt uten reserveløsning',
      },
      {
        driver: 'Vedlikeholdslogg',
        severity: 'low',
        description: 'Dokumentasjon av preventivt vedlikehold ikke oppdatert',
      },
    ],
    data_confidence: 0.65,
  },
  {
    site_id: 'SMOLT_S05',
    site_name: 'AquaGen Sunnfjord',
    municipality: 'Sunnfjord',
    production_type: 'RAS',
    capacity_msmolt: 8.0,
    total_risk_score: 28,
    dominant_domain: 'operational',
    expected_annual_loss_nok: 1_240_000,
    scr_contribution_nok: 3_840_000,
    scr_share_pct: 5.5,
    alerts_open: 0,
    alert_level: 'NORMAL',
    domain_breakdown: {
      ras_failure:  0.18,
      oxygen_event: 0.14,
      power_outage: 0.10,
      biological:   0.22,
      operational:  0.36,
    },
    top_drivers: [
      {
        driver: 'Automatiseringsnivå',
        severity: 'low',
        description: 'Høy grad av automatisering og redundans — lav operasjonell risiko',
      },
    ],
    data_confidence: 0.93,
  },
]

export const SMOLT_SITE_RISK_SUMMARY = {
  operator_id: 'DEMO_SMOLT_OP',
  operator_name: 'Agaqua AS',
  // First 3 sites are Agaqua AS's own facilities (Villa Smolt / Olden / Setran)
  // — same facilities used in PCC Feasibility smolt example
  total_eal_nok: 17_420_000,
  total_scr_nok: 46_740_000,
  n_sites: 5,
  n_ras: 2,
  n_flow_through: 3,
  critical_sites: 0,
  warning_sites: 2,
}

// Domain display metadata for smolt-specific risk categories
export const SMOLT_DOMAIN_META = {
  ras_failure:  { label: 'RAS-svikt',    color: '#0D9488' },
  oxygen_event: { label: 'Oksygenhend.', color: '#0284C7' },
  power_outage: { label: 'Strømbortfall',color: '#CA8A04' },
  biological:   { label: 'Biologisk',    color: '#059669' },
  operational:  { label: 'Operasjonelt', color: '#7C3AED' },
}

// Agaqua AS facilities — same 3 used in PCC Feasibility smolt example
// Used by Risk Intelligence ↔ Feasibility cross-linking
export const AGAQUA_FEASIBILITY_FACILITIES = [
  { site_id: 'SMOLT_S01', site_name: 'Villa Smolt AS',            municipality: 'Herøy',  production_type: 'RAS' },
  { site_id: 'SMOLT_S02', site_name: 'Olden Oppdrettsanlegg AS', municipality: 'Stryn',  production_type: 'flow-through' },
  { site_id: 'SMOLT_S03', site_name: 'Setran Settefisk AS',       municipality: 'Osen',   production_type: 'flow-through' },
]
