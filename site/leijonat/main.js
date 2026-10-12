// /leijonat page entry. Thin DOM glue: mounts the shared page controller with a
// renderSections that plants leijonatView strings into the HTML slots.

import { SKATER_COLUMNS, GOALIE_COLUMNS } from "/kiekkokeskus/columns.js";
import { t } from "/kiekkokeskus/i18n.js";
import { season } from "/kiekkokeskus/format.js";
import { mountPage } from "/kiekkokeskus/page.js";
import { leijonatView } from "./view.js";

// /leijonat keeps the full column sets (team column visible on both tables).
const columns = SKATER_COLUMNS;
const goalieColumns = GOALIE_COLUMNS;

const section = document.querySelector("main");
const slots = {
  header: section.querySelector('[data-slot="header"]'),
  stale: section.querySelector('[data-slot="stale"]'),
  error: section.querySelector('[data-slot="error"]'),
  pills: section.querySelector('[data-slot="pills"]'),
  skaters: section.querySelector('[data-slot="skaters"]'),
  goalies: section.querySelector('[data-slot="goalies"]'),
  footer: section.querySelector('[data-slot="footer"]'),
  tiles: section.querySelector('[data-slot="tiles"]'),
  lastNight: section.querySelector('[data-slot="lastNight"]'),
  lastNightTitle: section.querySelector('[data-slot="lastNight-title"]'),
  lastNightSub: section.querySelector('[data-slot="lastNight-sub"]'),
  byTeam: section.querySelector('[data-slot="byTeam"]'),
  byTeamTitle: section.querySelector('[data-slot="byTeam-title"]'),
  skatersTitle: section.querySelector('[data-slot="skaters-title"]'),
  goaliesTitle: section.querySelector('[data-slot="goalies-title"]'),
  skaterRookieLegend: section.querySelector('[data-slot="skaterRookieLegend"]'),
  goalieRookieLegend: section.querySelector('[data-slot="goalieRookieLegend"]'),
};

function placeholderTile(label) {
  const el = document.createElement("article");
  el.className = "kk-tile";
  const l = document.createElement("div");
  l.className = "kk-tile-label";
  l.textContent = label;
  const v = document.createElement("div");
  v.className = "kk-tile-value";
  v.textContent = "–";
  el.append(l, v);
  return el;
}

function renderTile(view) {
  const el = document.createElement("article");
  el.className = "kk-tile";
  const label = document.createElement("div");
  label.className = "kk-tile-label";
  label.textContent = view.label;
  const value = document.createElement("div");
  value.className = "kk-tile-value";
  value.textContent = view.value;
  el.append(label, value);
  return el;
}

function renderLastNight(root, titleSlot, subSlot, section, lang) {
  titleSlot.textContent = section.heading;
  subSlot.textContent = section.subLine;
  root.innerHTML = "";
  if (section.empty) {
    const msg = document.createElement("p");
    msg.className = "kk-empty";
    msg.textContent = t(`lastNight.${section.message}`, null, lang);
    root.appendChild(msg);
    return;
  }
  const grid = document.createElement("div");
  grid.className = "kk-ln-grid";
  for (const card of section.cards) {
    const el = document.createElement("article");
    el.className = "kk-ln-card";

    const head = document.createElement("div");
    head.className = "kk-ln-head";
    const name = document.createElement("span");
    name.className = "kk-ln-name";
    name.textContent = card.name;
    head.appendChild(name);
    if (card.rookie) {
      const mark = document.createElement("span");
      mark.className = "kk-mark";
      mark.setAttribute("aria-hidden", "true");
      mark.textContent = " *";
      head.appendChild(mark);
      const sr = document.createElement("span");
      sr.className = "kk-sr-only";
      sr.textContent = t("rookie.title", null, lang);
      head.appendChild(sr);
    }
    const team = document.createElement("span");
    team.className = "kk-ln-team";
    team.textContent = card.team;
    head.appendChild(team);
    el.appendChild(head);

    const big = document.createElement("div");
    big.className = "kk-ln-big";
    big.textContent = card.big;
    el.appendChild(big);

    const gameRow = document.createElement("div");
    gameRow.className = "kk-ln-game";
    const badge = document.createElement("span");
    badge.className = "kk-badge";
    badge.dataset.result = card.badge;
    badge.textContent = card.badge;
    const score = document.createElement("span");
    score.className = "kk-score";
    score.textContent = card.score + (card.suffix ? ` ${card.suffix}` : "");
    const opp = document.createElement("span");
    opp.className = "kk-opp";
    opp.textContent = card.oppLine;
    gameRow.append(badge, score, opp);
    el.appendChild(gameRow);

    grid.appendChild(el);
  }
  root.appendChild(grid);
}

