import { useEffect, useMemo, useState } from "react";

import { api } from "./services/api.js";

const navigation = [
  { id: "dashboard", label: "Dashboard", mark: "OV" },
  { id: "transactions", label: "Transaction Monitoring", mark: "TX" },
  { id: "risk", label: "Risk Analysis", mark: "RA" },
  { id: "network", label: "Account Network", mark: "AN" },
  { id: "cases", label: "Investigation Cases", mark: "IC" },
  { id: "reports", label: "Investigation Reports", mark: "IR" },
];

const currency = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});
const amount = (value) => currency.format(value || 0);
const percentage = (value) => `${((value || 0) * 100).toFixed(1)}%`;
const displayDate = (value) => value ? new Date(value).toLocaleString() : "—";

function PageTitle({ eyebrow, title, detail, action }) {
  return (
    <div className="page-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {detail && <p className="muted">{detail}</p>}
      </div>
      {action}
    </div>
  );
}

function Message({ error, loading, children }) {
  if (loading) return <div className="message"><span className="spinner" /> Loading SafePay data…</div>;
  if (error) return <div className="message error-message" role="alert">{error}</div>;
  return children;
}

function StatCard({ label, value, caption, accent = "blue" }) {
  return (
    <article className={`stat-card accent-${accent}`}>
      <div className="stat-top"><span>{label}</span><span className="stat-dot" /></div>
      <strong>{value}</strong>
      <small>{caption}</small>
    </article>
  );
}

function ActivityChart({ data = [] }) {
  const width = 660;
  const height = 190;
  const max = Math.max(...data.map((point) => point.count), 1);
  const points = data.map((point, index) => {
    const x = data.length < 2 ? width / 2 : 16 + (index * (width - 32)) / (data.length - 1);
    const y = height - 20 - (point.count / max) * (height - 42);
    return `${x},${y}`;
  }).join(" ");
  return (
    <div className="chart-wrap">
      {data.length ? (
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Transaction activity by step">
          {[0, 1, 2, 3].map((line) => <line key={line} x1="0" x2={width} y1={25 + line * 43} y2={25 + line * 43} className="chart-grid" />)}
          <polyline points={points} fill="none" className="activity-line" />
          {data.map((point, index) => {
            const x = data.length < 2 ? width / 2 : 16 + (index * (width - 32)) / (data.length - 1);
            const y = height - 20 - (point.count / max) * (height - 42);
            return <circle key={`${point.step}-${index}`} cx={x} cy={y} r="3.5" className="activity-point"><title>{`Step ${point.step}: ${point.count} transactions`}</title></circle>;
          })}
        </svg>
      ) : <div className="chart-empty">Upload a dataset to see transaction activity.</div>}
      {data.length > 0 && <div className="chart-foot"><span>Earlier steps</span><span>Transaction steps</span><span>Latest steps</span></div>}
    </div>
  );
}

function RiskDistribution({ data = [] }) {
  const values = ["high", "medium", "low"].map((level) => ({
    level,
    count: data.find((item) => item.risk_level === level)?.count || 0,
  }));
  const maximum = Math.max(...values.map((item) => item.count), 1);
  return (
    <div className="distribution">
      {values.map((item) => (
        <div className="distribution-row" key={item.level}>
          <div className="distribution-label"><span className={`risk-dot ${item.level}`} />{item.level}<strong>{item.count}</strong></div>
          <div className="bar-track"><div className={`bar-fill ${item.level}`} style={{ width: `${(item.count / maximum) * 100}%` }} /></div>
        </div>
      ))}
      {!data.length && <p className="muted small">Run transaction analysis to populate risk distribution.</p>}
    </div>
  );
}

