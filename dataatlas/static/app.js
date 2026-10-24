const $ = (selector) => document.querySelector(selector);
const qualityNavItem = document.querySelector(".nav-item.disabled");
if (qualityNavItem) {
  qualityNavItem.id = "quality-nav";
  qualityNavItem.href = "#quality";
  qualityNavItem.title = "Open data quality";
  qualityNavItem.classList.remove("disabled");
  qualityNavItem.innerHTML = "<span>◉</span> Quality";
}
const notificationButton = document.querySelector(".icon-button[aria-label='Notifications']");
if (notificationButton) notificationButton.id = "alerts-button";
const state = { datasets: [], jobs: [], search: "", view: "datasets", user: null, workspace: null, workspaces: [], authMode: "login", sqlTables: [], queries: [], transformations: [], transformRuns: [], lineageDatasets: [], qualityRules: [], qualityRuns: [], alerts: [], qualityDataset: "" };
const fmt = (value) => Number(value).toLocaleString();

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options });
  const data = await response.json();
  if (response.status === 401 && path !== "/api/auth/login" && path !== "/api/auth/register") {
    showAuth("Your session has ended. Sign in again.");
  }
  if (!response.ok) {
    const error = new Error(data.error || "Request failed");
    error.status = response.status;
    error.payload = data;
    throw error;
  }
  return data;
}

function showAuth(message = "") {
  $("#app-shell").hidden = true;
  $("#auth-screen").hidden = false;
  $("#auth-error").textContent = message;
  $("#auth-password").value = "";
}

function showApp() {
  $("#auth-screen").hidden = true;
  $("#app-shell").hidden = false;
}

function setAuthMode(mode) {
  state.authMode = mode;
  const login = mode === "login";
  $("#auth-title").textContent = login ? "Welcome back" : "Create your account";
  $(".auth-copy").textContent = login ? "Sign in to explore the datasets in your workspace." : "Create an account and start a private workspace.";
  $("#auth-submit").innerHTML = login ? "Sign in <span>→</span>" : "Create account <span>→</span>";
  $("#auth-switch-copy").textContent = login ? "New to DataAtlas?" : "Already have an account?";
  $("#auth-switch").textContent = login ? "Create account" : "Sign in";
  $("#demo-login").hidden = !login;
  $("#auth-password").autocomplete = login ? "current-password" : "new-password";
  $("#auth-error").textContent = "";
}

async function initializeAuth() {
  try {
    const current = await api("/api/auth/me");
    applyIdentity(current);
    showApp();
    await refresh();
  } catch {
    showAuth();
  }
}

function applyIdentity(current) {
  state.user = current.user;
  state.workspace = current.workspace;
  state.workspaces = current.workspaces;
  $("#username-label").textContent = current.user.username;
  $("#user-avatar").textContent = current.user.username.slice(0, 2).toUpperCase();
  $("#header-avatar").textContent = current.user.username.slice(0, 2).toUpperCase();
  $("#role-label").textContent = current.workspace.role === "owner" ? "Workspace owner" : "Workspace member";
  const options = current.workspaces.map((workspace) =>
    `<option value="${esc(workspace.id)}" ${workspace.id === current.workspace.id ? "selected" : ""}>${esc(workspace.name)}</option>`
  ).join("");
  $("#workspace-select").innerHTML = options;
  $("#mobile-workspace-select").innerHTML = options;
}

async function refresh() {
  try {
    const params = new URLSearchParams();
    if (state.search) params.set("q", state.search);
    if ($("#layer-filter").value) params.set("layer", $("#layer-filter").value);
    [state.datasets, state.jobs] = await Promise.all([
      api(`/api/datasets?${params.toString()}`), api("/api/jobs")
    ]);
    render();
    if (state.view === "sql") await refreshSql();
    if (state.view === "transformations") await refreshTransformations();
    if (state.view === "lineage") await refreshLineage();
    if (state.view === "quality") await refreshQuality();
  } catch (error) {
    if (!$("#auth-screen").hidden) return;
    toast(error.message);
  }
}

