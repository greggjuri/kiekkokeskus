// Pure page controller — no DOM. Owns the state reducer, a single loadData call cached in
// closure, writeState after every action, and the localStorage persist on setLang. The caller
// supplies a `render(state, data, { error })` adapter that handles the DOM (mountPage in
// page.js, or a recording stub in controller.test.js).

import { resolveLang } from "./i18n.js";
import { readState, writeState } from "./url.js";
import { loadData } from "./data.js";

const STORAGE_KEY = "kk.lang";

export function pageReducer(state, action) {
  switch (action.type) {
    case "setLang":
      return { ...state, lang: action.lang, langExplicit: true };
    case "setPos":
      return { ...state, pos: action.pos };
    case "setSort":
      return { ...state, sort: action.sortKey, dir: action.dir };
    case "setGsort":
      return { ...state, gsort: action.sortKey, gdir: action.dir };
    default:
      return state;
  }
}

function tryWriteStorage(storage, value) {
  try {
    storage?.setItem?.(STORAGE_KEY, value);
  } catch {
    // ignore: language just isn't persisted this session
  }
}

export function createController({
  dataPath,
  expectedSchemaVersion,
  columns,
  goalieColumns,
  fetchFn,
  history,
  storage,
  location,
  nav,
  render,
}) {
  const url = new URL(location.href);
  const resolved = resolveLang({ url, storage, nav }).lang;
  let state = readState({
    search: location.search,
    columns,
    goalieColumns,
    resolvedLang: resolved,
  });

  // Cached data + error — populated once by start(), reused by every subsequent render.
  let data = null;
  let error = null;

  function doRender() {
    render(state, data, { error });
  }

  function writeAndRender(prev) {
    const action = prev;
    if (action && action.type === "setLang") {
      tryWriteStorage(storage, state.lang);
    }
    writeState(state, {
      history,
      pathname: location.pathname,
      langExplicit: state.langExplicit,
    });
    doRender();
  }

  function dispatch(action) {
    state = pageReducer(state, action);
    writeAndRender(action);
  }

  async function start() {
    const result = await loadData(dataPath, expectedSchemaVersion, { fetchFn });
    if (result.ok) {
      data = result.data;
      error = null;
    } else {
      data = null;
      error = result.reason ?? "unknown";
    }
    doRender();
  }

  return { dispatch, start, getState: () => state, getData: () => data, getError: () => error };
}
