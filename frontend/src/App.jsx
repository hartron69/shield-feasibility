import React, { useState, useEffect } from 'react'
import OperatorProfile from './components/InputForm/OperatorProfile.jsx'
import ModelSettings from './components/InputForm/ModelSettings.jsx'
import StrategySettings from './components/InputForm/StrategySettings.jsx'
import MitigationPanel from './components/InputForm/MitigationPanel.jsx'
import PoolingSettings from './components/InputForm/PoolingSettings.jsx'
import RunControls from './components/RunControls.jsx'
import StatusBar from './components/StatusBar.jsx'
import ResultPanel from './components/results/ResultPanel.jsx'
import C5AIModule from './components/c5ai/C5AIModule.jsx'
import AlertsPage from './components/alerts/AlertsPage.jsx'
import InputsPage from './components/inputs/InputsPage.jsx'
import OverviewPage from './components/OverviewPage.jsx'
import StrategyComparisonPage from './components/StrategyComparisonPage.jsx'
import LearningPage from './components/LearningPage.jsx'
import ReportsPage from './components/ReportsPage.jsx'
import DashboardPage from './components/DashboardPage.jsx'
import LiveRiskFeedPage from './components/live_risk/LiveRiskFeedPage.jsx'
import LocalityLiveRiskPage from './components/live_risk/LocalityLiveRiskPage.jsx'
import { fetchMitigationLibrary, fetchExample, runFeasibility, fetchSmoltExample, runSmoltFeasibility, runC5AI, fetchC5AIStatus, notifyInputsUpdated, fetchC5AIRiskOverview } from './api/client.js'
import C5AIStatusBar from './components/C5AIStatusBar.jsx'
import { C5AI_MOCK } from './data/c5ai_mock.js'
import { MOCK_ALERTS } from './data/mockAlertsData.js'
import { AGAQUA_EXAMPLE } from './data/agaquaExample.js'
import { OperatorTypeSelector } from './components/InputForm/OperatorTypeSelector.jsx'
import { SmoltTIVPanel } from './components/InputForm/SmoltTIVPanel.jsx'
import ConfirmStaleC5AIModal from './components/ConfirmStaleC5AIModal.jsx'

// ── Derivation constants (calibrated against Nordic Aqua example) ────────────
const REVENUE_MULTIPLIER = 1.35
const PREMIUM_RATE = 0.0217

function deriveRevenue(biomass, valuePerTonne) {
  return Math.round(biomass * valuePerTonne * REVENUE_MULTIPLIER)
}
function derivePremium(revenue) {
  return Math.round(revenue * PREMIUM_RATE)
}

// ── Biomass valuation suggestion formula ─────────────────────────────────────
const REF_PRICE_DEFAULT = 80
const REALISATION_DEFAULT = 0.90
const HAIRCUT_DEFAULT = 0.10

export function computeSuggestedBiomassValue(refPricePerKg, realisation, haircut) {
  return Math.round(refPricePerKg * 1000 * realisation * (1 - haircut))
}

const DEFAULT_BIOMASS_VALUE = computeSuggestedBiomassValue(
  REF_PRICE_DEFAULT, REALISATION_DEFAULT, HAIRCUT_DEFAULT
)

const AUTO_FIELDS = new Set(['annual_revenue_nok', 'annual_premium_nok'])

const DEFAULT_OPERATOR = {
  name: '',
  country: 'Norge',
  n_sites: 3,
  total_biomass_tonnes: 9200,
  reference_price_per_kg: REF_PRICE_DEFAULT,
  realisation_factor: REALISATION_DEFAULT,
  prudence_haircut: HAIRCUT_DEFAULT,
  biomass_value_per_tonne_override: null,
  biomass_value_per_tonne: DEFAULT_BIOMASS_VALUE,
  annual_revenue_nok: deriveRevenue(9200, DEFAULT_BIOMASS_VALUE),
  annual_premium_nok: derivePremium(deriveRevenue(9200, DEFAULT_BIOMASS_VALUE)),
}
const DEFAULT_MODEL    = { n_simulations: 5000, domain_correlation: 'expert_default', generate_pdf: true, use_history_calibration: false }
const DEFAULT_STRATEGY = { strategy: 'pcc_captive', retention_nok: null }
const DEFAULT_POOLING  = {
  enabled: false,
  n_members: 4,
  inter_member_correlation: 0.25,
  similarity_spread: 0.15,
  pooled_retention_nok: 25_000_000,
  pooled_ri_limit_nok: 400_000_000,
  pooled_ri_loading_factor: 1.40,
  shared_admin_saving_pct: 0.20,
  allocation_basis: 'expected_loss',
}