function render() {
  const layer = $("#layer-filter").value;
  const jobsView = state.view === "jobs";
  const sqlView = state.view === "sql";
  const transformView = state.view === "transformations";
  const lineageView = state.view === "lineage";
  const qualityView = state.view === "quality";
  $("#catalog").hidden = sqlView || transformView || lineageView || qualityView;
  $("#sql-workspace").hidden = !sqlView;
  $("#transformations-view").hidden = !transformView;
  $("#lineage-view").hidden = !lineageView;
  $("#quality-view").hidden = !qualityView;
  document.querySelector('.nav-item[href="#catalog"]').classList.toggle("active", !sqlView && !transformView && !lineageView && !qualityView && !jobsView);
  $("#ingestion-nav").classList.toggle("active", jobsView);
  $("#sql-nav").classList.toggle("active", sqlView);
  $("#transform-nav").classList.toggle("active", transformView);
  $("#lineage-nav").classList.toggle("active", lineageView);
  $("#quality-nav").classList.toggle("active", qualityView);
  $(".crumb b").textContent = sqlView ? "SQL workspace" : transformView ? "Transformations" : lineageView ? "Lineage" : qualityView ? "Data quality" : jobsView ? "Ingestion" : "Catalog";
  if (sqlView || transformView || lineageView || qualityView) return;
  const list = state.datasets.filter((dataset) => !layer || dataset.layer === layer);
  $("#stat-datasets").textContent = fmt(state.datasets.length);
  $("#stat-rows").textContent = fmt(state.datasets.reduce((sum, dataset) => sum + dataset.row_count, 0));
  $("#asset-count").textContent = list.length;
  $("#job-count").textContent = state.jobs.length;
  $("#showing").textContent = jobsView ? `Showing ${state.jobs.length} ingestion run${state.jobs.length === 1 ? "" : "s"}` : `Showing ${list.length} dataset${list.length === 1 ? "" : "s"}`;
  $("#assets-tab").classList.toggle("active", !jobsView);
  $("#jobs-tab").classList.toggle("active", jobsView);
  $(".table-actions").hidden = jobsView;
  $("#dataset-table").hidden = jobsView || !list.length;
  $("#empty").hidden = jobsView || !!list.length;
  $("#jobs-table").hidden = !jobsView || !state.jobs.length;
  $("#jobs-empty").hidden = !jobsView || !!state.jobs.length;
  $("#jobs-table").style.display = jobsView && state.jobs.length ? "table" : "none";
  $("#dataset-rows").innerHTML = list.map((dataset) => `<tr data-id="${esc(dataset.id)}">
    <td><div class="dataset-name"><span class="dataset-icon">▦</span><span>${esc(dataset.name)}</span></div></td>
    <td>${esc(dataset.description || `Uploaded from ${dataset.source_name}`)}${dataset.tags?.length ? `<div class="tag-list">${dataset.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</div>` : ""}</td><td class="mono">${fmt(dataset.row_count)}</td>
    <td>${dataset.columns.length} columns</td><td><span class="layer">${esc(dataset.layer)}</span></td>
    <td>${new Date(dataset.updated_at || dataset.created_at).toLocaleDateString()}</td><td>›</td></tr>`).join("");
  $("#dataset-rows").querySelectorAll("tr").forEach((row) => { row.onclick = () => openDetail(row.dataset.id); });
  $("#job-rows").innerHTML = state.jobs.map((job) => `<tr data-job="${esc(job.id)}" data-dataset="${esc(job.dataset_id || "")}">
    <td class="mono">${esc(job.id.slice(0, 8))}</td><td>${esc(job.source_name)}</td>
    <td><span class="job-status ${esc(job.status)}">${esc(job.status)}</span></td>
    <td class="mono">${fmt(job.attempt_number || 1)}</td><td class="mono">${fmt(job.records_read)}</td><td class="mono">${fmt(job.records_written)}</td>
    <td class="mono">${fmt(job.duration_ms)} ms</td><td class="job-detail">${esc(job.error_message || job.storage_uri || "—")}</td>
    <td class="job-actions"><button type="button" class="job-events" data-id="${esc(job.id)}">Timeline</button>${job.dataset_id ? `<button type="button" class="job-dataset" data-id="${esc(job.dataset_id)}">Dataset</button>` : ""}${job.retry_available ? `<button type="button" class="retry-job" data-id="${esc(job.id)}">Retry</button>` : ""}</td></tr>`).join("");
  $("#job-rows").querySelectorAll("tr[data-job]").forEach((row) => {
    row.onclick = (event) => {
      if (event.target.closest("button")) return;
      loadJobEvents(row.dataset.job);
    };
  });
  $("#job-rows").querySelectorAll(".job-events").forEach((button) => button.onclick = () => loadJobEvents(button.dataset.id));
  $("#job-rows").querySelectorAll(".job-dataset").forEach((button) => button.onclick = () => openDetail(button.dataset.id));
  $("#job-rows").querySelectorAll(".retry-job").forEach((button) => button.onclick = () => {
    state.retryJob = state.jobs.find((job) => job.id === button.dataset.id);
    $("#retry-file").value = "";
    $("#retry-file").click();
  });
  const eventsPanel = $("#job-event-panel");
  if (eventsPanel.dataset.job && !state.jobs.some((job) => job.id === eventsPanel.dataset.job)) {
    eventsPanel.hidden = true;
    eventsPanel.textContent = "";
    delete eventsPanel.dataset.job;
  }
}

async function loadJobEvents(jobId) {
  try {
    const events = await api(`/api/jobs/${jobId}/events`);
    const job = state.jobs.find((item) => item.id === jobId);
    const panel = $("#job-event-panel");
    panel.hidden = false;
    panel.dataset.job = jobId;
    panel.innerHTML = `<div class="sql-card-head"><b>Run timeline · ${esc(job?.source_name || jobId.slice(0, 8))}</b><span>${fmt(job?.duration_ms || 0)} ms · attempt ${fmt(job?.attempt_number || 1)}</span></div>${events.length ? `<div class="job-timeline">${events.map((event) => `<div class="job-timeline-event"><span class="job-status ${esc(event.status)}">${esc(event.status)}</span><b>${esc(event.event_type.replaceAll("_", " "))}</b><time>${new Date(event.created_at).toLocaleString()}</time>${event.details.error ? `<small>${esc(event.details.error)}</small>` : ""}</div>`).join("")}</div>` : '<div class="detail-meta">No event timeline was recorded for this legacy job.</div>'}`;
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) { toast(error.message); }
}

async function refreshSql() {
  try {
    [state.sqlTables, state.queries] = await Promise.all([api("/api/sql/tables"), api("/api/queries")]);
    $("#sql-tables").innerHTML = state.sqlTables.length ? state.sqlTables.map((table) =>
      `<button type="button" class="sql-table" data-name="${esc(table.table_name)}"><b>${esc(table.dataset_name)}</b><code>${esc(table.table_name)}</code><small>${fmt(table.row_count)} rows · ${table.columns.length} columns</small><span>${table.columns.map((column) => `${esc(column.name)} (${esc(column.type)})`).join(" · ")}</span></button>`
    ).join("") : '<div class="detail-meta sql-empty">No datasets in this workspace yet. Upload a CSV to make a queryable table.</div>';
    $("#query-history").innerHTML = state.queries.length ? state.queries.map((query) =>
      `<button type="button" class="history-item" data-id="${esc(query.id)}"><span class="job-status ${esc(query.status)}">${esc(query.status)}</span><code>${esc(query.sql_text.replace(/\s+/g, " ").slice(0, 100))}</code><small>${new Date(query.created_at).toLocaleString()} · ${fmt(query.row_count)} rows · ${fmt(query.duration_ms)} ms</small></button>`
    ).join("") : '<div class="detail-meta sql-empty">Queries you run will appear here.</div>';
    $("#sql-tables").querySelectorAll(".sql-table").forEach((button) => button.onclick = () => {
      const editor = $("#sql-editor");
      editor.value = `SELECT * FROM "${button.dataset.name}" LIMIT 100;`;
      editor.focus();
    });
    $("#query-history").querySelectorAll(".history-item").forEach((button) => button.onclick = () => {
      const query = state.queries.find((item) => item.id === button.dataset.id);
      if (query) $("#sql-editor").value = query.sql_text;
    });
  } catch (error) { toast(error.message); }
}

async function refreshTransformations() {
  try {
    const [datasets, transformations, runs] = await Promise.all([
      api("/api/datasets"), api("/api/transformations"), api("/api/transformation-runs")
    ]);
    state.transformations = transformations;
    state.transformRuns = runs;
    const previous = $("#transform-source").value;
    $("#transform-source").innerHTML = datasets.map((dataset) =>
      `<option value="${esc(dataset.id)}">${esc(dataset.name)} · ${fmt(dataset.row_count)} rows · ${esc(dataset.layer)}</option>`
    ).join("");
    if (datasets.some((dataset) => dataset.id === previous)) $("#transform-source").value = previous;
    $("#transform-list").innerHTML = transformations.length ? transformations.map((item) =>
      `<div class="transform-card"><button type="button" class="transform-edit" data-id="${esc(item.id)}"><b>${esc(item.name)}</b><span>${esc(item.description || "No description")}</span><small>Revision ${item.revision} · ${esc(item.config.output_layer)} · ${item.config.steps.length} steps</small></button><button type="button" class="transform-run" data-id="${esc(item.id)}" title="Run recipe">▶</button></div>`
    ).join("") : '<div class="detail-meta sql-empty">Save a recipe to run repeatable transformations.</div>';
    $("#transform-runs").innerHTML = runs.length ? runs.slice(0, 30).map((run) => {
      const recipe = transformations.find((item) => item.id === run.transformation_id);
      return `<div class="history-item"><span class="job-status ${esc(run.status)}">${esc(run.status)}</span><code>${esc(recipe?.name || "Transformation")}</code><small>${fmt(run.input_rows)} → ${fmt(run.output_rows)} rows · ${fmt(run.duration_ms)} ms${run.output_dataset_id ? ` · ${esc(run.output_dataset_id.slice(0, 8))}` : ""}</small>${run.error_message ? `<span class="transform-error">${esc(run.error_message)}</span>` : ""}</div>`;
    }).join("") : '<div class="detail-meta sql-empty">Transformation runs will be recorded here.</div>';
    $("#transform-list").querySelectorAll(".transform-edit").forEach((button) => button.onclick = () => loadTransformation(button.dataset.id));
    $("#transform-list").querySelectorAll(".transform-run").forEach((button) => button.onclick = () => runSavedTransformation(button.dataset.id));
  } catch (error) { toast(error.message); }
}

async function refreshLineage() {
  try {
    const datasets = await api("/api/datasets");
    state.lineageDatasets = datasets;
    const previous = $("#lineage-dataset").value;
    $("#lineage-dataset").innerHTML = datasets.map((dataset) =>
      `<option value="${esc(dataset.id)}">${esc(dataset.name)} · ${esc(dataset.layer)} · ${fmt(dataset.row_count)} rows</option>`
    ).join("");
    if (datasets.some((dataset) => dataset.id === previous)) $("#lineage-dataset").value = previous;
    if (!datasets.length) {
      $("#lineage-summary").textContent = "No datasets are available in this workspace.";
      $("#lineage-graph").innerHTML = '<div class="empty"><b>No data to trace</b><p>Ingest a CSV or create a transformation output first.</p></div>';
      return;
    }
    await loadLineageGraph();
  } catch (error) { toast(error.message); }
}

async function loadLineageGraph() {
  const focusId = $("#lineage-dataset").value;
  if (!focusId) return;
  const params = new URLSearchParams({ dataset_id: focusId,
    direction: $("#lineage-direction").value, depth: $("#lineage-depth").value });
  try {
    const graph = await api(`/api/lineage/graph?${params.toString()}`);
    const byId = new Map(graph.nodes.map((node) => [node.id, node]));
    const grouped = new Map();
    for (const node of graph.nodes) {
      if (!grouped.has(node.level)) grouped.set(node.level, []);
      grouped.get(node.level).push(node);
    }
    const levels = [...grouped.keys()].sort((a, b) => a - b);
    const position = new Map();
    for (const level of levels) {
      grouped.get(level).sort((a, b) => a.name.localeCompare(b.name));
      grouped.get(level).forEach((node, index) => position.set(node.id, {
        x: 42 + (level - levels[0]) * 225, y: 34 + index * 96
      }));
    }
    const height = Math.max(240, ...levels.map((level) => grouped.get(level).length * 96 + 60));
    const width = Math.max(780, levels.length * 225 + 100);
    const edgeSvg = graph.edges.map((edge) => {
      const from = position.get(edge.source_dataset_id), to = position.get(edge.target_dataset_id);
      if (!from || !to) return "";
      const x1 = from.x + 168, y1 = from.y + 30, x2 = to.x, y2 = to.y + 30;
      return `<path class="lineage-edge" d="M ${x1} ${y1} C ${x1 + 45} ${y1}, ${x2 - 45} ${y2}, ${x2} ${y2}"><title>${esc(edge.event_type.replaceAll("_", " "))} · ${new Date(edge.created_at).toLocaleString()}</title></path>`;
    }).join("");
    const nodeSvg = graph.nodes.map((node) => {
      const point = position.get(node.id);
      const layerClass = node.focused ? "focused" : node.layer === "bronze" ? "" : "derived";
      return `<g class="lineage-node ${layerClass}" data-id="${esc(node.id)}" role="button" tabindex="0" aria-label="Focus ${esc(node.name)}"><rect x="${point.x}" y="${point.y}" width="168" height="60"></rect><text class="lineage-title" x="${point.x + 10}" y="${point.y + 23}">${esc(node.name.slice(0, 22))}</text><text class="lineage-meta" x="${point.x + 10}" y="${point.y + 43}">${esc(node.layer.toUpperCase())} · ${fmt(node.row_count)} rows</text></g>`;
    }).join("");
    $("#lineage-graph").innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Dataset lineage graph"><defs><marker id="lineage-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#9dbbb5"></path></marker></defs>${edgeSvg}${nodeSvg}</svg>`;
    $("#lineage-summary").textContent = `${graph.nodes.length} datasets · ${graph.edges.length} transformation edges${graph.truncated ? " · graph truncated at a safety limit or selected depth" : ""}. Select a node to refocus.`;
    $("#lineage-graph").querySelectorAll(".lineage-node").forEach((node) => {
      const focusNode = () => { $("#lineage-dataset").value = node.dataset.id; loadLineageGraph(); };
      node.onclick = focusNode;
      node.onkeydown = (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); focusNode(); } };
    });
  } catch (error) {
    $("#lineage-summary").textContent = error.message;
  }
}

