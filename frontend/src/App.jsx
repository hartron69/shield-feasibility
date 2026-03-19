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
import { fetchMitigationLibrary, fetchExample, runFeasibility, fetchSmoltExample, runSmoltFeasibility } from './api/client.js'
import { C5AI_MOCK } from './data/c5ai_mock.js'
import { MOCK_ALERTS } from './data/mockAlertsData.js'
import { AGAQUA_EXAMPLE } from './data/agaquaExample.js'
import { OperatorTypeSelector } from './components/InputForm/OperatorTypeSelector.jsx'
import { SmoltTIVPanel } from './components/InputForm/SmoltTIVPanel.jsx'

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
  equity_nok: null,
  operating_cf_nok: null,
  liquidity_nok: null,
  claims_history_years: 0,
  total_claims_paid_nok: 0,
  current_market_premium_nok: null,
}

// ── Navigation items ──────────────────────────────────────────────────────────
// Pages that show the left accordion panel (feasibility inputs)
const FEASIBILITY_PAGES = new Set(['feasibility', 'strategy'])

const NAV_ITEMS = [
  { id: 'overview',   label: 'Overview'               },
  { id: 'inputs',     label: 'Inputs'                 },
  { id: 'c5ai',       label: 'C5AI+ Risk Intelligence'},
  { id: 'alerts',     label: 'Alerts'                 },
  { id: 'feasibility',label: 'PCC Feasibility'        },
  { id: 'strategy',   label: 'Strategy Comparison'    },
  { id: 'learning',   label: 'Learning'               },
  { id: 'reports',    label: 'Reports'                },
]

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
  const [activePage, setActivePage]             = useState('overview')
  const [operatorType, setOperatorType]         = useState('sea')
  const [smoltFacilities, setSmoltFacilities]   = useState([{ ...DEFAULT_SMOLT_FACILITY }])
  const [smoltFinancials, setSmoltFinancials]   = useState({ ...DEFAULT_SMOLT_FINANCIALS })

  useEffect(() => {
    fetchMitigationLibrary().then(setLibrary).catch(() => {})
  }, [])

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
      setActivePage('feasibility')
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
      equity_nok:                AGAQUA_EXAMPLE.equity_nok,
      operating_cf_nok:          AGAQUA_EXAMPLE.operating_cf_nok,
      liquidity_nok:             AGAQUA_EXAMPLE.liquidity_nok,
      claims_history_years:      AGAQUA_EXAMPLE.claims_history_years,
      total_claims_paid_nok:     AGAQUA_EXAMPLE.total_claims_paid_nok,
      current_market_premium_nok: AGAQUA_EXAMPLE.current_market_premium_nok,
    })
    setOperatorType('smolt')
    setActivePage('feasibility')
  }

  function buildSmoltPayload() {
    return {
      operator_name:             smoltFinancials.operator_name || 'Settefisk AS',
      org_number:                smoltFinancials.org_number    || null,
      facilities:                smoltFacilities,
      annual_revenue_nok:        smoltFinancials.annual_revenue_nok        || null,
      equity_nok:                smoltFinancials.equity_nok                || null,
      operating_cf_nok:          smoltFinancials.operating_cf_nok          || null,
      liquidity_nok:             smoltFinancials.liquidity_nok             || null,
      claims_history_years:      smoltFinancials.claims_history_years      || 0,
      total_claims_paid_nok:     smoltFinancials.total_claims_paid_nok     || 0,
      current_market_premium_nok: smoltFinancials.current_market_premium_nok || null,
      model: { n_simulations: model.n_simulations, generate_pdf: model.generate_pdf },
      generate_pdf: model.generate_pdf,
    }
  }

  async function handleRun() {
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
        const payload = {
          operator_profile: operator,
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

  // Determine whether to show the left accordion (only for feasibility-related pages)
  const showLeftPanel = FEASIBILITY_PAGES.has(activePage)

  return (
    <div>
      {/* ── App header ───────────────────────────────────────────────────── */}
      <header className="app-header">
        <div>
          <div className="app-header h1">Shield Risk Platform</div>
          <div className="subtitle">PCC Feasibility &amp; Suitability Tool · C5AI+ v5.0</div>
        </div>
      </header>

      {/* ── Secondary navigation bar ─────────────────────────────────────── */}
      <nav className="main-nav">
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            className={`main-nav-btn ${activePage === item.id ? 'active' : ''}`}
            onClick={() => setActivePage(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

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
                <button
                  className="smolt-apply-btn"
                  style={{ marginTop: 4, width: '100%' }}
                  onClick={handleAgaquaExample}
                >
                  Last Agaqua-eksempel
                </button>
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
                      <OperatorProfile values={operator} onChange={handleOperatorChange} derived={AUTO_FIELDS} />
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
            <RunControls
              onRun={handleRun}
              onExample={handleExample}
              onReset={handleReset}
              loading={loading}
            />
            <StatusBar loading={loading} currentStep={step} error={error} />
          </div>
        )}

        {/* ── Right / main panel ──────────────────────────────────────── */}
        <div className="right-panel">
          {activePage === 'overview' && (
            <OverviewPage onNavigate={setActivePage} />
          )}
          {activePage === 'inputs' && (
            <InputsPage />
          )}
          {activePage === 'c5ai' && (
            <C5AIModule
              c5aiData={C5AI_MOCK}
              feasibilityResult={result}
              operator={operator}
            />
          )}
          {activePage === 'alerts' && (
            <AlertsPage alertsData={MOCK_ALERTS} />
          )}
          {activePage === 'feasibility' && (
            <ResultPanel
              result={result}
              selectedMitigations={selectedMitigations}
              library={library}
              operatorType={operatorType}
              smoltFacilities={smoltFacilities}
            />
          )}
          {activePage === 'strategy' && (
            <StrategyComparisonPage result={result} />
          )}
          {activePage === 'learning' && (
            <LearningPage />
          )}
          {activePage === 'reports' && (
            <ReportsPage />
          )}
        </div>
      </div>
    </div>
  )
}
