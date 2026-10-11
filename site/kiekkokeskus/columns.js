// Column definitions — the single source of truth for labels (ADR-038).
// Keys are the JSON field names, also the URL sort values (ADR-030).
// `format` is one of: name, text, int, signed, toi, pct1, rate3, dec2, position.
// `firstDir` is the direction applied on the first click of a sort-inactive column.

export const SKATER_COLUMNS = [
  { key: "name", en: "Player", enTitle: "Player", fi: "Pelaaja", fiTitle: "Pelaaja", format: "name", firstDir: "asc" },
  { key: "team", en: "Team", enTitle: "Team", fi: "Joukkue", fiTitle: "Joukkue", format: "text", firstDir: "asc" },
  { key: "positionCode", en: "Pos", enTitle: "Position", fi: "PP", fiTitle: "Pelipaikka", format: "position", firstDir: "asc" },
  { key: "gp", en: "GP", enTitle: "Games played", fi: "O", fiTitle: "Ottelut", format: "int", firstDir: "desc" },
  { key: "g", en: "G", enTitle: "Goals", fi: "M", fiTitle: "Maalit", format: "int", firstDir: "desc" },
  { key: "a", en: "A", enTitle: "Assists", fi: "S", fiTitle: "Syötöt", format: "int", firstDir: "desc" },
  { key: "p", en: "P", enTitle: "Points", fi: "P", fiTitle: "Pisteet", format: "int", firstDir: "desc" },
  { key: "pm", en: "+/-", enTitle: "Plus/minus", fi: "+/−", fiTitle: "Plus-miinus", format: "signed", firstDir: "desc" },
  { key: "pim", en: "PIM", enTitle: "Penalty minutes", fi: "R", fiTitle: "Rangaistusminuutit", format: "int", firstDir: "desc" },
  { key: "toiPerGame", en: "TOI/GP", enTitle: "Time on ice per game", fi: "Aika/O", fiTitle: "Peliaika ottelua kohden", format: "toi", firstDir: "desc" },
  { key: "sog", en: "SOG", enTitle: "Shots on goal", fi: "L", fiTitle: "Laukaukset", format: "int", firstDir: "desc" },
  { key: "shootingPct", en: "S%", enTitle: "Shooting percentage", fi: "L%", fiTitle: "Laukausprosentti", format: "pct1", firstDir: "desc" },
  { key: "ppg", en: "PPG", enTitle: "Power-play goals", fi: "YV", fiTitle: "Ylivoimamaalit", format: "int", firstDir: "desc" },
  { key: "ppp", en: "PPP", enTitle: "Power-play points", fi: "YVP", fiTitle: "Ylivoimapisteet", format: "int", firstDir: "desc" },
  { key: "shg", en: "SHG", enTitle: "Short-handed goals", fi: "AV", fiTitle: "Alivoimamaalit", format: "int", firstDir: "desc" },
  { key: "gwg", en: "GWG", enTitle: "Game-winning goals", fi: "VM", fiTitle: "Voittomaalit", format: "int", firstDir: "desc" },
  { key: "faceoffPct", en: "FO%", enTitle: "Faceoff win percentage", fi: "A%", fiTitle: "Aloitusprosentti", format: "pct1", firstDir: "desc" },
  { key: "hits", en: "HIT", enTitle: "Hits", fi: "TAK", fiTitle: "Taklaukset", format: "int", firstDir: "desc" },
  { key: "blocks", en: "BLK", enTitle: "Blocked shots", fi: "BL", fiTitle: "Blokatut laukaukset", format: "int", firstDir: "desc" },
];

export const GOALIE_COLUMNS = [
  { key: "name", en: "Goalie", enTitle: "Goalie", fi: "Maalivahti", fiTitle: "Maalivahti", format: "name", firstDir: "asc" },
  { key: "team", en: "Team", enTitle: "Team", fi: "Joukkue", fiTitle: "Joukkue", format: "text", firstDir: "asc" },
  { key: "gp", en: "GP", enTitle: "Games played", fi: "PO", fiTitle: "Pelatut ottelut", format: "int", firstDir: "desc" },
  { key: "gs", en: "GS", enTitle: "Games started", fi: "AK", fiTitle: "Avauskokoonpanossa", format: "int", firstDir: "desc" },
  { key: "w", en: "W", enTitle: "Wins", fi: "V", fiTitle: "Voitot", format: "int", firstDir: "desc" },
  { key: "l", en: "L", enTitle: "Losses", fi: "H", fiTitle: "Häviöt", format: "int", firstDir: "desc" },
  { key: "otl", en: "OTL", enTitle: "Overtime and shootout losses", fi: "JH", fiTitle: "Jatkoaika- ja voittomaalikilpailuhäviöt", format: "int", firstDir: "desc" },
  { key: "svPct", en: "SV%", enTitle: "Save percentage", fi: "T%", fiTitle: "Torjuntaprosentti", format: "rate3", firstDir: "desc" },
  { key: "gaa", en: "GAA", enTitle: "Goals-against average", fi: "KA", fiTitle: "Päästettyjen maalien keskiarvo", format: "dec2", firstDir: "asc" },
  { key: "so", en: "SO", enTitle: "Shutouts", fi: "NP", fiTitle: "Nollapelit", format: "int", firstDir: "desc" },
  { key: "toi", en: "TOI", enTitle: "Time on ice", fi: "Aika", fiTitle: "Peliaika", format: "toi", firstDir: "desc" },
];

// Default sort state defined once so url.js can validate column keys per page.
export const SKATER_SORT_DEFAULT = { sortKey: "p", dir: "desc" };
export const GOALIE_SORT_DEFAULT = { sortKey: "gp", dir: "desc" };

// Fixed position ordering for the `position` sort type.
export const POSITION_ORDER = ["C", "L", "R", "D", "G"];

export function findColumn(columns, key) {
  return columns.find((c) => c.key === key) ?? null;
}