const qualityExamples = {
  not_null: "{}", unique: "{}", expected_type: '{"expected_type":"integer"}',
  numeric_range: '{"min":0,"max":100}', regex: '{"pattern":"^[A-Z]{2}-[0-9]+$"}',
  allowed_values: '{"values":["pending","paid","cancelled"]}',
  min_value: '{"value":0}', max_value: '{"value":1000}', row_count: '{"min":1,"max":100000}',
  referential_integrity: '{"reference_dataset_id":"DATASET_ID","reference_column":"id"}'
};

async function refreshQuality() {
  try {
    const datasets = await api("/api/datasets");
    state.datasets = datasets;
    const previous = state.qualityDataset || $("#quality-dataset").value;
    $("#quality-dataset").innerHTML = datasets.map((dataset) =>
      `<option value="${esc(dataset.id)}">${esc(dataset.name)} · ${esc(dataset.layer)} · ${fmt(dataset.row_count)} rows</option>`
    ).join("");
    state.qualityDataset = datasets.some((dataset) => dataset.id === previous) ? previous : datasets[0]?.id || "";
    $("#quality-dataset").value = state.qualityDataset;
    if (!state.qualityDataset) {
      state.qualityRules = []; state.qualityRuns = []; state.alerts = [];
      renderQuality();
      $("#quality-column").innerHTML = "";
      $("#quality-results").dataset.run = "";
      return;
    }
    const params = new URLSearchParams({ dataset_id: state.qualityDataset });
    const [rules, runs, alerts, dataset] = await Promise.all([
      api(`/api/quality/rules?${params}`), api("/api/quality/runs"), api("/api/alerts"),
      api(`/api/datasets/${state.qualityDataset}`)
    ]);
    state.qualityRules = rules; state.qualityRuns = runs; state.alerts = alerts;
    const unreadAlerts = alerts.filter((alert) => !alert.read_at).length;
    $("#alerts-button").textContent = unreadAlerts ? `♧ ${unreadAlerts}` : "♧";
    $("#alerts-button").setAttribute("aria-label", unreadAlerts ? `Notifications, ${unreadAlerts} unread` : "Notifications");
    $("#alerts-button").title = unreadAlerts ? `${unreadAlerts} unread alert(s)` : "No unread alerts";
    $("#quality-column").innerHTML = dataset.schema.map((column) =>
      `<option value="${esc(column.name)}">${esc(column.name)} · ${esc(column.type)}</option>`
    ).join("");
    renderQuality();
    if (runs.length && !$("#quality-results").dataset.run) await loadQualityRun(runs[0].id);
  } catch (error) { toast(error.message); }
}

