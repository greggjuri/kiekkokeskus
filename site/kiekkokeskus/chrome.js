// Header, pills, banners, footer. Thin DOM glue; exercised by the harness + manual checklist.

import { t } from "./i18n.js";
import { isStale } from "./data.js";
import { date } from "./format.js";

export function renderHeader({ root, titleKey, subtitleKey, lang, onLangChange }) {
  const doc = root.ownerDocument;
  root.innerHTML = "";
  root.classList.add("kk-header");

  const crumb = doc.createElement("div");
  crumb.className = "kk-crumb";
  crumb.textContent = t("nav.crumb", null, lang);
  root.appendChild(crumb);

  const h1 = doc.createElement("h1");
  h1.className = "kk-title";
  if (titleKey) h1.textContent = t(titleKey, null, lang);
  root.appendChild(h1);

  if (subtitleKey) {
    const sub = doc.createElement("p");
    sub.className = "kk-subtitle";
    sub.textContent = t(subtitleKey, null, lang);
    root.appendChild(sub);
  }

  // Language toggle
  const toggle = doc.createElement("div");
  toggle.className = "kk-lang";
  toggle.setAttribute("role", "group");
  toggle.setAttribute("aria-label", t("lang.group", null, lang));
  for (const code of ["en", "fi"]) {
    const btn = doc.createElement("button");
    btn.type = "button";
    btn.dataset.lang = code;
    btn.textContent = code.toUpperCase();
    btn.setAttribute("aria-pressed", lang === code ? "true" : "false");
    btn.addEventListener("click", () => onLangChange?.(code));
    toggle.appendChild(btn);
  }
  root.appendChild(toggle);
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
