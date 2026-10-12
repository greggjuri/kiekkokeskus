// Table rendering. Thin DOM glue over sort.js + format.js + i18n.js. DOM rendering is
// exercised in the dev harness and the Layer 7 manual checklist. The pure
// `headerClickHandler` reducer is unit-tested in `table.test.js`.

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

// Pure header-click reducer. The listener attached to each <th>'s <button> uses this to look
// up the *current* state and onSortChange at click time, not the state captured in the first
// render's closure (that was the bug: second click on the same header always fired with the
// first-render state and never flipped the direction).
export function headerClickHandler(getCurrent, col) {
  const { state, onSortChange } = getCurrent() ?? {};
  onSortChange?.(nextSort(state, col));
}

// Pure. Returns the three parts the DOM renderer places into a name cell:
//   { name: 'Full Name', suffix: ' *' | null, title: 'Rookie' | null }
// `decorateName(row, lang)` is optional. When omitted (or when it returns null, or returns
// an object with falsy suffix), both suffix and title are null and the renderer leaves the
// name cell as a bare text node — so /bolts markup stays byte-identical to today.
export function nameCellParts(row, lang, decorateName) {
  const name = renderName(row, lang);
  if (!decorateName) return { name, suffix: null, title: null };
  const deco = decorateName(row, lang);
  if (!deco || !deco.suffix) return { name, suffix: null, title: null };
  return { name, suffix: deco.suffix, title: deco.title ?? null };
}

// renderTable: owns the DOM for one table. Builds <thead> once and swaps <tbody> on re-render.
// Every call stores the latest { state, onSortChange } on the table element so the header
// listeners (attached only once) can read them live.
//
// decorateName(row, lang) — optional. When passed and the column format is 'name', the cell
// decides via nameCellParts() whether to append a marker + sr-only title. Without
// decorateName (the /bolts case) the name cell is a bare text node, identical to today.
export function renderTable({ root, columns, rows, state, lang, onSortChange, decorateName }) {
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
      btn.addEventListener("click", () => headerClickHandler(() => table._kk, col));
      th.appendChild(btn);
      trh.appendChild(th);
    }
    thead.appendChild(trh);
    table.appendChild(thead);
    root.innerHTML = "";
    root.appendChild(table);
  }

  // Set BEFORE the early return below so the click handler always reads the latest state,
  // even when a render exits early (empty rows path).
  table._kk = { state, onSortChange };

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
      // Special-case the name column so decorateName can append a marker + sr-only title
      // without disturbing /bolts markup when decorateName is absent.
      if (col.format === "name") {
        const parts = nameCellParts(row, lang, decorateName);
        if (parts.suffix) {
          // Bare text node for the name, then <span class="kk-mark"> + <span class="kk-sr-only">
          td.appendChild(doc.createTextNode(parts.name));
          const mark = doc.createElement("span");
          mark.className = "kk-mark";
          mark.setAttribute("aria-hidden", "true");
          mark.textContent = parts.suffix;
          td.appendChild(mark);
          if (parts.title) {
            const sr = doc.createElement("span");
            sr.className = "kk-sr-only";
            sr.textContent = parts.title;
            td.appendChild(sr);
          }
        } else {
          td.textContent = parts.name; // bare text node — /bolts byte-identity
        }
        tr.appendChild(td);
        continue;
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
