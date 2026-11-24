(() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const statusStyles = {
    BERSIH: ["Bersih", "check_circle", "status-clean"],
    WASPADA: ["Waspada", "warning", "status-warning"],
    TIDAK_LAYAK: ["Tidak layak", "cancel", "status-critical"],
    belum_diuji: ["Belum diuji", "pending", "status-neutral"],
    belum_ada: ["Belum ada data", "sensors_off", "status-neutral"],
    menunggu: ["Menunggu", "schedule", "status-neutral"],
    antri: ["Antrean", "schedule", "status-neutral"],
    diproses: ["Diproses", "progress_activity", "status-info"],
    selesai: ["Selesai", "task_alt", "status-clean"],
    online: ["Online", "sensors", "status-clean"],
    offline: ["Offline", "sensors_off", "status-neutral"]
  };
  const fieldLabels = {
    ph: "pH",
    kekeruhan_ntu: "Kekeruhan",
    tds_mgl: "TDS"
  };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function icon(name, className) {
    const node = element("span", `material-symbols-outlined${className ? ` ${className}` : ""}`, name);
    node.setAttribute("aria-hidden", "true");
    return node;
  }

  function statusBadge(value) {
    const normalized = value || "belum_ada";
    const [label, symbol, className] = statusStyles[normalized] || [
      normalized.replaceAll("_", " "),
      "info",
      "status-neutral"
    ];
    const badge = element("span", `status-badge ${className}`);
    badge.setAttribute("aria-label", `Status: ${label}`);
    badge.append(icon(symbol), document.createTextNode(label));
    return badge;
  }

  function message(className, text, role = "status") {
    const node = element("div", className, text);
    node.setAttribute("role", role);
    return node;
  }

  function setMetadata(root, payload) {
    const key = root.dataset.metadataKey;
    if (!key) return;
    const panel = document.querySelector(`[data-behind-scenes="${CSS.escape(key)}"]`);
    if (!panel) return;
    const operation = panel.querySelector("[data-operation]");
    const complexity = panel.querySelector("[data-complexity]");
    if (operation) operation.textContent = payload.last_operation || "Tidak tersedia";
    if (complexity) {
      const value = payload.complexity || {};
      complexity.textContent = `Waktu ${value.time || "—"} · Ruang ${value.space || "—"}`;
    }
  }

  function showError(root, retry, detail) {
    const content = root.querySelector(".visual-content");
    content.replaceChildren();
    const error = message("visual-error", `Data tidak dapat dimuat: ${detail}`, "alert");
    const button = element("button", "button button-secondary", "Coba lagi");
    button.type = "button";
    button.addEventListener("click", retry);
    error.append(document.createTextNode(" "), button);
    content.append(error);
  }

  function renderQueue(root, data) {
    const content = root.querySelector(".visual-content");
    const priority = data.priority || [];
    const regular = data.regular || [];
    if (!priority.length && !regular.length) {
      content.replaceChildren(message("visual-empty", "Belum ada sampel dalam antrean."));
      return;
    }
    const lanes = element("div", "queue-lanes");
    [
      ["Prioritas", priority],
      ["Reguler", regular]
    ].forEach(([title, items]) => {
      const lane = element("section", "queue-lane");
      lane.setAttribute("aria-label", `${title}, ${items.length} sampel`);
      const heading = element("h3", "", title);
      heading.append(element("span", "tag", items.length));
      lane.append(heading);
      if (!items.length) {
        lane.append(message("visual-empty", "Kosong"));
      } else {
        const list = element("div", "queue-items");
        items.forEach((item, index) => {
          const card = element("article", `queue-item${data.front && data.front.id === item.id ? " is-front" : ""}`);
          const name = element("strong", "", `Sampel #${item.id} · ${item.source_name || "Sumber"}`);
          card.append(name);
          if (data.front && data.front.id === item.id) {
            const front = element("span", "visual-top-chip", "FRONT");
            front.setAttribute("aria-label", "Sampel berikutnya");
            card.append(front);
          }
          const details = [item.status, item.position ? `Posisi #${item.position}` : null].filter(Boolean).join(" · ");
          if (details) card.append(element("p", "", details));
          list.append(card);
        });
        lane.append(list);
      }
      lanes.append(lane);
    });
    content.replaceChildren(lanes);
  }

  function renderTelemetryQueue(root, data) {
    const content = root.querySelector(".visual-content");
    const items = data.items || [];
    if (!items.length) {
      content.replaceChildren(message("visual-empty", "Antrean telemetri kosong."));
      return;
    }
    const list = element("div", "queue-items");
    items.forEach((item, index) => {
      const card = element("article", `queue-item${index === 0 ? " is-front" : ""}`);
      card.append(element("strong", "", `#${item.id} · ${item.device_code} · ${item.source_name}`));
      if (index === 0) card.append(element("span", "visual-top-chip", "FRONT"));
      if (item.received_at) card.append(element("p", "muted", item.received_at));
      list.append(card);
    });
    content.replaceChildren(list);
  }

  function renderStack(root, data) {
    const content = root.querySelector(".visual-content");
    const items = data.items || [];
    if (!items.length) {
      content.replaceChildren(message("visual-empty", "Stack kosong; belum ada item untuk ditampilkan."));
      return;
    }
    const list = element("div", "stack-list");
    items.forEach((item, index) => {
      const card = element("article", `stack-item${index === 0 ? " is-top" : ""}`);
      if (index === 0) card.append(element("span", "stack-top-label", "TOP"));
      if (item.field) {
        card.append(element("strong", "", fieldLabels[item.field] || item.field));
        card.append(document.createTextNode(`: ${item.value}`));
      } else {
        card.append(element("strong", "", item.action || "Aksi"));
        if (item.created_at) card.append(element("p", "muted", item.created_at));
      }
      list.append(card);
    });
    content.replaceChildren(list);
  }

  function renderLinkedList(root, data) {
    const content = root.querySelector(".visual-content");
    const entries = data.entries || [];
    if (!entries.length) {
      content.replaceChildren(message("visual-empty", "Belum ada hasil pengujian pada sumber ini."));
      return;
    }
    const list = element("div", "linked-list");
    entries.forEach((entry, index) => {
      const wrap = element("div", "list-node-wrap");
      const card = element("article", "list-node");
      const endpoints = element("div", "actions");
      if (index === 0) endpoints.append(element("span", "list-end", "HEAD"));
      if (index === entries.length - 1) endpoints.append(element("span", "list-end", "TAIL"));
      if (endpoints.childNodes.length) card.append(endpoints);
      card.append(element("strong", "", `#${entry.id}`));
      const metrics = element("p", "mono", `pH ${entry.ph ?? "—"} · ${entry.kekeruhan_ntu ?? "—"} NTU · ${entry.tds_mgl ?? "—"} mg/L`);
      card.append(metrics, statusBadge(entry.status));
      if (entry.created_at) card.append(element("p", "muted", entry.created_at));
      wrap.append(card);
      if (index < entries.length - 1) wrap.append(icon("arrow_forward", "list-arrow"));
      list.append(wrap);
    });
    content.replaceChildren(list);
  }

  function renderDecisionTree(root, data) {
    const content = root.querySelector(".visual-content");
    const rootNode = data.root;
    if (!rootNode) {
      content.replaceChildren(message("visual-empty", "Decision tree tidak tersedia."));
      return;
    }
    const tree = element("div", "tree-list");
    const build = (node) => {
      if (!node) return element("div", "tree-node", "Node tidak tersedia");
      const container = element("div", "tree-node");
      if (node.type === "verdict") {
        const verdict = element("div", "tree-verdict");
        verdict.append(statusBadge(node.verdict), document.createTextNode(node.message || ""));
        container.append(verdict);
        return container;
      }
      const title = `${fieldLabels[node.feature] || node.feature} ${node.operator} ${node.threshold}`;
      container.append(element("div", "tree-condition", title));
      const branches = element("div", "tree-branches");
      [["Jika ya", node.true], ["Jika tidak", node.false]].forEach(([label, child]) => {
        const branch = element("section");
        branch.append(element("span", "tree-branch-label", label), build(child));
        branches.append(branch);
      });
      container.append(branches);
      return container;
    };
    tree.append(build(rootNode));
    if (data.thresholds && data.thresholds.is_example) {
      tree.append(message("tree-caveat", "Ambang adalah nilai contoh untuk simulasi, bukan baku mutu resmi."));
    }
    if (data.evaluation) {
      const result = element("section", "panel");
      result.append(element("h3", "", "Hasil evaluasi"));
      result.append(statusBadge(data.evaluation.verdict));
      (data.evaluation.trace || []).forEach((line) => result.append(element("p", "muted", line)));
      tree.append(result);
    }
    content.replaceChildren(tree);
  }

  function renderRegionTree(root, data) {
    const content = root.querySelector(".visual-content");
    const treeRoot = data.root;
    if (!treeRoot) {
      content.replaceChildren(message("visual-empty", "Belum ada data wilayah."));
      return;
    }
    const build = (node) => {
      const type = node.type || "region";
      const title = node.nama || node.name || (type === "root" ? "Wilayah" : `Node ${type}`);
      const card = element("div", "tree-node");
      const heading = element("strong", "", title);
      card.append(heading);
      if (node.level) card.append(element("span", "tag", node.level));
      if (node.jumlah_tercemar !== undefined && type !== "source") card.append(element("p", "muted", `${node.jumlah_tercemar} sumber tercemar`));
      if (node.status) card.append(statusBadge(node.status));
      const children = node.children || [];
      if (children.length) {
        const branches = element("div", "tree-branches");
        children.forEach((child) => branches.append(build(child)));
        card.append(branches);
      }
      return card;
    };
    const tree = element("div", "tree-list");
    tree.append(element("div", "metric-card", `${data.contaminated_sources ?? 0} sumber tercemar menurut hasil lab`));
    tree.append(build(treeRoot));
    content.replaceChildren(tree);
  }

  function svgElement(tag, attributes = {}) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  function renderGraph(root, data) {
    const content = root.querySelector(".visual-content");
    const nodes = data.nodes || [];
    const edges = data.edges || [];
    if (!nodes.length) {
      content.replaceChildren(message("visual-empty", "Belum ada sumber untuk membentuk jaringan."));
      return;
    }
    const columns = Math.min(5, Math.max(1, nodes.length));
    const rows = Math.ceil(nodes.length / columns);
    const width = Math.max(800, columns * 190);
    const height = Math.max(330, rows * 145 + 70);
    const positions = new Map();
    nodes.forEach((node, index) => {
      const col = index % columns;
      const row = Math.floor(index / columns);
      positions.set(node.id, {
        x: 100 + col * ((width - 200) / Math.max(columns - 1, 1)),
        y: 82 + row * 145
      });
    });
    const highlightedNodes = new Set(data.highlight_nodes || []);
    const highlightedEdges = new Set((data.highlight_edges || []).map((edge) => `${edge.from}:${edge.to}`));
    const scroll = element("div", "graph-scroll");
    const toolbar = element("div", "graph-toolbar");
    const svg = svgElement("svg", {
      class: "graph-svg",
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": `Graf sumber air: ${nodes.length} sumber dan ${edges.length} koneksi`
    });
    const defs = svgElement("defs");
    const marker = svgElement("marker", {
      id: `arrow-${root.dataset.visualId || "graph"}`,
      markerWidth: "8",
      markerHeight: "8",
      refX: "7",
      refY: "4",
      orient: "auto",
      markerUnits: "strokeWidth"
    });
    marker.append(svgElement("path", { d: "M0,0 L8,4 L0,8 z", fill: "#9aa8b5" }));
    defs.append(marker);
    svg.append(defs);
    const viewport = svgElement("g");
    const arrowId = `arrow-${root.dataset.visualId || "graph"}`;
    edges.forEach((edge) => {
      const from = positions.get(edge.from);
      const to = positions.get(edge.to);
      if (!from || !to) return;
      const deltaX = to.x - from.x;
      const deltaY = to.y - from.y;
      const distance = Math.hypot(deltaX, deltaY) || 1;
      const startX = from.x + deltaX / distance * 24;
      const startY = from.y + deltaY / distance * 24;
      const endX = to.x - deltaX / distance * 28;
      const endY = to.y - deltaY / distance * 28;
      const path = svgElement("path", {
        d: `M ${startX} ${startY} L ${endX} ${endY}`,
        class: `graph-edge${highlightedEdges.has(`${edge.from}:${edge.to}`) ? " is-highlighted" : ""}`,
        "marker-end": `url(#${arrowId})`
      });
      const title = svgElement("title");
      title.textContent = `${edge.distance_km} km`;
      path.append(title);
      viewport.append(path);
      const label = svgElement("text", {
        x: (startX + endX) / 2,
        y: (startY + endY) / 2 - 7,
        class: "graph-edge-label",
        "text-anchor": "middle"
      });
      label.textContent = `${edge.distance_km} km`;
      viewport.append(label);
    });
    nodes.forEach((node) => {
      const position = positions.get(node.id);
      const status = node.status;
      const statusClass = status === "BERSIH" ? "is-clean" : status === "WASPADA" ? "is-warning" : status === "TIDAK_LAYAK" ? "is-critical" : "is-neutral";
      const circle = svgElement("circle", {
        cx: position.x,
        cy: position.y,
        r: "23",
        class: `graph-node ${statusClass}${highlightedNodes.has(node.id) ? " is-highlighted" : ""}`
      });
      const title = svgElement("title");
      title.textContent = `${node.name} — ${status || "Belum diuji"}`;
      circle.append(title);
      viewport.append(circle);
      const label = svgElement("text", {
        x: position.x,
        y: position.y + 44,
        class: "graph-node-label",
        "text-anchor": "middle"
      });
      label.textContent = node.name;
      viewport.append(label);
    });
    svg.append(viewport);
    scroll.append(svg);
    const controls = [
      ["zoom_in", "Perbesar", () => changeZoom(1.2)],
      ["zoom_out", "Perkecil", () => changeZoom(1 / 1.2)],
      ["restart_alt", "Atur ulang tampilan", () => { zoom = 1; dx = 0; dy = 0; updateTransform(); }]
    ];
    let zoom = 1;
    let dx = 0;
    let dy = 0;
    const updateTransform = () => viewport.setAttribute("transform", `translate(${dx} ${dy}) scale(${zoom})`);
    const changeZoom = (factor) => { zoom = Math.min(2.5, Math.max(.65, zoom * factor)); updateTransform(); };
    controls.forEach(([symbol, label, action]) => {
      const button = element("button", "icon-button");
      button.type = "button";
      button.setAttribute("aria-label", label);
      button.title = label;
      button.append(icon(symbol));
      button.addEventListener("click", action);
      toolbar.append(button);
    });
    let drag = null;
    svg.addEventListener("pointerdown", (event) => {
      drag = { x: event.clientX - dx, y: event.clientY - dy };
      svg.setPointerCapture(event.pointerId);
    });
    svg.addEventListener("pointermove", (event) => {
      if (!drag) return;
      dx = event.clientX - drag.x;
      dy = event.clientY - drag.y;
      updateTransform();
    });
    const endDrag = () => { drag = null; };
    svg.addEventListener("pointerup", endDrag);
    svg.addEventListener("pointercancel", endDrag);
    const legend = element("div", "graph-legend");
    [["#298354", "Bersih"], ["#b18412", "Waspada"], ["#e41e3f", "Tidak layak"], ["#7d8995", "Belum diuji"]].forEach(([color, label]) => {
      const item = element("span");
      const dot = element("i", "legend-dot");
      dot.style.backgroundColor = color;
      item.append(dot, document.createTextNode(label));
      legend.append(item);
    });
    const resultPanel = element("div", "graph-result");
    const result = data.result;
    if (result && Array.isArray(result.impacted)) {
      resultPanel.append(element("h3", "", "Sumber hilir terjangkau"));
      if (!result.impacted.length) resultPanel.append(message("visual-empty", "Tidak ada sumber hilir yang dapat dicapai."));
      result.impacted.forEach((item) => {
        const row = element("p", "muted", `${item.name} · ${item.distance_km} km · rute ${item.route.join(" → ")}`);
        resultPanel.append(row);
      });
    } else if (result) {
      resultPanel.append(element("h3", "", `Sumber bersih terdekat: ${result.name}`));
      resultPanel.append(element("p", "muted", `${result.distance_km} km · rute ${result.route.join(" → ")}`));
    }
    content.replaceChildren(toolbar, scroll, legend);
    if (result && (result.impacted || result.name)) content.append(resultPanel);
  }

  function renderTelemetryFeed(root, data) {
    const content = root.querySelector(".visual-content");
    const items = data.items || [];
    if (!items.length) {
      content.replaceChildren(message("visual-empty", "Belum ada bacaan telemetri."));
      return;
    }
    const list = element("div", "feed-items");
    items.forEach((item) => {
      const card = element("article", "feed-item");
      const title = element("strong", "", `${item.device_code} · ${item.source_name}`);
      card.append(title, statusBadge(item.status));
      const metrics = element("div", "feed-metrics");
      [
        [`pH ${item.ph ?? "—"}`, "pH"],
        [`${item.kekeruhan_ntu ?? "—"} NTU`, "Kekeruhan"],
        [`${item.tds_mgl ?? "—"} mg/L`, "TDS"]
      ].forEach(([value, label]) => {
        const metric = element("span", "feed-metric", value);
        metric.setAttribute("aria-label", `${label}: ${value}`);
        metrics.append(metric);
      });
      card.append(metrics);
      if (item.received_at) card.append(element("p", "muted", item.received_at));
      if (item.priority_sample) card.append(element("p", "telemetry-accent", `Prioritas otomatis · Sampel #${item.priority_sample_id}`));
      list.append(card);
    });
    content.replaceChildren(list);
  }

  function renderSparkline(root, data) {
    const content = root.querySelector(".visual-content");
    const readings = data.series || data.items || [];
    if (!readings.length) {
      content.replaceChildren(message("visual-empty", "Belum cukup bacaan untuk membentuk grafik sensor."));
      return;
    }
    const grid = element("div", "sparkline-grid");
    const series = [
      ["ph", "pH", ""],
      ["kekeruhan_ntu", "Kekeruhan", " NTU"],
      ["tds_mgl", "TDS", " mg/L"]
    ];
    series.forEach(([key, label, unit]) => {
      const values = readings.map((reading) => Number(reading[key])).filter(Number.isFinite);
      const panel = element("section", "sparkline-panel");
      panel.append(element("h3", "telemetry-accent", label));
      if (!values.length) {
        panel.append(element("p", "muted", "Belum ada nilai."));
        grid.append(panel);
        return;
      }
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = max - min || 1;
      const svg = svgElement("svg", {
        class: "sparkline",
        viewBox: "0 0 320 74",
        role: "img",
        "aria-label": `${label}, rentang nilai ${min}${unit} hingga ${max}${unit}`
      });
      [15, 37, 59].forEach((y) => svg.append(svgElement("line", {
        x1: "2", y1: String(y), x2: "318", y2: String(y), class: "sparkline-gridline"
      })));
      const points = values.map((value, index) => {
        const x = values.length === 1 ? 160 : 4 + index * 312 / (values.length - 1);
        const y = 62 - ((value - min) / span) * 50;
        return `${x},${y}`;
      }).join(" ");
      svg.append(svgElement("polyline", { points, class: "sparkline-line" }));
      panel.append(svg);
      panel.append(element("p", "sparkline-foot", `${min}${unit} — ${max}${unit} · ${values.length} bacaan`));
      grid.append(panel);
    });
    content.replaceChildren(grid);
  }

  const renderers = {
    queue: renderQueue,
    "telemetry-queue": renderTelemetryQueue,
    stack: renderStack,
    "linked-list": renderLinkedList,
    "decision-tree": renderDecisionTree,
    "region-tree": renderRegionTree,
    graph: renderGraph,
    "telemetry-feed": renderTelemetryFeed,
    sparkline: renderSparkline
  };

  async function loadVisual(root) {
    const renderer = renderers[root.dataset.visual];
    if (!renderer) return;
    const content = root.querySelector(".visual-content");
    content.replaceChildren(message("visual-loading", "Memuat data visualisasi…"));
    const retry = () => loadVisual(root);
    try {
      const response = await fetch(root.dataset.apiUrl, {
        headers: { Accept: "application/json" },
        credentials: "same-origin"
      });
      if (!response.headers.get("content-type")?.includes("application/json")) {
        throw new Error(`Server mengembalikan respons non-JSON (HTTP ${response.status}).`);
      }
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      if (!payload || !payload.data) throw new Error("Format data API tidak sesuai.");
      setMetadata(root, payload);
      renderer(root, payload.data);
    } catch (error) {
      const detail = error.message || "Kesalahan tidak diketahui";
      showError(root, retry, detail);
      root.dataset.error = detail;
    } finally {
      root.querySelector(".visual-content").setAttribute("aria-busy", "false");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-visual][data-api-url]").forEach(loadVisual);
  });
})();
