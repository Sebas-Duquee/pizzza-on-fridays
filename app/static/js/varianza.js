/**
 * Vista "Análisis de Varianza": pide el histórico de un ticker a la API
 * (la misma que usa el gráfico), lo muestra en tabla y permite exportarlo
 * a CSV.
 */
(function () {
  "use strict";

  const form = document.getElementById("varianza-form");
  if (!form) return; // esta página no está montada

  const tickerInput = document.getElementById("ticker-input");
  const rangeSelect = document.getElementById("range-select");
  const fetchBtn = document.getElementById("fetch-btn");
  const statusEl = document.getElementById("varianza-status");
  const resultEl = document.getElementById("varianza-result");
  const tableBody = document.getElementById("varianza-table-body");
  const summaryEl = document.getElementById("result-summary");
  const downloadBtn = document.getElementById("download-csv-btn");

  let currentTicker = "";
  let currentRows = [];

  function setStatus(message, isError) {
    statusEl.hidden = !message;
    statusEl.textContent = message || "";
    statusEl.classList.toggle("is-error", Boolean(isError));
  }

  function fmtNumber(value) {
    return Number(value).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  }

  function fmtDate(unixSeconds) {
    return new Date(unixSeconds * 1000).toLocaleDateString("es-ES", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  }

  function renderTable(rows) {
    const fragment = document.createDocumentFragment();
    // Más reciente primero.
    [...rows].reverse().forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${fmtDate(row.time)}</td>
        <td>${fmtNumber(row.open)}</td>
        <td>${fmtNumber(row.high)}</td>
        <td>${fmtNumber(row.low)}</td>
        <td>${fmtNumber(row.close)}</td>
        <td>${row.volume.toLocaleString("es-ES")}</td>
      `;
      fragment.appendChild(tr);
    });
    tableBody.replaceChildren(fragment);
  }

  function toCsv(rows) {
    const header = "Fecha,Apertura,Maximo,Minimo,Cierre,Volumen";
    const lines = rows.map((row) => [fmtDate(row.time), row.open, row.high, row.low, row.close, row.volume].join(","));
    return [header, ...lines].join("\n");
  }

  function triggerDownload(filename, content) {
    const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) return;

    fetchBtn.disabled = true;
    resultEl.hidden = true;
    setStatus(`Descargando ${ticker}…`);

    fetch(`/api/candles/${encodeURIComponent(ticker)}?range=${rangeSelect.value}&interval=1d`)
      .then((res) => {
        if (!res.ok) throw new Error("api-error");
        return res.json();
      })
      .then((rows) => {
        if (!Array.isArray(rows) || rows.length === 0) {
          setStatus(`No se encontraron datos para "${ticker}". Verifica el ticker.`, true);
          return;
        }
        currentTicker = ticker;
        currentRows = rows;
        renderTable(rows);
        summaryEl.textContent = `${ticker} · ${rows.length} registros`;
        resultEl.hidden = false;
        setStatus("");
      })
      .catch(() => {
        setStatus(`Ocurrió un error al descargar "${ticker}". Verifica el ticker e inténtalo de nuevo.`, true);
      })
      .finally(() => {
        fetchBtn.disabled = false;
      });
  });

  downloadBtn.addEventListener("click", () => {
    if (!currentRows.length) return;
    triggerDownload(`${currentTicker}_precios.csv`, toCsv(currentRows));
  });
})();
