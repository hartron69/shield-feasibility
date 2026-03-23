import React from 'react'

const DOMAIN_GROUPS_SEA = {
  Structural: ['stronger_nets', 'stronger_anchors', 'stronger_moorings', 'deformation_monitoring'],
  Environmental: ['environmental_sensors', 'storm_contingency_plan'],
  Biological: ['lice_barriers', 'jellyfish_mitigation'],
  Operational: ['staff_training_program', 'risk_manager_hire', 'emergency_response_plan'],
  'AI-Integrated': ['ai_early_warning'],
}

// Smolt/RAS: 12 RAS-spesifikke tiltak
const DOMAIN_GROUPS_SMOLT = {
  'RAS-Teknisk':  ['smolt_oxygen_backup', 'smolt_backup_power', 'smolt_alarm_system'],
  Vannkvalitet:   ['smolt_temperature_control', 'smolt_co2_stripping', 'smolt_ph_dosing'],
  Biologisk:      ['smolt_biofilter_monitoring', 'smolt_uv_sterilization', 'smolt_fish_health_program', 'smolt_biosecurity'],
  Operasjonell:   ['smolt_staff_training', 'smolt_emergency_plan'],
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

const NO_NAMES = {
  // Sea mitigations
  stronger_nets:              'Sterkere nøter',
  stronger_anchors:           'Forsterket ankring',
  stronger_moorings:          'Fortøyningssystem',
  lice_barriers:              'Lusebeskyttelse',
  jellyfish_mitigation:       'Manettbarrierer',
  environmental_sensors:      'Miljøsensorer (O₂/temp)',
  storm_contingency_plan:     'Stormberedskap',
  staff_training_program:     'Personalkompetanse',
  deformation_monitoring:     'Deformasjonsovervåkning',
  ai_early_warning:           'AI-tidligvarsel',
  risk_manager_hire:          'Risikoleder',
  emergency_response_plan:    'Beredskapsplan',
  // Smolt / RAS mitigations
  smolt_oxygen_backup:        'O₂-backup (RAS)',
  smolt_temperature_control:  'Temperaturkontroll',
  smolt_co2_stripping:        'CO₂-stripping',
  smolt_ph_dosing:            'pH-dosering',
  smolt_biofilter_monitoring: 'Biofilterovervåkning',
  smolt_uv_sterilization:     'UV-sterilisering',
  smolt_backup_power:         'Nødstrøm / UPS',
  smolt_fish_health_program:  'Fiskehelseprogram',
  smolt_biosecurity:          'Biosikkerhet',
  smolt_alarm_system:         'Alarmsystem (sanntid)',
  smolt_staff_training:       'RAS-opplæring',
  smolt_emergency_plan:       'RAS-beredskapsplan',
}

function formatNOK(v) {
  if (v >= 1_000_000) return `NOK ${(v / 1_000_000).toFixed(1)}M/år`
  if (v >= 1_000) return `NOK ${(v / 1_000).toFixed(0)}k/år`
  return `NOK ${v}/år`
}

export default function MitigationPanel({ library, selected, onToggle, operatorType }) {
  const libMap = Object.fromEntries((library || []).map((a) => [a.id, a]))
  const DOMAIN_GROUPS = operatorType === 'smolt' ? DOMAIN_GROUPS_SMOLT : DOMAIN_GROUPS_SEA

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
                    <div className="mit-card-name">{NO_NAMES[id] || action.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</div>
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
