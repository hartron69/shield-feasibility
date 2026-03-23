import React from 'react'

export default function RunControls({ onRun, onExample, onReset, loading, c5aiStatus }) {
  const freshness = c5aiStatus?.freshness
  const showWarning = freshness === 'missing' || freshness === 'stale'

  return (
    <div className="run-controls">
      {showWarning && (
        <div className="c5ai-stale-warning">
          {freshness === 'missing'
            ? 'C5AI+ ikke kjørt — klikk «Oppdater C5AI+» for å aktivere analysen'
            : 'C5AI+ data er utdatert — oppdater for best resultat'}
        </div>
      )}
      <button className="btn btn-primary" onClick={onRun} disabled={loading}>
        {loading ? 'Running...' : 'Kjør Feasibility'}
      </button>
      <button className="btn btn-secondary" onClick={onExample} disabled={loading} title="Last Nordic Aqua Partners-eksempel">
        Eksempel
      </button>
      <button className="btn btn-ghost" onClick={onReset} disabled={loading}>
        Nullstill
      </button>
    </div>
  )
}
