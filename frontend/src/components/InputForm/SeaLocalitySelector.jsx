import React, { useState, useEffect } from 'react'
import { fetchSiteRegistry } from '../../api/client.js'

const BW_QUALITY_COLORS = {
  SUFFICIENT: { bg: '#dcfce7', text: '#166534', label: 'TILSTREKKELIG' },
  LIMITED:    { bg: '#fef9c3', text: '#854d0e', label: 'BEGRENSET' },
  POOR:       { bg: '#fee2e2', text: '#991b1b', label: 'SVAK' },
  NO_DATA:    { bg: '#f1f5f9', text: '#475569', label: 'INGEN DATA' },
  UNKNOWN:    { bg: '#f1f5f9', text: '#475569', label: 'UKJENT' },
}

function BWQualityBadge({ flag }) {
  const c = BW_QUALITY_COLORS[flag] || BW_QUALITY_COLORS.UNKNOWN
  return (
    <span style={{
      background: c.bg, color: c.text,
      padding: '1px 6px', borderRadius: 3,
      fontSize: 10, fontWeight: 700, letterSpacing: 0.3,
    }}>
      {c.label}
    </span>
  )
}

/**
 * SeaLocalitySelector
 *
 * Props:
 *   selectedIds  – Set<string> of currently-selected site_id values
 *   onChange     – (newSelectedIds: Set<string>, registrySites: object[]) => void
 */
export default function SeaLocalitySelector({ selectedIds = new Set(), onChange }) {
  const [sites, setSites] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchSiteRegistry()
      .then(data => {
        const all = data.sites || []
        setSites(all)
        setLoading(false)
        // Auto-select all sites on first load when nothing is selected yet
        if (all.length > 0 && selectedIds.size === 0) {
          onChange(new Set(all.map(s => s.site_id)), all)
        }
      })
      .catch(e => { setError(e.message); setLoading(false) })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function toggle(siteId) {
    const next = new Set(selectedIds)
    if (next.has(siteId)) next.delete(siteId)
    else next.add(siteId)
    onChange(next, sites)
  }

  function selectAll() {
    onChange(new Set(sites.map(s => s.site_id)), sites)
  }

  function clearAll() {
    onChange(new Set(), sites)
  }

  if (loading) return (
    <div style={{ padding: '12px 0', color: 'var(--dark-grey)', fontSize: 12 }}>
      Laster lokalitetsregister…
    </div>
  )

  if (error) return (
    <div style={{ padding: '12px 0', color: '#dc2626', fontSize: 12 }}>
      Feil ved lasting av register: {error}
    </div>
  )

  if (sites.length === 0) return (
    <div style={{ padding: '12px 0', color: 'var(--dark-grey)', fontSize: 12 }}>
      Ingen lokaliteter i registeret.
    </div>
  )

  return (
    <div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: 'var(--dark-grey)', flex: 1 }}>
          {selectedIds.size} av {sites.length} valgt
        </span>
        <button
          type="button"
          onClick={selectAll}
          style={{ fontSize: 10, padding: '2px 8px', borderRadius: 3,
            border: '1px solid #b8d0e8', background: '#f4f8fb',
            cursor: 'pointer', color: '#2c6e9c' }}
        >
          Velg alle
        </button>
        <button
          type="button"
          onClick={clearAll}
          style={{ fontSize: 10, padding: '2px 8px', borderRadius: 3,
            border: '1px solid #e5e7eb', background: '#f9fafb',
            cursor: 'pointer', color: '#6b7280' }}
        >
          Fjern alle
        </button>
      </div>

      <div style={{ border: '1px solid #e5e7eb', borderRadius: 6, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e5e7eb' }}>
              <th style={{ width: 28, padding: '6px 8px' }}></th>
              <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--dark-grey)' }}>Lokalitet</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--dark-grey)' }}>BW-nr</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 600, color: 'var(--dark-grey)' }}>BW-data</th>
            </tr>
          </thead>
          <tbody>
            {sites.map((site, i) => {
              const checked = selectedIds.has(site.site_id)
              return (
                <tr
                  key={site.site_id}
                  style={{
                    borderBottom: i < sites.length - 1 ? '1px solid #f0f0f0' : 'none',
                    background: checked ? 'rgba(27,138,122,0.05)' : 'transparent',
                    cursor: 'pointer',
                  }}
                  onClick={() => toggle(site.site_id)}
                >
                  <td style={{ padding: '6px 8px', textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(site.site_id)}
                      onClick={e => e.stopPropagation()}
                    />
                  </td>
                  <td style={{ padding: '6px 8px' }}>
                    <div style={{ fontWeight: checked ? 600 : 400 }}>{site.site_name}</div>
                    <div style={{ fontSize: 10, color: 'var(--dark-grey)', fontFamily: 'monospace' }}>
                      {site.site_id}
                    </div>
                  </td>
                  <td style={{ padding: '6px 8px', fontFamily: 'monospace', fontSize: 11 }}>
                    {site.locality_no}
                  </td>
                  <td style={{ padding: '6px 8px' }}>
                    <BWQualityBadge flag={site.bw_data_quality || 'NO_DATA'} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 6, fontSize: 10, color: 'var(--dark-grey)' }}>
        Kun havmerd-lokaliteter (sea_cage) er tilgjengelig for valg.
      </div>
    </div>
  )
}