function renderQuality() {
  const rules = state.qualityRules;
  $("#quality-rule-count").textContent = `${rules.length} rule${rules.length === 1 ? "" : "s"}`;
  $("#quality-rules").innerHTML = rules.length ? rules.map((rule) =>
    `<div class="quality-rule"><button type="button" class="quality-edit" data-id="${esc(rule.id)}"><b>${esc(rule.name)}</b><span>${esc(rule.rule_type.replaceAll("_", " "))}${rule.target_column ? ` · ${esc(rule.target_column)}` : ""} · ${esc(rule.severity)}</span><small>v${rule.version} · ${rule.enabled ? "enabled" : "disabled"}</small></button><button type="button" class="quality-toggle" data-id="${esc(rule.id)}" title="Toggle rule">${rule.enabled ? "On" : "Off"}</button></div>`
  ).join("") : '<div class="detail-meta sql-empty">Create a rule to start measuring this dataset.</div>';
  $("#quality-runs").innerHTML = state.qualityRuns.length ? state.qualityRuns.slice(0, 20).map((run) =>
    `<button type="button" class="quality-run-item" data-id="${esc(run.id)}"><span class="job-status ${run.status === "succeeded" ? (run.rules_failed ? "failed" : "succeeded") : "failed"}">${run.rules_failed ? `${run.rules_failed} failed` : run.status}</span><b>${esc(run.dataset_name)}</b><small>${fmt(run.rules_passed)} passed · ${fmt(run.rules_failed)} failed · ${new Date(run.completed_at).toLocaleString()}</small></button>`
  ).join("") : '<div class="detail-meta sql-empty">Run enabled rules to create a quality history.</div>';
  $("#quality-alerts").innerHTML = state.alerts.length ? state.alerts.slice(0, 20).map((alert) =>
    `<div class="quality-alert ${alert.read_at ? "read" : "unread"}"><button type="button" class="quality-alert-open" data-id="${esc(alert.id)}"><b>${esc(alert.title)}</b><span>${esc(alert.message)}</span><small>${esc(alert.severity)} · ${new Date(alert.created_at).toLocaleString()}</small></button>${alert.acknowledged_at ? '<small class="alert-ack">Acknowledged</small>' : `<button type="button" class="quality-alert-ack" data-id="${esc(alert.id)}">Acknowledge</button>`}</div>`
  ).join("") : '<div class="detail-meta sql-empty">No alerts in this workspace.</div>';
  $("#quality-rules").querySelectorAll(".quality-edit").forEach((button) => button.onclick = () => editQualityRule(button.dataset.id));
  $("#quality-rules").querySelectorAll(".quality-toggle").forEach((button) => button.onclick = () => toggleQualityRule(button.dataset.id));
  $("#quality-runs").querySelectorAll(".quality-run-item").forEach((button) => button.onclick = () => loadQualityRun(button.dataset.id));
  $("#quality-alerts").querySelectorAll(".quality-alert-open").forEach((button) => button.onclick = () => openQualityAlert(button.dataset.id));
  $("#quality-alerts").querySelectorAll(".quality-alert-ack").forEach((button) => button.onclick = () => acknowledgeQualityAlert(button.dataset.id));
}

