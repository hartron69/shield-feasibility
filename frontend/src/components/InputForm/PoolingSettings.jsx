import React from 'react'

function fmtM(nok) {
  return parseFloat((nok / 1_000_000).toFixed(1))
}
function toNok(mill) {
  return Math.round(parseFloat(mill) * 1_000_000) || 0
}

export default function PoolingSettings({ values, onChange }) {
  const set = (field) => (e) =>
    onChange({ ...values, [field]: e.target.value })
  const setNum = (field) => (e) =>
    onChange({ ...values, [field]: parseFloat(e.target.value) || 0 })
  const setInt = (field) => (e) =>
    onChange({ ...values, [field]: parseInt(e.target.value) || 2 })
  const setMillNok = (field) => (e) =>
    onChange({ ...values, [field]: toNok(e.target.value) })

  const enabled = values.enabled ?? false

  return (
    <div>
      {/* ── Enable toggle ─────────────────────────────────────────── */}
      <div className="field" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <input
          type="checkbox"
          id="pooling-enabled"
          checked={enabled}
          onChange={(e) => onChange({ ...values, enabled: e.target.checked })}
        />
        <label htmlFor="pooling-enabled" style={{ marginBottom: 0, cursor: 'pointer' }}>
          Enable pooled PCC scenario
          <span style={{ display: 'block', fontSize: 10, color: '#888', fontWeight: 400, marginTop: 1 }}>
            Evaluates viability when joining a peer risk-sharing pool
          </span>
        </label>
      </div>

      {!enabled && (
        <div style={{
          fontSize: 11, color: '#999', background: '#f8f9fa',
          border: '1px solid #e0e0e0', borderRadius: 6,
          padding: '8px 12px', marginTop: 8,
        }}>
          Enable pooling to see whether joining a peer pool makes your PCC viable.
        </div>
      )}

      {enabled && (
        <div style={{ marginTop: 12 }}>
          {/* ── Pool structure ─────────────────────────────────────── */}
          <div style={{
            fontSize: 11, fontWeight: 700, color: '#667',
            textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8,
          }}>
            Pool structure
          </div>

          <div className="field-row">
            <div className="field">
              <label>Number of members</label>
              <input
                type="number" min="2" max="10"
                value={values.n_members ?? 4}
                onChange={setInt('n_members')}
              />
            </div>
            <div className="field">
              <label>Inter-member correlation</label>
              <input
                type="number" min="0" max="0.95" step="0.05"
                value={values.inter_member_correlation ?? 0.25}
                onChange={setNum('inter_member_correlation')}
              />
            </div>
          </div>

          <div className="field">
            <label>Similarity spread (±%)</label>
            <input
              type="number" min="0" max="0.50" step="0.05"
              value={values.similarity_spread ?? 0.15}
              onChange={setNum('similarity_spread')}
            />
            <span style={{ fontSize: 10, color: '#888', marginTop: 2, display: 'block' }}>
              How similar synthetic pool peers are to this operator (0 = identical, 0.5 = ±50% variation)
            </span>
          </div>

          {/* ── Pooled reinsurance ─────────────────────────────────── */}
          <div style={{
            fontSize: 11, fontWeight: 700, color: '#667',
            textTransform: 'uppercase', letterSpacing: '0.5px',
            marginTop: 12, marginBottom: 8,
          }}>
            Pooled reinsurance
          </div>

          <div className="field-row">
            <div className="field">
              <label>Pooled retention (Mill NOK)</label>
              <input
                type="number" min="1" step="5"
                value={fmtM(values.pooled_retention_nok ?? 25_000_000)}
                onChange={setMillNok('pooled_retention_nok')}
              />
            </div>
            <div className="field">
              <label>Pooled RI limit (Mill NOK)</label>
              <input
                type="number" min="1" step="50"
                value={fmtM(values.pooled_ri_limit_nok ?? 400_000_000)}
                onChange={setMillNok('pooled_ri_limit_nok')}
              />
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label>RI loading factor</label>
              <input
                type="number" min="1.0" max="3.0" step="0.05"
                value={values.pooled_ri_loading_factor ?? 1.40}
                onChange={setNum('pooled_ri_loading_factor')}
              />
            </div>
            <div className="field">
              <label>Shared admin saving</label>
              <input
                type="number" min="0" max="0.50" step="0.05"
                value={values.shared_admin_saving_pct ?? 0.20}
                onChange={setNum('shared_admin_saving_pct')}
              />
            </div>
          </div>

          <div className="field">
            <label>Allocation basis</label>
            <select
              value={values.allocation_basis ?? 'expected_loss'}
              onChange={set('allocation_basis')}
            >
              <option value="expected_loss">Expected loss (recommended)</option>
              <option value="premium">Premium proportional</option>
            </select>
          </div>

          {/* ── v2.1 transparency note ─────────────────────────────── */}
          <div style={{
            fontSize: 10, color: '#999',
            background: '#f5f5f5', border: '1px solid #e0e0e0',
            borderRadius: 4, padding: '6px 10px', marginTop: 10,
          }}>
            v2.1: Synthetic peer pool (actual peer data not uploaded). Correlation
            uses rank-based blending (approximate). See results tab for full
            model assumptions.
          </div>
        </div>
      )}
    </div>
  )
}
