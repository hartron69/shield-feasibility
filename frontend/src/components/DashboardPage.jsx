import React from 'react'
import { C5AI_MOCK } from '../data/c5ai_mock.js'
import { MOCK_ALERTS } from '../data/mockAlertsData.js'

function fmtM(v) { return `NOK ${(v / 1_000_000).toFixed(1)}M` }

export default function DashboardPage({ onNavigate }) {
  const overall = C5AI_MOCK.overall_risk_score
  const critCount = MOCK_ALERTS.filter(a => a.alert_level === 'CRITICAL').length
  const warnCount = MOCK_ALERTS.filter(a => a.alert_level === 'WARNING').length
  const totalAnnualLoss = Object.values(C5AI_MOCK.domain_breakdown)
    .reduce((s, d) => s + d.annual_loss_nok, 0)
  const scoreColor = overall >= 65 ? '#B91C1C' : overall >= 40 ? '#D97706' : '#16A34A'

  return (
    <div className="dashboard-page">

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <div className="dashboard-hero">
        <div className="dashboard-hero-title">Velkommen til Shield Risk Platform</div>
        <div className="dashboard-hero-sub">
          PCC Captive-gjennomførbarhetsanalyse og C5AI+ risikointelligens for norsk havbruk
        </div>
      </div>

      {/* ── KPI summary row ───────────────────────────────────────────────── */}
      <div className="dashboard-kpi-row">
        <div className="dashboard-kpi-card">
          <div className="dashboard-kpi-label">Risikoindeks</div>
          <div className="dashboard-kpi-value" style={{ color: scoreColor }}>
            {overall}<span style={{ fontSize: 14, color: 'var(--dark-grey)', marginLeft: 2 }}>/100</span>
          </div>
        </div>
        <div className="dashboard-kpi-card">
          <div className="dashboard-kpi-label">Kritiske varsler</div>
          <div className="dashboard-kpi-value" style={{ color: critCount > 0 ? '#B91C1C' : '#16A34A' }}>
            {critCount}
          </div>
          <div className="dashboard-kpi-sub">{warnCount} advarsler åpne</div>
        </div>
        <div className="dashboard-kpi-card">
          <div className="dashboard-kpi-label">Forventet tap / år</div>
          <div className="dashboard-kpi-value" style={{ fontSize: 18 }}>{fmtM(totalAnnualLoss)}</div>
          <div className="dashboard-kpi-sub">Alle domener</div>
        </div>
        <div className="dashboard-kpi-card">
          <div className="dashboard-kpi-label">Analyselokaliteter</div>
          <div className="dashboard-kpi-value">{C5AI_MOCK.sites.length}</div>
          <div className="dashboard-kpi-sub">Havbruksanlegg</div>
        </div>
      </div>

      {/* ── Workflow cards ────────────────────────────────────────────────── */}
      <div className="dashboard-workflow-row">
        <button className="dashboard-workflow-card" onClick={() => onNavigate('risk', 'oversikt')}>
          <div className="dashboard-workflow-icon" style={{ background: '#ECFDF5', color: '#059669' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div className="dashboard-workflow-title">C5AI+ Risikointelligens</div>
          <div className="dashboard-workflow-desc">
            Biologiske, strukturelle, miljømessige og operasjonelle risikovarsler basert på historiske data og prediktive modeller.
          </div>
          <div className="dashboard-workflow-cta">Gå til risikooversikt &rarr;</div>
        </button>

        <button className="dashboard-workflow-card" onClick={() => onNavigate('feasibility', 'oversikt')}>
          <div className="dashboard-workflow-icon" style={{ background: '#EFF6FF', color: '#2563EB' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18"/>
              <path d="M9 21V9"/>
            </svg>
          </div>
          <div className="dashboard-workflow-title">PCC Captive-gjennomførbarhetsanalyse</div>
          <div className="dashboard-workflow-desc">
            9-trinns stokastisk analyse av PCC-egnethet, tap, SCR-allokering og kapitalstruktur for norske oppdrettere.
          </div>
          <div className="dashboard-workflow-cta">Start analyse &rarr;</div>
        </button>
      </div>

      {/* ── Quick links ───────────────────────────────────────────────────── */}
      <div className="dashboard-quicklinks">
        <div className="dashboard-quicklinks-label">Hurtiglenker</div>
        <div className="dashboard-quicklinks-list">
          {[
            { label: 'Varsler',      section: 'risk',        tab: 'varsler'      },
            { label: 'Målinger',     section: 'risk',        tab: 'maaling'      },
            { label: 'Tapsanalyse',  section: 'feasibility', tab: 'tapsanalyse'  },
            { label: 'Tiltak',       section: 'feasibility', tab: 'tiltak'       },
            { label: 'Strategi',     section: 'feasibility', tab: 'strategi'     },
            { label: 'Rapporter',    section: 'feasibility', tab: 'rapporter'    },
            { label: 'Læring',       section: 'risk',        tab: 'laering'      },
          ].map(({ label, section, tab }) => (
            <button
              key={label}
              className="dashboard-quicklink-btn"
              onClick={() => onNavigate(section, tab)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