function resetQualityForm() {
  $("#quality-form").reset();
  $("#quality-rule-id").value = "";
  $("#quality-severity").value = "warning";
  $("#quality-config").value = "{}";
  $("#quality-form-title").textContent = "New quality rule";
  $("#quality-version").textContent = "";
  $("#quality-message").textContent = "Rule results are calculated from stored dataset records.";
  $("#quality-type").value = "not_null";
  updateQualityType();
}

function editQualityRule(id) {
  const rule = state.qualityRules.find((item) => item.id === id);
  if (!rule) return;
  $("#quality-dataset").value = rule.dataset_id;
  $("#quality-rule-id").value = rule.id;
  $("#quality-name").value = rule.name;
  $("#quality-description").value = rule.description;
  $("#quality-type").value = rule.rule_type;
  $("#quality-column").value = rule.target_column || "";
  $("#quality-severity").value = rule.severity;
  $("#quality-config").value = JSON.stringify(rule.config, null, 2);
  $("#quality-form-title").textContent = "Edit quality rule";
  $("#quality-version").textContent = `Current version ${rule.version}`;
  $("#quality-message").textContent = "Saving creates a new immutable result-definition version.";
  updateQualityType();
}

function updateQualityType() {
  const type = $("#quality-type").value;
  const rowCount = type === "row_count";
  $("#quality-column-wrap").hidden = rowCount;
  $("#quality-config-example").textContent = qualityExamples[type] || "{}";
  $("#quality-config-help").textContent = type === "referential_integrity" ? "Use IDs from another dataset in this workspace" : "Example configuration";
}

