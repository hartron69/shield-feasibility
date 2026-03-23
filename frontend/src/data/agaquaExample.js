/**
 * Agaqua AS / Settefisk 1-gruppen — fullstendig demo-eksempel.
 * Tilgjengelig via "Last Agaqua-eksempel"-knapp i GUI.
 * Kilde: Agaqua AS faktiske 2024-tall.
 */
export const AGAQUA_EXAMPLE = {
  operator_name: 'Agaqua AS',
  org_number: '930529591',
  facilities: [
    {
      facility_name: 'Villa Smolt AS',
      facility_type: 'smolt_ras',
      building_components: [
        { name: 'Hall over fish tanks', area_sqm: 1370, value_per_sqm_nok: 27000 },
        { name: 'RAS 1-2',              area_sqm: 530,  value_per_sqm_nok: 27000 },
        { name: 'RAS 3-4',              area_sqm: 610,  value_per_sqm_nok: 27000 },
        { name: 'Gamledelen',           area_sqm: 1393, value_per_sqm_nok: 27000 },
        { name: 'Forlager',             area_sqm: 275,  value_per_sqm_nok: 27000 },
      ],
      site_clearance_nok:            20_000_000,
      machinery_nok:                200_000_000,
      avg_biomass_insured_value_nok: 39_680_409,
      bi_sum_insured_nok:           243_200_000,
      bi_indemnity_months: 24,
      municipality: 'Herøy',
    },
    {
      facility_name: 'Olden Oppdrettsanlegg AS',
      facility_type: 'smolt_flow',
      building_components: [
        { name: 'Påvekstavdeling',        area_sqm: 2204, value_per_sqm_nok: 27000 },
        { name: 'Yngel',                  area_sqm: 899,  value_per_sqm_nok: 27000 },
        { name: 'Klekkeri/startforing',   area_sqm: 221,  value_per_sqm_nok: 27000 },
        { name: 'Teknisk/vannbehandling', area_sqm: 77,   value_per_sqm_nok: 27000 },
      ],
      site_clearance_nok:            20_000_000,
      machinery_nok:                120_000_000,
      avg_biomass_insured_value_nok: 18_260_208,
      bi_sum_insured_nok:           102_000_000,
      bi_indemnity_months: 24,
      municipality: 'Ørland',
    },
    {
      facility_name: 'Setran Settefisk AS',
      facility_type: 'smolt_flow',
      building_components: [
        { name: 'Hall A',         area_sqm: 280,  value_per_sqm_nok: 27000 },
        { name: 'Vannbehandling', area_sqm: 170,  value_per_sqm_nok: 27000 },
        { name: 'Hall B',         area_sqm: 715,  value_per_sqm_nok: 27000 },
        { name: 'Hall C',         area_sqm: 979,  value_per_sqm_nok: 27000 },
      ],
      site_clearance_nok:            15_000_000,
      machinery_nok:                 45_000_000,
      avg_biomass_insured_value_nok: 13_287_917,
      bi_sum_insured_nok:            85_100_000,
      bi_indemnity_months: 24,
      municipality: 'Osen',
    },
  ],
  annual_revenue_nok:    232_248_232,
  ebitda_nok:             70_116_262,
  equity_nok:             39_978_809,
  operating_cf_nok:       46_510_739,
  liquidity_nok:          55_454_950,
  claims_history_years:   10,
  total_claims_paid_nok:  0,
  current_market_premium_nok: null,
}
