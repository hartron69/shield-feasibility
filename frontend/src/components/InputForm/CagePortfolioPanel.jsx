/**
 * CagePortfolioPanel.jsx
 *
 * Inline cage-portfolio editor for one sea locality.
 *
 * Biomass per cage is entered as **% of the locality's total biomass**.
 * The actual biomass_tonnes for each cage is computed:
 *   biomass_tonnes = (biomass_pct / 100) × totalSiteBiomass
 *
 * A control-sum bar shows the sum of all cage percentages and warns if
 * the total exceeds 100%.  Cages with 0% are allowed (empty/fallow merder).
 *
 * Props:
 *   siteId            string    — locality site_id (for key scoping)
 *   siteName          string    — display name
 *   totalSiteBiomass  number    — locality total biomass in tonnes
 *   cages             array     — [{cage_id, cage_type, biomass_pct, biomass_tonnes, ...advancedFields}]
 *   onChange          fn(cages) — called with full updated cages array (biomass_tonnes is always derived)
 */

import React, { useId, useState } from 'react';
import {
  CAGE_TYPE_META,
  CAGE_TYPES_ORDERED,
  DOMAIN_DISPLAY,
  CAGE_TYPE_DEFAULT_SCORES,
  FAILURE_MODE_OPTIONS,
  REDUNDANCY_OPTIONS,
  computeLocalityDomainMultipliers,
} from '../../data/cageTechnologyMeta';

const DOMAINS = ['biological', 'structural', 'environmental', 'operational'];

// ── Helpers ────────────────────────────────────────────────────────────────

/** Derive biomass_tonnes from pct + site total. */
function pctToTonnes(pct, siteTotalBiomass) {
  return (parseFloat(pct) || 0) * (siteTotalBiomass || 0) / 100;
}

/** When a cage object is emitted via onChange, ensure biomass_tonnes is in sync. */
function withComputedTonnes(cage, siteTotalBiomass) {
  return {
    ...cage,
    biomass_tonnes: pctToTonnes(cage.biomass_pct, siteTotalBiomass),
  };
}

// ── Sub-components ─────────────────────────────────────────────────────────

function MultiplierBar({ value }) {
  const pct = Math.round(value * 100);
  const color = value < 0.9 ? '#36A271' : value > 1.1 ? '#FF6B6B' : '#4A90D9';
  const barWidth = Math.min(Math.max(pct, 0), 200);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{
        width: 80, height: 8, background: '#e0e0e0', borderRadius: 4, overflow: 'hidden',
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, height: '100%',
          width: `${barWidth / 2}%`,
          background: color,
          borderRadius: 4,
        }} />
        <div style={{
          position: 'absolute', left: '50%', top: 0, height: '100%',
          width: 1, background: '#888',
        }} />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 600 }}>{pct}%</span>
    </div>
  );
}

function DefaultBadge() {
  return (
    <span style={{
      fontSize: 10, padding: '1px 5px', borderRadius: 3,
      background: '#e8f0fe', color: '#3c4fa8', marginLeft: 4,
    }}>standard</span>
  );
}

