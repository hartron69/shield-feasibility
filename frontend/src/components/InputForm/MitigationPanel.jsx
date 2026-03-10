import React from 'react'

const DOMAIN_GROUPS = {
  Structural: ['stronger_nets', 'stronger_anchors', 'stronger_moorings', 'deformation_monitoring'],
  Environmental: ['environmental_sensors', 'storm_contingency_plan'],
  Biological: ['lice_barriers', 'jellyfish_mitigation'],
  Operational: ['staff_training_program', 'risk_manager_hire', 'emergency_response_plan'],
  'AI-Integrated': ['ai_early_warning'],
}

const BADGE_CLASS = {
  structural: 'badge-structural',
  biological: 'badge-biological',
  environmental: 'badge-environmental',
  operational: 'badge-operational',
  ai: 'badge-ai',
}

function domainBadgeClass(domain) {
  const key = domain.toLowerCase().split('/')[0]
  return BADGE_CLASS[key] || 'badge-structural'
}

function formatNOK(v) {
  if (v >= 1_000_000) return `NOK ${(v / 1_000_000).toFixed(1)}M/yr`
  if (v >= 1_000) return `NOK ${(v / 1_000).toFixed(0)}k/yr`
  return `NOK ${v}/yr`
}

export default function MitigationPanel({ library, selected, onToggle }) {
  const libMap = Object.fromEntries((library || []).map((a) => [a.id, a]))

  return (
    <div>
      {Object.entries(DOMAIN_GROUPS).map(([group, ids]) => {
        const items = ids.filter((id) => libMap[id])
        if (!items.length) return null
        return (
          <div key={group}>
            <div className="mit-group-label">{group}</div>
            {items.map((id) => {
              const action = libMap[id]
              const isSelected = selected.includes(id)
              return (
                <div
                  key={id}
                  className={`mit-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => onToggle(id)}
                >
                  <div className="mit-card-toggle">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggle(id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                  <div className="mit-card-body">
                    <div className="mit-card-name">{action.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</div>
                    <div className="mit-card-desc">{action.description}</div>
                    <div className="mit-card-meta">
                      {action.affected_domains.slice(0, 2).map((d) => (
                        <span key={d} className={`badge ${domainBadgeClass(d)}`}>{d}</span>
                      ))}
                      <span className="badge badge-cost">{formatNOK(action.annual_cost_nok)}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
