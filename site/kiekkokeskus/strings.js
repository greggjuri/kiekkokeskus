// UI strings for both pages (ADR-028). Column labels do NOT live here — see columns.js.
// Disclaimer EN matches README.md verbatim (ADR-002).

export const STRINGS = {
  en: {
    "nav.crumb": "jurigregg.com / kiekkokeskus",
    "lang.group": "Language",
    "pos.group": "Position",
    "pos.all": "All",
    "pos.f": "Forwards",
    "pos.d": "Defense",
    "table.skaters": "Skaters",
    "table.goalies": "Goalies",
    "table.sortBy": "Sort by {title}",
    "table.loading": "Loading…",
    "table.empty": "No games played yet.",
    "table.noMatch": "No players match this filter.",
    "banner.stale":
      "Data may be out of date. Last updated {date} at {time}.",
    "banner.error": "Stats couldn't be loaded. Try again later.",
    "footer.through": "Data through {date} · updated daily at 10:00 ET",
    "footer.disclaimer":
      "Kiekkokeskus is a personal, non-commercial project. It is not affiliated with, endorsed by, or sponsored by the National Hockey League, the Tampa Bay Lightning, or any NHL team. Team and league names are trademarks of their respective owners. Data comes from publicly accessible NHL endpoints.",
    "posCode.C": "C",
    "posCode.L": "L",
    "posCode.R": "R",
    "posCode.D": "D",
    "posCode.G": "G",
  },
  fi: {
    "nav.crumb": "jurigregg.com / kiekkokeskus",
    "lang.group": "Kieli",
    "pos.group": "Pelipaikka",
    "pos.all": "Kaikki",
    "pos.f": "Hyökkääjät",
    "pos.d": "Puolustajat",
    "table.skaters": "Kenttäpelaajat",
    "table.goalies": "Maalivahdit",
    "table.sortBy": "Lajittele: {title}",
    "table.loading": "Ladataan…",
    "table.empty": "Ei vielä pelattuja otteluita.",
    "table.noMatch": "Ei pelaajia tällä suodattimella.",
    "banner.stale":
      "Tiedot voivat olla vanhentuneita. Päivitetty viimeksi {date} klo {time}.",
    "banner.error": "Tilastoja ei voitu ladata. Yritä myöhemmin uudelleen.",
    "footer.through":
      "Tiedot {date} asti · päivittyy päivittäin klo 10.00 (ET)",
    "footer.disclaimer":
      "Kiekkokeskus on henkilökohtainen, ei-kaupallinen projekti. Se ei ole sidoksissa NHL:ään, Tampa Bay Lightningiin tai mihinkään NHL-joukkueeseen, eivätkä ne ole hyväksyneet tai tukeneet sitä. Joukkueiden ja liigan nimet ovat omistajiensa tavaramerkkejä. Tiedot ovat peräisin NHL:n julkisista rajapinnoista.",
    "posCode.C": "KH",
    "posCode.L": "VL",
    "posCode.R": "OL",
    "posCode.D": "P",
    "posCode.G": "MV",
  },
};

export const SUPPORTED_LANGS = ["en", "fi"];
