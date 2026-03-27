/**
 * CageRiskProfileTab.jsx
 *
 * Results tab: shows per-locality cage composition and effective domain
 * multipliers when cage_profiles is present in the feasibility response.
 *
 * Props:
 *   cageProfiles  array  — LocalityCageRiskProfile[] from FeasibilityResponse
 */

import React, { useState } from 'react';
import { CAGE_TYPE_META, DOMAIN_DISPLAY } from '../../data/cageTechnologyMeta';

const DOMAINS = ['biological', 'structural', 'environmental', 'operational'];

function MultiplierCard({ domain, value }) {
  const display = DOMAIN_DISPLAY[domain] || { label: domain, color: '#888' };
  const pct = Math.round(value * 100);
  const delta = pct - 100;
  const deltaSign = delta > 0 ? '+' : '';
  const cardColor = value < 0.85 ? '#e8f5e9' : value > 1.15 ? '#fdecea' : '#e3f2fd';
  const textColor = value < 0.85 ? '#2e7d32' : value > 1.15 ? '#c62828' : '#1565c0';
  return (
    <div className="cage-mult-card" style={{ background: cardColor }}>
      <div className="cage-mult-card-domain" style={{ color: display.color }}>
        {display.label}
      </div>
      <div className="cage-mult-card-value" style={{ color: textColor }}>
        {pct}%
      </div>
      <div className="cage-mult-card-delta" style={{ color: textColor }}>
        {deltaSign}{delta}%
      </div>
    </div>
  );
}

