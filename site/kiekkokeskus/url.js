// URL state: parse and serialize view state. Default values are dropped so a fresh view is a
// clean URL. `lang` is only written when the user explicitly set it (?lang= on arrival or
// toggle click), so shared default-locale links don't lock recipients into the sender's
// language (ADR-028).

import {
  SKATER_SORT_DEFAULT,
  GOALIE_SORT_DEFAULT,
  findColumn,
} from "./columns.js";
import { SUPPORTED_LANGS } from "./strings.js";

const POS_VALUES = ["all", "f", "d"];
const DIR_VALUES = ["asc", "desc"];

export function readState({ search, columns, goalieColumns, resolvedLang }) {
  const params = new URLSearchParams(search ?? "");
  const urlLang = params.get("lang");
  const langExplicit =
    typeof urlLang === "string" && SUPPORTED_LANGS.includes(urlLang);
  const lang = langExplicit ? urlLang : resolvedLang ?? "en";

  const pos = POS_VALUES.includes(params.get("pos")) ? params.get("pos") : "all";

  const rawSort = params.get("sort");
  const sort = rawSort && findColumn(columns, rawSort)
    ? rawSort
    : SKATER_SORT_DEFAULT.sortKey;

  const rawDir = params.get("dir");
  const dir = DIR_VALUES.includes(rawDir) ? rawDir : SKATER_SORT_DEFAULT.dir;

  const rawGsort = params.get("gsort");
  const gsort = rawGsort && findColumn(goalieColumns, rawGsort)
    ? rawGsort
    : GOALIE_SORT_DEFAULT.sortKey;

  const rawGdir = params.get("gdir");
  const gdir = DIR_VALUES.includes(rawGdir) ? rawGdir : GOALIE_SORT_DEFAULT.dir;

  return { lang, langExplicit, pos, sort, dir, gsort, gdir };
}

export function writeState(state, { history, pathname, langExplicit }) {
  const params = new URLSearchParams();
  if (langExplicit) {
    params.set("lang", state.lang);
  }
  if (state.pos !== "all") params.set("pos", state.pos);
  if (state.sort !== SKATER_SORT_DEFAULT.sortKey) params.set("sort", state.sort);
  if (state.dir !== SKATER_SORT_DEFAULT.dir) params.set("dir", state.dir);
  if (state.gsort !== GOALIE_SORT_DEFAULT.sortKey)
    params.set("gsort", state.gsort);
  if (state.gdir !== GOALIE_SORT_DEFAULT.dir) params.set("gdir", state.gdir);

  const query = params.toString();
  const url = query ? `${pathname}?${query}` : pathname;
  history?.replaceState?.(null, "", url);
  return url;
}
