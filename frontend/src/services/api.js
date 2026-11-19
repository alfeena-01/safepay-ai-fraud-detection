const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

function queryString(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const result = query.toString();
  return result ? `?${result}` : "";
}

export const api = {
  dashboard: () => request("/dashboard/metrics"),
  datasetSummary: () => request("/dataset/summary"),
  uploadDataset: (file) => {
    const body = new FormData();
    body.append("file", file);
    return request("/dataset/upload", { method: "POST", body });
  },
  transactions: (filters = {}) => request(`/transactions/${queryString(filters)}`),
  transaction: (id) => request(`/transactions/${id}`),
  analyze: (id) => request(`/transactions/${id}/analyze`, { method: "POST" }),
  alerts: () => request("/alerts/"),
  network: (accountId) => request(`/accounts/${encodeURIComponent(accountId)}/network`),
  cases: () => request("/cases/"),
  createCase: (payload) => request("/cases/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
  updateCase: (id, payload) => request(`/cases/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
  addCaseNote: (id, note) => request(`/cases/${id}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  }),
  reports: () => request("/reports/"),
  createReport: (payload) => request("/reports/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
};