const ACCORDION_SECTIONS = ['Operator', 'Model', 'Strategy', 'Mitigation', 'Pooling']

const DEFAULT_SMOLT_FACILITY = {
  facility_name: '',
  facility_type: 'smolt_ras',
  building_components: [{ name: '', area_sqm: 0, value_per_sqm_nok: 27000 }],
  site_clearance_nok: 0,
  machinery_nok: 0,
  avg_biomass_insured_value_nok: 0,
  bi_sum_insured_nok: 0,
  bi_indemnity_months: 24,
  municipality: '',
}

const DEFAULT_SMOLT_FINANCIALS = {
  operator_name: '',
  org_number: '',
  annual_revenue_nok: null,
  ebitda_nok: null,
  equity_nok: null,
  operating_cf_nok: null,
  liquidity_nok: null,
  claims_history_years: 0,
  total_claims_paid_nok: 0,
  current_market_premium_nok: null,
}

// ── Navigation structure ──────────────────────────────────────────────────────
const L1_NAV = [
  { id: 'dashboard',    label: 'Dashboard'            },
  { id: 'risk',         label: 'Risk Intelligence'    },
  { id: 'live_risk',    label: 'Live Risk'             },
  { id: 'feasibility',  label: 'PCC Feasibility'      },
]

const L2_RISK_NAV = [
  { id: 'oversikt',  label: 'Oversikt'  },
  { id: 'maaling',   label: 'Målinger'  },
  { id: 'risiko',    label: 'Risiko'    },
  { id: 'varsler',   label: 'Varsler'   },
  { id: 'laering',   label: 'Læring'    },
]

const L2_FEASIBILITY_NAV = [
  { id: 'oversikt',     label: 'Oversikt'     },
  { id: 'tapsanalyse',  label: 'Tapsanalyse'  },
  { id: 'tiltak',       label: 'Tiltak'       },
  { id: 'strategi',     label: 'Strategi'     },
  { id: 'rapporter',    label: 'Rapporter'    },
]

// Maps feasibility sub-tab → ResultPanel internal tab name
const FEASIBILITY_TO_RESULT_TAB = {
  oversikt:    'Summary',
  tapsanalyse: 'Tapsanalyse',
  tiltak:      'Mitigation',
}

// Legacy page IDs (from OverviewPage.onNavigate calls) → new section/tab
const LEGACY_PAGE_MAP = {
  alerts:      ['risk',        'varsler'    ],
  c5ai:        ['risk',        'risiko'     ],
  inputs:      ['risk',        'maaling'    ],
  overview:    ['risk',        'oversikt'   ],
  feasibility: ['feasibility', 'oversikt'   ],
  strategy:    ['feasibility', 'strategi'   ],
  learning:    ['risk',        'laering'    ],
  reports:     ['feasibility', 'rapporter'  ],
}

