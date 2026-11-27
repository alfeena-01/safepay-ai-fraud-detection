const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api").replace(/\/$/, "");

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = sessionStorage.getItem("safepay_access_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("Unable to reach the SafePay API. Check that the backend is running, then try again.");
    }
    throw error;
  }
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
  login: (payload) => request("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  register: (payload) => request("/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  me: () => request("/auth/me"),
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
  analyzeBatch: (limit = 100) => request(`/transactions/analyze-batch?limit=${limit}`, { method: "POST" }),
  accountBehavior: (accountId) => request(`/accounts/${encodeURIComponent(accountId)}/behavior`),
  alerts: (limit = 10) => request(`/alerts/?limit=${limit}`),
  updateAlert: (id, status) => request(`/alerts/${id}?status=${encodeURIComponent(status)}`, { method: "PATCH" }),
  liveTransactions: (limit = 10) => request(`/transactions/live?limit=${limit}`),
  network: (accountId, depth = 1) => request(`/accounts/${encodeURIComponent(accountId)}/network?depth=${depth}`),
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