async function saveQualityRule(event) {
  event.preventDefault();
  let config;
  try { config = JSON.parse($("#quality-config").value); }
  catch { $("#quality-message").textContent = "Configuration must be valid JSON."; return; }
  const id = $("#quality-rule-id").value;
  const payload = { name: $("#quality-name").value, description: $("#quality-description").value,
    dataset_id: $("#quality-dataset").value, target_column: $("#quality-column-wrap").hidden ? null : $("#quality-column").value,
    rule_type: $("#quality-type").value, config, severity: $("#quality-severity").value };
  try {
    const saved = await api(id ? `/api/quality/rules/${id}` : "/api/quality/rules", {
      method: id ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    $("#quality-message").textContent = `Saved rule version ${saved.version}.`;
    await refreshQuality();
    toast("Quality rule saved");
  } catch (error) { $("#quality-message").textContent = error.payload?.error || error.message; }
}

async function toggleQualityRule(id) {
  const rule = state.qualityRules.find((item) => item.id === id);
  if (!rule) return;
  try {
    await api(`/api/quality/rules/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !rule.enabled }) });
    await refreshQuality();
  } catch (error) { toast(error.message); }
}

async function runQualityChecks() {
  const datasetId = $("#quality-dataset").value;
  if (!datasetId) { toast("Add a dataset before running quality checks."); return; }
  const button = $("#run-quality"); button.disabled = true; button.textContent = "Running checks…";
  try {
    const run = await api(`/api/quality/datasets/${datasetId}/run`, { method: "POST" });
    await refreshQuality();
    if (run.id) await loadQualityRun(run.id);
    toast(run.rules_total ? `Quality run finished: ${run.rules_passed} passed, ${run.rules_failed} failed` : "No enabled rules for this dataset");
  } catch (error) { toast(error.message); }
  finally { button.disabled = false; button.innerHTML = 'Run checks <span>▶</span>'; }
}

async function loadQualityRun(id) {
  try {
    const run = await api(`/api/quality/runs/${id}`);
    $("#quality-results").dataset.run = run.id;
    $("#quality-run-status").textContent = `${esc(run.dataset_name)} · ${run.rules_passed} passed · ${run.rules_failed} failed · schema v${run.schema_version} · ${run.duration_ms} ms`;
    $("#quality-results").innerHTML = run.results.length ? `<div class="detail-table"><table><thead><tr><th>RULE</th><th>STATUS</th><th>ROWS</th><th>VIOLATIONS</th><th>SEVERITY</th><th>SAMPLES</th></tr></thead><tbody>${run.results.map((result) =>
      `<tr><td>${esc(result.rule_name)}<small class="table-sub">${esc(result.rule_type.replaceAll("_", " "))}${result.target_column ? ` · ${esc(result.target_column)}` : ""} · definition v${result.rule_version}</small></td><td><span class="job-status ${result.status === "passed" ? "succeeded" : "failed"}">${esc(result.status)}</span>${result.error_message ? `<small class="transform-error">${esc(result.error_message)}</small>` : ""}</td><td>${fmt(result.rows_evaluated)}</td><td>${fmt(result.violations)}</td><td>${esc(result.severity)}</td><td>${result.samples.length ? `<details><summary>${result.samples.length} sample(s)</summary><pre>${esc(JSON.stringify(result.samples, null, 2))}</pre></details>` : "—"}</td></tr>`
    ).join("")}</tbody></table></div>` : '<div class="detail-meta">No enabled rules were evaluated for this dataset.</div>';
  } catch (error) { $("#quality-run-status").textContent = error.message; }
}

async function openQualityAlert(id) {
  const alert = state.alerts.find((item) => item.id === id);
  if (!alert) return;
  try { await api(`/api/alerts/${id}/read`, { method: "POST" }); } catch { /* alert remains inspectable */ }
  if (alert.source_type === "quality_rule") {
    state.qualityDataset = alert.related_id || state.qualityDataset;
    state.view = "quality"; render();
    await refreshQuality();
    editQualityRule(alert.source_id);
  } else if (alert.related_type === "dataset" && alert.related_id) {
    try { await openDetail(alert.related_id); } catch { /* resource may have been removed */ }
  } else if (alert.related_type === "ingestion_job") {
    state.view = "jobs"; render();
    await loadJobEvents(alert.related_id);
  }
  await refreshQuality();
}

async function acknowledgeQualityAlert(id) {
  try { await api(`/api/alerts/${id}/acknowledge`, { method: "POST" }); await refreshQuality(); }
  catch (error) { toast(error.message); }
}

function loadTransformation(id) {
  const item = state.transformations.find((entry) => entry.id === id);
  if (!item) return;
  $("#transform-id").value = item.id;
  $("#transform-name").value = item.name;
  $("#transform-description").value = item.description;
  $("#transform-source").value = item.config.source_dataset_id;
  $("#transform-layer").value = item.config.output_layer;
  $("#transform-steps").value = JSON.stringify(item.config.steps, null, 2);
  $("#transform-form-title").textContent = "Edit transformation recipe";
  $("#transform-revision").textContent = `Current revision ${item.revision}`;
  $("#transform-message").textContent = "Save changes to create a new recipe revision.";
}

function resetTransformationForm() {
  $("#transform-form").reset();
  $("#transform-id").value = "";
  $("#transform-layer").value = "silver";
  $("#transform-steps").value = "[]";
  $("#transform-form-title").textContent = "Transformation recipe";
  $("#transform-revision").textContent = "";
  $("#transform-message").textContent = "Each run creates a new dataset and lineage event.";
}

function transformationPayload() {
  let steps;
  try { steps = JSON.parse($("#transform-steps").value); }
  catch { throw new Error("Steps must be valid JSON."); }
  return { name: $("#transform-name").value, description: $("#transform-description").value,
    source_dataset_id: $("#transform-source").value, output_layer: $("#transform-layer").value, steps };
}

async function saveTransformation() {
  const id = $("#transform-id").value;
  const result = await api(id ? `/api/transformations/${id}` : "/api/transformations", {
    method: id ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(transformationPayload())
  });
  $("#transform-id").value = result.id;
  $("#transform-form-title").textContent = "Edit transformation recipe";
  $("#transform-revision").textContent = `Current revision ${result.revision}`;
  await refreshTransformations();
  return result;
}

async function runSavedTransformation(id) {
  try {
    const result = await api(`/api/transformations/${id}/run`, { method: "POST" });
    $("#transform-message").textContent = `Created ${result.dataset_name} with ${fmt(result.output_rows)} rows.`;
    await refresh();
    toast(`Transformation created ${result.dataset_name}`);
  } catch (error) {
    $("#transform-message").textContent = error.payload?.error_message || error.message;
    await refreshTransformations();
  }
}

function renderQueryResult(result) {
  if (result.error_message) {
    $("#sql-results").innerHTML = `<div class="sql-error">${esc(result.error_message)}</div>`;
    return;
  }
  if (!result.columns?.length) {
    $("#sql-results").innerHTML = '<div class="detail-meta">Query completed with no result columns.</div>';
    return;
  }
  $("#sql-results").innerHTML = `<div class="detail-meta sql-result-meta">${fmt(result.row_count)} rows · ${fmt(result.duration_ms)} ms · saved to query history</div><div class="detail-table"><table><thead><tr>${result.columns.map((column) => `<th>${esc(column)}</th>`).join("")}</tr></thead><tbody>${result.rows.map((row) => `<tr>${result.columns.map((column) => `<td>${esc(row[column] ?? "∅")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function esc(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2800);
}

$("#auth-switch").onclick = () => setAuthMode(state.authMode === "login" ? "register" : "login");
$("#demo-login").onclick = () => {
  $("#auth-username").value = "demo";
  $("#auth-password").value = "dataatlas-demo";
};
$("#auth-form").onsubmit = async (event) => {
  event.preventDefault();
  const button = $("#auth-submit");
  button.disabled = true;
  $("#auth-error").textContent = "";
  const path = state.authMode === "login" ? "/api/auth/login" : "/api/auth/register";
  try {
    await api(path, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("#auth-username").value, password: $("#auth-password").value }) });
    const current = await api("/api/auth/me");
    applyIdentity(current);
    showApp();
    await refresh();
  } catch (error) {
    $("#auth-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
};

async function switchWorkspace(workspaceId) {
  try {
    await api("/api/workspaces/select", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: workspaceId }) });
    const current = await api("/api/auth/me");
    applyIdentity(current);
    await refresh();
  } catch (error) { toast(error.message); }
}
$("#workspace-select").onchange = (event) => switchWorkspace(event.target.value);
$("#mobile-workspace-select").onchange = (event) => switchWorkspace(event.target.value);

async function createWorkspace() {
  const name = prompt("Name your new workspace");
  if (!name?.trim()) return;
  try {
    await api("/api/workspaces", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
    const current = await api("/api/auth/me");
    applyIdentity(current);
    await refresh();
    toast(`Switched to ${current.workspace.name}`);
  } catch (error) { toast(error.message); }
}
$("#create-workspace").onclick = createWorkspace;
$("#mobile-create-workspace").onclick = createWorkspace;

$("#sign-out").onclick = async () => {
  try { await api("/api/auth/logout", { method: "POST" }); } catch { /* clear the local view even if the session expired */ }
  state.datasets = [];
  showAuth();
};

const upload = $("#upload-dialog");
async function showUpload() {
  $("#upload-error").textContent = "";
  try {
    const all = await api("/api/datasets");
    $("#replace-target").innerHTML = '<option value="">Create a new dataset</option>' + all.map((dataset) =>
      `<option value="${esc(dataset.id)}">Replace ${esc(dataset.name)} · ${fmt(dataset.row_count)} rows</option>`
    ).join("");
  } catch (error) { toast(error.message); return; }
  upload.showModal();
}
["#open-upload", "#empty-upload"].forEach((selector) => { $(selector).onclick = showUpload; });
["#close-upload", "#cancel-upload"].forEach((selector) => { $(selector).onclick = () => upload.close(); });
let searchTimer;
$("#search").oninput = (event) => {
  state.search = event.target.value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refresh, 220);
};
$("#layer-filter").onchange = refresh;
let uploadIdempotencyKey = null;
$("#assets-tab").onclick = () => { state.view = "datasets"; render(); };
$("#jobs-tab").onclick = () => { state.view = "jobs"; render(); };
$("#ingestion-nav").onclick = (event) => { event.preventDefault(); state.view = "jobs"; render(); };
$("#sql-nav").onclick = async (event) => { event.preventDefault(); state.view = "sql"; render(); await refreshSql(); };
$("#transform-nav").onclick = async (event) => { event.preventDefault(); state.view = "transformations"; render(); await refreshTransformations(); };
$("#lineage-nav").onclick = async (event) => { event.preventDefault(); state.view = "lineage"; render(); await refreshLineage(); };
$("#quality-nav").onclick = async (event) => { event.preventDefault(); state.view = "quality"; render(); await refreshQuality(); };
$("#alerts-button").onclick = async () => { state.view = "quality"; render(); await refreshQuality(); };
$("#refresh-sql-tables").onclick = refreshSql;
$("#refresh-transformations").onclick = refreshTransformations;
$("#refresh-lineage").onclick = loadLineageGraph;
$("#lineage-dataset").onchange = loadLineageGraph;
$("#lineage-direction").onchange = loadLineageGraph;
$("#lineage-depth").onchange = loadLineageGraph;
$("#quality-dataset").onchange = async () => { state.qualityDataset = $("#quality-dataset").value; resetQualityForm(); await refreshQuality(); };
$("#quality-type").onchange = updateQualityType;
$("#quality-form").onsubmit = saveQualityRule;
$("#run-quality").onclick = runQualityChecks;
$("#new-quality-rule").onclick = resetQualityForm;
$("#cancel-quality-edit").onclick = resetQualityForm;
$("#refresh-alerts").onclick = refreshQuality;
$("#new-transformation").onclick = resetTransformationForm;
$("#transform-form").onsubmit = async (event) => {
  event.preventDefault();
  try {
    const saved = await saveTransformation();
    $("#transform-message").textContent = `Saved revision ${saved.revision}.`;
    toast("Transformation recipe saved");
  } catch (error) { $("#transform-message").textContent = error.payload?.error || error.message; }
};
$("#save-run-transform").onclick = async () => {
  try {
    const saved = await saveTransformation();
    await runSavedTransformation(saved.id);
  } catch (error) { $("#transform-message").textContent = error.payload?.error || error.message; }
};
$("#run-query").onclick = async () => {
  const button = $("#run-query");
  button.disabled = true;
  $("#sql-message").textContent = "Running query…";
  try {
    const result = await api("/api/queries", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sql: $("#sql-editor").value }) });
    renderQueryResult(result);
    $("#sql-message").textContent = "Query succeeded";
  } catch (error) {
    renderQueryResult(error.payload || { error_message: error.message });
    $("#sql-message").textContent = "Query failed; details were saved to history.";
  } finally {
    button.disabled = false;
    await refreshSql();
  }
};
$("#jobs-upload").onclick = showUpload;
$("#retry-file").onchange = async (event) => {
  const file = event.target.files[0];
  const job = state.retryJob;
  state.retryJob = null;
  if (!file || !job) return;
  if (file.name !== job.source_name) {
    toast(`Choose the original file name: ${job.source_name}`);
    return;
  }
  const form = new FormData();
  form.append("file", file);
  const headers = { "Idempotency-Key": crypto.randomUUID(), "DataAtlas-Retry-Of": job.id };
  if (job.target_dataset_id) headers["DataAtlas-Replace-Dataset"] = job.target_dataset_id;
  try {
    const result = await api("/api/ingest/csv", { method: "POST", headers, body: form });
    await refresh();
    await loadJobEvents(result.job_id);
    toast("Retry completed successfully");
  } catch (error) {
    await refresh();
    if (error.payload?.job_id) await loadJobEvents(error.payload.job_id);
    toast(error.payload?.error || error.message);
  }
};
$("#file-input").onchange = (event) => { uploadIdempotencyKey = null; $("#file-label").textContent = event.target.files[0]?.name || "Choose a CSV or drop it here"; };
$("#replace-target").onchange = () => { uploadIdempotencyKey = null; };
const dropZone = $("#drop-zone");
dropZone.ondragover = (event) => { event.preventDefault(); dropZone.classList.add("drag"); };
dropZone.ondragleave = () => dropZone.classList.remove("drag");
dropZone.ondrop = (event) => {
  event.preventDefault(); dropZone.classList.remove("drag");
  const file = event.dataTransfer.files[0];
  if (file) { uploadIdempotencyKey = null; $("#file-input").files = event.dataTransfer.files; $("#file-label").textContent = file.name; }
};