export default function App() {
  const [operator, setOperator]                 = useState(DEFAULT_OPERATOR)
  const [model, setModel]                       = useState(DEFAULT_MODEL)
  const [strategy, setStrategy]                 = useState(DEFAULT_STRATEGY)
  const [selectedMitigations, setSelectedMitigations] = useState([])
  const [library, setLibrary]                   = useState([])
  const [open, setOpen]                         = useState({ Operator: true, Model: false, Strategy: false, Mitigation: false, Pooling: false })
  const [pooling, setPooling]                   = useState(DEFAULT_POOLING)
  const [loading, setLoading]                   = useState(false)
  const [step, setStep]                         = useState(0)
  const [error, setError]                       = useState(null)
  const [result, setResult]                     = useState(null)
  const [activeMainSection, setActiveMainSection] = useState('dashboard')
  const [activeRiskTab, setActiveRiskTab]         = useState('oversikt')
  const [activeFeasibilityTab, setActiveFeasibilityTab] = useState('oversikt')
  const [operatorType, setOperatorType]         = useState('sea')
  const [smoltFacilities, setSmoltFacilities]   = useState([{ ...DEFAULT_SMOLT_FACILITY }])
  const [smoltFinancials, setSmoltFinancials]   = useState({ ...DEFAULT_SMOLT_FINANCIALS })
  const [c5aiStatus, setC5aiStatus]             = useState(null)
  const [c5aiLoading, setC5aiLoading]           = useState(false)
  const [c5aiRiskData, setC5aiRiskData]         = useState(null)
  const [showStaleModal, setShowStaleModal]     = useState(false)
  const [siteSelectionMode, setSiteSelectionMode] = useState('generic')
  const [selectedSites, setSelectedSites]       = useState([])
  const [liveRiskLocalityId, setLiveRiskLocalityId] = useState(null)

  useEffect(() => {
    const ft = operatorType === 'smolt' ? 'smolt' : 'sea'
    fetchMitigationLibrary(ft).then(setLibrary).catch(() => {})
  }, [operatorType])

  useEffect(() => {
    fetchC5AIStatus().then(setC5aiStatus).catch(() => {})
    fetchC5AIRiskOverview().then(setC5aiRiskData).catch(() => {})
  }, [])

  function refreshC5AIRiskOverview() {
    // Re-run C5AI+ pipeline with latest Live Risk feed data, then refresh scores
    runC5AI().catch(() => {}).finally(() => {
      fetchC5AIRiskOverview().then(setC5aiRiskData).catch(() => {})
    })
  }

  async function handleC5AIRun() {
    setC5aiLoading(true)
    try {
      await runC5AI()
      const s = await fetchC5AIStatus()
      setC5aiStatus(s)
    } catch {
      // best-effort — status may still update
      fetchC5AIStatus().then(setC5aiStatus).catch(() => {})
    } finally {
      setC5aiLoading(false)
    }
  }

  // Central navigation — accepts (section, tab) or legacy single-string page ID
  function navigateTo(sectionOrLegacy, tab) {
    if (tab === undefined && LEGACY_PAGE_MAP[sectionOrLegacy]) {
      const [sec, t] = LEGACY_PAGE_MAP[sectionOrLegacy]
      setActiveMainSection(sec)
      if (sec === 'risk') setActiveRiskTab(t)
      else if (sec === 'feasibility') setActiveFeasibilityTab(t)
      return
    }
    setActiveMainSection(sectionOrLegacy)
    if (sectionOrLegacy === 'risk') setActiveRiskTab(tab || 'oversikt')
    else if (sectionOrLegacy === 'feasibility') setActiveFeasibilityTab(tab || 'oversikt')
  }

  function handleOperatorChange(next) {
    const prev = operator

    const valuationParamsChanged =
      next.reference_price_per_kg !== prev.reference_price_per_kg ||
      next.realisation_factor !== prev.realisation_factor ||
      next.prudence_haircut !== prev.prudence_haircut

    if (valuationParamsChanged && next.biomass_value_per_tonne_override === null) {
      const suggested = computeSuggestedBiomassValue(
        next.reference_price_per_kg, next.realisation_factor, next.prudence_haircut
      )
      next = { ...next, biomass_value_per_tonne: suggested }
    }

    const biomassChanged =
      next.total_biomass_tonnes !== prev.total_biomass_tonnes ||
      next.biomass_value_per_tonne !== prev.biomass_value_per_tonne

    if (biomassChanged) {
      const revenue = deriveRevenue(next.total_biomass_tonnes, next.biomass_value_per_tonne)
      setOperator({ ...next, annual_revenue_nok: revenue, annual_premium_nok: derivePremium(revenue) })
      return
    }

    if (next.annual_revenue_nok !== prev.annual_revenue_nok) {
      setOperator({ ...next, annual_premium_nok: derivePremium(next.annual_revenue_nok) })
      return
    }

    setOperator(next)
  }

  function toggleSection(name) {
    setOpen((prev) => ({ ...prev, [name]: !prev[name] }))
  }

  function toggleMitigation(id) {
    setSelectedMitigations((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  async function handleExample() {
    try {
      const ex = await fetchExample()
      if (ex.operator_profile) {
        const merged = { ...DEFAULT_OPERATOR, ...ex.operator_profile }
        if (merged.biomass_value_per_tonne_override == null) {
          const suggested = computeSuggestedBiomassValue(
            merged.reference_price_per_kg, merged.realisation_factor, merged.prudence_haircut
          )
          if (Math.abs(merged.biomass_value_per_tonne - suggested) > 1) {
            merged.biomass_value_per_tonne_override = merged.biomass_value_per_tonne
          }
        }
        setOperator(merged)
      }
      if (ex.model_settings) setModel(ex.model_settings)
      if (ex.strategy_settings) setStrategy(ex.strategy_settings)
      if (ex.mitigation?.selected_actions) setSelectedMitigations(ex.mitigation.selected_actions)
      setOpen({ Operator: true, Model: false, Strategy: false, Mitigation: true })
      navigateTo('feasibility', 'oversikt')
      notifyInputsUpdated().then(() => fetchC5AIStatus().then(setC5aiStatus).catch(() => {})).catch(() => {})
    } catch (e) {
      setError(`Failed to load example: ${e.message}`)
    }
  }

  function handleReset() {
    setOperator(DEFAULT_OPERATOR)
    setModel(DEFAULT_MODEL)
    setStrategy(DEFAULT_STRATEGY)
    setPooling(DEFAULT_POOLING)
    setSelectedMitigations([])
    setSmoltFacilities([{ ...DEFAULT_SMOLT_FACILITY }])
    setSmoltFinancials({ ...DEFAULT_SMOLT_FINANCIALS })
    setSiteSelectionMode('generic')
    setSelectedSites([])
    setResult(null)
    setError(null)
    setStep(0)
  }

  async function handleAgaquaExample() {
    setSmoltFacilities(AGAQUA_EXAMPLE.facilities.map(f => ({ ...f })))
    setSmoltFinancials({
      operator_name:             AGAQUA_EXAMPLE.operator_name,
      org_number:                AGAQUA_EXAMPLE.org_number,
      annual_revenue_nok:        AGAQUA_EXAMPLE.annual_revenue_nok,
      ebitda_nok:                AGAQUA_EXAMPLE.ebitda_nok,
      equity_nok:                AGAQUA_EXAMPLE.equity_nok,
      operating_cf_nok:          AGAQUA_EXAMPLE.operating_cf_nok,
      liquidity_nok:             AGAQUA_EXAMPLE.liquidity_nok,
      claims_history_years:      AGAQUA_EXAMPLE.claims_history_years,
      total_claims_paid_nok:     AGAQUA_EXAMPLE.total_claims_paid_nok,
      current_market_premium_nok: AGAQUA_EXAMPLE.current_market_premium_nok,
    })
    setOperatorType('smolt')
    navigateTo('feasibility', 'oversikt')
    notifyInputsUpdated().then(() => fetchC5AIStatus().then(setC5aiStatus).catch(() => {})).catch(() => {})
  }

  function buildSmoltPayload() {
    return {
      operator_name:             smoltFinancials.operator_name || 'Settefisk AS',
      org_number:                smoltFinancials.org_number    || null,
      facilities:                smoltFacilities,
      annual_revenue_nok:        smoltFinancials.annual_revenue_nok        || null,
      ebitda_nok:                smoltFinancials.ebitda_nok                || null,
      equity_nok:                smoltFinancials.equity_nok                || null,
      operating_cf_nok:          smoltFinancials.operating_cf_nok          || null,
      liquidity_nok:             smoltFinancials.liquidity_nok             || null,
      claims_history_years:      smoltFinancials.claims_history_years      || 0,
      total_claims_paid_nok:     smoltFinancials.total_claims_paid_nok     || 0,
      current_market_premium_nok: smoltFinancials.current_market_premium_nok || null,
      model: {
        n_simulations:          model.n_simulations,
        generate_pdf:           model.generate_pdf,
        domain_correlation:     model.domain_correlation,
        use_history_calibration: model.use_history_calibration,
      },
      generate_pdf: model.generate_pdf,
      mitigation: { selected_actions: selectedMitigations },
    }
  }

  function handleRun() {
    const freshness = c5aiStatus?.freshness
    if (freshness === 'missing' || freshness === 'stale') {
      setShowStaleModal(true)
      return
    }
    _doRun()
  }

  async function _doRun() {
    setLoading(true)
    setError(null)
    setResult(null)
    setStep(1)

    const stepInterval = setInterval(() => {
      setStep((s) => Math.min(s + 1, 5))
    }, 800)

    try {
      let res
      if (operatorType === 'smolt') {
        res = await runSmoltFeasibility(buildSmoltPayload())
      } else {
        // Build operator_profile with site-selection fields
        const isSpecific = siteSelectionMode === 'specific' && selectedSites.length > 0
        const operatorProfile = {
          ...operator,
          site_selection_mode: isSpecific ? 'specific' : 'generic',
          selected_sites: isSpecific
            ? selectedSites.map(s => ({
                site_id:            s.site_id,
                locality_no:        s.locality_no ?? null,
                site_name:          s.site_name,
                biomass_tonnes:     parseFloat(s.biomass_tonnes) || 3000,
                biomass_value_nok:  s.biomass_value_manual
                  ? (parseFloat(s.biomass_value_nok) || null)
                  : null,
                fjord_exposure:     s.fjord_exposure || 'semi_exposed',
                lice_pressure_factor: parseFloat(s.lice_pressure_factor) || 1.0,
                hab_risk_factor:    parseFloat(s.hab_risk_factor) || 1.0,
              }))
            : null,
          // In specific mode, n_sites matches actual selected count for risk scaling
          n_sites: isSpecific ? selectedSites.length : operator.n_sites,
        }
        const payload = {
          operator_profile: operatorProfile,
          model_settings: model,
          strategy_settings: strategy,
          mitigation: { selected_actions: selectedMitigations },
          pooling_settings: pooling,
        }
        res = await runFeasibility(payload)
      }
      clearInterval(stepInterval)
      setStep(6)
      setResult(res)
    } catch (e) {
      clearInterval(stepInterval)
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const showLeftPanel = activeMainSection === 'feasibility'

  // Feasibility sub-tabs that render ResultPanel (vs. standalone pages)
  const feasibilityUsesResultPanel = activeFeasibilityTab in FEASIBILITY_TO_RESULT_TAB

  return (
    <div className="app-shell">
      {/* ── App header ───────────────────────────────────────────────────── */}
      <header className="app-header">
        <div>
          <div className="app-header h1">Shield Risk Platform</div>
          <div className="subtitle">PCC Feasibility &amp; Suitability Tool · C5AI+ v5.0</div>
        </div>
      </header>

      {/* ── Level-1 main navigation ───────────────────────────────────────── */}
      <nav className="main-nav">
        {L1_NAV.map(item => (
          <button
            key={item.id}
            className={`main-nav-btn ${activeMainSection === item.id ? 'active' : ''}`}
            onClick={() => { setActiveMainSection(item.id); if (item.id !== 'live_risk') setLiveRiskLocalityId(null) }}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {/* ── Level-2 sub-navigation ───────────────────────────────────────── */}
      {activeMainSection === 'risk' && (
        <nav className="sub-nav">
          {L2_RISK_NAV.map(item => (
            <button
              key={item.id}
              className={`sub-nav-btn ${activeRiskTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveRiskTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      )}
      {activeMainSection === 'feasibility' && (
        <nav className="sub-nav">
          {L2_FEASIBILITY_NAV.map(item => (
            <button
              key={item.id}
              className={`sub-nav-btn ${activeFeasibilityTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveFeasibilityTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      )}

      {/* ── App body ─────────────────────────────────────────────────────── */}
      <div className={`app-body ${showLeftPanel ? '' : 'no-left-panel'}`}>

        {/* ── Left panel (feasibility inputs only) ────────────────────── */}
        {showLeftPanel && (
          <div className="left-panel">
            <OperatorTypeSelector value={operatorType} onChange={setOperatorType} />
            {operatorType === 'smolt' && (
              <div style={{ padding: '8px 12px 4px', borderBottom: '1px solid #e5e7eb' }}>
                <div className="smolt-field-row">
                  <label style={{ fontSize: 12 }}>Operatørnavn</label>
                  <input
                    type="text"
                    value={smoltFinancials.operator_name}
                    onChange={e => setSmoltFinancials(f => ({ ...f, operator_name: e.target.value }))}
                    className="smolt-input"
                    placeholder="Agaqua AS"
                  />
                </div>
                <div className="smolt-field-row">
                  <label style={{ fontSize: 12 }}>Skadefri historikk (år)</label>
                  <input
                    type="number"
                    min="0"
                    max="30"
                    value={smoltFinancials.claims_history_years || ''}
                    onChange={e => setSmoltFinancials(f => ({ ...f, claims_history_years: parseInt(e.target.value) || 0 }))}
                    className="smolt-input"
                    placeholder="0"
                  />
                </div>
                <div className="smolt-field-row">
                  <label style={{ fontSize: 12 }}>Total krav utbetalt (NOK)</label>
                  <input
                    type="number"
                    min="0"
                    value={smoltFinancials.total_claims_paid_nok || ''}
                    onChange={e => setSmoltFinancials(f => ({ ...f, total_claims_paid_nok: parseFloat(e.target.value) || 0 }))}
                    className="smolt-input"
                    placeholder="0"
                  />
                </div>

                {/* Known smolt facilities — same as Risk Intelligence */}
                <div style={{
                  marginTop: 8, padding: '7px 9px',
                  background: '#eff6ff', border: '1px solid #bfdbfe',
                  borderRadius: 5,
                }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#1e40af', marginBottom: 4 }}>
                    Agaqua AS — kjente settefiskanlegg
                  </div>
                  <div style={{ fontSize: 11, color: '#374151', lineHeight: 1.7 }}>
                    Villa Smolt AS (Herøy, RAS)<br />
                    Olden Oppdrettsanlegg AS (Stryn, gjennomstrøm)<br />
                    Setran Settefisk AS (Osen, gjennomstrøm)
                  </div>
                  <button
                    className="smolt-apply-btn"
                    style={{ marginTop: 6, width: '100%', background: '#1e40af', color: '#fff', fontWeight: 700 }}
                    onClick={handleAgaquaExample}
                  >
                    Last inn disse anleggene
                  </button>
                </div>
              </div>
            )}
            {ACCORDION_SECTIONS.map((section) => (
              <div key={section} className="accordion">
                <button className="accordion-header" onClick={() => toggleSection(section)}>
                  {section}
                  <span>{open[section] ? '▲' : '▼'}</span>
                </button>
                {open[section] && (
                  <div className="accordion-body">
                    {section === 'Operator' && operatorType === 'sea' && (
                      <OperatorProfile
                        values={operator}
                        onChange={handleOperatorChange}
                        derived={AUTO_FIELDS}
                        siteSelectionMode={siteSelectionMode}
                        onSiteModeChange={setSiteSelectionMode}
                        selectedSites={selectedSites}
                        onSelectedSitesChange={setSelectedSites}
                      />
                    )}
                    {section === 'Operator' && operatorType === 'smolt' && (
                      <SmoltTIVPanel
                        facilities={smoltFacilities}
                        onChange={setSmoltFacilities}
                        onAddFacility={() => setSmoltFacilities(f => [...f, { ...DEFAULT_SMOLT_FACILITY }])}
                        onRemoveFacility={i => setSmoltFacilities(f => f.filter((_, idx) => idx !== i))}
                      />
                    )}
                    {section === 'Model' && (
                      <ModelSettings values={model} onChange={setModel} />
                    )}
                    {section === 'Strategy' && (
                      <StrategySettings values={strategy} onChange={setStrategy} />
                    )}
                    {section === 'Mitigation' && (
                      <MitigationPanel
                        library={library}
                        selected={selectedMitigations}
                        onToggle={toggleMitigation}
                        operatorType={operatorType}
                      />
                    )}
                    {section === 'Pooling' && (
                      <PoolingSettings values={pooling} onChange={setPooling} />
                    )}
                  </div>
                )}
              </div>
            ))}

            <div style={{ flex: 1 }} />
            <C5AIStatusBar
              status={c5aiStatus}
              loading={c5aiLoading}
              onRun={handleC5AIRun}
            />
            <RunControls
              onRun={handleRun}
              onExample={handleExample}
              onReset={handleReset}
              loading={loading}
              c5aiStatus={c5aiStatus}
            />
            <StatusBar loading={loading} currentStep={step} error={error} />
          </div>
        )}

        {/* ── Right / main panel ──────────────────────────────────────── */}
        <div className="right-panel">

          {/* Dashboard */}
          {activeMainSection === 'dashboard' && (
            <DashboardPage onNavigate={navigateTo} />
          )}

          {/* Risk Intelligence sub-tabs */}
          {activeMainSection === 'risk' && activeRiskTab === 'oversikt' && (
            <OverviewPage onNavigate={navigateTo} />
          )}
          {activeMainSection === 'risk' && activeRiskTab === 'maaling' && (
            <InputsPage operatorType={operatorType} operator={operator} />
          )}
          {activeMainSection === 'risk' && activeRiskTab === 'risiko' && (
            <C5AIModule
              c5aiData={c5aiRiskData
                ? { ...C5AI_MOCK, overall_risk_score: c5aiRiskData.overall_risk_score, sites: c5aiRiskData.sites, domain_breakdown: c5aiRiskData.domain_breakdown }
                : C5AI_MOCK}
              feasibilityResult={result}
              operator={operator}
              onNavigateToLiveRisk={id => {
                setLiveRiskLocalityId(id)
                setActiveMainSection('live_risk')
              }}
            />
          )}
          {activeMainSection === 'risk' && activeRiskTab === 'varsler' && (
            <AlertsPage alertsData={MOCK_ALERTS} />
          )}
          {activeMainSection === 'risk' && activeRiskTab === 'laering' && (
            <LearningPage />
          )}

          {/* Live Risk Intelligence */}
          {activeMainSection === 'live_risk' && !liveRiskLocalityId && (
            <LiveRiskFeedPage
              onSelectLocality={id => setLiveRiskLocalityId(id)}
              onFeedRefreshed={refreshC5AIRiskOverview}
            />
          )}
          {activeMainSection === 'live_risk' && liveRiskLocalityId && (
            <LocalityLiveRiskPage
              localityId={liveRiskLocalityId}
              onBack={() => setLiveRiskLocalityId(null)}
            />
          )}

          {/* PCC Feasibility sub-tabs — ResultPanel */}
          {activeMainSection === 'feasibility' && feasibilityUsesResultPanel && (
            <ResultPanel
              result={result}
              selectedMitigations={selectedMitigations}
              library={library}
              operatorType={operatorType}
              smoltFacilities={smoltFacilities}
              initialTab={FEASIBILITY_TO_RESULT_TAB[activeFeasibilityTab]}
              onNavigate={navigateTo}
            />
          )}

          {/* PCC Feasibility sub-tabs — standalone pages */}
          {activeMainSection === 'feasibility' && activeFeasibilityTab === 'strategi' && (
            <StrategyComparisonPage result={result} />
          )}
          {activeMainSection === 'feasibility' && activeFeasibilityTab === 'rapporter' && (
            <ReportsPage />
          )}
        </div>
      </div>
      {showStaleModal && (
        <ConfirmStaleC5AIModal
          freshness={c5aiStatus?.freshness}
          onUpdateFirst={() => { setShowStaleModal(false); handleC5AIRun() }}
          onRunAnyway={() => { setShowStaleModal(false); _doRun() }}
          onCancel={() => setShowStaleModal(false)}
        />
      )}
    </div>
  )
}
