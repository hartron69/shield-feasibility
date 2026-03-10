import React from 'react'
import AlertLevelBadge from './AlertLevelBadge.jsx'
import ProbabilityShiftBadge from './ProbabilityShiftBadge.jsx'

const RISK_TYPE_DOMAIN = {
  hab: 'biological', lice: 'biological', jellyfish: 'biological', pathogen: 'biological',
  mooring_failure: 'structural', net_integrity: 'structural', cage_structural: 'structural',
  deformation: 'structural', anchor_deterioration: 'structural',
  oxygen_stress: 'environmental', temperature_extreme: 'environmental',
  current_storm: 'environmental', ice: 'environmental', exposure_anomaly: 'environmental',
  human_error: 'operational', procedure_failure: 'operational',
  equipment_failure: 'operational', incident: 'operational', maintenance_backlog: 'operational',
}

export default function AlertDetailPanel({ alert, onClose }) {
  if (!alert) return null
  const domain = alert.domain || RISK_TYPE_DOMAIN[alert.risk_type] || 'biological'

  return (
    <div className="alert-detail-panel">
      <div className="alert-detail-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <AlertLevelBadge level={alert.alert_level} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>
            {alert.risk_type.toUpperCase()} — {alert.site_id}
          </span>
          <span className={`domain-badge domain-badge-${domain}`}>
            {domain.charAt(0).toUpperCase() + domain.slice(1)}
          </span>
          {alert.board_visibility && (
            <span className="board-flag">Board</span>
          )}
        </div>
        {onClose && (
          <button className="alert-detail-close" onClick={onClose}>✕</button>
        )}
      </div>

      {/* ── Probability ────────────────────────────────────────────────────── */}
      <div className="alert-detail-section">
        <div className="alert-detail-section-title">Probability</div>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginTop: 6 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Current</div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>
              {(alert.current_probability * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Previous</div>
            <div style={{ fontWeight: 600 }}>
              {(alert.previous_probability * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Shift</div>
            <ProbabilityShiftBadge delta={alert.probability_delta} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Alert Type</div>
            <div style={{ textTransform: 'capitalize', fontWeight: 600 }}>
              {alert.alert_type.replace('_', ' ')}
            </div>
          </div>
        </div>
      </div>

      {/* ── Explanation ─────────────────────────────────────────────────────── */}
      <div className="alert-detail-section">
        <div className="alert-detail-section-title">Explanation</div>
        <p style={{ marginTop: 6, lineHeight: 1.6, color: 'var(--navy)' }}>
          {alert.explanation_text}
        </p>
      </div>

      {/* ── Top Drivers ─────────────────────────────────────────────────────── */}
      {alert.top_drivers && alert.top_drivers.length > 0 && (
        <div className="alert-detail-section">
          <div className="alert-detail-section-title">Top Drivers</div>
          <ul className="alert-detail-list">
            {alert.top_drivers.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Triggered Rules ──────────────────────────────────────────────────── */}
      {alert.triggered_rules && alert.triggered_rules.length > 0 && (
        <div className="alert-detail-section">
          <div className="alert-detail-section-title">Triggered Rules</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
            {alert.triggered_rules.map(r => (
              <span key={r} className="rule-tag">{r}</span>
            ))}
          </div>
        </div>
      )}

      {/* ── Recommended Actions ──────────────────────────────────────────────── */}
      {alert.recommended_actions && alert.recommended_actions.length > 0 && (
        <div className="alert-detail-section">
          <div className="alert-detail-section-title">Recommended Actions</div>
          <ol className="alert-detail-list alert-detail-ol">
            {alert.recommended_actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        </div>
      )}

      {/* ── Workflow ─────────────────────────────────────────────────────────── */}
      <div className="alert-detail-section">
        <div className="alert-detail-section-title">Workflow</div>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginTop: 6 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Status</div>
            <span className={`workflow-badge workflow-${alert.workflow_status}`}>
              {alert.workflow_status}
            </span>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Owner Role</div>
            <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>
              {alert.owner_role.replace('_', ' ')}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--dark-grey)' }}>Board Visibility</div>
            <div style={{ fontWeight: 600 }}>{alert.board_visibility ? 'Yes' : 'No'}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
