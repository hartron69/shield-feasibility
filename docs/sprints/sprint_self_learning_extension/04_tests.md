# Self-Learning Extension – Test Results

## Summary

| Metric | Value |
|---|---|
| Test file | `tests/test_learning_loop.py` |
| New tests | 66 |
| Full suite (after sprint) | 1028 passed, 0 failed, 38 warnings |
| Full suite (before sprint) | 826 passed |
| Runtime (new test file only) | ~11 s |
| Runtime (full suite) | ~36 s |

---

## Test Classes

### `TestPredictionStore` — 6 tests
| Test | What it verifies |
|---|---|
| `test_save_and_load_round_trip` | All fields survive JSON serialisation |
| `test_load_missing_returns_none` | Non-existent key → None, no exception |
| `test_save_multiple_risk_types` | 4 risk types stored and recalled correctly |
| `test_overwrite_same_key` | Second save replaces first (idempotent) |
| `test_list_years` | Returns sorted year list for a given risk type |
| `test_load_all_empty_operator` | Unknown operator → empty list, no exception |

---

### `TestEventStore` — 6 tests
| Test | What it verifies |
|---|---|
| `test_save_and_load_round_trip` | Fields survive JSON round-trip |
| `test_load_missing_returns_none` | Missing file → None |
| `test_save_merges_risk_types` | Two saves for same year merge correctly |
| `test_matched_pairs_join` | Inner-join on (risk_type, year) works |
| `test_matched_pairs_empty_when_no_overlap` | Mismatched years → empty list |
| `test_load_all_accumulates_years` | load_all spans multiple year files |

---

### `TestBetaBinomialModel` — 8 tests
| Test | What it verifies |
|---|---|
| `test_prior_mean_equals_prior_prob` | Prior(0.20) → predict() = 0.20 exactly |
| `test_update_event_shifts_probability_up` | Positive update increases probability |
| `test_update_no_event_shifts_probability_down` | Negative update decreases probability |
| `test_version_increments_on_update` | Version string changes after each update |
| `test_many_events_converges_to_high_probability` | 50 events → P > 0.80 |
| `test_many_no_events_converges_to_low_probability` | 50 non-events → P < 0.20 |
| `test_serialise_round_trip` | to_dict / from_dict preserves probability and version |
| `test_predict_always_in_unit_interval` | predict() ∈ [0, 1] after 20 alternating updates |

---

### `TestLogNormalSeverityModel` — 6 tests
| Test | What it verifies |
|---|---|
| `test_prior_p50_less_than_mean_less_than_p90` | LogNormal ordering property |
| `test_update_increments_n_obs` | n_obs counter increments correctly |
| `test_update_shifts_mean_toward_data` | 5 small losses pull E[loss] below prior |
| `test_version_increments_on_update` | Version string changes on update |
| `test_serialise_round_trip` | to_dict / from_dict preserves fitted state |
| `test_ignores_nonpositive_losses` | update(0) and update(-100) → n_obs still 0 |

---

### `TestEvaluator` — 8 tests
| Test | What it verifies |
|---|---|
| `test_perfect_predictor_brier_zero` | p=1 when y=1, p=0 when y=0 → Brier = 0.0 |
| `test_uninformative_predictor_brier_025` | p=0.5 always → Brier = 0.25 |
| `test_empty_pairs_returns_default_metrics` | 0 pairs → default EvaluationMetrics, no exception |
| `test_severity_mae_correct` | Predicted 600k, actuals 400k/800k → MAE = 200k |
| `test_should_retrain_when_sufficient_samples` | n=10, Brier=0.15 → retrain = True |
| `test_should_not_retrain_when_too_few_samples` | n=2 → retrain = False regardless of Brier |
| `test_is_shadow_better_detects_improvement` | Shadow Brier 0.12 vs current 0.20, n=15 → True |
| `test_is_shadow_not_better_when_insufficient_samples` | Shadow n=5 < threshold → False |

---

### `TestSiteDataSimulator` — 8 tests
| Test | What it verifies |
|---|---|
| `test_generates_valid_operator_input` | Returns C5AIOperatorInput with correct site count |
| `test_temperature_has_seasonal_pattern` | Summer > winter temperature |
| `test_lice_counts_in_reasonable_range` | avg_lice_per_fish ∈ [0, 10) |
| `test_hab_alerts_summer_skewed` | > 50% of HAB alerts in months 4–9 |
| `test_multiple_sites_have_unique_ids` | No duplicate site IDs |
| `test_forecast_years_default` | forecast_years = 5 |
| `test_reproducible_with_same_seed` | Same seed → identical observations |
| `test_jellyfish_density_positive` | density_index ≥ 0 always |

---

### `TestEventSimulator` — 6 tests
| Test | What it verifies |
|---|---|
| `test_p1_always_event` | P=1.0 → all events occur |
| `test_p0_never_event` | P=0.0 → no events occur |
| `test_loss_zero_when_no_event` | actual_loss_nok = 0 when not occurred |
| `test_loss_positive_when_event` | actual_loss_nok > 0 when P=1 and mean > 0 |
| `test_multi_year_returns_all_years` | Keys = {2020, 2021, 2022} for 3-year run |
| `test_events_have_correct_operator_id` | operator_id propagated correctly |

---

### `TestRetrainingPipeline` — 6 tests
| Test | What it verifies |
|---|---|
| `test_no_events_returns_none` | No stored events → returns None, no exception |
| `test_small_sample_uses_beta_binomial` | n=5 → BetaBinomialModel (not RF) |
| `test_shadow_registered_after_retrain` | get_shadow_model returns model after retrain |
| `test_retrain_all_covers_all_risk_types` | retrain_all keys = {hab, lice, jellyfish, pathogen} |
| `test_model_probability_in_unit_interval` | predict() ∈ [0, 1] after retrain |
| `test_retrain_when_no_data_for_type_returns_false` | Missing risk type → False in result dict |

---

### `TestLearningLoop` — 12 tests
| Test | What it verifies |
|---|---|
| `test_first_cycle_cold_status` | Cycle 0 → status = "cold" |
| `test_cycle_id_increments` | Second cycle has cycle_id = first + 1 |
| `test_warming_status_after_3_cycles` | 3 cycles → "warming" |
| `test_active_status_after_10_cycles` | 10 cycles → "active" |
| `test_metrics_for_all_risk_types` | metrics_by_risk_type has all 4 keys |
| `test_brier_score_in_unit_interval` | Brier ∈ [0, 1] for all risk types after 3 cycles |
| `test_adjusted_probability_set_after_first_cycle` | baseline + adjusted populated |
| `test_adjusted_differs_from_baseline_after_many_cycles` | Registry updated, predict() runs |
| `test_pcc_compatibility_scale_factor_unchanged` | scale_factor identical before/after cycle |
| `test_result_is_learning_cycle_result` | Return type correct |
| `test_to_dict_serialisable` | result.to_dict() is JSON-serialisable |
| `test_provided_events_used_over_simulated` | Manual event with known loss stored correctly |

---

## Running the Tests

```bash
# New tests only
pytest tests/test_learning_loop.py -v

# Full suite
pytest tests/ -q

# With coverage (if pytest-cov installed)
pytest tests/test_learning_loop.py --cov=c5ai_plus.learning --cov=c5ai_plus.models \
       --cov=c5ai_plus.simulation --cov-report=term-missing
```
