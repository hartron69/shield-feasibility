import React from 'react'

export default function RunControls({ onRun, onExample, onReset, loading }) {
  return (
    <div className="run-controls">
      <button className="btn btn-primary" onClick={onRun} disabled={loading}>
        {loading ? 'Running...' : 'Run Feasibility'}
      </button>
      <button className="btn btn-secondary" onClick={onExample} disabled={loading} title="Load Nordic Aqua Partners example">
        Example
      </button>
      <button className="btn btn-ghost" onClick={onReset} disabled={loading}>
        Reset
      </button>
    </div>
  )
}
