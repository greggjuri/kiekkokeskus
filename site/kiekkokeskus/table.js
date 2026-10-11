// Table rendering. Thin DOM glue over sort.js + format.js + i18n.js.
// Not unit-tested — exercised in the dev harness and the Layer 7 manual checklist.

import {
  int,
  signed,
  rate3,
  pct1,
  dec2,
  toi,
  position,
} from "./format.js";
import { renderName, t } from "./i18n.js";
import { sortRows, filterSkaters, nextSort } from "./sort.js";

function cellValue(column, row, lang) {
  const key = column.key;
  const raw = row[key];
  switch (column.format) {
    case "name":
      return { text: renderName(row, lang), isNull: false };
    case "text":
      return { text: raw ?? "–", isNull: raw == null };
    case "int":
      return { text: int(raw), isNull: raw == null };
    case "signed":
      return { text: signed(raw, lang), isNull: raw == null };
    case "rate3":
      return { text: rate3(raw, lang), isNull: raw == null };
    case "pct1":
      return { text: pct1(raw, lang), isNull: raw == null };
    case "dec2":
      return { text: dec2(raw, lang), isNull: raw == null };
    case "toi":
      return { text: toi(raw, lang), isNull: raw == null };
    case "position":
      return { text: position(raw, lang), isNull: raw == null };
    default:
      return { text: String(raw ?? "–"), isNull: raw == null };
  }
}

function headerLabel(column, lang) {
  return lang === "fi" ? column.fi : column.en;
}

function headerTitle(column, lang) {
  return lang === "fi" ? column.fiTitle : column.enTitle;
}

function ariaSort(column, state) {
  if (!state || state.sortKey !== column.key) return "none";
  return state.dir === "desc" ? "descending" : "ascending";
}

// renderTable: owns the DOM for one table. Builds <thead> on first render and swaps <tbody>
// on re-render. onSortChange(newState) is called when a header is clicked; the caller passes
// nextSort(state, column) and then calls renderTable again with the new state.
export function renderTable({ root, columns, rows, state, lang, onSortChange }) {
  const doc = root.ownerDocument;

  let table = root.querySelector("table.kk-table");
  if (!table) {
    table = doc.createElement("table");
    table.className = "kk-table";
    const thead = doc.createElement("thead");
    const trh = doc.createElement("tr");
    for (const col of columns) {
      const th = doc.createElement("th");
      th.scope = "col";
      th.dataset.key = col.key;
      if (col.format !== "name" && col.format !== "text" && col.format !== "position") {
        th.classList.add("kk-numeric");
      }
      const btn = doc.createElement("button");
      btn.type = "button";
      btn.textContent = headerLabel(col, lang);
      btn.title = headerTitle(col, lang);
      btn.setAttribute(
        "aria-label",
        t("table.sortBy", { title: headerTitle(col, lang) }, lang),
      );
      btn.addEventListener("click", () => onSortChange?.(nextSort(state, col)));
      th.appendChild(btn);
      trh.appendChild(th);
    }
    thead.appendChild(trh);
    table.appendChild(thead);
    root.innerHTML = "";
    root.appendChild(table);
  }

  // Keep aria-sort and header labels in sync (handles language switch).
  const headers = table.querySelectorAll("thead th");
  headers.forEach((th, i) => {
    const col = columns[i];
    th.setAttribute("aria-sort", ariaSort(col, state));
    const btn = th.querySelector("button");
    if (btn) {
      btn.textContent = headerLabel(col, lang);
      btn.title = headerTitle(col, lang);
      btn.setAttribute(
        "aria-label",
        t("table.sortBy", { title: headerTitle(col, lang) }, lang),
      );
    }
  });

  // Replace <tbody>.
  const oldBody = table.querySelector("tbody");
  if (oldBody) oldBody.remove();

  const tbody = doc.createElement("tbody");

  if (!rows || rows.length === 0) {
    const tr = doc.createElement("tr");
    const td = doc.createElement("td");
    td.colSpan = columns.length;
    td.className = "kk-empty";
    td.textContent = t("table.empty", null, lang);
    tr.appendChild(td);
    tbody.appendChild(tr);
    table.appendChild(tbody);
    return;
  }

  for (const row of rows) {
    const tr = doc.createElement("tr");
    for (const col of columns) {
      const td = doc.createElement("td");
      if (col.format !== "name" && col.format !== "text" && col.format !== "position") {
        td.classList.add("kk-numeric");
      }
      const cell = cellValue(col, row, lang);
      if (cell.isNull) td.classList.add("kk-null");
      td.textContent = cell.text;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
}

// Convenience: apply filter + sort for the skater table in one call. Returns the row array
// the caller passes to renderTable.
export function prepareSkaterRows(rows, { pos, sortKey, dir, lang }, columns) {
  const filtered = filterSkaters(rows, pos);
  const col = columns.find((c) => c.key === sortKey) ?? columns[0];
  return sortRows(filtered, col, { dir, lang });
}

export function prepareGoalieRows(rows, { sortKey, dir, lang }, columns) {
  const col = columns.find((c) => c.key === sortKey) ?? columns[0];
  return sortRows(rows, col, { dir, lang });
}

// If a filter trimmed every row, swap in the "no match" message.
export function renderNoMatchIfEmpty({ root, rowsBefore, rowsAfter, columns, lang }) {
  if (rowsBefore.length === 0 || rowsAfter.length > 0) return false;
  const doc = root.ownerDocument;
  const table = root.querySelector("table.kk-table");
  if (!table) return false;
  const oldBody = table.querySelector("tbody");
  if (oldBody) oldBody.remove();
  const tbody = doc.createElement("tbody");
  const tr = doc.createElement("tr");
  const td = doc.createElement("td");
  td.colSpan = columns.length;
  td.className = "kk-empty";
  td.textContent = t("table.noMatch", null, lang);
  tr.appendChild(td);
  tbody.appendChild(tr);
  table.appendChild(tbody);
  return true;
}
