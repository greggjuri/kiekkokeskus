// Pure view model for /bolts. Takes bolts.json shape + lang; returns display strings for
// every page-specific section. No DOM, no fetch. Testable in Node against tests/golden/bolts.json.

import { t, tp, localName } from "../kiekkokeskus/i18n.js";
import {
  signed,
  pct1Sign,
  date,
  gameTime,
  ordinal,
  season,
} from "../kiekkokeskus/format.js";

const EN_DASH = "–"; // U+2013

function gihClause(gih, lang) {
  if (gih == null || gih === 0) return "";
  if (gih > 0) return ` · ${tp("gih.ahead", gih, lang)}`;
  return ` · ${tp("gih.behind", -gih, lang)}`;
}

function recordTile(s, lang) {
  const value = s.gp === 0 && s.w === 0 && s.l === 0 && s.otl === 0
    ? `0${EN_DASH}0${EN_DASH}0`
    : `${s.w}${EN_DASH}${s.l}${EN_DASH}${s.otl}`;
  const pts = tp("unit.pts", s.pts ?? 0, lang);
  const sub = s.streak
    ? `${pts} · ${t("tile.streak", null, lang)} ${t(
        `streak.${s.streak.code}`,
        { n: s.streak.count },
        lang,
      )}`
    : pts;
  return { label: t("tile.record", null, lang), value, sub };
}

function divisionTile(s, lang) {
  return {
    label: t(`div.${s.division.abbrev}`, null, lang),
    value: ordinal(s.division.rank, lang),
    sub: t(
      "tile.divisionSub",
      {
        confRank: ordinal(s.conference.rank, lang),
        conf: t(`conf.${s.conference.abbrev}`, null, lang),
        leagueRank: ordinal(s.leagueRank, lang),
      },
      lang,
    ),
  };
}

function divisionLeadTile(s, lang) {
  const dl = s.divisionLead;
  const tblLeads = dl.leader === "TBL";
  return {
    label: tblLeads ? t("tile.divLeader", null, lang) : t("tile.divLead", null, lang),
    // From Tampa's point of view: positive = ahead, negative = behind. gap is reference −
    // TBL points; TBL "behind by gap" renders as −gap.
    value: tblLeads ? "0" : signed(-dl.gap, lang),
    sub:
      `${dl.leader} · ${tp("unit.pts", dl.leaderPts, lang)}` +
      gihClause(dl.gamesInHand, lang),
  };
}

function playoffLineTile(s, lang) {
  const pl = s.playoffLine;
  // In position: value is the cushion (positive). Out of position: value is the deficit
  // (negative). Both are Tampa's point of view.
  const value = pl.inPosition ? signed(+pl.gap, lang) : signed(-pl.gap, lang);
  return {
    label: pl.inPosition
      ? t("tile.playoffIn", null, lang)
      : t("tile.playoffOut", null, lang),
    value,
    sub:
      `${pl.team} · ${tp("unit.pts", pl.teamPts, lang)}` +
      gihClause(pl.gamesInHand, lang),
  };
}

function lastGameCard(data, lang) {
  if (!data.lastGame) return null;
  const g = data.lastGame;
  const suffix = g.decidedIn && g.decidedIn !== "REG"
    ? t(`decided.${g.decidedIn}`, null, lang)
    : "";
  return {
    badge: t(`result.${g.result}`, null, lang),
    score: `${g.tblScore}${EN_DASH}${g.oppScore}`,
    suffix,
    oppLine: t(g.home ? "opp.home" : "opp.away", { opp: localName(g.opponent.name, lang) }, lang),
    dateStr: date(g.date, lang),
  };
}

function nextGamesList(data, lang) {
  return (data.nextGames ?? []).map((g) => ({
    when: gameTime(g.startTimeUTC, lang),
    oppLine: t(g.home ? "opp.home" : "opp.away", { opp: localName(g.opponent.name, lang) }, lang),
  }));
}

function specialSide(data, key, labelKey, lang) {
  const st = data.specialTeams ?? {};
  const pct = st[`${key}Pct`];
  const rank = st[`${key}Rank`];
  return {
    label: t(labelKey, null, lang),
    pct: pct1Sign(pct, lang),
    rank: rank != null ? t("special.rank", { rank: ordinal(rank, lang) }, lang) : null,
  };
}

export function boltsView(data, lang) {
  const s = data.standing;
  return {
    pageTitle: t("page.bolts.title", null, lang),
    subtitle: t(
      "page.bolts.subtitle",
      { season: season(data.season) },
      lang,
    ),
    hero: { src: "/bolts/hero.webp", width: 900, height: 604, alt: "" },
    tiles: {
      record: recordTile(s, lang),
      division: divisionTile(s, lang),
      divisionLead: divisionLeadTile(s, lang),
      playoffLine: playoffLineTile(s, lang),
    },
    lastGame: lastGameCard(data, lang),
    nextGames: nextGamesList(data, lang),
    special: {
      pp: specialSide(data, "pp", "special.pp", lang),
      pk: specialSide(data, "pk", "special.pk", lang),
    },
  };
}