$("#upload-form").onsubmit = async (event) => {
  event.preventDefault();
  const file = $("#file-input").files[0];
  if (!file) return;
  const button = $("#submit-upload");
  uploadIdempotencyKey ||= crypto.randomUUID();
  button.disabled = true;
  button.textContent = "Ingesting…";
  $("#upload-error").textContent = "";
  try {
    const form = new FormData();
    form.append("file", file);
    const headers = { "Idempotency-Key": uploadIdempotencyKey };
    const replaceId = $("#replace-target").value;
    if (replaceId) {
      const selected = $("#replace-target").selectedOptions[0].textContent;
      if (!confirm(`Replace the current data in ${selected.replace(/^Replace /, "").split(" · ")[0]}? A raw file version and schema history will be kept.`)) return;
      headers["DataAtlas-Replace-Dataset"] = replaceId;
    }
    const data = await api("/api/ingest/csv", { method: "POST", headers, body: form });
    upload.close();
    $("#upload-form").reset();
    uploadIdempotencyKey = null;
    $("#file-label").textContent = "Choose a CSV or drop it here";
    await refresh();
    toast(`Ingested ${fmt(data.row_count)} rows into ${data.name}`);
    openDetail(data.id);
  } catch (error) {
    $("#upload-error").textContent = error.message;
    if (error.status) uploadIdempotencyKey = null;
    await refresh();
  } finally {
    button.disabled = false;
    button.innerHTML = 'Ingest dataset <span>→</span>';
  }
};

