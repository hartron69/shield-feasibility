import React, { useState, useEffect, useCallback } from 'react'

// ILA Risiko-fane — MRE-1 snapshot og MRE-2 sesongkurve
// Polles hvert 10. minutt (MRE-1 oppdateres ved Barentswatch-sync)

const VARSEL_COLORS = {
  'GRØNN': { bg: '#e6f4ea', border: '#2e7d32', text: '#1b5e20', dot: '#2e7d32' },
  'ILA01': { bg: '#fff8e1', border: '#f57f17', text: '#e65100', dot: '#f9a825' },
  'ILA02': { bg: '#fff3e0', border: '#e65100', text: '#bf360c', dot: '#ef6c00' },
  'ILA03': { bg: '#fce4ec', border: '#c62828', text: '#b71c1c', dot: '#d32f2f' },
  'ILA04': { bg: '#fdecea', border: '#7b1fa2', text: '#4a148c', dot: '#8e24aa' },
}

const KILDE_NAVN = {
  hydro:  'Hydrodynamisk',
  wb:     'Brønnbåt',
  ops:    'Delte ops.',
  smolt:  'Smolt',
  wild:   'Villfisk',
  mutate: 'Mutasjon',
}

const TILTAK = {
  HYDRO:  'Øk overvåking av HPR0-tetthet i nærliggende farvann',
  WB:     'Prioriter brønnbåt-desinfeksjon — vurder å redusere besøksfrekvens',
  OPS:    'Streng begrensning av delte operasjoner med nabolokaliteter',
  SMOLT:  'Forleng karantenetid etter smolt-utsett',
  WILD:   'Villfisk-barrierer og tettere lukkede merdsystemer',
  MUTATE: 'Øk HPR3-screening-frekvens',
  BIRD:   'Aktiver fugle-deterrent i sesong',
}

