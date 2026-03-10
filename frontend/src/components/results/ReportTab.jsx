import React from 'react'

export default function ReportTab({ report }) {
  if (!report) {
    return (
      <div className="card" style={{ textAlign: 'center', color: 'var(--dark-grey)', padding: 40 }}>
        Report not yet generated. Run the analysis with "Generate board PDF report" enabled.
      </div>
    )
  }

  return (
    <div className="card">
      <div className="section-title">Board PDF Report</div>
      {report.available && report.pdf_url ? (
        <>
          <p style={{ marginBottom: 16, color: 'var(--dark-grey)', fontSize: 13 }}>
            The report has been generated and is ready for download.
          </p>
          <a
            href={report.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="btn btn-primary"
            style={{ display: 'inline-block', textDecoration: 'none', padding: '10px 24px' }}
          >
            Download PDF Report
          </a>
        </>
      ) : (
        <p style={{ color: 'var(--dark-grey)', fontSize: 13 }}>
          {report.available === false
            ? 'PDF generation is disabled or failed. Enable "Generate board PDF report" in Model Settings and re-run.'
            : 'Report status unknown.'}
        </p>
      )}
    </div>
  )
}
