const BASE = ''  // Vite proxy forwards /api and /static to localhost:8000

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

export async function fetchMitigationLibrary() {
  const res = await fetch(`${BASE}/api/mitigation/library`)
  if (!res.ok) throw new Error(`Library fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchExample() {
  const res = await fetch(`${BASE}/api/feasibility/example`, { method: 'POST' })
  if (!res.ok) throw new Error(`Example fetch failed: ${res.status}`)
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