function DashboardPage() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.dashboard().then(setMetrics).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  }, []);
  return (
    <section>
      <PageTitle eyebrow="OVERVIEW" title="Dashboard" detail="A live view of transactions, emerging risk, and investigation activity." />
      <Message loading={loading} error={error}>
        {metrics && <>
          <div className="stat-grid">
            <StatCard label="Total transactions" value={metrics.total_transactions.toLocaleString()} caption={`${amount(metrics.total_amount)} total value`} />
            <StatCard label="Fraud labels" value={metrics.fraud_transactions.toLocaleString()} caption={`${percentage(metrics.fraud_rate)} of uploaded rows`} accent="cyan" />
            <StatCard label="High-risk transactions" value={metrics.high_risk_transactions.toLocaleString()} caption="Demo analyses requiring review" accent="orange" />
            <StatCard label="Open alerts" value={metrics.open_alerts.toLocaleString()} caption="Awaiting analyst attention" accent="red" />
          </div>
          <div className="panel-grid">
            <article className="panel wide-panel">
              <div className="panel-heading"><div><h2>Transaction activity</h2><p>Recorded activity by dataset step</p></div><span className="legend"><i /> Transactions</span></div>
              <ActivityChart data={metrics.activity} />
            </article>
            <article className="panel">
              <div className="panel-heading"><div><h2>Risk distribution</h2><p>Saved demo risk assessments</p></div></div>
              <RiskDistribution data={metrics.risk_distribution} />
              <div className="demo-banner">Demo heuristic results are illustrative, not model predictions.</div>
            </article>
          </div>
        </>}
      </Message>
    </section>
  );
}

function TransactionsPage({ goToRisk }) {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [fraudOnly, setFraudOnly] = useState("");
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploading, setUploading] = useState(false);

  const loadRows = () => {
    setLoading(true);
    setError("");
    api.transactions({
      q: query,
      transaction_type: type,
      risk_level: riskLevel,
      fraud_only: fraudOnly === "true" ? true : fraudOnly === "false" ? false : undefined,
      limit: 50,
    })
      .then(setRows).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
    api.datasetSummary().then(setSummary).catch((reason) => setError(reason.message));
  };
  useEffect(() => { loadRows(); }, [query, type, riskLevel, fraudOnly]);
  useEffect(() => {
    if (!selected) return;
    api.transaction(selected).then(setDetail).catch((reason) => setError(reason.message));
  }, [selected]);

  async function uploadFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const result = await api.uploadDataset(file);
      setNotice(`${result.inserted.toLocaleString()} rows imported; ${result.duplicates_skipped.toLocaleString()} duplicates skipped.`);
      loadRows();
    } catch (reason) {
      setError(reason.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <section>
      <PageTitle eyebrow="MONITORING" title="Transaction monitoring" detail="Search, review, and import PaySim-compatible transaction data."
        action={<label className={`button primary upload-button ${uploading ? "disabled" : ""}`}>{uploading ? "Uploading…" : "Upload CSV"}<input type="file" accept=".csv,text/csv" disabled={uploading} onChange={uploadFile} /></label>} />
      {summary && <div className="summary-strip"><span><strong>{summary.total_transactions.toLocaleString()}</strong> records</span><span><strong>{amount(summary.total_amount)}</strong> total amount</span><span><strong>{summary.fraud_transactions.toLocaleString()}</strong> fraud labels</span></div>}
      {notice && <div className="notice" role="status">{notice}</div>}
      {error && <div className="message error-message" role="alert">{error}</div>}
      <div className="panel table-panel">
        <div className="filters">
          <label className="search-field"><span>Search</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Transaction or account ID" /></label>
          <label className="select-field"><span>Type</span><select value={type} onChange={(event) => setType(event.target.value)}><option value="">All types</option><option>TRANSFER</option><option>CASH_OUT</option><option>PAYMENT</option><option>CASH_IN</option><option>DEBIT</option></select></label>
          <label className="select-field"><span>Risk</span><select value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)}><option value="">All risk levels</option><option value="high">High risk</option><option value="medium">Medium risk</option><option value="low">Low risk</option></select></label>
          <label className="select-field"><span>Fraud label</span><select value={fraudOnly} onChange={(event) => setFraudOnly(event.target.value)}><option value="">All labels</option><option value="true">Fraud only</option><option value="false">Non-fraud only</option></select></label>
          <span className="row-count">{rows.length} shown · up to 50</span>
        </div>
        <Message loading={loading}>
          <div className="table-scroll"><table><thead><tr><th>Transaction</th><th>Type</th><th>Amount</th><th>Sender</th><th>Receiver</th><th>Label</th><th /></tr></thead>
            <tbody>{rows.map((row) => <tr key={row.id} onClick={() => setSelected(row.id)} className="clickable-row">
              <td className="mono">{row.transaction_id}</td><td><span className="type-pill">{row.transaction_type}</span></td><td>{amount(row.amount)}</td>
              <td className="mono truncate">{row.name_orig || "—"}</td><td className="mono truncate">{row.name_dest || "—"}</td>
              <td><span className={`status-pill ${row.is_fraud ? "danger" : "neutral"}`}>{row.is_fraud ? "Fraud label" : "No label"}</span></td><td className="arrow">›</td>
            </tr>)}</tbody>
          </table></div>
          {!rows.length && <div className="empty-state">No transactions found. Upload a CSV to get started.</div>}
        </Message>
      </div>
      {selected && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) { setSelected(null); setDetail(null); } }}>
        <article className="modal panel">
          <div className="modal-head"><div><p className="eyebrow">TRANSACTION DETAIL</p><h2>{detail?.transaction_id || "Loading…"}</h2></div><button className="icon-button" onClick={() => { setSelected(null); setDetail(null); }} aria-label="Close details">×</button></div>
          {detail && <>
            <div className="detail-grid"><div><small>Type</small><strong>{detail.transaction_type}</strong></div><div><small>Amount</small><strong>{amount(detail.amount)}</strong></div><div><small>Sender</small><strong className="mono">{detail.name_orig || "—"}</strong></div><div><small>Receiver</small><strong className="mono">{detail.name_dest || "—"}</strong></div><div><small>Fraud label</small><strong>{detail.is_fraud ? "Yes" : "No"}</strong></div><div><small>Recorded</small><strong>{displayDate(detail.created_at)}</strong></div></div>
            {detail.risk_assessment && <div className="inline-risk">Saved risk assessment: <strong>{detail.risk_assessment.risk_level}</strong> · {detail.risk_assessment.overall_risk_score}/100</div>}
            <div className="modal-actions"><button className="button primary" onClick={() => goToRisk(selected)}>Open risk analysis</button><button className="button secondary" onClick={() => setSelected(null)}>Close</button></div>
          </>}
        </article>
      </div>}
    </section>
  );
}

