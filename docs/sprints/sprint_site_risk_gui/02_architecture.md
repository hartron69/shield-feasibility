# Sprint Site Risk GUI — Architecture Notes

## Component Hierarchy

```
App.jsx
│
├── OverviewPage.jsx               ← MODIFIED
│   ├── (imports) SMOLT_SITE_RISK, SMOLT_DOMAIN_META
│   ├── SiteRiskDetailPanel        ← NEW (inline detail)
│   └── [inline card rendering — top 3]
│
└── C5AIModule.jsx                 ← MODIFIED (tab 8 added)
    └── SmoltSiteRiskTab.jsx       ← NEW
        ├── SiteRiskSummaryCards.jsx  ← NEW
        ├── TopRiskSitesTable.jsx     ← NEW
        ├── SiteEALChart.jsx          ← NEW (SVG)
        ├── SiteSCRContributionChart.jsx ← NEW (SVG)
        └── SiteRiskDetailPanel.jsx   ← NEW (shared)
```

## Data Flow

```
mockSmoltSiteRiskData.js
  SMOLT_SITE_RISK[]        → all components (direct import, mock phase)
  SMOLT_SITE_RISK_SUMMARY  → SmoltSiteRiskTab KPI row
  SMOLT_DOMAIN_META        → colors + labels in all components
```

## State

- `selectedSmoltId: string | null` — which facility is expanded in detail panel
  - Lives in OverviewPage (for Overview section)
  - Lives in SmoltSiteRiskTab (for C5AI+ Anlegg tab)
  - Passed down as `selectedId` + `onSelect` to SiteRiskSummaryCards and TopRiskSitesTable
- `view: 'table' | 'charts'` — toggle in SmoltSiteRiskTab only

## Backend Wiring Path (future)

When `/api/feasibility/smolt/sites/risk` is implemented:

```
App.jsx
  const [smoltSiteRisk, setSmoltSiteRisk] = useState(SMOLT_SITE_RISK)   // fallback to mock
  // fetch on smolt run completion, store in smoltSiteRisk
  // pass as prop: <C5AIModule smoltSiteRisk={smoltSiteRisk} />
  //               <OverviewPage smoltSiteRisk={smoltSiteRisk} />
```

Components accept optional `sites` prop, falling back to mock import if not provided.
This keeps backward compatibility during rollout.
