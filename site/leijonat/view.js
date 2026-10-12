// Pure view model for /leijonat. Takes leijonat.json shape + lang; returns display strings
// for every page-specific section. No DOM, no fetch. Testable in Node against
// tests/golden/leijonat.json.

import { t, tp, localName, renderName } from "../kiekkokeskus/i18n.js";
import { date, rate3, season } from "../kiekkokeskus/format.js";

const EN_DASH = "–"; // U+2013

function countRookies(data) {
  const sk = (data.skaters ?? []).filter((r) => r.rookie).length;
  const go = (data.goalies ?? []).filter((r) => r.rookie).length;
  return sk + go;
}

function hasRookie(rows) {
  return (rows ?? []).some((r) => r.rookie);
}

function tilesSection(data, lang) {
  return {
    skaters: {
      label: t("count.skaters", null, lang),
      value: `${(data.skaters ?? []).length}`,
    },
    goalies: {
      label: t("count.goalies", null, lang),
      value: `${(data.goalies ?? []).length}`,
    },
    teams: {
      label: t("count.teams", null, lang),
      value: `${(data.teams ?? []).length}`,
    },
    rookies: {
      label: t("count.rookies", null, lang),
      value: `${countRookies(data)}`,
    },
  };
}

function lastNightCard(row, kind, lang) {
  const g = row.game;
  const badge = t(`result.${g.result}`, null, lang);
  const suffix = g.decidedIn && g.decidedIn !== "REG"
    ? t(`decided.${g.decidedIn}`, null, lang)
    : "";
  // game.opponent is a plain abbreviation here (not a localized object).
  const oppLine = t(g.home ? "opp.home" : "opp.away", { opp: g.opponent }, lang);
  const score = `${g.teamScore}${EN_DASH}${g.oppScore}`;
  const big = kind === "skater"
    ? t("lastNight.skaterLine", { g: row.g, a: row.a }, lang)
    : t(
        "lastNight.goalieLine",
        {
          saves: row.saves ?? "–",
          sa: row.shotsAgainst ?? "–",
          svPct: rate3(row.svPct, lang), // '–' when svPct is null
        },
        lang,
      );
  return {
    kind,
    name: renderName(row, lang),
    team: row.team,
    rookie: !!row.rookie,
    big,
    badge,
    score,
    suffix,
    oppLine,
  };
}

function lastNightSection(data, lang) {
  const ln = data?.lastNight;
  const games = ln?.gamesCompleted ?? 0;
  const dateStr = ln?.date ? date(ln.date, lang) : "–";
  const heading = t("lastNight.title", null, lang);
  const subLine = `${dateStr} · ${tp("lastNight.games", games, lang)}`;
  if (!ln || games === 0) return { empty: true, heading, subLine, message: "noGames" };
  const cards = [
    ...(ln.skaters ?? []).map((r) => lastNightCard(r, "skater", lang)),
    ...(ln.goalies ?? []).map((r) => lastNightCard(r, "goalie", lang)),
  ];
  if (cards.length === 0) return { empty: true, heading, subLine, message: "noFinns" };
  return { empty: false, heading, subLine, cards };
}

function byTeamRows(data, lang) {
  const perTeam = {};
  for (const list of [data.skaters ?? [], data.goalies ?? []]) {
    for (const row of list) {
      (perTeam[row.team] ??= []).push(row);
    }
  }
  const rows = (data.teams ?? []).map((team) => {
    // Sort on the DISPLAYED label, not fi ?? default. For EN we show `default`; sorting on
    // `fi ?? default` would misorder a Finn whose FI spelling starts with a different
    // letter than their EN default. Today Teräväinen/Määttä/Vasilevski all share first
    // letters, but defensively correct.
    const names = (perTeam[team.abbrev] ?? [])
      .map((r) => {
        const label = lang === "fi"
          ? (r.lastName?.fi ?? r.lastName?.default ?? "")
          : (r.lastName?.default ?? "");
        return { label, sortKey: label.toLocaleLowerCase(lang) };
      })
      .sort((a, b) => a.sortKey.localeCompare(b.sortKey, lang))
      .map((x) => x.label)
      .join(", ");
    const total = (team.skaters ?? 0) + (team.goalies ?? 0);
    return {
      name: localName(team.name, lang),
      total,
      playersLabel: tp("byTeam.players", total, lang),
      finnNames: names,
    };
  });
  rows.sort((a, b) => (b.total - a.total) || a.name.localeCompare(b.name, lang));
  return rows;
}

export function leijonatView(data, lang) {
  return {
    pageTitle: t("page.leijonat.title", null, lang),
    subtitle: t(
      "page.leijonat.subtitle",
      { season: season(data.season) },
      lang,
    ),
    hero: { src: "/leijonat/hero.webp", width: 900, height: 604, alt: "" },
    tiles: tilesSection(data, lang),
    lastNight: lastNightSection(data, lang),
    byTeam: byTeamRows(data, lang),
    skaterRookieLegend: hasRookie(data.skaters),
    goalieRookieLegend: hasRookie(data.goalies),
  };
}
