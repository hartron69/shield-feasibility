const BASE = ''  // Vite proxy forwards /api and /static to localhost:8000

export async function runC5AI() {
  const res = await fetch(`${BASE}/api/c5ai/run`, { method: 'POST' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`C5AI+ run failed (${res.status}): ${text}`)
  }
  return res.json()
}

export async function fetchC5AIStatus() {
  const res = await fetch(`${BASE}/api/c5ai/status`)
  if (!res.ok) throw new Error(`C5AI status fetch failed: ${res.status}`)
  return res.json()
}

export async function notifyInputsUpdated() {
  // Best-effort — ignore errors (backend may not be running)
  try {
    await fetch(`${BASE}/api/c5ai/inputs/updated`, { method: 'POST' })
  } catch {}
}

export async function fetchSmoltExample() {
  const res = await fetch(`${BASE}/api/feasibility/smolt/example/agaqua`)
  if (!res.ok) throw new Error(`Smolt example fetch failed: ${res.status}`)
  return res.json()
}

export async function runSmoltFeasibility(payload) {
  const res = await fetch(`${BASE}/api/feasibility/smolt/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Smolt run failed (${res.status}): ${text}`)
  }
  return res.json()
}

export async function fetchMitigationLibrary(facilityType = 'sea') {
  const res = await fetch(`${BASE}/api/mitigation/library?facility_type=${facilityType}`)
  if (!res.ok) throw new Error(`Library fetch failed: ${res.status}`)
  return res.json()
}

export async function runScenario(params) {
  const res = await fetch(`${BASE}/api/c5ai/scenario`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Scenario run failed (${res.status}): ${text}`)
  }
  return res.json()
}

export async function fetchExample() {
  const res = await fetch(`${BASE}/api/feasibility/example`, { method: 'POST' })
  if (!res.ok) throw new Error(`Example fetch failed: ${res.status}`)
  return res.json()
}

export async function triggerBWPrefetch() {
  const res = await fetch(`${BASE}/api/c5ai/prefetch`, { method: 'POST' })
  if (!res.ok) throw new Error(`BW prefetch failed: ${res.status}`)
  return res.json()
}

export async function fetchBWDataStatus() {
  const res = await fetch(`${BASE}/api/c5ai/bw/data-status`)
  if (!res.ok) throw new Error(`BW data status failed: ${res.status}`)
  return res.json()
}

export async function fetchSiteRegistry() {
  const res = await fetch(`${BASE}/api/c5ai/site-registry`)
  if (!res.ok) throw new Error(`Site registry fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchInputsAudit() {
  const res = await fetch(`${BASE}/api/inputs/audit`)
  if (!res.ok) throw new Error(`Inputs audit fetch failed: ${res.status}`)
  return res.json()
}

export async function runFeasibility(payload) {
  const res = await fetch(`${BASE}/api/feasibility/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Run failed (${res.status}): ${text}`)
  }
  return res.json()
}