async function openDetail(id) {
  try {
    const [dataset, profile, lineage, versions, changes] = await Promise.all([
      api(`/api/datasets/${id}`), api(`/api/datasets/${id}/profile`), api(`/api/datasets/${id}/lineage`),
      api(`/api/datasets/${id}/schemas`), api(`/api/datasets/${id}/schema-changes`)
    ]);
    const metrics = (column) => {
      if (column.min !== undefined) return `Range ${fmt(column.min)}–${fmt(column.max)} · mean ${fmt(column.mean)} · SD ${fmt(column.standard_deviation)} · outliers ${fmt(column.outlier_count)}${column.top_values?.length ? ` · top ${column.top_values.map((v) => `${esc(v.value)} (${fmt(v.count)})`).join(", ")}` : ""}`;
      if (column.min_length !== undefined) return `Length ${fmt(column.min_length)}–${fmt(column.max_length)} · mean ${fmt(column.mean_length)}${column.top_values?.length ? ` · top ${column.top_values.map((v) => `${esc(v.value)} (${fmt(v.count)})`).join(", ")}` : ""}`;
      if (column.true_count !== undefined) return `${fmt(column.true_count)} true · ${fmt(column.false_count)} false`;
      if (column.earliest !== undefined) return `${esc(column.earliest)} → ${esc(column.latest)}`;
      return column.top_values?.length ? column.top_values.map((value) => `${esc(value.value)} (${fmt(value.count)})`).join(", ") : "—";
    };
    $("#detail-content").innerHTML = `<div class="detail-header"><div class="eyebrow">DATASET PROFILE <span class="slash">/</span> ${esc(dataset.layer.toUpperCase())}</div>
      <h2>${esc(dataset.name)}</h2><div class="detail-meta">Source: ${esc(dataset.source_name)} · Ingested ${new Date(dataset.created_at).toLocaleString()}</div>
      <div class="detail-meta storage-meta">${dataset.storage_uri ? `Bronze file: <code>${esc(dataset.storage_uri)}</code>${dataset.storage_bytes ? ` · ${fmt(dataset.storage_bytes)} bytes` : ""} · SHA-256 <code>${esc(dataset.content_sha256 || "not recorded")}</code>` : dataset.storage_format === "sqlite_json" ? "Derived records: SQLite JSON catalog" : "Legacy dataset without a raw file"}</div></div>
      <div class="detail-stats"><div><b>${fmt(dataset.row_count)}</b><small>Rows stored</small></div><div><b>${dataset.schema.length}</b><small>Columns · schema v${dataset.schema_version}</small></div><div><b>${lineage.length}</b><small>Observed lineage events</small></div></div>
      <form id="metadata-form" class="metadata-form"><label>Description<input name="description" maxlength="500" value="${esc(dataset.description || "")}" placeholder="Describe this dataset"></label><label>Tags<input name="tags" maxlength="500" value="${esc((dataset.tags || []).join(", "))}" placeholder="sales, monthly, demo"></label><button class="secondary" type="submit">Save catalog details</button><span id="metadata-status" role="status"></span></form>
      <div class="detail-section">COLUMN PROFILE</div><div class="detail-table"><table><thead><tr><th>NAME</th><th>TYPE</th><th>NULLS</th><th>DISTINCT</th><th>PROFILE SUMMARY</th></tr></thead><tbody>
      ${profile.columns.map((column) => `<tr><td class="mono">${esc(column.name)}</td><td>${esc(column.type)}${column.nullable ? " · nullable" : ""}</td><td>${fmt(column.null_count)}</td><td>${fmt(column.distinct_count)}</td><td>${metrics(column)}</td></tr>`).join("")}
      </tbody></table></div><div class="detail-section">SAMPLE ROWS <span style="letter-spacing:0">· ${Math.min(20, dataset.sample.length)} of ${fmt(dataset.row_count)}</span></div>
      <div class="detail-table"><table><thead><tr>${dataset.schema.map((column) => `<th>${esc(column.name)}</th>`).join("")}</tr></thead><tbody>
      ${dataset.sample.slice(0, 5).map((row) => `<tr>${dataset.schema.map((column) => `<td>${esc(row[column.name] ?? "∅")}</td>`).join("")}</tr>`).join("")}
      </tbody></table></div><div class="detail-section">SCHEMA HISTORY</div><div class="schema-history">${versions.map((version) => `<div><b>v${version.version}</b><span>${version.schema.length} columns · ${new Date(version.recorded_at).toLocaleString()}</span></div>`).join("")}</div>
      <div class="detail-section">SCHEMA CHANGES</div><div class="schema-change-list">${changes.length ? changes.map((change) => `<div class="schema-change"><span class="job-status ${esc(change.severity)}">${esc(change.severity)}</span><span><b>${esc(change.change_type.replaceAll("_", " "))}</b> · ${esc(change.column_name)}</span>${change.acknowledged ? '<small class="acknowledged">Acknowledged</small>' : `<button class="ack-schema-change" data-id="${esc(change.id)}">Acknowledge</button>`}</div>`).join("") : '<div class="detail-meta">No detected schema changes.</div>'}</div>
      <div class="detail-section">OBSERVED LINEAGE</div><div class="detail-meta">${lineage.map((item) => `${esc(item.event_type.replaceAll("_", " "))} · ${esc(item.details.source_file)} → ${fmt(item.details.rows_written)} rows written`).join("<br>")}</div>`;
    $("#metadata-form").onsubmit = async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      try {
        await api(`/api/datasets/${id}/metadata`, { method: "PATCH", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ description: form.get("description"), tags: String(form.get("tags")).split(",").map((tag) => tag.trim()).filter(Boolean) }) });
        await refresh();
        $("#detail-dialog").close();
        await openDetail(id);
        toast("Catalog details saved");
      } catch (error) { $("#metadata-status").textContent = error.message; }
    };
    $("#detail-content").querySelectorAll(".ack-schema-change").forEach((button) => {
      button.onclick = async () => {
        try { await api(`/api/schema-changes/${button.dataset.id}/acknowledge`, { method: "POST" }); $("#detail-dialog").close(); await openDetail(id); }
        catch (error) { toast(error.message); }
      };
    });
    $("#detail-dialog").showModal();
  } catch (error) { toast(error.message); }
}

$("#close-detail").onclick = () => $("#detail-dialog").close();
$("#detail-dialog").addEventListener("click", (event) => { if (event.target === $("#detail-dialog")) $("#detail-dialog").close(); });
initializeAuth();
