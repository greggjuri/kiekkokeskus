// Formatters. Data stays raw (fractions 0–1, int seconds); this is the only place units change.
// Every formatter returns '–' (U+2013) for null or undefined (ADR-015).

import { STRINGS } from "./strings.js";

export const NULL_DISPLAY = "–"; // U+2013 EN DASH

function nullish(n) {
  return n == null || Number.isNaN(n);
}

const INT_EN = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const INT_FI = new Intl.NumberFormat("fi-FI", { maximumFractionDigits: 0 });

const SIGNED_EN = new Intl.NumberFormat("en-US", { signDisplay: "exceptZero" });
const SIGNED_FI = new Intl.NumberFormat("fi-FI", { signDisplay: "exceptZero" });

const DEC2_EN = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const DEC2_FI = new Intl.NumberFormat("fi-FI", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const PCT1_EN = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const PCT1_FI = new Intl.NumberFormat("fi-FI", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const PCT1SIGN_EN = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const PCT1SIGN_FI = new Intl.NumberFormat("fi-FI", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const DATE_EN = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});
const DATE_FI = new Intl.DateTimeFormat("fi-FI", {
  year: "numeric",
  month: "numeric",
  day: "numeric",
  timeZone: "UTC",
});

export function int(n) {
  if (nullish(n)) return NULL_DISPLAY;
  return INT_EN.format(n); // digit shape identical across EN/FI for integers
}

// U+2212 MINUS SIGN in both languages. Intl's en-US emits U+002D hyphen-minus, so normalize.
export function signed(n, lang) {
  if (nullish(n)) return NULL_DISPLAY;
  const fmt = lang === "fi" ? SIGNED_FI : SIGNED_EN;
  const raw = fmt.format(n);
  return raw.replace(/^-/u, "−");
}

// rate3: EN strips leading 0 only (0.915 → .915, 1.000 stays).
// FI multiplies by 100 and uses decimal style with 2 fraction digits so there's no trailing
// NBSP+% to strip. Alternative would be percent style with /\s*%$/u (NBSP, not ASCII space).
export function rate3(n, lang) {
  if (nullish(n)) return NULL_DISPLAY;
  if (lang === "fi") {
    return DEC2_FI.format(n * 100);
  }
  const s = n.toFixed(3);
  return s.startsWith("0.") ? s.slice(1) : s;
}

// pct1: both langs multiply the fraction by 100 and format as decimal (1 fraction digit).
// No % sign in the cell; the column header carries it (ADR-038).
export function pct1(n, lang) {
  if (nullish(n)) return NULL_DISPLAY;
  const fmt = lang === "fi" ? PCT1_FI : PCT1_EN;
  return fmt.format(n * 100);
}

// pct1Sign: EN "14.3%" (no space), FI "14,3 %" (NBSP U+00A0 between number and %).
// Intl.NumberFormat percent style gives both naturally.
export function pct1Sign(n, lang) {
  if (nullish(n)) return NULL_DISPLAY;
  const fmt = lang === "fi" ? PCT1SIGN_FI : PCT1SIGN_EN;
  return fmt.format(n);
}

export function dec2(n, lang) {
  if (nullish(n)) return NULL_DISPLAY;
  const fmt = lang === "fi" ? DEC2_FI : DEC2_EN;
  return fmt.format(n);
}

// toi: integer seconds → MM:SS (EN) or MM.SS (FI). Minutes aren't padded; seconds are.
export function toi(seconds, lang) {
  if (nullish(seconds)) return NULL_DISPLAY;
  const total = Math.floor(seconds);
  const mm = Math.floor(total / 60);
  const ss = total % 60;
  const sep = lang === "fi" ? "." : ":";
  return `${mm}${sep}${String(ss).padStart(2, "0")}`;
}

// date: parse YYYY-MM-DD as UTC noon so no viewer timezone can shift the day.
export function date(iso, lang) {
  if (nullish(iso) || typeof iso !== "string") return NULL_DISPLAY;
  const d = new Date(`${iso}T12:00:00Z`);
  if (Number.isNaN(d.getTime())) return NULL_DISPLAY;
  return (lang === "fi" ? DATE_FI : DATE_EN).format(d);
}

// gameTime: ISO UTC → viewer-local time with the short zone name. The whole point is that
// a late Eastern-time game rolls over the day for a Finnish viewer.
export function gameTime(iso, lang) {
  if (nullish(iso) || typeof iso !== "string") return NULL_DISPLAY;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return NULL_DISPLAY;
  const locale = lang === "fi" ? "fi-FI" : "en-US";
  const fmt = new Intl.DateTimeFormat(locale, {
    weekday: "short",
    day: "numeric",
    month: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: lang !== "fi",
    timeZoneName: "short",
  });
  return fmt.format(d);
}

export function position(code, lang) {
  if (nullish(code)) return NULL_DISPLAY;
  const key = `posCode.${code}`;
  const dict = STRINGS[lang] ?? STRINGS.en;
  return dict[key] ?? STRINGS.en[key] ?? code;
}