function ControlSumBar({ sumPct, siteBiomass }) {
  const clamped = Math.min(sumPct, 100);
  const over = sumPct > 100;
  const full = Math.abs(sumPct - 100) < 0.5;
  const barColor = over ? '#ef5350' : full ? '#43a047' : '#1976d2';
  const leftPct = (100 - sumPct).toFixed(1);
  const usedTonnes = Math.round(sumPct * siteBiomass / 100);
  const leftTonnes = Math.round(siteBiomass - usedTonnes);

  return (
    <div className="cage-control-sum">
      <div className="cage-control-sum-label">
        Kontrollsum
        <span style={{ marginLeft: 8, fontWeight: 700, color: barColor }}>
          {sumPct.toFixed(1)}%
        </span>
        {over && (
          <span style={{ marginLeft: 8, fontSize: 11, color: '#ef5350', fontWeight: 600 }}>
            &#9888; Overskrider 100%!
          </span>
        )}
        {!over && !full && (
          <span style={{ marginLeft: 8, fontSize: 11, color: '#666' }}>
            ({leftPct}% ufordelt &#8776; {leftTonnes.toLocaleString('nb-NO')} t)
          </span>
        )}
        {full && (
          <span style={{ marginLeft: 8, fontSize: 11, color: '#43a047' }}>
            Fullt fordelt &#10003;
          </span>
        )}
      </div>
      <div className="cage-control-sum-bar-track">
        <div
          className="cage-control-sum-bar-fill"
          style={{ width: `${Math.min(clamped, 100)}%`, background: barColor }}
        />
      </div>
    </div>
  );
}

// ── Advanced fields (collapsible per cage) ─────────────────────────────────

function AdvancedCageFields({ cage, idx, cageType, onChange }) {
  const defaults = CAGE_TYPE_DEFAULT_SCORES[cageType] || {};

  const isComplexityDefault = cage.operational_complexity_score == null;
  const isCriticalityDefault = cage.structural_criticality_score == null;
  const isRedundancyDefault = cage.redundancy_level == null;
  const isFailureModeDefault = cage.failure_mode_class == null || cage.failure_mode_class === 'proportional';

  return (
    <div className="cage-advanced-fields">
      <div className="cage-adv-row">
        <label className="cage-adv-label">Konsekvensfaktor</label>
        <input
          type="number" min="0.1" max="5.0" step="0.05"
          value={cage.consequence_factor ?? 1.0}
          onChange={e => onChange(idx, 'consequence_factor', parseFloat(e.target.value) || 1.0)}
          className="cage-adv-input" style={{ width: 70 }}
        />
        {(cage.consequence_factor == null || cage.consequence_factor === 1.0) && <DefaultBadge />}
      </div>
      <div className="cage-adv-row">
        <label className="cage-adv-label">Biomasseverdi (NOK)</label>
        <input
          type="number" min="0" step="1000000" placeholder="Ikke satt"
          value={cage.biomass_value_nok ?? ''}
          onChange={e => {
            const v = e.target.value === '' ? null : parseFloat(e.target.value);
            onChange(idx, 'biomass_value_nok', v);
          }}
          className="cage-adv-input" style={{ width: 110 }}
        />
        {cage.biomass_value_nok == null && <DefaultBadge />}
      </div>
      <div className="cage-adv-row">
        <label className="cage-adv-label">Operasjonell kompleksitet</label>
        <input
          type="number" min="0" max="1" step="0.05"
          placeholder={`${defaults.complexity ?? 0.5} (std)`}
          value={cage.operational_complexity_score ?? ''}
          onChange={e => {
            const v = e.target.value === '' ? null : parseFloat(e.target.value);
            onChange(idx, 'operational_complexity_score', v);
          }}
          className="cage-adv-input" style={{ width: 70 }}
        />
        {isComplexityDefault && <DefaultBadge />}
      </div>
      <div className="cage-adv-row">
        <label className="cage-adv-label">Strukturell kritikalitet</label>
        <input
          type="number" min="0" max="1" step="0.05"
          placeholder={`${defaults.criticality ?? 0.5} (std)`}
          value={cage.structural_criticality_score ?? ''}
          onChange={e => {
            const v = e.target.value === '' ? null : parseFloat(e.target.value);
            onChange(idx, 'structural_criticality_score', v);
          }}
          className="cage-adv-input" style={{ width: 70 }}
        />
        {isCriticalityDefault && <DefaultBadge />}
      </div>
      <div className="cage-adv-row">
        <label className="cage-adv-label">
          <input
            type="checkbox"
            checked={cage.single_point_of_failure ?? false}
            onChange={e => onChange(idx, 'single_point_of_failure', e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Enkelt feilpunkt (SPOF)
        </label>
      </div>
      <div className="cage-adv-row">
        <label className="cage-adv-label">Redundansniv&#229;</label>
        <select
          value={cage.redundancy_level ?? defaults.redundancy_level ?? 3}
          onChange={e => {
            const v = parseInt(e.target.value, 10);
            onChange(idx, 'redundancy_level', v === defaults.redundancy_level ? null : v);
          }}
          className="cage-adv-select"
        >
          {REDUNDANCY_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        {isRedundancyDefault && <DefaultBadge />}
      </div>
      <div className="cage-adv-row">
        <label className="cage-adv-label">Feilmodus</label>
        <select
          value={cage.failure_mode_class ?? 'proportional'}
          onChange={e => {
            const v = e.target.value;
            onChange(idx, 'failure_mode_class', v === 'proportional' ? null : v);
          }}
          className="cage-adv-select"
        >
          {FAILURE_MODE_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        {isFailureModeDefault && <DefaultBadge />}
      </div>
    </div>
  );
}

// ── Counter for default cage IDs ───────────────────────────────────────────

let _cageCounter = 1;
function newCageId() { return `CAGE_${_cageCounter++}`; }

// ── Main component ─────────────────────────────────────────────────────────

export default function CagePortfolioPanel({ siteId, siteName, totalSiteBiomass = 0, cages, onChange }) {
  const uid = useId();
  const [expandedCages, setExpandedCages] = useState({});

  const safeCages = cages || [];
  const sumPct = safeCages.reduce((s, c) => s + (parseFloat(c.biomass_pct) || 0), 0);
  const overLimit = sumPct > 100.05;  // small epsilon for float rounding

  // Effective multipliers for the live preview — use biomass_tonnes (derived)
  const cagesForMults = safeCages
    .map(c => ({ ...c, biomass_tonnes: pctToTonnes(c.biomass_pct, totalSiteBiomass) }))
    .filter(c => c.biomass_tonnes > 0);
  const effectiveMults = computeLocalityDomainMultipliers(cagesForMults);

  function toggleAdvanced(cageKey) {
    setExpandedCages(prev => ({ ...prev, [cageKey]: !prev[cageKey] }));
  }

  function emit(updatedCages) {
    // Always keep biomass_tonnes in sync with pct × site total
    onChange(updatedCages.map(c => withComputedTonnes(c, totalSiteBiomass)));
  }

  function handleAddCage() {
    const newCage = {
      cage_id: newCageId(),
      cage_type: 'open_net',
      biomass_pct: 0,
      biomass_tonnes: 0,
      volume_m3: null,
    };
    emit([...safeCages, newCage]);
  }

  function handleRemoveCage(idx) {
    emit(safeCages.filter((_, i) => i !== idx));
  }

  function handleFieldChange(idx, field, value) {
    const updated = safeCages.map((c, i) => {
      if (i !== idx) return c;
      return withComputedTonnes({ ...c, [field]: value }, totalSiteBiomass);
    });
    onChange(updated);
  }

  function handleDistributeEvenly() {
    if (safeCages.length === 0) return;
    const perCage = +(100 / safeCages.length).toFixed(2);
    emit(safeCages.map((c, i) => ({
      ...c,
      biomass_pct: i === safeCages.length - 1
        ? +(100 - perCage * (safeCages.length - 1)).toFixed(2)
        : perCage,
    })));
  }

  function hasAdvancedData(cage) {
    return (
      (cage.biomass_value_nok != null) ||
      (cage.consequence_factor != null && cage.consequence_factor !== 1.0) ||
      cage.operational_complexity_score != null ||
      cage.structural_criticality_score != null ||
      cage.single_point_of_failure === true ||
      cage.redundancy_level != null ||
      (cage.failure_mode_class != null && cage.failure_mode_class !== 'proportional')
    );
  }

  const noSiteTotal = !totalSiteBiomass || totalSiteBiomass <= 0;

  return (
    <div className="cage-portfolio-panel">
      <div className="cage-portfolio-header">
        <span className="cage-portfolio-title">
          Merdportefolje &#8212; {siteName}
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          {safeCages.length > 1 && (
            <button
              type="button"
              className="cage-add-btn"
              style={{ background: '#f5f5f5', color: '#555' }}
              onClick={handleDistributeEvenly}
              title="Fordel biomasse jevnt mellom alle merder"
            >
              Fordel jevnt
            </button>
          )}
          <button type="button" className="cage-add-btn" onClick={handleAddCage}>
            + Legg til merd
          </button>
        </div>
      </div>

      {noSiteTotal && (
        <div style={{ fontSize: 11, color: '#b45309', background: '#fffbeb',
          border: '1px solid #fde68a', borderRadius: 4, padding: '4px 8px', marginBottom: 6 }}>
          Angi total biomasse for lokaliteten f&#248;rst for &#229; beregne merdandeler.
        </div>
      )}

      {safeCages.length === 0 ? (
        <div className="cage-empty-msg">
          Ingen merder konfigurert &#8212; lokaliteten behandles som homogen risikoenhet.
        </div>
      ) : (
        <>
          <table className="cage-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Teknologi</th>
                <th style={{ textAlign: 'right' }}>% av lok.</th>
                <th style={{ textAlign: 'right' }}>Biomasse (t)</th>
                <th></th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {safeCages.map((cage, idx) => {
                const meta = CAGE_TYPE_META[cage.cage_type] || {};
                const pct = parseFloat(cage.biomass_pct) || 0;
                const tonnes = pctToTonnes(pct, totalSiteBiomass);
                const isEmpty = pct === 0;
                const cageKey = cage.cage_id || idx;
                const isExpanded = expandedCages[cageKey];
                const hasAdv = hasAdvancedData(cage);

                return (
                  <React.Fragment key={cageKey}>
                    <tr style={{ opacity: isEmpty ? 0.6 : 1 }}>
                      <td>
                        <input
                          type="text"
                          value={cage.cage_id}
                          onChange={e => handleFieldChange(idx, 'cage_id', e.target.value)}
                          className="cage-id-input"
                          aria-label="Merd-ID"
                        />
                      </td>
                      <td>
                        <select
                          value={cage.cage_type}
                          onChange={e => handleFieldChange(idx, 'cage_type', e.target.value)}
                          className="cage-type-select"
                          aria-label="Teknologi"
                          style={{ borderLeft: `3px solid ${meta.color || '#ccc'}` }}
                        >
                          {CAGE_TYPES_ORDERED.map(ct => (
                            <option key={ct} value={ct}>{CAGE_TYPE_META[ct].label}</option>
                          ))}
                        </select>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="0.5"
                            value={pct}
                            onChange={e => handleFieldChange(idx, 'biomass_pct', parseFloat(e.target.value) || 0)}
                            className="cage-biomass-input"
                            style={{
                              width: 60, textAlign: 'right',
                              borderColor: overLimit ? '#ef5350' : undefined,
                            }}
                            aria-label="Prosentandel"
                          />
                          <span style={{ fontSize: 11, color: '#555' }}>%</span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right', fontSize: 12, color: isEmpty ? '#aaa' : '#333' }}>
                        {isEmpty
                          ? <span style={{ fontStyle: 'italic', fontSize: 11 }}>Tom</span>
                          : <>{tonnes.toLocaleString('nb-NO', { maximumFractionDigits: 0 })} t</>
                        }
                      </td>
                      <td>
                        <button
                          type="button"
                          className="cage-adv-toggle-btn"
                          onClick={() => toggleAdvanced(cageKey)}
                          title={isExpanded ? 'Skjul avanserte felt' : 'Vis avanserte felt'}
                          style={{ color: hasAdv ? '#3c4fa8' : '#888' }}
                        >
                          {isExpanded ? '&#9650;' : '&#9660;'} Avansert
                          {hasAdv && <span style={{ marginLeft: 4, fontSize: 9, color: '#3c4fa8' }}>&#9679;</span>}
                        </button>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="cage-remove-btn"
                          onClick={() => handleRemoveCage(idx)}
                          aria-label="Fjern merd"
                        >
                          &#215;
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="cage-advanced-row">
                        <td colSpan={6} style={{ padding: '0 8px 8px 24px' }}>
                          <AdvancedCageFields
                            cage={cage}
                            idx={idx}
                            cageType={cage.cage_type}
                            onChange={handleFieldChange}
                          />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>

          {/* Control sum */}
          <ControlSumBar sumPct={sumPct} siteBiomass={totalSiteBiomass} />

          {/* Effective multiplier summary */}
          {effectiveMults && !noSiteTotal && (
            <div className="cage-multiplier-summary">
              <div className="cage-multiplier-summary-title">Effektive domenemultiplikatorer (biomasseveid)</div>
              <div className="cage-multiplier-rows">
                {DOMAINS.map(domain => (
                  <div key={domain} className="cage-multiplier-row">
                    <span
                      className="cage-multiplier-domain-label"
                      style={{ color: DOMAIN_DISPLAY[domain]?.color }}
                    >
                      {DOMAIN_DISPLAY[domain]?.label || domain}
                    </span>
                    <MultiplierBar value={effectiveMults[domain]} />
                  </div>
                ))}
              </div>
              <div className="cage-biomass-total">
                Fordelt biomasse: <strong>
                  {Math.round(sumPct * totalSiteBiomass / 100).toLocaleString('nb-NO')} t
                </strong>
                {' '}av <strong>{totalSiteBiomass.toLocaleString('nb-NO')} t</strong> totalt
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
