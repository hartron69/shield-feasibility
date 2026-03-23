import React, { useState } from 'react'
import {
  SMOLT_SITE_RISK,
  SMOLT_SITE_RISK_SUMMARY,
  SMOLT_DOMAIN_META,
} from '../../data/mockSmoltSiteRiskData.js'
import TopRiskSitesTable from './TopRiskSitesTable.jsx'
import SiteRiskSummaryCards from './SiteRiskSummaryCards.jsx'
import SiteEALChart from './SiteEALChart.jsx'
import SiteSCRContributionChart from './SiteSCRContributionChart.jsx'
import SiteRiskDetailPanel from './SiteRiskDetailPanel.jsx'

function fmtM(v) {
  return `NOK ${(v / 1_000_000).toFixed(1)}M`
}

export default function SmoltSiteRiskTab() {
  const [selectedId, setSelectedId] = useState(null)
  const [view, setView] = useState('table') // 'table' | 'charts'

  const sites = SMOLT_SITE_RISK
  const summary = SMOLT_SITE_RISK_SUMMARY
  const selectedSite = sites.find(s => s.site_id === selectedId) || null

  const critCount  = sites.filter(s => s.alert_level === 'CRITICAL').length
  const warnCount  = sites.filter(s => s.alert_level === 'WARNING').length
  const totalAlerts = sites.reduce((acc, s) => acc + s.alerts_open, 0)

  return (
    <div>
      {/* ── Section header ────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>Anlegg — Settefisk / RAS</div>
          <div style={{ fontSize: 12, color: 'var(--dark-grey)' }}>
            {summary.operator_name} · {summary.n_sites} anlegg ({summary.n_ras} RAS, {summary.n_flow_through} gjennomstrøm)
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className={`tab-btn ${view === 'table' ? 'active' : ''}`}
            style={{ fontSize: 11, padding: '4px 10px' }}
            onClick={() => setView('table')}
          >
            Tabell
          </button>
          <button
            className={`tab-btn ${view === 'charts' ? 'active' : ''}`}
            style={{ fontSize: 11, padding: '4px 10px' }}
            onClick={() => setView('charts')}
          >
            Grafer
          </button>
        </div>
      </div>

      {/* ── Portfolio summary KPIs ─────────────────────────────────────── */}
      <div className="kpi-grid" style={{ marginBottom: 16 }}>
        <div className="kpi-card">
          <div className="kpi-label">Total EAL</div>
          <div className="kpi-value" style={{ fontSize: 16 }}>{fmtM(summary.total_eal_nok)}</div>
          <div className="kpi-sub">Forventet årstap, alle anlegg</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total SCR</div>
          <div className="kpi-value" style={{ fontSize: 16 }}>{fmtM(summary.total_scr_nok)}</div>
          <div className="kpi-sub">Solvensbehov netto</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Kritiske anlegg</div>
          <div className="kpi-value" style={{ fontSize: 16, color: critCount > 0 ? '#DC2626' : '#059669' }}>
            {critCount}
          </div>
          <div className="kpi-sub">{warnCount} med advarsel</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Åpne varsler</div>
          <div className="kpi-value" style={{ fontSize: 16, color: totalAlerts > 0 ? '#D97706' : '#059669' }}>
            {totalAlerts}
          </div>
          <div className="kpi-sub">Alle anlegg samlet</div>
        </div>
      </div>

      {/* ── Top 3 summary cards ───────────────────────────────────────── */}
      <div className="card">
        <div className="section-title" style={{ marginBottom: 10 }}>Topp 3 risikoeksponerte anlegg</div>
        <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 12 }}>
          Rangert etter total risikoscore. Klikk et kort for å se detaljer.
        </div>
        <SiteRiskSummaryCards
          sites={sites}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        {selectedSite && (
          <div style={{ marginTop: 16 }}>
            <SiteRiskDetailPanel
              site={selectedSite}
              onClose={() => setSelectedId(null)}
            />
          </div>
        )}
      </div>

      {/* ── Table or charts ───────────────────────────────────────────── */}
      {view === 'table' && (
        <div className="card">
          <div className="section-title" style={{ marginBottom: 10 }}>Alle anlegg — fullstendig rangering</div>
          <div style={{ fontSize: 12, color: 'var(--dark-grey)', marginBottom: 10 }}>
            Klikk en rad for å se detaljert risikoprofil. Sortert etter risikoscore.
          </div>
          <div style={{ overflowX: 'auto' }}>
            <TopRiskSitesTable
              sites={sites}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
          {selectedSite && (
            <div style={{ marginTop: 16 }}>
              <SiteRiskDetailPanel
                site={selectedSite}
                onClose={() => setSelectedId(null)}
              />
            </div>
          )}
        </div>
      )}

      {view === 'charts' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="card">
            <SiteEALChart sites={sites} />
          </div>
          <div className="card">
            <SiteSCRContributionChart sites={sites} />
          </div>
        </div>
      )}

      {/* ── Domain legend ─────────────────────────────────────────────── */}
      <div className="card" style={{ padding: '10px 16px' }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--dark-grey)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
          Risikodomener — settefisk/RAS
        </div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {Object.entries(SMOLT_DOMAIN_META).map(([key, meta]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: meta.color, display: 'inline-block' }} />
              <span style={{ fontSize: 11, color: 'var(--dark-grey)' }}>{meta.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
