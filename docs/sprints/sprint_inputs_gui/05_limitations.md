# Sprint – Inputs GUI: Limitations

## 1. All data is mock / simulated
`mockInputsData.js` contains hard-coded demo values consistent with Nordic Aqua
Partners AS (3 sites, 9,200 t). No API routes exist for:
- `GET /api/inputs/site-profiles`
- `GET /api/inputs/biological/{site_id}`
- `GET /api/inputs/signals/{site_id}`
- `GET /api/inputs/quality/{site_id}`
- `POST /api/c5ai/scenario`

Backend wiring is a future sprint item.

## 2. Scenario "Run" is a stub
The ScenarioOverridePanel computes a rough linear scale factor estimate client-side
(~900ms timeout) instead of invoking the Monte Carlo engine. The result is labelled
as "Estimate" and includes a note pointing to the future API route.

## 3. No frontend unit tests
No Jest/Vitest tests were added for the new components. Manual checklist is in
`04_tests.md`. This is acceptable for a prototype sprint; unit tests should be
added before production deployment.

## 4. Mitigation nav item not created
The nav includes no standalone "Mitigation" page — mitigations remain in the
left accordion panel on the PCC Feasibility page, which is where operators
configure them. A future sprint could add a read-only MitigationLibraryPage.

## 5. Biological inputs are per-site snapshots only
No time-series visualisation. Historical trends require data upload or API
integration. The panel shows point-in-time readings only.

## 6. Alert Signals are not wired to live alert engine output
The `MOCK_ALERT_SIGNALS` array is constructed manually. In production the signals
should come from `AlertEngine.generate_alerts()` via an API route so they reflect
real-time precursor detector output.

## 7. Left panel still visible on Strategy Comparison page
By design (strategy inputs are in the accordion), but may be confusing since
the Strategy Comparison page shows static illustrative values, not results
scoped to the left panel's current operator. This will improve once
`/api/feasibility/run` results are passed to `StrategyComparisonPage`.
