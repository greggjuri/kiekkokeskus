// Language resolution, string lookup, name rendering (ADR-018 + ADR-028).
// Pure functions take explicit inputs; wireToggle is the only DOM glue.

import { STRINGS, SUPPORTED_LANGS } from "./strings.js";

const STORAGE_KEY = "kk.lang";

function readStorage(storage) {
  try {
    return storage?.getItem?.(STORAGE_KEY) ?? null;
  } catch {
    return null;
  }
}

function writeStorage(storage, lang) {
  try {
    storage?.setItem?.(STORAGE_KEY, lang);
  } catch {
    // ignore; the language choice simply isn't persisted this session
  }
}

// resolveLang follows ADR-028's order: ?lang= → localStorage → navigator.language starting
// "fi" → EN. Also returns whether lang came from an explicit source (URL or storage/toggle),
// so writeState knows whether to keep ?lang= in the URL (prevents shared links from locking
// recipients to the sender's locale).
export function resolveLang({ url, storage, nav } = {}) {
  const urlLang = url?.searchParams?.get("lang");
  if (urlLang && SUPPORTED_LANGS.includes(urlLang)) {
    return { lang: urlLang, source: "url" };
  }

  const stored = readStorage(storage);
  if (stored && SUPPORTED_LANGS.includes(stored)) {
    return { lang: stored, source: "storage" };
  }

  const navLang = nav?.language ?? "";
  if (typeof navLang === "string" && navLang.toLowerCase().startsWith("fi")) {
    return { lang: "fi", source: "nav" };
  }

  return { lang: "en", source: "default" };
}

export function t(key, vars, lang) {
  const dict = STRINGS[lang] ?? STRINGS.en;
  const template = dict[key] ?? STRINGS.en[key] ?? key;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, name) =>
    Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : `{${name}}`,
  );
}

// renderName: ADR-018 says builders pass through localized objects untouched; this is the
// only place a language is picked (ADR-028).
// EN: firstName.default + " " + lastName.default
// FI: each part's own fi key with default fallback, so Vasilevskiy (lastName.fi only) renders
// "Andrei Vasilevski" without resorting to the EN surname.
export function renderName(row, lang) {
  const { firstName, lastName } = row ?? {};
  const first = pickPart(firstName, lang);
  const last = pickPart(lastName, lang);
  return `${first} ${last}`.trim();
}

function pickPart(part, lang) {
  if (part == null) return "";
  if (typeof part === "string") return part;
  if (lang === "fi") return part.fi ?? part.default ?? "";
  return part.default ?? "";
}

// Sort key for the name column (last-then-first, lowercased for localeCompare in the caller).
export function nameSortKey(row, lang) {
  const last = pickPart(row?.lastName, lang).toLocaleLowerCase(lang);
  const first = pickPart(row?.firstName, lang).toLocaleLowerCase(lang);
  return `${last} ${first}`;
}

// wireToggle: DOM glue. Attaches to the two EN|FI buttons rendered by chrome.renderHeader and
// calls onChange(nextLang, "toggle") when the user picks a language. Keeps <html lang>, URL,
// and localStorage in sync. The caller owns re-rendering.
export function wireToggle({ buttons, storage, html, onChange }) {
  if (!buttons) return;
  for (const btn of buttons) {
    btn.addEventListener("click", () => {
      const next = btn.dataset.lang;
      if (!SUPPORTED_LANGS.includes(next)) return;
      if (html) html.setAttribute("lang", next);
      writeStorage(storage, next);
      onChange?.(next, "toggle");
    });
  }
}

// tp: plural lookup. Picks `${key}.${cat}` where cat ∈ {zero, one, two, few, many, other}
// (whichever Intl.PluralRules returns for the locale + n), falling back to `${key}.other`.
// Then runs the result through t()'s {name} interpolation with { n, ...vars }.
const PLURAL_RULES = { en: new Intl.PluralRules("en-US"), fi: new Intl.PluralRules("fi-FI") };

export function tp(key, n, lang, vars) {
  const rules = PLURAL_RULES[lang] ?? PLURAL_RULES.en;
  const cat = rules.select(n);
  const dict = STRINGS[lang] ?? STRINGS.en;
  const template = dict[`${key}.${cat}`] ?? dict[`${key}.other`]
    ?? STRINGS.en[`${key}.${cat}`] ?? STRINGS.en[`${key}.other`]
    ?? key;
  return template.replace(/\{(\w+)\}/g, (_, name) => {
    if (name === "n") return String(n);
    if (vars && Object.prototype.hasOwnProperty.call(vars, name)) return String(vars[name]);
    return `{${name}}`;
  });
}

// localName: for team names and anything else carrying a {default, fi?} object that is NOT a
// person. People use renderName (first + last). FI → obj.fi ?? obj.default; EN → obj.default.
// Null-safe. init-08 reuses for `teams[].name`.
export function localName(obj, lang) {
  if (obj == null) return "–";
  if (typeof obj === "string") return obj;
  if (lang === "fi") return obj.fi ?? obj.default ?? "–";
  return obj.default ?? "–";
}
