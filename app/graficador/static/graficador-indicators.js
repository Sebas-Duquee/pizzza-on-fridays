/*
 * Indicadores técnicos del Graficador, al estilo de TradingView.
 *
 * - El botón «Indicadores» abre un diálogo con buscador y categorías. Cada clic
 *   añade un indicador; se pueden añadir 1 o N, incluso el mismo con distintos
 *   parámetros (SMA 20 y SMA 50).
 * - Los de tendencia (medias, Bollinger, SAR) se dibujan sobre el precio; el
 *   resto, en su propio panel bajo el volumen (panes de lightweight-charts v5).
 * - Cada indicador tiene su leyenda con los valores bajo el cursor y los
 *   botones de ocultar, ajustes y quitar.
 * - Los valores los calcula el servidor con TA-Lib:
 *   GET /api/graficador/<ticker>/indicators?range=&interval=&ind=sma:20&ind=…
 * - La lista de indicadores (con sus parámetros y colores) se recuerda en el
 *   navegador y se aplica a cualquier ticker.
 *
 * Depende de ``window.GraficadorChart``, que define graficador.js.
 */
(function () {
  "use strict";

  const G = window.GraficadorChart;
  if (!G) return;
  const { root, chart, LC, THEME, ticker, getJSON, withAlpha, fmtPrice, fmtVolume, escapeHtml } = G;

  const $ = (id) => document.getElementById(id);
  const button = $("graficador-indicators-btn");
  const countEl = $("graficador-indicators-count");
  const chartEl = $("graficador-chart");
  const wrapEl = chartEl.parentElement;
  const stackEl = $("graficador-legend-stack");
  const overlayEl = $("gind-overlay");
  const panesEl = $("gind-panes");
  const toastEl = $("gind-toast");
  const picker = $("gind-picker");
  const settings = $("gind-settings");
  if (!button || !picker || !settings) return;

  const computeUrl = root.dataset.computeUrl.replace("__T__", encodeURIComponent(ticker));
  const STORAGE_KEY = "graficador:indicators:v1";
  const MAX_INSTANCES = 20; // la API acepta hasta 25 por petición
  const PANE_STRETCH = 1.2; // altura de un panel de indicador respecto al de volumen (1)
  const PANE_EXTRA_HEIGHT = 150; // px que crece el gráfico por cada panel extra
  const MOBILE = window.matchMedia("(max-width: 640px)");

  let catalog = null; // {palette, categories, indicators[]}
  let byId = new Map();
  const instances = [];
  let uidSeq = 0;
  let tokenSeq = 0;

  // ───────────────────────── Persistencia ─────────────────────────
  function readSaved() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(saved) ? saved : [];
    } catch (error) {
      return [];
    }
  }

  function save() {
    try {
      const data = instances.map((i) => ({ id: i.def.id, params: i.params, colors: i.colors, visible: i.visible }));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (error) {
      /* sin almacenamiento (modo privado): la lista dura mientras la página */
    }
  }

  // ───────────────────────── Utilidades ─────────────────────────
  const ICONS = {
    eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
    "eye-off":
      '<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/>',
    settings:
      '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  };
  const icon = (name) =>
    '<svg class="ui-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    ICONS[name] +
    "</svg>";

  const normalize = (text) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  let toastTimer = 0;
  function toast(text, ms) {
    toastEl.textContent = text;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toastEl.hidden = true), ms || 3500);
  }

  const specOf = (inst) => inst.def.id + (inst.def.params.length ? ":" + inst.def.params.map((p) => inst.params[p.key]).join(",") : "");
  const paramsText = (inst) => inst.def.params.map((p) => inst.params[p.key]).join(", ");
  function fmtValue(inst, value) {
    if (value === null || value === undefined) return "—";
    if (inst.def.category !== "Volumen") return fmtPrice(value);
    if (value === 0) return "0"; // fmtVolume muestra «—» para 0
    return (value < 0 ? "-" : "") + fmtVolume(Math.abs(value));
  }

  // ───────────────────────── Series de un indicador ─────────────────────────
  function pickColor(def, output, index) {
    // Los de una sola línea toman el siguiente color libre de la paleta; los que
    // tienen varias (MACD, Bollinger…) conservan los suyos, que ya se distinguen.
    if (def.outputs.length > 1) return output.color;
    const used = new Set();
    instances.forEach((i) => Object.values(i.colors).forEach((c) => used.add(c.toLowerCase())));
    const free = catalog.palette.find((c) => !used.has(c.toLowerCase()));
    return free || catalog.palette[index % catalog.palette.length];
  }

  function buildSeries(inst) {
    const def = inst.def;
    const paneIndex = def.overlay ? 0 : chart.panes().length;
    // Los histogramas primero, para que las líneas del mismo panel se pinten encima.
    const outputs = def.outputs.slice().sort((a, b) => (b.style === "histogram") - (a.style === "histogram"));

    outputs.forEach((out) => {
      const options = {
        priceLineVisible: false,
        lastValueVisible: !def.overlay && out.style !== "histogram",
        visible: inst.visible,
      };
      if (def.bounds) {
        options.autoscaleInfoProvider = () => ({ priceRange: { minValue: def.bounds[0], maxValue: def.bounds[1] } });
      }
      if (def.category === "Volumen") options.priceFormat = { type: "volume" };

      let series;
      if (out.style === "histogram") {
        series = chart.addSeries(LC.HistogramSeries, options, paneIndex);
      } else {
        Object.assign(options, { color: inst.colors[out.key], lineWidth: def.overlay ? 2 : 1.5, crosshairMarkerRadius: 3 });
        if (out.style === "dashed") options.lineStyle = LC.LineStyle.Dashed;
        if (out.style === "dots") Object.assign(options, { lineVisible: false, pointMarkersVisible: true, pointMarkersRadius: 2.5 });
        series = chart.addSeries(LC.LineSeries, options, paneIndex);
      }
      inst.series[out.key] = series;
    });

    // Líneas de referencia (30/70 en el RSI…) sobre la primera línea del indicador.
    const anchor = def.outputs.find((o) => o.style !== "histogram") || def.outputs[0];
    def.levels.forEach((price) =>
      inst.series[anchor.key].createPriceLine({
        price,
        color: withAlpha(THEME.ink, 0.28),
        lineWidth: 1,
        lineStyle: LC.LineStyle.Dashed,
        axisLabelVisible: false,
      }),
    );

    if (!def.overlay) {
      chart.panes()[paneIndex].setStretchFactor(PANE_STRETCH);
      // Márgenes de escala más ajustados que los del precio: un RSI acotado a 0-100
      // no debe llegar a 120 por el margen superior por defecto.
      const margin = def.bounds ? 0.06 : 0.12;
      chart.priceScale("right", paneIndex).applyOptions({ scaleMargins: { top: margin, bottom: margin } });
    }
  }

  function applyData(inst, time, outputs) {
    inst.def.outputs.forEach((out) => {
      const values = outputs[out.key] || [];
      const points = [];
      for (let i = 0; i < time.length; i++) {
        const value = values[i];
        if (value === null || value === undefined) continue; // periodo de calentamiento
        points.push(
          out.style === "histogram"
            ? { time: time[i], value, color: withAlpha(value >= 0 ? THEME.up : THEME.down, 0.55) }
            : { time: time[i], value },
        );
      }
      inst.series[out.key].setData(points);
      inst.last[out.key] = points.length ? points[points.length - 1].value : null;
    });
  }

  function clearData(inst) {
    inst.def.outputs.forEach((out) => {
      inst.series[out.key].setData([]);
      inst.last[out.key] = null;
    });
  }

  // ───────────────────────── Cálculo (API) ─────────────────────────
  function compute(list) {
    const ctx = G.getContext();
    if (!ctx || !list.length) return; // sin velas todavía: se calculará en onData
    if (!ctx.candles.length) {
      list.forEach((inst) => {
        clearData(inst);
        setState(inst, "");
        renderValues(inst, null);
      });
      return;
    }
    const token = ++tokenSeq;
    list.forEach((inst) => {
      inst.token = token;
      setState(inst, "loading");
    });
    const query = "provider=" + encodeURIComponent(G.getProvider()) + "&range=" + ctx.range + "&interval=" + ctx.interval + list.map((i) => "&ind=" + encodeURIComponent(specOf(i))).join("");
    getJSON(computeUrl + "?" + query)
      .then((data) => {
        list.forEach((inst, index) => {
          if (inst.token !== token) return; // sustituido por otra petición o quitado
          applyData(inst, data.time, data.indicators[index].outputs);
          setState(inst, "");
          renderValues(inst, null);
        });
      })
      .catch((error) => {
        list.forEach((inst) => inst.token === token && setState(inst, "error"));
        toast("No se pudieron calcular los indicadores: " + (error && error.message ? error.message : "error de red"));
      });
  }

  G.onData(() => compute(instances.slice()));

  // ───────────────────────── Leyenda de cada indicador ─────────────────────────
  function buildRow(inst) {
    const row = document.createElement("div");
    row.className = "gind-row" + (inst.def.overlay ? "" : " gind-row--pane");
    row.dataset.uid = String(inst.uid);
    row.innerHTML =
      '<span class="gind-row__name">' + escapeHtml(inst.def.short) + (inst.def.params.length ? ' <span class="gind-row__params">' + escapeHtml(paramsText(inst)) + "</span>" : "") + "</span>" +
      '<span class="gind-row__vals"></span>' +
      '<span class="gind-row__actions">' +
      '<button type="button" class="gind-icon-btn" data-act="toggle"></button>' +
      '<button type="button" class="gind-icon-btn" data-act="settings" aria-label="Ajustes de ' + escapeHtml(inst.def.short) + '" title="Ajustes">' + icon("settings") + "</button>" +
      '<button type="button" class="gind-icon-btn" data-act="remove" aria-label="Quitar ' + escapeHtml(inst.def.short) + '" title="Quitar">' + icon("x") + "</button>" +
      "</span>";
    (inst.def.overlay ? overlayEl : panesEl).appendChild(row);
    inst.row = row;
    inst.valsEl = row.querySelector(".gind-row__vals");
    updateToggle(inst);
  }

  function updateToggle(inst) {
    const toggle = inst.row.querySelector('[data-act="toggle"]');
    const name = inst.def.short;
    toggle.innerHTML = icon(inst.visible ? "eye" : "eye-off");
    toggle.setAttribute("aria-label", (inst.visible ? "Ocultar " : "Mostrar ") + name);
    toggle.title = inst.visible ? "Ocultar" : "Mostrar";
    inst.row.classList.toggle("is-off", !inst.visible);
  }

  function updateName(inst) {
    const params = inst.row.querySelector(".gind-row__params");
    if (params) params.textContent = paramsText(inst);
  }

  function setState(inst, state) {
    inst.row.classList.toggle("is-loading", state === "loading");
    inst.row.classList.toggle("is-error", state === "error");
    if (state) inst.valsEl.textContent = state === "loading" ? "…" : "error";
  }

  // Valores bajo el cursor (o el último si el cursor está fuera del gráfico).
  function renderValues(inst, param) {
    const parts = [];
    inst.def.outputs.forEach((out) => {
      const series = inst.series[out.key];
      let value = inst.last[out.key];
      if (param && param.time !== undefined) {
        const point = param.seriesData.get(series);
        value = point ? point.value : null;
      }
      const color = out.style === "histogram" ? (value !== null && value < 0 ? THEME.down : THEME.up) : inst.colors[out.key];
      parts.push('<span class="gind-val" style="color:' + color + '" title="' + escapeHtml(out.label) + '">' + fmtValue(inst, value) + "</span>");
    });
    inst.valsEl.innerHTML = parts.join("");
  }

  chart.subscribeCrosshairMove((param) => instances.forEach((inst) => !inst.row.classList.contains("is-loading") && renderValues(inst, param)));

  // Los paneles son filas de una tabla interna: se colocan a mano las leyendas.
  let layoutFrame = 0;
  function layout() {
    layoutFrame = 0;
    const layerTop = panesEl.getBoundingClientRect().top;
    let panes = 0;
    instances.forEach((inst) => {
      if (inst.def.overlay) return;
      panes += 1;
      const first = Object.values(inst.series)[0];
      const element = first && first.getPane().getHTMLElement();
      if (element) inst.row.style.top = element.getBoundingClientRect().top - layerTop + 6 + "px";
    });
    // Más paneles, más alto: así el precio no se aplasta con 4 o 5 indicadores.
    const base = MOBILE.matches ? 400 : 460;
    wrapEl.style.minHeight = panes ? base + panes * PANE_EXTRA_HEIGHT + "px" : "";
    // En móvil la leyenda ocupa su franja y el gráfico empieza debajo.
    chartEl.style.top = MOBILE.matches ? stackEl.offsetHeight + 12 + "px" : "";
  }
  function scheduleLayout() {
    if (!layoutFrame) layoutFrame = requestAnimationFrame(layout);
  }
  function settleLayout() {
    // El gráfico recoloca sus paneles de forma asíncrona tras añadir o quitar uno.
    scheduleLayout();
    setTimeout(scheduleLayout, 60);
    setTimeout(scheduleLayout, 250);
  }
  new ResizeObserver(scheduleLayout).observe(chartEl);
  new ResizeObserver(scheduleLayout).observe(stackEl);
  chartEl.addEventListener("pointermove", scheduleLayout); // arrastrar el separador de un panel
  chartEl.addEventListener("pointerup", scheduleLayout);

  // ───────────────────────── Alta, baja y cambios ─────────────────────────
  function updateCount() {
    countEl.textContent = String(instances.length);
    countEl.hidden = !instances.length;
    button.setAttribute("aria-label", "Indicadores" + (instances.length ? " (" + instances.length + " añadidos)" : ""));
    refreshPickerBadges();
  }

  function createInstance(def, saved) {
    const inst = { uid: ++uidSeq, def, params: {}, colors: {}, visible: !saved || saved.visible !== false, series: {}, last: {}, token: 0 };
    def.params.forEach((p) => {
      const value = saved && saved.params ? Number(saved.params[p.key]) : NaN;
      inst.params[p.key] = Number.isFinite(value) ? value : p.default;
    });
    def.outputs.forEach((out, index) => {
      const color = saved && saved.colors && typeof saved.colors[out.key] === "string" ? saved.colors[out.key] : pickColor(def, out, instances.length);
      inst.colors[out.key] = color;
    });
    instances.push(inst);
    buildSeries(inst);
    buildRow(inst);
    return inst;
  }

  function add(id) {
    const def = byId.get(id);
    if (!def) return;
    if (instances.length >= MAX_INSTANCES) {
      toast("Máximo " + MAX_INSTANCES + " indicadores en el gráfico.");
      return;
    }
    const inst = createInstance(def, null);
    save();
    updateCount();
    settleLayout();
    compute([inst]);
  }

  function remove(inst) {
    inst.token = -1; // descarta cualquier respuesta pendiente
    Object.values(inst.series).forEach((series) => chart.removeSeries(series)); // el último de un panel lo cierra
    inst.row.remove();
    instances.splice(instances.indexOf(inst), 1);
    save();
    updateCount();
    settleLayout();
  }

  function removeAll() {
    instances.slice().forEach(remove);
  }

  function setVisible(inst, visible) {
    inst.visible = visible;
    Object.values(inst.series).forEach((series) => series.applyOptions({ visible }));
    updateToggle(inst);
    save();
  }

  [overlayEl, panesEl].forEach((container) =>
    container.addEventListener("click", (event) => {
      const target = event.target.closest("[data-act]");
      const row = event.target.closest(".gind-row");
      if (!target || !row) return;
      const inst = instances.find((i) => String(i.uid) === row.dataset.uid);
      if (!inst) return;
      if (target.dataset.act === "toggle") setVisible(inst, !inst.visible);
      else if (target.dataset.act === "remove") remove(inst);
      else if (target.dataset.act === "settings") openSettings(inst);
    }),
  );

  // ───────────────────────── Diálogo «Indicadores» ─────────────────────────
  const searchEl = $("gind-search");
  const catsEl = $("gind-cats");
  const listEl = $("gind-list");
  const emptyEl = $("gind-empty");
  let activeCategory = "Todos";

  function buildPicker() {
    catsEl.innerHTML = ["Todos"]
      .concat(catalog.categories)
      .map((c) => '<button type="button" class="gind-chip" data-cat="' + escapeHtml(c) + '" aria-pressed="' + (c === activeCategory) + '">' + escapeHtml(c) + "</button>")
      .join("");
    listEl.innerHTML = catalog.indicators
      .map(
        (d) =>
          '<li><button type="button" class="gind-item" data-id="' + d.id + '">' +
          '<span class="gind-item__title"><b>' + escapeHtml(d.short) + "</b><span>" + escapeHtml(d.name) + "</span></span>" +
          '<span class="gind-item__desc">' + escapeHtml(d.description) + "</span>" +
          '<span class="gind-item__meta"><span class="gind-tag">' + escapeHtml(d.category) + '</span><span class="gind-tag gind-tag--soft">' +
          (d.overlay ? "Sobre el precio" : "Panel propio") + '</span><span class="gind-item__count" hidden></span></span>' +
          "</button></li>",
      )
      .join("");
    filterPicker();
  }

  function filterPicker() {
    const query = normalize(searchEl.value.trim());
    let visible = 0;
    catalog.indicators.forEach((d, index) => {
      const item = listEl.children[index];
      const text = normalize([d.id, d.short, d.name, d.description, d.category].join(" "));
      const show = (activeCategory === "Todos" || d.category === activeCategory) && (!query || query.split(/\s+/).every((word) => text.includes(word)));
      item.hidden = !show;
      if (show) visible += 1;
    });
    emptyEl.hidden = visible > 0;
  }

  function refreshPickerBadges() {
    if (!catalog) return;
    catalog.indicators.forEach((d, index) => {
      const badge = listEl.children[index] && listEl.children[index].querySelector(".gind-item__count");
      if (!badge) return;
      const n = instances.filter((i) => i.def.id === d.id).length;
      badge.hidden = !n;
      badge.textContent = n ? "×" + n + " añadido" + (n > 1 ? "s" : "") : "";
    });
    $("gind-clear").disabled = !instances.length;
  }

  searchEl.addEventListener("input", filterPicker);
  searchEl.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const first = Array.from(listEl.children).find((li) => !li.hidden);
    if (first) add(first.firstElementChild.dataset.id);
  });
  catsEl.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-cat]");
    if (!chip) return;
    activeCategory = chip.dataset.cat;
    catsEl.querySelectorAll("[data-cat]").forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
    filterPicker();
  });
  listEl.addEventListener("click", (event) => {
    const item = event.target.closest("[data-id]");
    if (item) add(item.dataset.id);
  });
  $("gind-clear").addEventListener("click", removeAll);
  picker.querySelectorAll("[data-gind-close]").forEach((b) => b.addEventListener("click", () => picker.close()));
  // Clic en el fondo (fuera de la tarjeta) cierra el diálogo.
  [picker, settings].forEach((dialog) =>
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close("cancel");
    }),
  );
  picker.addEventListener("close", () => button.focus());

  button.addEventListener("click", () => {
    if (!catalog) {
      toast("Cargando los indicadores…");
      return;
    }
    picker.showModal();
    searchEl.focus();
    searchEl.select();
  });

  // ───────────────────────── Diálogo de ajustes ─────────────────────────
  const settingsBody = $("gind-settings-body");
  const settingsForm = $("gind-settings-form");
  let editing = null;

  function fillSettings(inst, params, colors) {
    const def = inst.def;
    let html = "";
    if (def.params.length) {
      html += '<fieldset class="gind-fieldset"><legend>Parámetros</legend>';
      def.params.forEach((p) => {
        html +=
          '<label class="gind-field"><span>' + escapeHtml(p.label) + '</span><input type="number" name="p_' + p.key + '" value="' + params[p.key] +
          '" min="' + p.min + '" max="' + p.max + '" step="' + (p.kind === "int" ? 1 : "any") + '" required inputmode="decimal"></label>';
      });
      html += "</fieldset>";
    }
    const styled = def.outputs.filter((o) => o.style !== "histogram");
    if (styled.length) {
      html += '<fieldset class="gind-fieldset"><legend>Colores</legend>';
      styled.forEach((o) => {
        html += '<label class="gind-field"><span>' + escapeHtml(o.label) + '</span><input type="color" name="c_' + o.key + '" value="' + colors[o.key] + '"></label>';
      });
      html += "</fieldset>";
    }
    settingsBody.innerHTML = html;
  }

  function openSettings(inst) {
    editing = inst;
    $("gind-settings-title").textContent = inst.def.name;
    fillSettings(inst, inst.params, inst.colors);
    settings.showModal();
  }

  $("gind-reset").addEventListener("click", () => {
    if (!editing) return;
    const defaults = {};
    editing.def.params.forEach((p) => (defaults[p.key] = p.default));
    const colors = {};
    editing.def.outputs.forEach((o) => (colors[o.key] = o.color));
    fillSettings(editing, defaults, colors);
  });

  settings.addEventListener("close", () => {
    const inst = editing;
    editing = null;
    if (!inst || !instances.includes(inst) || settings.returnValue !== "ok") return;
    const data = new FormData(settingsForm);

    let changed = false;
    inst.def.params.forEach((p) => {
      const value = Number(data.get("p_" + p.key));
      if (Number.isFinite(value) && value !== inst.params[p.key]) {
        inst.params[p.key] = value;
        changed = true;
      }
    });
    inst.def.outputs.forEach((o) => {
      const color = data.get("c_" + o.key);
      if (typeof color === "string" && color && color !== inst.colors[o.key]) {
        inst.colors[o.key] = color;
        inst.series[o.key].applyOptions({ color });
      }
    });
    updateName(inst);
    save();
    if (changed) compute([inst]);
    else renderValues(inst, null);
  });

  // ───────────────────────── Arranque ─────────────────────────
  function start(data) {
    catalog = data;
    byId = new Map(catalog.indicators.map((d) => [d.id, d]));
    buildPicker();

    // Recupera los indicadores de la última visita.
    readSaved()
      .filter((s) => s && byId.has(s.id))
      .slice(0, MAX_INSTANCES)
      .forEach((s) => createInstance(byId.get(s.id), s));
    updateCount();
    settleLayout();
    compute(instances.slice());
  }

  button.disabled = true;
  getJSON(root.dataset.indicatorsUrl)
    .then((data) => {
      button.disabled = false;
      start(data);
    })
    .catch(() => {
      button.disabled = false;
      toast("No se pudo cargar la lista de indicadores. Recarga la página.");
    });
})();
