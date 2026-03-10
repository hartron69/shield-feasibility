import React from 'react'

function fmtM(n) {
  if (n == null) return '—'
  return `NOK ${(n / 1e6).toFixed(1)} M`
}

function pct(n) {
  if (n == null) return '—'
  return `${n.toFixed(1)} %`
}

const DOMAIN_COLOURS = {
  biological:    { bg: '#e3f2fd', border: '#90caf9', text: '#1565c0' },
  structural:    { bg: '#fff3e0', border: '#ffcc80', text: '#e65100' },
  environmental: { bg: '#e8f5e9', border: '#a5d6a7', text: '#2e7d32' },
  operational:   { bg: '#f3e5f5', border: '#ce93d8', text: '#6a1b9a' },
  unknown:       { bg: '#f5f5f5', border: '#bdbdbd', text: '#424242' },
}

const DOMAIN_LABELS = {
  biological:    'Biological',
  structural:    'Structural',
  environmental: 'Environmental',
  operational:   'Operational',
  unknown:       'Unknown',
}

function DomainBadge({ domain }) {
  const c = DOMAIN_COLOURS[domain] || DOMAIN_COLOURS.unknown
  return (
    <span style={{
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      borderRadius: 4, padding: '1px 6px', fontSize: 11, fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>
      {DOMAIN_LABELS[domain] || domain}
    </span>
  )
}

const EVENT_TYPE_LABELS = {
  mortality:             'Fish Mortality',
  property:              'Property Damage',
  business_interruption: 'Business Interruption',
}
function eventLabel(t) { return EVENT_TYPE_LABELS[t] || t }

export default function LossHistoryTab({ history }) {
  if (!history) {
    return (
      <div className="tab-content" style={{ color: '#888', padding: 24 }}>
        Loss history not available.
      </div>
    )
  }

  const {
    history_loaded, history_source, record_count, years_covered, n_years_observed,
    portfolio_total_gross, portfolio_mean_severity, portfolio_events_per_year,
    domain_summaries = [],
    mapping_warnings = [],
    calibration_active, calibration_source, calibration_mode,
    calibrated_parameters = {},
    records = [],
  } = history

  if (!history_loaded || record_count === 0) {
    return (
      <div className="tab-content" style={{ color: '#888', padding: 24 }}>
        No historical loss records found in the template.
      </div>
    )
  }

  const yearSpan = years_covered.length > 0
    ? `${years_covered[0]}–${years_covered[years_covered.length - 1]}`
    : '—'

  return (
    <div className="tab-content">

      {/* ── Mapping warnings ──────────────────────────────────────── */}
      {mapping_warnings.length > 0 && (
        <div style={{
          background: '#fff3cd', border: '1px solid #ffc107',
          borderRadius: 6, padding: '8px 14px', marginBottom: 16, fontSize: 12,
        }}>
          <strong>Domain mapping notices</strong>
          <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
            {mapping_warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      {/* ── A. Summary cards ──────────────────────────────────────── */}
      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        <div className="kpi-card">
          <div className="kpi-label">Records loaded</div>
          <div className="kpi-value">{record_count}</div>
          <div className="kpi-sub">Source: {history_source}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Years covered</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>{yearSpan}</div>
          <div className="kpi-sub">{n_years_observed} distinct year{n_years_observed !== 1 ? 's' : ''}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Avg events / year</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>
            {portfolio_events_per_year != null ? portfolio_events_per_year.toFixed(1) : '—'}
          </div>
          <div className="kpi-sub">Poisson frequency proxy</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Avg gross / event</div>
          <div className="kpi-value" style={{ fontSize: 20 }}>{fmtM(portfolio_mean_severity)}</div>
          <div className="kpi-sub">Mean event severity</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Avg annual gross loss</div>
          <div className="kpi-value" style={{ fontSize: 18 }}>
            {n_years_observed > 0 ? fmtM(portfolio_total_gross / n_years_observed) : '—'}
          </div>
          <div className="kpi-sub">Total / {n_years_observed} yrs</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Total gross loss</div>
          <div className="kpi-value" style={{ fontSize: 18 }}>{fmtM(portfolio_total_gross)}</div>
          <div className="kpi-sub">All records combined</div>
        </div>
      </div>

      {/* ── Calibration status ─────────────────────────────────────── */}
      <div style={{
        background: calibration_active ? '#e8f5e9' : '#f4f8fb',
        border: `1px solid ${calibration_active ? '#a5d6a7' : '#d5e3ee'}`,
        borderRadius: 6, padding: '8px 14px', marginBottom: 20, fontSize: 12,
      }}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <span><strong>History source:</strong> {history_source}</span>
          <span><strong>Domain mapping:</strong> automatic</span>
          <span>
            <strong>Calibration:</strong>{' '}
            {calibration_active
              ? `Active (mode: ${calibration_mode}, source: ${calibration_source})`
              : 'Inactive — enable "Calibrate risk parameters from loss history" in Model settings'}
          </span>
        </div>
        {calibration_active && Object.keys(calibrated_parameters).length > 0 && (
          <div style={{ marginTop: 6, color: '#2e7d32' }}>
            <strong>Calibrated parameters: </strong>
            {Object.entries(calibrated_parameters).map(([k, v]) =>
              `${k.replace(/_/g, ' ')}: ${typeof v === 'number' && v > 1000
                ? v.toLocaleString('nb-NO')
                : v}`
            ).join(' · ')}
          </div>
        )}
      </div>

      {/* ── Domain breakdown cards ─────────────────────────────────── */}
      {domain_summaries.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h4 style={{ margin: '0 0 10px', fontSize: 13, color: '#555' }}>
            Domain breakdown
          </h4>
          <div className="kpi-grid">
            {domain_summaries.map(ds => {
              const c = DOMAIN_COLOURS[ds.domain] || DOMAIN_COLOURS.unknown
              return (
                <div key={ds.domain} className="kpi-card" style={{ borderColor: c.border }}>
                  <div className="kpi-label">
                    <DomainBadge domain={ds.domain} />
                  </div>
                  <div className="kpi-value" style={{ fontSize: 18 }}>
                    {fmtM(ds.total_gross_loss)}
                  </div>
                  <div className="kpi-sub">
                    {ds.event_count} event{ds.event_count !== 1 ? 's' : ''} · {pct(ds.loss_share_pct)}
                  </div>
                  <div className="kpi-sub">
                    Mean: {fmtM(ds.mean_severity)} · {ds.events_per_year.toFixed(2)}/yr
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── C. Domain summary table ────────────────────────────────── */}
      {domain_summaries.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#555' }}>
            Domain frequency / severity
          </h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%', borderCollapse: 'collapse',
              fontSize: 12, minWidth: 540,
            }}>
              <thead>
                <tr style={{ background: '#f0f4f8', textAlign: 'left' }}>
                  {['Domain', 'Events', 'Total gross', 'Mean severity', 'Events/yr', 'Loss share'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {domain_summaries.map(ds => (
                  <tr key={ds.domain} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '5px 10px' }}><DomainBadge domain={ds.domain} /></td>
                    <td style={{ padding: '5px 10px' }}>{ds.event_count}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(ds.total_gross_loss)}</td>
                    <td style={{ padding: '5px 10px' }}>{fmtM(ds.mean_severity)}</td>
                    <td style={{ padding: '5px 10px' }}>{ds.events_per_year.toFixed(2)}</td>
                    <td style={{ padding: '5px 10px' }}>{pct(ds.loss_share_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── B. Event table ────────────────────────────────────────── */}
      <h4 style={{ margin: '0 0 8px', fontSize: 13, color: '#555' }}>
        Historical loss records
      </h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          fontSize: 12, minWidth: 640,
        }}>
          <thead>
            <tr style={{ background: '#f0f4f8', textAlign: 'left' }}>
              {['Year', 'Event type', 'Domain', 'Gross loss', 'Insured loss', 'Retained loss'].map(h => (
                <th key={h} style={{ padding: '6px 10px', borderBottom: '2px solid #ddd' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.map((r, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '5px 10px', fontWeight: 600 }}>{r.year}</td>
                <td style={{ padding: '5px 10px' }}>{eventLabel(r.event_type)}</td>
                <td style={{ padding: '5px 10px' }}><DomainBadge domain={r.domain} /></td>
                <td style={{ padding: '5px 10px' }}>{fmtM(r.gross_loss)}</td>
                <td style={{ padding: '5px 10px' }}>{fmtM(r.insured_loss)}</td>
                <td style={{ padding: '5px 10px', color: '#c0392b' }}>{fmtM(r.retained_loss)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr style={{ background: '#f7f9fb', fontWeight: 700 }}>
              <td style={{ padding: '6px 10px' }} colSpan={3}>Total ({record_count} records)</td>
              <td style={{ padding: '6px 10px' }}>{fmtM(portfolio_total_gross)}</td>
              <td style={{ padding: '6px 10px' }}>—</td>
              <td style={{ padding: '6px 10px', color: '#c0392b' }}>—</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p style={{ fontSize: 11, color: '#888', marginTop: 8 }}>
        Domain mapping: mortality → biological, property → structural,
        business_interruption → operational. Averages use the full {n_years_observed}-year
        history window ({yearSpan}).
      </p>
    </div>
  )
}
