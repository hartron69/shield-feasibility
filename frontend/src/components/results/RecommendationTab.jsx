import React from 'react'

function verdictClass(verdict) {
  if (verdict.startsWith('STRONGLY')) return 'verdict-STRONGLY'
  if (verdict.startsWith('RECOMMENDED')) return 'verdict-RECOMMENDED'
  if (verdict.startsWith('POTENTIALLY')) return 'verdict-POTENTIALLY'
  return 'verdict-NOT'
}

export default function RecommendationTab({ baseline, mitigated }) {
  const { summary, criterion_scores } = baseline
  const { verdict, composite_score, confidence_level } = summary
  const mitSummary = mitigated?.summary
  const scoreDelta = mitSummary != null ? mitSummary.composite_score - composite_score : null
  const verdictChanged = mitSummary != null && mitSummary.verdict !== verdict

  return (
    <div>
      <div className={`verdict-banner ${verdictClass(verdict)}`}>
        {verdict}
        <span style={{ fontSize: 13, fontWeight: 400, marginLeft: 14 }}>
          Score: {composite_score.toFixed(1)}/100 &nbsp;·&nbsp; Confidence: {confidence_level}
        </span>
      </div>

      {/* Mitigated scenario callout */}
      {mitSummary != null && (
        <div style={{
          margin: '10px 0', padding: '10px 16px', borderRadius: 6,
          background: scoreDelta > 0 ? '#F0FDF4' : '#F9FAFB',
          border: `1px solid ${scoreDelta > 0 ? '#BBF7D0' : '#E5E7EB'}`,
          display: 'flex', alignItems: 'center', gap: 16, fontSize: 13,
        }}>
          <span style={{ fontWeight: 700, color: 'var(--dark-grey)' }}>Med tiltak:</span>
          <span className={`verdict-banner ${verdictClass(mitSummary.verdict)}`}
                style={{ padding: '3px 10px', fontSize: 12, margin: 0 }}>
            {mitSummary.verdict}
          </span>
          <span style={{ fontWeight: 700, color: scoreDelta > 0 ? '#16A34A' : scoreDelta < 0 ? '#DC2626' : 'var(--dark-grey)' }}>
            {scoreDelta > 0 ? '+' : ''}{scoreDelta.toFixed(1)} pts
            &nbsp;({mitSummary.composite_score.toFixed(1)}/100)
          </span>
          {verdictChanged && (
            <span style={{ fontSize: 11, color: '#7C3AED', fontWeight: 600, marginLeft: 4 }}>
              ▲ Verdict oppgradert
            </span>
          )}
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--dark-grey)', marginBottom: 3 }}>
          <span>Baseline</span>
          <span>{composite_score.toFixed(1)}/100</span>
        </div>
        <div className="score-bar-outer" style={{ margin: 0 }}>
          <div className="score-bar-inner" style={{ width: `${composite_score}%` }} />
        </div>
        {mitSummary != null && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#16A34A', marginTop: 6, marginBottom: 3, fontWeight: 600 }}>
              <span>Med tiltak</span>
              <span>{mitSummary.composite_score.toFixed(1)}/100</span>
            </div>
            <div className="score-bar-outer" style={{ margin: 0 }}>
              <div className="score-bar-inner" style={{ width: `${mitSummary.composite_score}%`, background: '#16A34A' }} />
            </div>
          </>
        )}
      </div>

      <div className="card">
        <div className="section-title">Criterion Scores</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Criterion</th>
              <th>Weight</th>
              <th>Score (0–100)</th>
              <th>Weighted</th>
              <th>Finding</th>
            </tr>
          </thead>
          <tbody>
            {(criterion_scores || []).map((c) => (
              <tr key={c.name}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td>{(c.weight * 100).toFixed(1)}%</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, background: 'var(--mid-grey)', borderRadius: 4, height: 6 }}>
                      <div style={{ width: `${c.raw_score}%`, height: 6, borderRadius: 4, background: c.raw_score >= 60 ? 'var(--teal)' : c.raw_score >= 40 ? 'var(--gold)' : 'var(--danger)' }} />
                    </div>
                    <span style={{ fontSize: 12, minWidth: 28 }}>{c.raw_score.toFixed(0)}</span>
                  </div>
                </td>
                <td>{c.weighted_score.toFixed(1)}</td>
                <td style={{ fontSize: 12, color: 'var(--dark-grey)' }}>{c.finding}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="section-title">PCC Captive Cell Implications</div>
        <p style={{ fontSize: 13, color: 'var(--dark-grey)', lineHeight: 1.7 }}>
          Based on the composite score of <strong>{composite_score.toFixed(1)}/100</strong>,
          the operator is assessed as <strong>{verdict}</strong> for a PCC captive cell structure.
          {composite_score >= 55
            ? ' The risk profile, premium volume, and balance sheet strength support establishing a captive cell under appropriate governance conditions.'
            : composite_score >= 40
            ? ' Further analysis is recommended before committing to a captive structure. Key improvement areas are indicated in the criterion scores above.'
            : ' The current risk profile and financials present significant barriers to a viable captive structure.'}
        </p>
      </div>
    </div>
  )
}
