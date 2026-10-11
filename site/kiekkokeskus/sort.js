// Pure sort + filter helpers for the player tables.

import { nameSortKey } from "./i18n.js";
import { POSITION_ORDER } from "./columns.js";

function isNullish(v) {
  return v == null;
}

// Comparator for a given column type. Returns a sort function that pairs with Array.sort.
function makeCompare(type, lang) {
  if (type === "name") {
    return (a, b) => nameSortKey(a, lang).localeCompare(nameSortKey(b, lang), lang);
  }
  if (type === "text") {
    return (a, b) => {
      const sa = String(a ?? "");
      const sb = String(b ?? "");
      return sa.localeCompare(sb, lang);
    };
  }
  if (type === "position") {
    return (a, b) => {
      const ia = POSITION_ORDER.indexOf(a);
      const ib = POSITION_ORDER.indexOf(b);
      return ia - ib;
    };
  }
  // numeric
  return (a, b) => Number(a) - Number(b);
}

// sortRows: nulls always sort last in both directions; sort is stable.
export function sortRows(rows, column, { dir, lang }) {
  const type = column.format;
  const nonNull = [];
  const nulls = [];

  for (const row of rows) {
    const v = type === "name" ? row : row?.[column.key];
    if (type !== "name" && isNullish(v)) nulls.push(row);
    else nonNull.push(row);
  }

  const compare = makeCompare(type, lang);
  // Decorate with original index for stability under equal keys.
  const decorated = nonNull.map((row, i) => ({ row, i }));
  decorated.sort((x, y) => {
    const a = type === "name" ? x.row : x.row?.[column.key];
    const b = type === "name" ? y.row : y.row?.[column.key];
    const c = compare(a, b);
    if (c !== 0) return dir === "desc" ? -c : c;
    return x.i - y.i;
  });

  return [...decorated.map((d) => d.row), ...nulls];
}

export function filterSkaters(rows, posFilter) {
  if (posFilter === "all" || !posFilter) return rows;
  if (posFilter === "d") return rows.filter((r) => r.positionCode === "D");
  if (posFilter === "f") {
    return rows.filter((r) => r.positionCode === "C" || r.positionCode === "L" || r.positionCode === "R");
  }
  return rows;
}

// Pure header-click reducer. Called by the table UI; keeps DOM state out of the test surface.
// If the click targets the active sort column, flip the direction. Otherwise fall to the
// column's firstDir. The caller then re-renders.
export function nextSort(state, column) {
  if (state?.sortKey === column.key) {
    return { sortKey: column.key, dir: state.dir === "desc" ? "asc" : "desc" };
  }
  return { sortKey: column.key, dir: column.firstDir };
}
