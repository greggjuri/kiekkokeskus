// Header, pills, banners, footer. Thin DOM glue; exercised by the harness + manual checklist.

import { t } from "./i18n.js";
import { isStale } from "./data.js";
import { date } from "./format.js";

// renderHeader options:
//   titleKey:     string | null — looked up via t(titleKey, null, lang) when subtitle isn't given
//   subtitle:     string | null — pre-resolved subtitle string from the caller (preferred;
//                 mountPage calls subtitle(data, lang) and passes the result here)
//   subtitleKey:  string | null — legacy convenience: falls back to t(subtitleKey, null, lang)
//                 when subtitle is undefined. Never used by pages; the harness still uses it
//                 for its own labels.
//   hero:         { src, width, height, alt='' } | null — optional decorative image (ADR-040).
//                 Rendered after the title block. decoding="async", NOT lazy-loaded (above fold).
// renderHeader builds the header DOM once (on first call for a given `root`) and patches it
// in place on every subsequent call. This keeps the hero <img> alive across language toggles,
// pill clicks and sort clicks — otherwise every re-render would rebuild the img, re-decode
// it, and visibly flash the whole header.
export function renderHeader({
  root,
  titleKey,
  subtitle,
  subtitleKey,
  lang,
  onLangChange,
  hero,
}) {
  const doc = root.ownerDocument;

  // Build once.
  if (!root.dataset.kkHeaderBuilt) {
    root.innerHTML = "";
    root.classList.add("kk-header");

    const crumb = doc.createElement("div");
    crumb.className = "kk-crumb";
    root.appendChild(crumb);

    const h1 = doc.createElement("h1");
    h1.className = "kk-title";
    root.appendChild(h1);

    const sub = doc.createElement("p");
    sub.className = "kk-subtitle";
    root.appendChild(sub);

    if (hero && hero.src) {
      // ADR-040: decorative, pre-flattened on --kk-bg; alt="" so AT skips it; width+height
      // set to prevent layout shift; decoding async; above the fold, so NOT lazy.
      const img = doc.createElement("img");
      img.className = "kk-hero";
      img.src = hero.src;
      img.alt = hero.alt ?? "";
      if (hero.width) img.width = hero.width;
      if (hero.height) img.height = hero.height;
      img.decoding = "async";
      root.appendChild(img);
    }

    const toggle = doc.createElement("div");
    toggle.className = "kk-lang";
    toggle.setAttribute("role", "group");
    for (const code of ["en", "fi"]) {
      const btn = doc.createElement("button");
      btn.type = "button";
      btn.dataset.lang = code;
      btn.textContent = code.toUpperCase();
      btn.addEventListener("click", () => onLangChange?.(code));
      toggle.appendChild(btn);
    }
    root.appendChild(toggle);

    root.dataset.kkHeaderBuilt = "1";
  }

  // Patch text + aria-pressed on every call. The hero <img> is never touched.
  root.querySelector(".kk-crumb").textContent = t("nav.crumb", null, lang);

  const h1 = root.querySelector(".kk-title");
  h1.textContent = titleKey ? t(titleKey, null, lang) : "";

  const sub = root.querySelector(".kk-subtitle");
  const subtitleText =
    typeof subtitle === "string" ? subtitle : subtitleKey ? t(subtitleKey, null, lang) : null;
  if (subtitleText) {
    sub.textContent = subtitleText;
    sub.hidden = false;
  } else {
    sub.textContent = "";
    sub.hidden = true;
  }

  const toggle = root.querySelector(".kk-lang");
  toggle.setAttribute("aria-label", t("lang.group", null, lang));
  for (const btn of toggle.querySelectorAll("button")) {
    btn.setAttribute("aria-pressed", btn.dataset.lang === lang ? "true" : "false");
  }
}

export function renderPills({ root, state, onChange, lang }) {
  const doc = root.ownerDocument;
  root.innerHTML = "";
  root.classList.add("kk-pills");
  root.setAttribute("role", "group");
  root.setAttribute("aria-label", t("pos.group", null, lang));

  for (const value of ["all", "f", "d"]) {
    const btn = doc.createElement("button");
    btn.type = "button";
    btn.className = "kk-pill";
    btn.dataset.pos = value;
    btn.textContent = t(`pos.${value}`, null, lang);
    btn.setAttribute("aria-pressed", state.pos === value ? "true" : "false");
    btn.addEventListener("click", () => onChange?.(value));
    root.appendChild(btn);
  }
}

export function renderStaleBanner({ root, generatedAt, lang, now }) {
  if (!isStale(generatedAt, now)) {
    root.innerHTML = "";
    root.hidden = true;
    return;
  }
  const d = new Date(generatedAt);
  const dateStr = date(d.toISOString().slice(0, 10), lang);
  const timeFmt = new Intl.DateTimeFormat(lang === "fi" ? "fi-FI" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: lang !== "fi",
    timeZone: "UTC",
  });
  const timeStr = timeFmt.format(d) + " UTC";
  root.hidden = false;
  root.className = "kk-banner kk-banner-stale";
  root.setAttribute("role", "status");
  root.textContent = t("banner.stale", { date: dateStr, time: timeStr }, lang);
}

export function renderErrorBanner({ root, lang }) {
  root.hidden = false;
  root.className = "kk-banner kk-banner-error";
  root.setAttribute("role", "alert");
  root.textContent = t("banner.error", null, lang);
}

export function hideBanner(root) {
  root.innerHTML = "";
  root.hidden = true;
}

export function renderFooter({ root, dataDate, lang }) {
  const doc = root.ownerDocument;
  root.innerHTML = "";
  root.classList.add("kk-footer");

  const through = doc.createElement("p");
  through.className = "kk-through";
  through.textContent = t(
    "footer.through",
    { date: dataDate ? date(dataDate, lang) : "–" },
    lang,
  );
  root.appendChild(through);

  const disc = doc.createElement("p");
  disc.className = "kk-disclaimer";
  disc.textContent = t("footer.disclaimer", null, lang);
  root.appendChild(disc);
}