function RiskPage({ initialTransaction }) {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState("");
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api.transactions({ limit: 100 }).then((result) => {
      setRows(result);
      if (result.length) setSelected(String(initialTransaction || result[0].id));
    }).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  }, [initialTransaction]);
  async function analyze() {
    if (!selected) return;
    setAnalyzing(true);
    setError("");
    try {
      setRisk(await api.analyze(selected));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setAnalyzing(false);
    }
  }
  return (
    <section>
      <PageTitle eyebrow="DECISION SUPPORT" title="Risk analysis" detail="Inspect risk signals and recommended review actions for a transaction." />
      <div className="demo-banner prominent">Sample scoring only — demo heuristic, not a trained or calibrated fraud model.</div>
      <div className="panel analysis-picker"><label className="select-field"><span>Transaction</span><select value={selected} onChange={(event) => { setSelected(event.target.value); setRisk(null); }}><option value="">Choose transaction</option>{rows.map((row) => <option key={row.id} value={row.id}>{row.transaction_id} · {row.transaction_type} · {amount(row.amount)}</option>)}</select></label><button className="button primary" onClick={analyze} disabled={!selected || analyzing}>{analyzing ? "Analyzing…" : "Run demo analysis"}</button></div>
      {loading && <div className="message"><span className="spinner" /> Loading transactions…</div>}
      {error && <div className="message error-message" role="alert">{error}</div>}
      {!loading && !rows.length && <div className="empty-state panel">Upload transactions before running risk analysis.</div>}
      {risk && <div className="panel risk-result">
        <div className="risk-score-head"><div><p className="eyebrow">OVERALL RISK SCORE</p><div className={`score-value ${risk.risk_level}`}>{risk.overall_risk_score}<span>/100</span></div></div><span className={`status-pill ${risk.risk_level}`}>{risk.risk_level} risk</span></div>
        <div className="score-grid">
          <ScoreBar label="Fraud probability" value={risk.fraud_probability * 100} display={percentage(risk.fraud_probability)} />
          <ScoreBar label="Anomaly score" value={risk.anomaly_score * 100} display={percentage(risk.anomaly_score)} />
          <ScoreBar label="Graph risk" value={risk.graph_risk * 100} display={percentage(risk.graph_risk)} />
        </div>
        <div className="explanation-box"><h3>Risk explanation</h3><p>{risk.explanation}</p><h3>Recommended action</h3><p>{risk.recommended_action}</p></div>
        <small className="model-footnote">Analysis source: {risk.model_version} · {displayDate(risk.assessed_at)}</small>
      </div>}
    </section>
  );
}

