import React from 'react'

// Panel showing data source health status and metadata per source

const STATUS_CONFIG = {
  ok:       { bg: '#e8f5e9', color: '#2e7d32', label: 'OK' },
  delayed:  { bg: '#fff8e1', color: '#f57f17', label: 'Forsinket' },
  failed:   { bg: '#fdecea', color: '#c62828', label: 'Feil' },
  no_data:  { bg: '#f3f4f6', color: '#6b7280', label: 'Ingen data' },
}

const HEALTH_SUMMARY_CONFIG = {
  ok:       { bg: '#e8f5e9', color: '#2e7d32', label: 'Alle kilder OK' },
  degraded: { bg: '#fff8e1', color: '#f57f17', label: 'Delvis degradert' },
  critical: { bg: '#fdecea', color: '#c62828', label: 'Kritisk feil' },
}

function formatTimestamp(isoStr) {
  if (!isoStr) return '—'
  const d = new Date(isoStr)
  return d.toLocaleString('nb-NO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function StatusChip({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.no_data
  return (
    <span style={{
      background: cfg.bg,
      color: cfg.color,
      border: `1px solid ${cfg.color}33`,
      borderRadius: 10,
      padding: '2px 8px',
      fontSize: 11,
      fontWeight: 600,
    }}>
      {cfg.label}
    </span>
  )
}

function ContributesMark({ contributes }) {
  return contributes
    ? <span style={{ color: '#2e7d32', fontSize: 16 }} title="Bidrar til risikoscore">&#10003;</span>
    : <span style={{ color: '#d1d5db', fontSize: 16 }} title="Bidrar ikke til risikoscore">&#8212;</span>
}

export default function SourceStatusPanel({ sources = [], healthSummary = 'ok' }) {
  const hcfg = HEALTH_SUMMARY_CONFIG[healthSummary] || HEALTH_SUMMARY_CONFIG.ok

  return (
    <div className="lr-source-panel">
      {/* Health summary chip */}
      <div style={{ marginBottom: 12 }}>
        <span style={{
          display: 'inline-block',
          background: hcfg.bg,
          color: hcfg.color,
          border: `1px solid ${hcfg.color}33`,
          borderRadius: 12,
          padding: '4px 14px',
          fontSize: 13,
          fontWeight: 700,
        }}>
          {hcfg.label}
        </span>
      </div>

      {sources.length === 0 ? (
        <p style={{ color: '#6b7280', fontStyle: 'italic' }}>Ingen datakilder registrert</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
                {['Kilde', 'Type', 'Status', 'Sist oppdatert', 'Poster', 'Bidrar til risiko'].map(h => (
                  <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#374151', whiteSpace: 'nowrap' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sources.map((src, i) => (
                <React.Fragment key={src.source_id || i}>
                  <tr style={{
                    borderBottom: src.last_error ? 'none' : '1px solid #f3f4f6',
                    background: i % 2 === 0 ? 'white' : '#fafafa',
                  }}>
                    <td style={{ padding: '8px 10px', fontWeight: 600 }}>{src.source_name || src.source_id}</td>
                    <td style={{ padding: '8px 10px', color: '#6b7280' }}>{src.source_type || '—'}</td>
                    <td style={{ padding: '8px 10px' }}><StatusChip status={src.status} /></td>
                    <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', color: '#374151' }}>
                      {formatTimestamp(src.last_sync)}
                      {src.freshness_hours != null && (
                        <span style={{ color: '#9ca3af', fontSize: 11, marginLeft: 4 }}>
                          ({src.freshness_hours}t siden)
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '8px 10px', color: '#374151' }}>
                      {src.records_received != null ? src.records_received.toLocaleString('nb-NO') : '—'}
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                      <ContributesMark contributes={src.contributes_to_risk} />
                    </td>
                  </tr>
                  {src.last_error && (
                    <tr style={{ background: i % 2 === 0 ? 'white' : '#fafafa', borderBottom: '1px solid #f3f4f6' }}>
                      <td colSpan={6} style={{ padding: '4px 10px 8px', color: '#c62828', fontSize: 11 }}>
                        {src.last_error}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
