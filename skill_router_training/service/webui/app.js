const state = {
  policy: null,
  summary: null,
  events: [],
};

const $ = (id) => document.getElementById(id);
const CHART_HEIGHTS = {
  avgChart: 220,
  seriesChart: 220,
  changeChart: 280,
  latencyChart: 220,
};

function pct(value) {
  return value === null || value === undefined ? "-" : `${(value * 100).toFixed(1)}%`;
}

function num(value, digits = 1) {
  return value === null || value === undefined ? "-" : Number(value).toFixed(digits);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function refresh() {
  try {
    const [summary, events] = await Promise.all([
      api("/v1/dashboard/summary"),
      api("/v1/dashboard/events?limit=80"),
    ]);
    state.summary = summary;
    state.policy = summary.policy;
    state.events = events.events || [];
    render();
    $("healthBadge").textContent = "ready";
    $("healthBadge").className = "badge ready";
  } catch (error) {
    $("healthBadge").textContent = "error";
    $("healthBadge").className = "badge error";
    $("runtimeLine").textContent = error.message;
  }
}

function render() {
  renderPolicy();
  renderRuntime();
  renderMetrics();
  renderEvents();
  drawCharts();
  $("lastUpdated").textContent = new Date().toLocaleString();
}

function renderPolicy() {
  const policy = state.policy || {};
  $("routingEnabled").checked = policy.routing_enabled !== false;
  $("enforceParameters").checked = !!policy.enforce_parameters;
  $("threshold").value = policy.threshold ?? 0.5;
  $("thresholdValue").textContent = Number(policy.threshold ?? 0.5).toFixed(2);
  $("topK").value = policy.top_k ?? 8;
}

function renderRuntime() {
  const router = state.summary?.router || {};
  $("runtimeLine").textContent = `${router.status || "-"} · ${router.default_threshold ?? "-"} / top ${router.default_top_k ?? "-"}`;
  $("checkpointText").textContent = router.checkpoint || "-";
  $("skillCountText").textContent = router.num_skills ?? "-";
  $("deviceText").textContent = router.device || "-";
}

function renderMetrics() {
  const metrics = state.summary?.metrics || {};
  $("eventCount").textContent = metrics.event_count ?? 0;
  $("comparableCount").textContent = metrics.comparable_count ?? 0;
  $("okRate").textContent = pct(metrics.ok_rate);
  $("reductionRate").textContent = pct(metrics.selected_reduction);
}

function renderEvents() {
  const rows = state.events.slice().reverse().map((event) => {
    const shadow = event.shadow_comparison || {};
    const before = (shadow.baseline_skills || []).length;
    const after = (event.selected_skill_names || []).length;
    const latency = [
      event.latency_ms !== null && event.latency_ms !== undefined ? `${event.latency_ms}ms` : "",
      event.plugin_latency_ms !== null && event.plugin_latency_ms !== undefined ? `${event.plugin_latency_ms}ms` : "",
    ].filter(Boolean).join(" / ");
    return `<tr>
      <td>${formatTime(event.timestamp)}</td>
      <td class="${event.ok ? "ok" : "fail"}">${event.ok ? "OK" : "FAIL"}</td>
      <td>${before || "-"}</td>
      <td>${after || "-"}</td>
      <td>${latency || "-"}</td>
      <td>${escapeHtml(event.skipped || event.error || event.request_id || "-")}</td>
    </tr>`;
  });
  $("eventRows").innerHTML = rows.join("") || `<tr><td colspan="6">暂无事件</td></tr>`;
}

function formatTime(value) {
  if (!value) return "-";
  const date = typeof value === "number" ? new Date(value * 1000) : new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function setupCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  const cssHeight = CHART_HEIGHTS[canvas.id] || 220;
  canvas.style.height = `${cssHeight}px`;
  canvas.width = Math.max(300, Math.floor(rect.width * scale));
  canvas.height = Math.floor(cssHeight * scale);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.clearRect(0, 0, rect.width, cssHeight);
  ctx.font = "12px Segoe UI, Arial";
  return { ctx, width: rect.width, height: cssHeight };
}

function drawCharts() {
  const metrics = state.summary?.metrics || {};
  drawGroupedBars($("avgChart"), ["Before", "After"], [metrics.avg_selected_before || 0], [metrics.avg_selected_after || 0], "#d84a4a", "#008b8b");
  drawSeries($("seriesChart"), metrics.series || []);
  drawChanges($("changeChart"), metrics.top_additions || [], metrics.top_removals || []);
  const lat = metrics.latency || {};
  drawSimpleBars($("latencyChart"), ["R P50", "R P95", "P P50", "P P95"], [
    lat.router_p50_ms || 0,
    lat.router_p95_ms || 0,
    lat.plugin_p50_ms || 0,
    lat.plugin_p95_ms || 0,
  ], "#3767a6");
}

function drawAxes(ctx, width, height) {
  ctx.strokeStyle = "#dde3ea";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(36, 12);
  ctx.lineTo(36, height - 28);
  ctx.lineTo(width - 12, height - 28);
  ctx.stroke();
}

function drawGroupedBars(canvas, labels, before, after, beforeColor, afterColor) {
  const { ctx, width, height } = setupCanvas(canvas);
  drawAxes(ctx, width, height);
  const max = Math.max(1, ...before, ...after);
  const base = height - 28;
  const plotHeight = height - 48;
  const groupWidth = (width - 64) / labels.length;
  labels.forEach((label, index) => {
    const x = 48 + index * groupWidth;
    const bH = before[index] / max * plotHeight;
    const aH = after[index] / max * plotHeight;
    ctx.fillStyle = beforeColor;
    ctx.fillRect(x, base - bH, 28, bH);
    ctx.fillStyle = afterColor;
    ctx.fillRect(x + 36, base - aH, 28, aH);
    ctx.fillStyle = "#172026";
    ctx.fillText(label, x + 8, height - 8);
    ctx.fillText(num(before[index]), x, base - bH - 5);
    ctx.fillText(num(after[index]), x + 36, base - aH - 5);
  });
}

function drawSimpleBars(canvas, labels, values, color) {
  const { ctx, width, height } = setupCanvas(canvas);
  drawAxes(ctx, width, height);
  const max = Math.max(1, ...values);
  const base = height - 28;
  const plotHeight = height - 48;
  const step = (width - 64) / labels.length;
  labels.forEach((label, index) => {
    const h = values[index] / max * plotHeight;
    const x = 46 + index * step;
    ctx.fillStyle = color;
    ctx.fillRect(x, base - h, Math.max(22, step * 0.45), h);
    ctx.fillStyle = "#172026";
    ctx.fillText(label, x - 2, height - 8);
    ctx.fillText(num(values[index]), x - 2, base - h - 5);
  });
}

function drawSeries(canvas, rows) {
  const { ctx, width, height } = setupCanvas(canvas);
  drawAxes(ctx, width, height);
  if (!rows.length) {
    ctx.fillStyle = "#64717c";
    ctx.fillText("暂无可对比事件", 48, 36);
    return;
  }
  const max = Math.max(1, ...rows.map((row) => row.before_count), ...rows.map((row) => row.after_count));
  drawLine(ctx, rows.map((row) => row.before_count), max, width, height, "#d84a4a");
  drawLine(ctx, rows.map((row) => row.after_count), max, width, height, "#008b8b");
}

function drawLine(ctx, values, max, width, height, color) {
  const base = height - 28;
  const plotHeight = height - 48;
  const step = values.length > 1 ? (width - 60) / (values.length - 1) : 0;
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = 36 + index * step;
    const y = base - value / max * plotHeight;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawChanges(canvas, additions, removals) {
  const { ctx, width, height } = setupCanvas(canvas);
  const rows = [
    ...additions.map((item) => ({ label: `+ ${item.skill}`, value: item.count, color: "#008b8b" })),
    ...removals.map((item) => ({ label: `- ${item.skill}`, value: -item.count, color: "#d84a4a" })),
  ].slice(0, 16);
  const mid = width * 0.52;
  ctx.strokeStyle = "#172026";
  ctx.beginPath();
  ctx.moveTo(mid, 10);
  ctx.lineTo(mid, height - 12);
  ctx.stroke();
  if (!rows.length) {
    ctx.fillStyle = "#64717c";
    ctx.fillText("暂无变化数据", 18, 32);
    return;
  }
  const max = Math.max(1, ...rows.map((row) => Math.abs(row.value)));
  const rowHeight = Math.max(16, (height - 20) / rows.length);
  rows.forEach((row, index) => {
    const y = 14 + index * rowHeight;
    const bar = Math.abs(row.value) / max * (width * 0.38);
    ctx.fillStyle = row.color;
    if (row.value >= 0) {
      ctx.fillRect(mid, y, bar, rowHeight * 0.55);
      ctx.fillStyle = "#172026";
      ctx.fillText(`${row.label} ${row.value}`, mid + bar + 6, y + 10);
    } else {
      ctx.fillRect(mid - bar, y, bar, rowHeight * 0.55);
      ctx.fillStyle = "#172026";
      ctx.textAlign = "right";
      ctx.fillText(`${row.label} ${Math.abs(row.value)}`, mid - bar - 6, y + 10);
      ctx.textAlign = "left";
    }
  });
}

$("threshold").addEventListener("input", () => {
  $("thresholdValue").textContent = Number($("threshold").value).toFixed(2);
});

$("savePolicyBtn").addEventListener("click", async () => {
  const payload = {
    routing_enabled: $("routingEnabled").checked,
    enforce_parameters: $("enforceParameters").checked,
    threshold: Number($("threshold").value),
    top_k: Number($("topK").value),
  };
  await api("/v1/dashboard/policy", { method: "PUT", body: JSON.stringify(payload) });
  await refresh();
});

$("refreshBtn").addEventListener("click", refresh);
window.addEventListener("resize", () => drawCharts());

refresh();
setInterval(refresh, 10000);