function ScoreBar({ label, value, display }) {
  return <div className="score-bar"><div><span>{label}</span><strong>{display}</strong></div><div className="bar-track"><div className="bar-fill blue" style={{ width: `${Math.min(value, 100)}%` }} /></div></div>;
}

function NetworkPage() {
  const [accountId, setAccountId] = useState("");
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function search(event) {
    event.preventDefault();
    if (!accountId.trim()) return;
    setLoading(true);
    setError("");
    try {
      setGraph(await api.network(accountId.trim()));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }
  const nodes = graph?.connected_accounts || [];
  const center = { x: 250, y: 170 };
  const positions = useMemo(() => nodes.map((node, index) => {
    const angle = (2 * Math.PI * index) / Math.max(nodes.length, 1) - Math.PI / 2;
    return { ...node, x: center.x + 150 * Math.cos(angle), y: center.y + 110 * Math.sin(angle) };
  }), [nodes]);
  return (
    <section>
      <PageTitle eyebrow="RELATIONSHIP INTELLIGENCE" title="Account network" detail="Explore sender and receiver links across uploaded transactions." />
      <form className="panel network-search" onSubmit={search}><label className="search-field"><span>Account ID</span><input value={accountId} onChange={(event) => setAccountId(event.target.value)} placeholder="For example, an account from your dataset" /></label><button className="button primary" disabled={loading}>{loading ? "Searching…" : "Analyze network"}</button></form>
      {error && <div className="message error-message" role="alert">{error}</div>}
      {graph && <>
        <div className="stat-grid network-stats"><StatCard label="Connected transactions" value={graph.transaction_count} caption="Direct sender/receiver links" /><StatCard label="Connected accounts" value={nodes.length} caption="Distinct counterparties" accent="cyan" /><StatCard label="Suspicious connections" value={graph.suspicious_connections} caption="Fraud label or high demo score" accent="orange" /></div>
        <div className="panel network-panel"><div className="panel-heading"><div><h2>Network visualization</h2><p>{graph.truncated ? "Showing the most recent 200 transactions." : "Direct account connections from the dataset."}</p></div></div>
          {nodes.length ? <svg className="network-svg" viewBox="0 0 500 340" role="img" aria-label={`Account network centered on ${graph.account_id}`}>
            {positions.map((node) => <line key={`line-${node.account_id}`} x1={center.x} y1={center.y} x2={node.x} y2={node.y} className={graph.edges.some((edge) => edge.suspicious && (edge.from === node.account_id || edge.to === node.account_id)) ? "network-edge suspicious" : "network-edge"} />)}
            <circle cx={center.x} cy={center.y} r="36" className="network-node central" /><text x={center.x} y={center.y + 4} className="network-label center-label">{graph.account_id.slice(0, 12)}</text>
            {positions.map((node) => <g key={node.account_id}><circle cx={node.x} cy={node.y} r="25" className="network-node" /><text x={node.x} y={node.y + 4} className="network-label">{node.account_id.slice(0, 9)}</text></g>)}
          </svg> : <div className="empty-state">No connected accounts found for this ID.</div>}
          <div className="connection-list">{nodes.slice(0, 8).map((node) => <div key={node.account_id}><span className="risk-dot blue-dot" /><span className="mono">{node.account_id}</span><small>{node.transaction_count} tx · {amount(node.total_amount)}</small></div>)}</div>
        </div>
      </>}
    </section>
  );
}

function CasesPage() {
  const [cases, setCases] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [form, setForm] = useState({ title: "", description: "", transaction_id: "", priority: "medium" });
  const [notes, setNotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const reload = () => api.cases().then(setCases).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  useEffect(() => {
    reload();
    api.transactions({ limit: 100 }).then(setTransactions).catch((reason) => setError(reason.message));
  }, []);
  async function create(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createCase({ ...form, transaction_id: form.transaction_id ? Number(form.transaction_id) : null });
      setForm({ title: "", description: "", transaction_id: "", priority: "medium" });
      setNotice("Investigation case created.");
      reload();
    } catch (reason) {
      setError(reason.message);
    } finally {
      setSaving(false);
    }
  }
  async function changeStatus(id, status) {
    try {
      await api.updateCase(id, { status });
      reload();
    } catch (reason) { setError(reason.message); }
  }
  async function addNote(id) {
    if (!notes[id]?.trim()) return;
    try {
      await api.addCaseNote(id, notes[id].trim());
      setNotes({ ...notes, [id]: "" });
      setNotice("Investigation note added.");
      reload();
    } catch (reason) { setError(reason.message); }
  }
  return (
    <section>
      <PageTitle eyebrow="CASE MANAGEMENT" title="Investigation cases" detail="Create a case, track its status, and keep an auditable note trail." />
      <form className="panel create-form" onSubmit={create}><div className="form-heading"><h2>New investigation</h2><span className="muted small">Required fields are marked</span></div>
        <div className="form-grid"><label>Case title *<input required minLength="3" maxLength="255" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Describe the investigation" /></label>
          <label>Priority<select value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })}><option>low</option><option>medium</option><option>high</option><option>critical</option></select></label>
          <label>Linked transaction<select value={form.transaction_id} onChange={(event) => setForm({ ...form, transaction_id: event.target.value })}><option value="">No linked transaction</option>{transactions.map((tx) => <option key={tx.id} value={tx.id}>{tx.transaction_id} · {amount(tx.amount)}</option>)}</select></label>
          <label className="span-two">Description<textarea rows="2" maxLength="10000" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Initial context and reason for review" /></label>
        </div><button className="button primary" disabled={saving}>{saving ? "Creating…" : "Create case"}</button>
      </form>
      {error && <div className="message error-message" role="alert">{error}</div>}{notice && <div className="notice">{notice}</div>}
      <div className="case-list"><Message loading={loading}>
        {cases.map((item) => <article className="panel case-card" key={item.id}>
          <div className="case-main"><div><span className="case-number">{item.case_number}</span><h3>{item.title}</h3><p>{item.description || "No description provided."}</p></div><div className="case-controls"><span className={`status-pill ${item.priority}`}>{item.priority} priority</span><select value={item.status} onChange={(event) => changeStatus(item.id, event.target.value)} aria-label={`Status for ${item.case_number}`}><option value="open">Open</option><option value="in_progress">In progress</option><option value="closed">Closed</option></select></div></div>
          <div className="case-meta">Created {displayDate(item.created_at)}{item.transaction_id && <span> · Transaction #{item.transaction_id}</span>}</div>
          {item.notes && <div className="notes-preview"><strong>Notes</strong><p>{item.notes}</p></div>}
          <div className="note-entry"><input value={notes[item.id] || ""} onChange={(event) => setNotes({ ...notes, [item.id]: event.target.value })} placeholder="Add an investigation note" maxLength="5000" /><button className="button secondary" onClick={() => addNote(item.id)} disabled={!notes[item.id]?.trim()}>Add note</button></div>
        </article>)}
        {!cases.length && <div className="empty-state panel">No investigation cases yet. Create one above.</div>}
      </Message></div>
    </section>
  );
}

