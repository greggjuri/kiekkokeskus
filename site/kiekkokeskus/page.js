// mountPage — the DOM entry on top of createController. Wires the controller's
// render(state, data, {error}) adapter to the real renderers (header + hero, pills, banners,
// tables, page-specific sections via renderSections, footer).

import { createController } from "./controller.js";
import {
  renderHeader,
  renderPills,
  renderStaleBanner,
  renderErrorBanner,
  hideBanner,
  renderFooter,
} from "./chrome.js";
import {
  renderTable,
  prepareSkaterRows,
  prepareGoalieRows,
  renderNoMatchIfEmpty,
} from "./table.js";

export async function mountPage({
  dataPath,
  expectedSchemaVersion,
  columns,
  goalieColumns,
  titleKey,
  subtitle,
  hero,
  renderSections,
  slots,
  // Overrides for the harness / tests
  window: win = typeof window !== "undefined" ? window : undefined,
  document: doc = typeof document !== "undefined" ? document : undefined,
  fetchFn,
  now,
}) {
  if (!win || !doc) throw new Error("mountPage: window/document unavailable");

  function render(state, data, { error }) {
    doc.documentElement.setAttribute("lang", state.lang);

    const resolvedSubtitle =
      typeof subtitle === "function" ? subtitle(data, state.lang) : subtitle ?? null;

    renderHeader({
      root: slots.header,
      titleKey,
      subtitle: resolvedSubtitle,
      lang: state.lang,
      hero,
      onLangChange: (nextLang) => controller.dispatch({ type: "setLang", lang: nextLang }),
    });

    // Error and stale banners are mutually exclusive — error wins.
    if (error) {
      hideBanner(slots.stale);
      renderErrorBanner({ root: slots.error, lang: state.lang });
    } else {
      slots.error.hidden = true;
      renderStaleBanner({
        root: slots.stale,
        generatedAt: data?.generatedAt,
        lang: state.lang,
        now: now ?? new Date(),
      });
    }

    renderPills({
      root: slots.pills,
      state,
      lang: state.lang,
      onChange: (pos) => controller.dispatch({ type: "setPos", pos }),
    });

    const skaters = data
      ? prepareSkaterRows(
          data.skaters ?? [],
          { pos: state.pos, sortKey: state.sort, dir: state.dir, lang: state.lang },
          columns,
        )
      : [];
    renderTable({
      root: slots.skaters,
      columns,
      rows: skaters,
      state: { sortKey: state.sort, dir: state.dir },
      lang: state.lang,
      onSortChange: (ns) =>
        controller.dispatch({ type: "setSort", sortKey: ns.sortKey, dir: ns.dir }),
    });
    if (data) {
      renderNoMatchIfEmpty({
        root: slots.skaters,
        rowsBefore: data.skaters ?? [],
        rowsAfter: skaters,
        columns,
        lang: state.lang,
      });
    }

    const goalies = data
      ? prepareGoalieRows(
          data.goalies ?? [],
          { sortKey: state.gsort, dir: state.gdir, lang: state.lang },
          goalieColumns,
        )
      : [];
    renderTable({
      root: slots.goalies,
      columns: goalieColumns,
      rows: goalies,
      state: { sortKey: state.gsort, dir: state.gdir },
      lang: state.lang,
      onSortChange: (ns) =>
        controller.dispatch({ type: "setGsort", sortKey: ns.sortKey, dir: ns.dir }),
    });

    renderSections?.({ data, lang: state.lang, slots });

    renderFooter({ root: slots.footer, dataDate: data?.dataDate ?? null, lang: state.lang });
  }

  const controller = createController({
    dataPath,
    expectedSchemaVersion,
    columns,
    goalieColumns,
    fetchFn,
    history: win.history,
    storage: win.localStorage,
    location: win.location,
    nav: win.navigator,
    render,
  });

  await controller.start();
  return controller;
}
