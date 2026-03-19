import React, { useState } from 'react'

/**
 * SmoltBIWidget
 * Kalkulatorwidget for BI-sum i settefiskanlegg.
 * Formel: volum x pris x (måneder / 12)
 */
export function SmoltBIWidget({ onApply, facilityName }) {
  const [volume,  setVolume]  = useState('')
  const [price,   setPrice]   = useState('')
  const [months,  setMonths]  = useState(24)

  const vol = parseFloat(volume) || 0
  const prc = parseFloat(price)  || 0
  const bi  = vol * prc * (months / 12)

  function fmt(n) {
    return n.toLocaleString('nb-NO', { maximumFractionDigits: 0 })
  }

  return (
    <div className="smolt-bi-widget">
      <div className="smolt-bi-widget-title">BI-kalkulator</div>

      <div className="smolt-field-row">
        <label>Smoltvolum / år</label>
        <input
          type="number"
          value={volume}
          onChange={e => setVolume(e.target.value)}
          placeholder="3 200 000"
          className="smolt-input"
        />
      </div>

      <div className="smolt-field-row">
        <label>Salgspris per stk (NOK)</label>
        <input
          type="number"
          value={price}
          onChange={e => setPrice(e.target.value)}
          placeholder="38"
          className="smolt-input"
        />
      </div>

      <div className="smolt-field-row">
        <label>Indemnitetperiode</label>
        <select
          value={months}
          onChange={e => setMonths(Number(e.target.value))}
          className="smolt-input"
        >
          <option value={12}>12 måneder</option>
          <option value={24}>24 måneder</option>
          <option value={36}>36 måneder</option>
        </select>
      </div>

      {vol > 0 && prc > 0 && (
        <div className="smolt-bi-result">
          <span style={{ fontSize: 11, color: '#666' }}>
            {fmt(vol)} x NOK {fmt(prc)} x {months / 12} år =
          </span>
          <strong style={{ marginLeft: 6, color: '#0D1B2A' }}>
            NOK {fmt(bi)}
          </strong>
        </div>
      )}

      <button
        className="smolt-apply-btn"
        disabled={bi <= 0}
        onClick={() => onApply(Math.round(bi))}
      >
        Bruk denne verdien
      </button>
    </div>
  )
}