function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [cases, setCases] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ title: "", case_id: "", transaction_id: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const reload = () => api.reports().then((items) => { setReports(items); if (!selected && items.length) setSelected(items[0]); }).catch((reason) => setError(reason.message)).finally(() => setLoading(false));
  useEffect(() => {
    reload();
    api.cases().then(setCases).catch((reason) => setError(reason.message));
    api.transactions({ limit: 100 }).then(setTransactions).catch((reason) => setError(reason.message));
  }, []);
  async function generate(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const report = await api.createReport({
        title: form.title,
        case_id: form.case_id ? Number(form.case_id) : null,
        transaction_id: form.transaction_id ? Number(form.transaction_id) : null,
      });
      setForm({ title: "", case_id: "", transaction_id: "" });
      setSelected(report);
      reload();
    } catch (reason) {
      setError(reason.message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <section className="reports-page">
      <PageTitle eyebrow="DOCUMENTATION" title="Investigation reports" detail="Generate and review a case summary for internal investigation records." action={<button className="button secondary" onClick={() => window.print()} disabled={!selected}>Print / export</button>} />
      <form className="panel report-form" onSubmit={generate}><h2>Generate report</h2><div className="form-grid">
        <label>Report title *<input required minLength="3" maxLength="255" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Investigation summary" /></label>
        <label>Case<select value={form.case_id} onChange={(event) => setForm({ ...form, case_id: event.target.value })}><option value="">No case</option>{cases.map((item) => <option key={item.id} value={item.id}>{item.case_number} · {item.title}</option>)}</select></label>
        <label className="span-two">Transaction<select value={form.transaction_id} onChange={(event) => setForm({ ...form, transaction_id: event.target.value })}><option value="">No transaction</option>{transactions.map((item) => <option key={item.id} value={item.id}>{item.transaction_id} · {amount(item.amount)}</option>)}</select></label>
      </div><button className="button primary" disabled={saving}>{saving ? "Generating…" : "Generate report"}</button></form>
      {error && <div className="message error-message" role="alert">{error}</div>}
      <div className="report-layout"><div className="panel report-list"><div className="panel-heading"><div><h2>Saved reports</h2><p>Stored in the investigation database</p></div></div>
        <Message loading={loading}>{reports.map((report) => <button key={report.id} className={`report-item ${selected?.id === report.id ? "selected" : ""}`} onClick={() => setSelected(report)}><strong>{report.title}</strong><small>{displayDate(report.created_at)}</small></button>)}{!reports.length && <div className="empty-state">No reports generated yet.</div>}</Message>
      </div>
      <article className="panel report-detail" id="report-content">{selected ? <><div className="report-detail-head"><div><p className="eyebrow">INVESTIGATION REPORT</p><h2>{selected.title}</h2><p className="muted">Generated {displayDate(selected.created_at)}</p></div><span className="report-id">SP-R{String(selected.id).padStart(5, "0")}</span></div><pre>{selected.content}</pre></> : <div className="empty-state">Select or generate a report to view details.</div>}</article></div>
    </section>
  );
}

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [riskTransaction, setRiskTransaction] = useState("");
  const active = navigation.find((item) => item.id === activePage);
  function openRisk(id) {
    setRiskTransaction(String(id));
    setActivePage("risk");
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">S</div><div><strong>SafePay</strong><small>FRAUD INTELLIGENCE</small></div></div>
        <div className="nav-caption">WORKSPACE</div>
        <nav>{navigation.map((item) => <button key={item.id} aria-label={item.label} title={item.label} onClick={() => setActivePage(item.id)} className={`nav-item ${activePage === item.id ? "active" : ""}`}><span className="nav-mark">{item.mark}</span><span>{item.label}</span>{activePage === item.id && <i />}</button>)}</nav>
        <div className="sidebar-bottom"><span className="online-dot" /><span>Monitoring workspace</span><small>SafePay · Local</small></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div><span className="breadcrumbs">Workspace</span><span className="crumb-separator">/</span><strong>{active?.label}</strong></div><div className="user-badge"><span className="online-dot" /> Local workspace</div></header>
        <div className="content-area">
          {activePage === "dashboard" && <DashboardPage />}
          {activePage === "transactions" && <TransactionsPage goToRisk={openRisk} />}
          {activePage === "risk" && <RiskPage initialTransaction={riskTransaction} />}
          {activePage === "network" && <NetworkPage />}
          {activePage === "cases" && <CasesPage />}
          {activePage === "reports" && <ReportsPage />}
          <footer className="page-footer">SafePay Financial Fraud Detection Platform <span>·</span> Sample risk scores are for demonstration only</footer>
        </div>
      </main>
    </div>
  );
}