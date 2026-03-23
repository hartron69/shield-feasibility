# User Flow — C5AI+ Traceability Refinement

## Flow 1: Fresh run (happy path)

1. User opens app → Dashboard
2. Left panel shows C5AIStatusBar: **red dot "C5AI+ ikke kjørt"**
3. User clicks "Oppdater C5AI+" → spinner → green dot "C5AI+ oppdatert · [timestamp]"
4. User configures operator profile
5. User clicks "Kjør Feasibility" → runs immediately (no modal)
6. ResultPanel opens with:
   - Green trace strip: "Oppdatert · Basert på C5AI+ kjøring [id] · [timestamp]"
   - Chips: "Lokaliteter: 3" · "Simulert" · "4 domener"
   - Datakilde: "Simulert — demo data"
7. Below strip: "Anlegg i analysen (3)" collapsible toggle
8. User expands → table shows 3 sites with domain pills, EAL, SCR
9. User clicks "Se anlegg i C5AI+ Risiko →" → navigates to Risk Intelligence / Risiko tab

## Flow 2: Stale run (yellow path)

1. C5AI+ was run earlier → green status
2. User loads a new operator example → `notifyInputsUpdated()` fires → status becomes yellow
3. Left panel shows: **yellow dot "C5AI+ ikke oppdatert"**
4. RunControls shows yellow warning banner: "C5AI+ data er utdatert — oppdater for best resultat"
5. User clicks "Kjør Feasibility" → **stale modal appears**:
   - "C5AI+-data er utdatert. Feasibility-analysen vil bruke et risikobilde..."
   - Button: "Oppdater C5AI+ først" (primary)
   - Button: "Kjør likevel" (secondary)
   - Button: "Avbryt" (ghost)
6a. User clicks "Oppdater C5AI+ først" → modal closes, C5AI+ runs, status turns green
6b. User clicks "Kjør likevel" → modal closes, feasibility runs immediately
    - ResultPanel trace strip shows **yellow "Utdatert"** badge + warning text

## Flow 3: Missing run (blocked path)

1. Fresh backend session → C5AI+ never run
2. Left panel: **red dot "C5AI+ ikke kjørt"**
3. RunControls: yellow warning banner "C5AI+ ikke kjørt — klikk «Oppdater C5AI+»..."
4. User clicks "Kjør Feasibility" → **missing modal appears** (no "Kjør likevel" button)
5. User must either click "Oppdater C5AI+ først" or "Avbryt"
6. ResultPanel (if run despite missing) shows **red "Ikke kjørt"** trace strip

## Site trace panel detail

When expanded, the "Anlegg i analysen" panel shows:

| Anlegg | Domene | Forv. tap/år | SCR-bidrag |
|---|---|---|---|
| Site-1 | 🟢 biological | NOK 8.5M | NOK 44.7M |
| Site-2 | 🟢 biological | NOK 7.7M | NOK 40.5M |
| Site-3 | 🟢 biological | NOK 6.4M | NOK 49.0M |

Footer note: "EAL er eksakt (Monte Carlo). SCR-bidrag er proporsjonal approksimering."
