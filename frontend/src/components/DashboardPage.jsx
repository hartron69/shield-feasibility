import React from 'react'

// ── Module card data ──────────────────────────────────────────────────────────

const MODULES = [
  {
    id: 'live_risk',
    nav: ['live_risk'],
    label: 'Live Risk',
    tagline: 'Operativ status',
    description:
      'Operativ oversikt over oppdaterte data, målinger, risikoutvikling og hendelser per lokalitet. ' +
      'Brukes når du vil se hva som skjer nå, hvilke data som er oppdatert, og hvorfor risikoen endrer seg.',
    cta: 'Åpne Live Risk',
    accent: '#059669',
    bg: '#ECFDF5',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>
      </svg>
    ),
  },
  {
    id: 'risk',
    nav: ['risk', 'risiko'],
    label: 'Risk Intelligence',
    tagline: 'Strategisk analyse',
    description:
      'Strategisk risikobilde basert på oppdaterte signaler fra Live Risk, med prioritering av lokaliteter ' +
      'og kobling til captive-vurdering. Brukes når du vil forstå hvilke lokaliteter og risikotyper som ' +
      'betyr mest for selskapets samlede risiko.',
    cta: 'Åpne Risk Intelligence',
    accent: '#7C3AED',
    bg: '#F5F3FF',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
      </svg>
    ),
  },
  {
    id: 'feasibility',
    nav: ['feasibility', 'oversikt'],
    label: 'PCC Feasibility',
    tagline: 'Captive-analyse',
    description:
      'Analyse av forventet tap, SCR, egnethet og captive-struktur basert på utvalgte lokaliteter og ' +
      'scenarioforutsetninger. Brukes når du vil gjennomføre feasibility-analyse og vurdere ' +
      'økonomisk og strukturell captive-egnethet.',
    cta: 'Åpne PCC Feasibility',
    accent: '#2563EB',
    bg: '#EFF6FF',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M3 9h18"/>
        <path d="M9 21V9"/>
      </svg>
    ),
  },
]

// ── Process flow data ─────────────────────────────────────────────────────────

const PROCESS_STEPS = [
  {
    id: 'data',
    label: 'Data inn',
    color: '#64748B',
    bg: '#F8FAFC',
    border: '#CBD5E1',
    inputs: null,
    outputs: ['BarentsWatch', 'Miljødata', 'Lokalitetsdata', 'Interne input', 'Modellparametere'],
    ioLabel: 'Kilder',
  },
  {
    id: 'live',
    label: 'Live Risk',
    color: '#059669',
    bg: '#ECFDF5',
    border: '#6EE7B7',
    inputs: 'Oppdaterte datakilder og målinger',
    outputs: ['Operativ status', 'Risikoutvikling', 'Målinger per lokalitet', 'Hendelser og endringer'],
    ioLabel: 'Viser',
  },
  {
    id: 'intel',
    label: 'Risk Intelligence',
    color: '#7C3AED',
    bg: '#F5F3FF',
    border: '#C4B5FD',
    inputs: 'Oppdaterte risikosignaler fra Live Risk',
    outputs: ['Strategisk risikobilde', 'Prioritering av lokaliteter', 'Konsentrasjonsanalyse', 'Feasibility-kobling'],
    ioLabel: 'Viser',
  },
  {
    id: 'pcc',
    label: 'PCC Feasibility',
    color: '#2563EB',
    bg: '#EFF6FF',
    border: '#BFDBFE',
    inputs: 'Lokaliteter, risikobilde og analyseforutsetninger',
    outputs: ['Forventet tap', 'SCR-krav', 'Egnethetsresultat', 'Captive-konsekvens'],
    ioLabel: 'Viser',
  },
  {
    id: 'result',
    label: 'Resultat',
    color: '#B45309',
    bg: '#FFFBEB',
    border: '#FDE68A',
    inputs: 'Analyse fra alle moduler',
    outputs: ['Tiltak og prioritering', 'Feasibility-beslutning', 'Captive-struktur', 'Kapital- og prisvurdering'],
    ioLabel: 'Brukes til',
  },
]

// ── Component ─────────────────────────────────────────────────────────────────

export default function DashboardPage({ onNavigate }) {
  return (
    <div className="dashboard-page">

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <div className="dashboard-hero">
        <div className="dashboard-hero-title">Shield Risk Platform</div>
        <div className="dashboard-hero-sub">
          Operativ risikotransparens, strategisk risikoforståelse og PCC feasibility-analyse for havbruk.
        </div>
        <div style={{ marginTop: 8, fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
          Bruk dashboardet som startpunkt for å navigere mellom operativ status, strategisk analyse og feasibility-resultater.
        </div>
      </div>

      {/* ── "Hva ønsker du å gjøre?" ──────────────────────────────────────── */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--navy)' }}>
            Hva ønsker du å gjøre?
          </div>
          <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginTop: 2 }}>
            Velg modulen som passer best til oppgaven din.
          </div>
        </div>

        <div className="dashboard-workflow-row" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginTop: 16 }}>
          {MODULES.map(m => (
            <button
              key={m.id}
              className="dashboard-workflow-card"
              onClick={() => onNavigate(...m.nav)}
              style={{ textAlign: 'left' }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
                <div style={{
                  background: m.bg,
                  color: m.accent,
                  borderRadius: 10,
                  padding: 10,
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  {m.icon}
                </div>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: m.accent, marginBottom: 2 }}>
                    {m.tagline}
                  </div>
                  <div className="dashboard-workflow-title" style={{ marginBottom: 0 }}>{m.label}</div>
                </div>
              </div>
              <div className="dashboard-workflow-desc">{m.description}</div>
              <div className="dashboard-workflow-cta" style={{ color: m.accent }}>{m.cta} &rarr;</div>
            </button>
          ))}
        </div>
      </div>

      {/* ── System process overview ───────────────────────────────────────── */}
      <div>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--navy)' }}>
            Slik henger plattformen sammen
          </div>
          <div style={{ fontSize: 13, color: 'var(--dark-grey)', marginTop: 2 }}>
            Fra datakilder til beslutning — hvert steg bygger på det forrige.
          </div>
        </div>

        {/* Horizontal flow */}
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, overflowX: 'auto', paddingBottom: 4 }}>
          {PROCESS_STEPS.map((step, i) => (
            <React.Fragment key={step.id}>
              {/* Step card */}
              <div style={{
                flex: '1 1 0',
                minWidth: 140,
                background: step.bg,
                border: `1px solid ${step.border}`,
                borderRadius: 10,
                padding: '14px 14px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}>
                {/* Step number + label */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <div style={{
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    background: step.color,
                    color: '#fff',
                    fontSize: 11,
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    {i + 1}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: step.color }}>{step.label}</div>
                </div>

                {/* Input */}
                {step.inputs && (
                  <div style={{ fontSize: 11, color: 'var(--dark-grey)', fontStyle: 'italic', lineHeight: 1.45 }}>
                    Tar inn: {step.inputs}
                  </div>
                )}

                {/* Outputs */}
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: step.color, marginBottom: 4 }}>
                    {step.ioLabel}
                  </div>
                  <ul style={{ margin: 0, paddingLeft: 14, listStyle: 'disc' }}>
                    {step.outputs.map(o => (
                      <li key={o} style={{ fontSize: 11.5, color: 'var(--navy)', lineHeight: 1.6 }}>{o}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Arrow between steps */}
              {i < PROCESS_STEPS.length - 1 && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0 4px',
                  color: 'var(--mid-grey)',
                  fontSize: 18,
                  flexShrink: 0,
                }}>
                  ›
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

    </div>
  )
}
