/**
 * Settefisk-spesifikke scenariopreset.
 * Tilsvarer SCENARIO_PRESETS men for smolt-modus.
 */
export const SMOLT_SCENARIO_PRESETS = [
  {
    id: 'ras_total_collapse',
    label: 'RAS-totalkollaps',
    description: 'Biofiltersvikt kombinert med strømbortfall. Rammer én produksjonsavdeling.',
    icon: 'E',
    params: { loss_multiplier: 4.20, bi_trigger: true },
  },
  {
    id: 'oxygen_crisis',
    label: 'Oksygenkrise (4t)',
    description: 'Pumpesvikt → O2 < 6 mg/L. Tap av 30–80 % av berørt generasjon.',
    icon: 'O',
    params: { loss_multiplier: 2.80, bi_trigger: true },
  },
  {
    id: 'water_contamination',
    label: 'Vannforurensning',
    description: 'Ekstern kilde. Sjelden men katastrofal for hele anlegget.',
    icon: 'V',
    params: { loss_multiplier: 6.50, frequency_multiplier: 0.25 },
  },
  {
    id: 'power_outage_48h',
    label: 'Strømbortfall 48 timer',
    description: 'Nett og aggregat feiler. BI-eksponering hele anlegget.',
    icon: 'S',
    params: { loss_multiplier: 3.20, bi_trigger: true },
  },
]