function renderByTeam(root, rows) {
  root.innerHTML = "";
  for (const row of rows) {
    const r = document.createElement("div");
    r.className = "kk-byteam-row";
    const n = document.createElement("div");
    n.className = "kk-byteam-name";
    n.textContent = row.name;
    const c = document.createElement("div");
    c.className = "kk-byteam-count";
    c.textContent = row.playersLabel;
    const l = document.createElement("div");
    l.className = "kk-byteam-list";
    l.textContent = row.finnNames;
    r.append(n, c, l);
    root.appendChild(r);
  }
}

mountPage({
  dataPath: "/data/kiekkokeskus/leijonat.json",
  expectedSchemaVersion: 1,
  columns,
  goalieColumns,
  defaults: { pos: "all", sort: "p", dir: "desc", gsort: "gp", gdir: "desc" },
  titleKey: "page.leijonat.title",
  subtitle: (data, lang) =>
    data
      ? t("page.leijonat.subtitle", { season: season(data.season) }, lang)
      : t("page.leijonat.subtitleNoSeason", null, lang),
  hero: { src: "/leijonat/hero.webp", width: 900, height: 604, alt: "" },
  slots,
  // Passed to BOTH tables (skater + goalie). Appears on rookie rows only.
  decorateName: (row, lang) =>
    row?.rookie
      ? { suffix: " *", title: t("rookie.title", null, lang) }
      : null,
  renderSections: ({ data, lang, slots }) => {
    slots.skatersTitle.textContent = t("table.skaters", null, lang);
    slots.goaliesTitle.textContent = t("table.goalies", null, lang);
    slots.byTeamTitle.textContent = t("byTeam.title", null, lang);

    slots.tiles.innerHTML = "";
    if (data) {
      const view = leijonatView(data, lang);
      slots.tiles.append(
        renderTile(view.tiles.skaters),
        renderTile(view.tiles.goalies),
        renderTile(view.tiles.teams),
        renderTile(view.tiles.rookies),
      );
      renderLastNight(slots.lastNight, slots.lastNightTitle, slots.lastNightSub, view.lastNight, lang);
      renderByTeam(slots.byTeam, view.byTeam);
      slots.skaterRookieLegend.hidden = !view.skaterRookieLegend;
      slots.skaterRookieLegend.textContent = view.skaterRookieLegend
        ? t("rookie.legend", null, lang)
        : "";
      slots.goalieRookieLegend.hidden = !view.goalieRookieLegend;
      slots.goalieRookieLegend.textContent = view.goalieRookieLegend
        ? t("rookie.legend", null, lang)
        : "";
    } else {
      // Error or pre-fetch: render placeholder tiles so layout holds steady.
      slots.tiles.append(
        placeholderTile(t("count.skaters", null, lang)),
        placeholderTile(t("count.goalies", null, lang)),
        placeholderTile(t("count.teams", null, lang)),
        placeholderTile(t("count.rookies", null, lang)),
      );
      slots.lastNightTitle.textContent = t("lastNight.title", null, lang);
      slots.lastNightSub.textContent = "";
      slots.lastNight.innerHTML = "";
      slots.byTeam.innerHTML = "";
      slots.skaterRookieLegend.hidden = true;
      slots.goalieRookieLegend.hidden = true;
    }
  },
});
