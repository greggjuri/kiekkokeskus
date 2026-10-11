// /bolts page entry. Thin DOM glue: mounts the shared page controller with a renderSections
// that plants boltsView strings into the HTML slots.

import { SKATER_COLUMNS, GOALIE_COLUMNS } from "/kiekkokeskus/columns.js";
import { t } from "/kiekkokeskus/i18n.js";
import { season } from "/kiekkokeskus/format.js";
import { mountPage } from "/kiekkokeskus/page.js";
import { boltsView } from "./view.js";

const columns = SKATER_COLUMNS.filter((c) => c.key !== "team");
const goalieColumns = GOALIE_COLUMNS.filter((c) => c.key !== "team");

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
  lastGame: section.querySelector('[data-slot="lastGame"]'),
  nextGames: section.querySelector('[data-slot="nextGames"]'),
  special: section.querySelector('[data-slot="special"]'),
  skatersTitle: section.querySelector('[data-slot="skaters-title"]'),
  goaliesTitle: section.querySelector('[data-slot="goalies-title"]'),
  lastGameTitle: section.querySelector('[data-slot="lastGame-title"]'),
  nextGamesTitle: section.querySelector('[data-slot="nextGames-title"]'),
  specialTitle: section.querySelector('[data-slot="special-title"]'),
};

function placeholderTile(label) {
  const el = document.createElement("article");
  el.className = "kk-tile";
  el.innerHTML = `<div class="kk-tile-label"></div><div class="kk-tile-value">–</div><div class="kk-tile-sub"></div>`;
  el.querySelector(".kk-tile-label").textContent = label;
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
  const sub = document.createElement("div");
  sub.className = "kk-tile-sub";
  sub.textContent = view.sub;
  el.append(label, value, sub);
  return el;
}

function renderLastGame(root, g, lang) {
  root.innerHTML = "";
  if (!g) {
    root.textContent = t("table.empty", null, lang);
    root.className = "kk-empty";
    return;
  }
  root.className = "";
  const badge = document.createElement("span");
  badge.className = "kk-badge";
  badge.dataset.result = g.badge;
  badge.textContent = g.badge;
  const score = document.createElement("span");
  score.className = "kk-score";
  score.textContent = g.score + (g.suffix ? ` ${g.suffix}` : "");
  const opp = document.createElement("div");
  opp.className = "kk-opp";
  opp.textContent = g.oppLine;
  const d = document.createElement("div");
  d.className = "kk-when";
  d.textContent = g.dateStr;
  const row = document.createElement("div");
  row.className = "kk-lastgame-row";
  row.append(badge, score);
  root.append(row, opp, d);
}

function renderNextGames(root, games, lang) {
  root.innerHTML = "";
  if (games.length === 0) {
    root.textContent = t("nextGames.none", null, lang);
    root.className = "kk-empty";
    return;
  }
  root.className = "";
  for (const g of games) {
    const row = document.createElement("div");
    row.className = "kk-nextgame-row";
    const when = document.createElement("div");
    when.className = "kk-when";
    when.textContent = g.when;
    const opp = document.createElement("div");
    opp.className = "kk-opp";
    opp.textContent = g.oppLine;
    row.append(when, opp);
    root.appendChild(row);
  }
}

function renderSpecial(root, special) {
  root.innerHTML = "";
  for (const side of ["pp", "pk"]) {
    const s = special[side];
    const row = document.createElement("div");
    row.className = "kk-special-row";
    const label = document.createElement("div");
    label.className = "kk-special-label";
    label.textContent = s.label;
    const pct = document.createElement("div");
    pct.className = "kk-special-pct";
    pct.textContent = s.pct;
    row.append(label, pct);
    if (s.rank) {
      const rank = document.createElement("div");
      rank.className = "kk-special-rank";
      rank.textContent = s.rank;
      row.appendChild(rank);
    }
    root.appendChild(row);
  }
}

mountPage({
  dataPath: "/data/kiekkokeskus/bolts.json",
  expectedSchemaVersion: 1,
  columns,
  goalieColumns,
  titleKey: "page.bolts.title",
  // Resolved per render so the literal {season} never leaks into the DOM during load/error.
  subtitle: (data, lang) =>
    data
      ? t("page.bolts.subtitle", { season: season(data.season) }, lang)
      : t("page.bolts.subtitleNoSeason", null, lang),
  hero: { src: "/bolts/hero.webp", width: 900, height: 604, alt: "" },
  slots,
  renderSections: ({ data, lang, slots }) => {
    slots.skatersTitle.textContent = t("table.skaters", null, lang);
    slots.goaliesTitle.textContent = t("table.goalies", null, lang);
    slots.lastGameTitle.textContent = t("lastGame.title", null, lang);
    slots.nextGamesTitle.textContent = t("nextGames.title", null, lang);
    slots.specialTitle.textContent = t("special.title", null, lang);

    slots.tiles.innerHTML = "";
    if (data) {
      const view = boltsView(data, lang);
      slots.tiles.append(
        renderTile(view.tiles.record),
        renderTile(view.tiles.division),
        renderTile(view.tiles.divisionLead),
        renderTile(view.tiles.playoffLine),
      );
      renderLastGame(slots.lastGame, view.lastGame, lang);
      renderNextGames(slots.nextGames, view.nextGames, lang);
      renderSpecial(slots.special, view.special);
    } else {
      // Error or pre-fetch: render placeholder tiles with '–' value so layout holds steady.
      slots.tiles.append(
        placeholderTile(t("tile.record", null, lang)),
        placeholderTile(t("div.A", null, lang)),
        placeholderTile(t("tile.divLead", null, lang)),
        placeholderTile(t("tile.playoffIn", null, lang)),
      );
      renderLastGame(slots.lastGame, null, lang);
      renderNextGames(slots.nextGames, [], lang);
      slots.special.innerHTML = "–";
    }
  },
});
