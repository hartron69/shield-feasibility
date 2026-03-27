/**
 * cageTechnologyMeta.js — Norwegian labels and UI metadata for cage types.
 *
 * domain_multipliers mirrors models/cage_technology.py::CAGE_DOMAIN_MULTIPLIERS
 * and is used client-side for live preview (no round-trip needed for display).
 */

export const CAGE_TYPE_META = {
  open_net: {
    label: 'Åpen not',
    shortLabel: 'Åpen',
    description: 'Konvensjonelt oppdrettsmerda med full gjennomstrømning. Referanseteknologi.',
    color: '#4A90D9',
    riskLevel: 'Baseline',
    domain_multipliers: {
      biological:    1.00,
      structural:    1.00,
      environmental: 1.00,
      operational:   1.00,
    },
  },
  semi_closed: {
    label: 'Semi-lukket merd',
    shortLabel: 'Semi-lukket',
    description: 'Delvis lukket system med redusert vanngjennomstrømning. Lavere biologisk risiko, noe økt driftskompleksitet.',
    color: '#5BA85A',
    riskLevel: 'Moderat redusert',
    domain_multipliers: {
      biological:    0.75,
      structural:    0.95,
      environmental: 0.80,
      operational:   1.10,
    },
  },
  fully_closed: {
    label: 'Helt lukket merd',
    shortLabel: 'Lukket',
    description: 'Lukket resirkulerende system (RAS-sjø). Vesentlig lavere biologisk risiko, men høy strukturell og operasjonell risiko.',
    color: '#E8824A',
    riskLevel: 'Lav biologisk / Høy ops.',
    domain_multipliers: {
      biological:    0.45,
      structural:    1.20,
      environmental: 0.60,
      operational:   1.25,
    },
  },
  submerged: {
    label: 'Neddykket merd',
    shortLabel: 'Neddykket',
    description: 'Neddykket merd — beskyttet mot overflatevær, men med økte forankringslaster og kompleks logistikk.',
    color: '#9B59B6',
    riskLevel: 'Lav miljø / Høy struktur',
    domain_multipliers: {
      biological:    0.70,
      structural:    1.15,
      environmental: 0.55,
      operational:   1.15,
    },
  },
};

/** Ordered list of cage types for consistent rendering. */
export const CAGE_TYPES_ORDERED = ['open_net', 'semi_closed', 'fully_closed', 'submerged'];

/** Domain display config — label, color for SVG bars. */
export const DOMAIN_DISPLAY = {
  biological:    { label: 'Biologisk',    color: '#3A86FF' },
  structural:    { label: 'Strukturell',  color: '#FF6B6B' },
  environmental: { label: 'Miljø',        color: '#36A271' },
  operational:   { label: 'Operasjonell', color: '#F4A620' },
};

/**
 * Default scores per cage type — mirrors config/cage_weighting.py::CAGE_TYPE_DEFAULT_SCORES.
 * Used client-side to show "standard" badges in the advanced fields panel.
 */
export const CAGE_TYPE_DEFAULT_SCORES = {
  open_net:     { complexity: 0.20, criticality: 0.20, redundancy_level: 3, failure_mode_class: 'proportional' },
  semi_closed:  { complexity: 0.55, criticality: 0.45, redundancy_level: 2, failure_mode_class: 'proportional' },
  fully_closed: { complexity: 0.80, criticality: 0.65, redundancy_level: 2, failure_mode_class: 'proportional' },
  submerged:    { complexity: 0.70, criticality: 0.60, redundancy_level: 2, failure_mode_class: 'proportional' },
};

export const FAILURE_MODE_OPTIONS = [
  { value: 'proportional',            label: 'Proporsjonal (standard)' },
  { value: 'threshold',               label: 'Terskel (1.5×)' },
  { value: 'binary_high_consequence', label: 'Binær/høy konsekvens (2.5×)' },
];

export const REDUNDANCY_OPTIONS = [
  { value: 1, label: '1 — Ingen redundans (2.0×)' },
  { value: 2, label: '2 — Lav (1.5×)' },
  { value: 3, label: '3 — Moderat (1.0×)' },
  { value: 4, label: '4 — God (0.75×)' },
  { value: 5, label: '5 — Full redundans (0.5×)' },
];

/** Compute biomass-weighted domain multipliers for a list of cage objects.
 *  Each cage: { cage_type: string, biomass_tonnes: number }
 *  Returns { biological, structural, environmental, operational } or null if empty.
 */
export function computeLocalityDomainMultipliers(cages) {
  if (!cages || cages.length === 0) return null;
  const total = cages.reduce((s, c) => s + (c.biomass_tonnes || 0), 0);
  if (total === 0) return null;
  const domains = ['biological', 'structural', 'environmental', 'operational'];
  const result = {};
  for (const domain of domains) {
    result[domain] = cages.reduce((acc, c) => {
      const meta = CAGE_TYPE_META[c.cage_type];
      if (!meta) return acc;
      return acc + (c.biomass_tonnes / total) * meta.domain_multipliers[domain];
    }, 0);
  }
  return result;
}