function DomainBarChart({ mults }) {
  const barHeight = 24;
  const barGap = 6;
  const labelWidth = 90;
  const maxWidth = 200;
  const svgH = DOMAINS.length * (barHeight + barGap);

  return (
    <svg width={labelWidth + maxWidth + 60} height={svgH} role="img" aria-label="Domenemultiplikatorer">
      {DOMAINS.map((domain, i) => {
        const display = DOMAIN_DISPLAY[domain] || { label: domain, color: '#888' };
        const val = mults[domain] ?? 1.0;
        const barW = Math.min(val * (maxWidth / 2), maxWidth);
        const y = i * (barHeight + barGap);
        return (
          <g key={domain}>
            <text x={labelWidth - 4} y={y + barHeight / 2 + 5} textAnchor="end" fontSize={11} fill="#555">
              {display.label}
            </text>
            <line
              x1={labelWidth + maxWidth / 2}
              y1={y}
              x2={labelWidth + maxWidth / 2}
              y2={y + barHeight}
              stroke="#ccc"
              strokeWidth={1}
              strokeDasharray="3,2"
            />
            <rect
              x={labelWidth}
              y={y}
              width={barW}
              height={barHeight}
              rx={3}
              fill={display.color}
              opacity={0.75}
            />
            <text x={labelWidth + barW + 4} y={y + barHeight / 2 + 5} fontSize={10} fill="#444">
              {Math.round(val * 100)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function WeightingModeBadge({ mode }) {
  const isAdvanced = mode === 'advanced';
  return (
    <span style={{
      fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600,
      background: isAdvanced ? '#e8eaf6' : '#f5f5f5',
      color: isAdvanced ? '#3949ab' : '#757575',
      border: `1px solid ${isAdvanced ? '#9fa8da' : '#e0e0e0'}`,
    }}>
      {isAdvanced ? 'Avansert vekting' : 'Biomasseveid'}
    </span>
  );
}

function CageWeightDetailsTable({ details }) {
  const [expanded, setExpanded] = useState(false);
  if (!details || details.length === 0) return null;

  return (
    <div style={{ marginTop: 12 }}>
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: '#3949ab', fontSize: 12, padding: 0, marginBottom: 6,
        }}
      >
        {expanded ? '&#9650;' : '&#9660;'} Vis merdvektingsdetaljer
      </button>
      {expanded && (
        <div style={{ overflowX: 'auto' }}>
          <table className="cage-detail-table" style={{ fontSize: 11 }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Kompleksitet</th>
                <th>Kritikalitet</th>
                <th>Feilmodus</th>
                <th style={{ color: DOMAIN_DISPLAY.biological?.color }}>Bio</th>
                <th style={{ color: DOMAIN_DISPLAY.structural?.color }}>Str</th>
                <th style={{ color: DOMAIN_DISPLAY.environmental?.color }}>Milj</th>
                <th style={{ color: DOMAIN_DISPLAY.operational?.color }}>Ops</th>
                <th>Kilde</th>
              </tr>
            </thead>
            <tbody>
              {details.map(d => (
                <tr key={d.cage_id}>
                  <td>{d.cage_id}</td>
                  <td>{(d.derived_complexity * 100).toFixed(0)}%</td>
                  <td>{(d.derived_criticality * 100).toFixed(0)}%</td>
                  <td style={{ fontSize: 10 }}>
                    {d.failure_mode_class === 'binary_high_consequence'
                      ? 'Bin/hoy'
                      : d.failure_mode_class === 'threshold'
                      ? 'Terskel'
                      : 'Prop'}
                  </td>
                  {DOMAINS.map(dom => (
                    <td key={dom} style={{ color: DOMAIN_DISPLAY[dom]?.color }}>
                      {d.domain_weights && d.domain_weights[dom] != null
                        ? `${(d.domain_weights[dom] * 100).toFixed(1)}%`
                        : '—'}
                    </td>
                  ))}
                  <td style={{ fontSize: 10, color: d.defaults_used ? '#9e9e9e' : '#2e7d32' }}>
                    {d.defaults_used ? 'std' : 'eks'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
            Bio/Str/Milj/Ops = merdandel per domene (summer til 100% per kolonne).
            Kilde: std = standard typeverdier, eks = eksplisitt satt.
          </div>
        </div>
      )}
    </div>
  );
}

function LocalityCard({ profile }) {
  const biomassTotal = Object.values(profile.biomass_by_cage_type || {}).reduce((s, v) => s + v, 0);

  return (
    <div className="cage-locality-card">
      <div className="cage-locality-header">
        <span className="cage-locality-name">{profile.site_name}</span>
        <span className="cage-locality-id">{profile.site_id}</span>
        <span className="cage-locality-count">{profile.cage_count} merder</span>
        <WeightingModeBadge mode={profile.weighting_mode || 'biomass_only'} />
      </div>

      {/* Warnings */}
      {profile.warnings && profile.warnings.length > 0 && (
        <div style={{
          margin: '8px 0', padding: '6px 10px', background: '#fff8e1',
          border: '1px solid #ffe082', borderRadius: 4, fontSize: 12,
        }}>
          {profile.warnings.map((w, i) => (
            <div key={i} style={{ color: '#795548' }}>&#9888; {w}</div>
          ))}
        </div>
      )}

      {/* Cage type composition */}
      <div className="cage-composition-row">
        {profile.cage_types_present.map(ct => {
          const meta = CAGE_TYPE_META[ct] || { label: ct, color: '#888' };
          const biomass = profile.biomass_by_cage_type?.[ct] ?? 0;
          const pct = biomassTotal > 0 ? ((biomass / biomassTotal) * 100).toFixed(0) : '&#8212;';
          return (
            <div key={ct} className="cage-type-chip" style={{ borderColor: meta.color }}>
              <span className="cage-type-chip-dot" style={{ background: meta.color }} />
              <span className="cage-type-chip-label">{meta.shortLabel || meta.label}</span>
              <span className="cage-type-chip-pct">{pct}%</span>
            </div>
          );
        })}
      </div>

      {/* Domain multiplier cards */}
      <div className="cage-mult-cards">
        {DOMAINS.map(domain => (
          <MultiplierCard
            key={domain}
            domain={domain}
            value={profile.effective_domain_multipliers?.[domain] ?? 1.0}
          />
        ))}
      </div>

      {/* SVG bar chart */}
      <div className="cage-bar-chart-wrap">
        <div className="cage-bar-chart-title">Domenemultiplikatorer vs. apen not (100%)</div>
        <DomainBarChart mults={profile.effective_domain_multipliers || {}} />
      </div>

      {/* Per-cage table */}
      {profile.cages && profile.cages.length > 0 && (
        <table className="cage-detail-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Teknologi</th>
              <th>Biomasse</th>
              <th>Andel</th>
            </tr>
          </thead>
          <tbody>
            {profile.cages.map(cage => {
              const meta = CAGE_TYPE_META[cage.cage_type] || { label: cage.cage_type, color: '#888' };
              const share = biomassTotal > 0
                ? ((cage.biomass_tonnes / biomassTotal) * 100).toFixed(1)
                : '&#8212;';
              return (
                <tr key={cage.cage_id}>
                  <td>{cage.cage_id}</td>
                  <td>
                    <span className="cage-type-badge" style={{ background: meta.color + '22', color: meta.color }}>
                      {meta.label}
                    </span>
                  </td>
                  <td>{cage.biomass_tonnes.toLocaleString('nb-NO')} t</td>
                  <td>{share}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {/* Advanced cage weight details (collapsible) */}
      <CageWeightDetailsTable details={profile.cage_weight_details} />
    </div>
  );
}

export default function CageRiskProfileTab({ cageProfiles }) {
  if (!cageProfiles || cageProfiles.length === 0) {
    return (
      <div className="cage-tab-empty">
        <p>Ingen merdprofiler tilgjengelig.</p>
        <p style={{ fontSize: 13, color: '#888' }}>
          Konfigurer merder per lokalitet i inndatapanelet for a aktivere merdbasert risikovurdering.
        </p>
      </div>
    );
  }

  return (
    <div className="cage-risk-profile-tab">
      <div className="cage-tab-intro">
        <strong>Merdprofiler</strong> &#8212; risikovurdering per lokalitet basert pa merdsammensetning og teknologi.
        Domenemultiplikatorer &lt; 100% indikerer lavere risiko enn apen not (referanse).
      </div>
      <div className="cage-locality-cards">
        {cageProfiles.map(profile => (
          <LocalityCard key={profile.site_id} profile={profile} />
        ))}
      </div>
    </div>
  );
}