// ── MRE-1 kilde-tabell ────────────────────────────────────────────────────────
function KildeTabell({ mre1 }) {
  const kilder = Object.entries(KILDE_NAVN)
    .map(([kode, navn]) => ({
      kode,
      navn,
      p:     mre1[`p_${kode}`]      ?? 0,
      attrib: mre1[`attrib_${kode}`] ?? 0,
    }))
    .filter(k => k.p > 0.001)
    .sort((a, b) => b.attrib - a.attrib)

  const dom = (mre1.dominerende_kilde ?? '').toLowerCase()

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
      <thead>
        <tr style={{ background: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
          {['Kilde', 'P [%]', 'Andel'].map(h => (
            <th key={h} style={{ padding: '5px 8px', textAlign: 'left', fontWeight: 600, color: '#374151' }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {kilder.map(k => (
          <tr key={k.kode}
              style={{
                borderBottom: '1px solid #f3f4f6',
                background: k.kode === dom ? '#eff6ff' : 'white',
                fontWeight: k.kode === dom ? 700 : 400,
              }}>
            <td style={{ padding: '5px 8px' }}>
              {k.kode === dom && <span style={{ marginRight: 4, color: '#3b82f6' }}>▶</span>}
              {k.navn}
            </td>
            <td style={{ padding: '5px 8px', fontFamily: 'monospace' }}>{(k.p * 100).toFixed(1)}%</td>
            <td style={{ padding: '5px 8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 60, height: 5, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${k.attrib * 100}%`, height: '100%', background: '#3b82f6', borderRadius: 3 }} />
                </div>
                <span style={{ fontFamily: 'monospace', fontSize: 11 }}>{(k.attrib * 100).toFixed(0)}%</span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ── MRE-2 SVG-sesongkurve ─────────────────────────────────────────────────────
function SesongKurve({ uker }) {
  if (!uker || uker.length === 0) {
    return <p style={{ color: '#9ca3af', fontSize: 12, fontStyle: 'italic' }}>Ingen sesongdata.</p>
  }

  const W = 340, H = 160, PAD = 28
  const xScale = (W - 2 * PAD) / Math.max(uker.length - 1, 1)
  const yScale = H - 2 * PAD

  const pts = uker.map((u, i) => ({
    x: PAD + i * xScale,
    y: PAD + (1 - u.p_kumulativ) * yScale,
    u,
  }))
  const poly = pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')

  // ILA threshold lines (y positions)
  const yIla01 = PAD + (1 - 0.05) * yScale
  const yIla02 = PAD + (1 - 0.20) * yScale
  const yIla03 = PAD + (1 - 0.50) * yScale
  const yIla04 = PAD + (1 - 0.80) * yScale

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ display: 'block', width: '100%', maxWidth: 340 }}>
      {/* Zone fills */}
      <rect x={PAD} y={PAD}           width={W-2*PAD} height={yIla04-PAD}        fill="#f3e5f522" />
      <rect x={PAD} y={yIla04}        width={W-2*PAD} height={yIla03-yIla04}     fill="#fce4ec33" />
      <rect x={PAD} y={yIla03}        width={W-2*PAD} height={yIla02-yIla03}     fill="#fff3e033" />
      <rect x={PAD} y={yIla02}        width={W-2*PAD} height={yIla01-yIla02}     fill="#fff8e133" />
      <rect x={PAD} y={yIla01}        width={W-2*PAD} height={PAD+yScale-yIla01} fill="#e8f5e933" />

      {/* Threshold dashed lines */}
      {[
        { y: yIla01, label: '5%',  color: '#f57f17' },
        { y: yIla02, label: '20%', color: '#e65100' },
        { y: yIla03, label: '50%', color: '#c62828' },
      ].map(({ y, label, color }) => (
        <g key={label}>
          <line x1={PAD} y1={y} x2={W-PAD} y2={y}
                stroke={color} strokeWidth="0.8" strokeDasharray="3 3" opacity="0.6" />
          <text x={PAD - 2} y={y + 3} fontSize="8" fill={color} textAnchor="end">{label}</text>
        </g>
      ))}

      {/* Curve */}
      <polyline points={poly} fill="none" stroke="#1e40af" strokeWidth="1.8" strokeLinejoin="round" />

      {/* Axis labels */}
      <text x={PAD} y={H - 6} fontSize="9" fill="#9ca3af">Uke 1</text>
      <text x={W - PAD} y={H - 6} fontSize="9" fill="#9ca3af" textAnchor="end">Uke {uker.length}</text>
      <text x={4} y={PAD + 4} fontSize="9" fill="#9ca3af">100%</text>
      <text x={4} y={PAD + yScale} fontSize="9" fill="#9ca3af">0%</text>
    </svg>
  )
}

// ── SEIR badge ────────────────────────────────────────────────────────────────
function SEIRBadge({ uke }) {
  if (!uke) return null
  const deler = [
    { kode: 'S', navn: 'Mottagelig', v: uke.s, farge: '#2e7d32' },
    { kode: 'E', navn: 'Eksponert',  v: uke.e, farge: '#f57f17' },
    { kode: 'I', navn: 'Infisert',   v: uke.i, farge: '#c62828' },
    { kode: 'R', navn: 'Restituert', v: uke.r, farge: '#78909c' },
  ]
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
      {deler.map(d => (
        <div key={d.kode} title={`${d.navn}: ${(d.v * 100).toFixed(2)}%`}
             style={{
               display: 'flex', alignItems: 'center', gap: 4,
               fontSize: 11, color: '#374151',
             }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.farge }} />
          <span style={{ fontWeight: 700, color: d.farge }}>{d.kode}</span>
          <span>{(d.v * 100).toFixed(1)}%</span>
        </div>
      ))}
      <span style={{ fontSize: 11, color: '#9ca3af', marginLeft: 4 }}>uke {uke.uke_nr}</span>
    </div>
  )
}

// ── Varsel-header ─────────────────────────────────────────────────────────────
function VarselHeader({ varselniva, pTotal, eTapMnok }) {
  const c = VARSEL_COLORS[varselniva] || VARSEL_COLORS['GRØNN']
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
      padding: '10px 14px',
      background: c.bg,
      border: `1.5px solid ${c.border}`,
      borderRadius: 8,
      marginBottom: 16,
    }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 10px',
        background: c.border,
        color: 'white',
        borderRadius: 20,
        fontWeight: 700,
        fontSize: 13,
      }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'white', display: 'inline-block' }} />
        {varselniva}
      </div>
      <span style={{ fontSize: 16, fontWeight: 700, color: c.text }}>
        P_total = {(pTotal * 100).toFixed(1)}%
      </span>
      {eTapMnok != null && (
        <span style={{ fontSize: 12, color: c.text, opacity: 0.85 }}>
          Forventet tap: NOK {eTapMnok.toFixed(1)}M
        </span>
      )}
    </div>
  )
}

// ── Hovedkomponent ────────────────────────────────────────────────────────────
export default function ILARiskTab({ localityId }) {
  const [mre1,    setMre1]    = useState(null)
  const [mre2,    setMre2]    = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  const hentData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [r1, r2] = await Promise.all([
        fetch(`/api/ila/${localityId}/mre1`).then(r => r.ok ? r.json() : null),
        fetch(`/api/ila/${localityId}/mre2`).then(r => r.ok ? r.json() : { uker: [] }),
      ])
      setMre1(r1)
      setMre2((r2?.uker) || [])
    } catch (e) {
      setError('Kunne ikke hente ILA-risikodata.')
    } finally {
      setLoading(false)
    }
  }, [localityId])

  useEffect(() => {
    hentData()
    const poll = setInterval(hentData, 10 * 60 * 1000)  // 10 min
    return () => clearInterval(poll)
  }, [hentData])

  if (loading) return (
    <div style={{ textAlign: 'center', padding: 40, color: '#9ca3af', fontSize: 13 }}>
      &#8987; Henter ILA-risikodata…
    </div>
  )

  if (error) return (
    <div style={{ background: '#fdecea', color: '#c62828', padding: '10px 14px', borderRadius: 8, fontSize: 13 }}>
      {error}
    </div>
  )

  if (!mre1) return (
    <div style={{ padding: 20, color: '#6b7280', fontSize: 13 }}>
      <p style={{ fontWeight: 600, marginBottom: 6 }}>Ingen ILA-profil aktivert for denne lokaliteten.</p>
      <p style={{ color: '#9ca3af' }}>Kontakt Shield-admin for å aktivere ILA-overvåking.</p>
    </div>
  )

  const tiltak = TILTAK[mre1.dominerende_kilde?.toUpperCase()]
  const sisteUke = mre2.length > 0 ? mre2[mre2.length - 1] : null

  return (
    <div>
      {/* Varselnivå-header */}
      <VarselHeader
        varselniva={mre1.varselniva}
        pTotal={mre1.p_total}
        eTapMnok={mre1.e_tap_mnok}
      />

      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>

        {/* Venstre: MRE-1 kilde-breakdown */}
        <div style={{ flex: '1 1 240px', minWidth: 220 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
            MRE-1 snapshot
            <span style={{ fontWeight: 400, fontSize: 11, color: '#9ca3af', marginLeft: 6 }}>
              HPR0={mre1.hpr0_tetthet} · sone={mre1.ila_sone}
            </span>
          </div>
          <KildeTabell mre1={mre1} />

          <div style={{ marginTop: 8, fontSize: 12, color: '#374151' }}>
            Dominerende kilde: <strong>{mre1.dominerende_kilde}</strong>
          </div>

          {tiltak && (
            <div style={{
              marginTop: 10, padding: '8px 10px',
              background: '#eff6ff', border: '1px solid #bfdbfe',
              borderRadius: 6, fontSize: 12, color: '#1e40af',
            }}>
              <strong>Anbefalt tiltak:</strong> {tiltak}
            </div>
          )}
        </div>

        {/* Høyre: MRE-2 sesongkurve */}
        <div style={{ flex: '1 1 220px', minWidth: 200 }}>
          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
            MRE-2 sesongkurve
            {sisteUke && (
              <span style={{ fontWeight: 400, fontSize: 11, color: '#9ca3af', marginLeft: 6 }}>
                P_kum={( sisteUke.p_kumulativ * 100).toFixed(1)}% uke {sisteUke.uke_nr}
              </span>
            )}
          </div>
          <SesongKurve uker={mre2} />
          {sisteUke && <SEIRBadge uke={sisteUke} />}
        </div>
      </div>

      {/* Oppdater-knapp */}
      <div style={{ marginTop: 14, textAlign: 'right' }}>
        <button
          onClick={hentData}
          style={{
            background: 'none', border: 'none',
            color: 'var(--navy)', fontSize: 11,
            fontWeight: 600, cursor: 'pointer', padding: 0,
          }}
        >
          &#8635; Oppdater nå
        </button>
      </div>
    </div>
  )
}
