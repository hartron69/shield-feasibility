import React from 'react'

export default function ConfirmStaleC5AIModal({ freshness, onUpdateFirst, onRunAnyway, onCancel }) {
  if (!freshness || freshness === 'fresh') return null

  const isMissing = freshness === 'missing'

  return (
    <div className="modal-backdrop">
      <div className="modal-box">
        <div className="modal-icon">{isMissing ? '\u26A0' : '\u26A0'}</div>
        <h3 className="modal-title">
          {isMissing ? 'C5AI+ ikke kjørt' : 'C5AI+-data er utdatert'}
        </h3>
        <p className="modal-body">
          {isMissing
            ? 'C5AI+ må kjøres for å gi et oppdatert risikobilde. Feasibility-analysen vil bruke en statisk modell uten live risikodata.'
            : 'C5AI+-data er utdatert. Feasibility-analysen vil bruke et risikobilde som ikke er oppdatert etter siste endringer.'}
        </p>
        <p className="modal-body" style={{ marginTop: 4 }}>
          Vil du oppdatere C5AI+ først, eller kjøre analysen likevel?
        </p>
        <div className="modal-actions">
          <button className="btn btn-primary" onClick={onUpdateFirst}>
            Oppdater C5AI+ først
          </button>
          {!isMissing && (
            <button className="btn btn-secondary" onClick={onRunAnyway}>
              Kjør likevel
            </button>
          )}
          <button className="btn btn-ghost" onClick={onCancel}>
            Avbryt
          </button>
        </div>
      </div>
    </div>
  )
}
