import { test } from "node:test";
import assert from "node:assert/strict";

import {
  resolveLang,
  t,
  renderName,
  nameSortKey,
} from "./i18n.js";

const makeUrl = (search) => new URL(`https://x.test/${search}`);

test("resolveLang: ?lang=fi wins", () => {
  const r = resolveLang({
    url: makeUrl("?lang=fi"),
    storage: { getItem: () => "en" },
    nav: { language: "en-US" },
  });
  assert.deepEqual(r, { lang: "fi", source: "url" });
});

test("resolveLang: unknown ?lang falls through to storage", () => {
  const r = resolveLang({
    url: makeUrl("?lang=xx"),
    storage: { getItem: () => "fi" },
    nav: { language: "en-US" },
  });
  assert.deepEqual(r, { lang: "fi", source: "storage" });
});

test("resolveLang: storage wins over navigator", () => {
  const r = resolveLang({
    url: makeUrl(""),
    storage: { getItem: () => "en" },
    nav: { language: "fi-FI" },
  });
  assert.deepEqual(r, { lang: "en", source: "storage" });
});

test("resolveLang: navigator fi-FI → fi", () => {
  const r = resolveLang({
    url: makeUrl(""),
    storage: { getItem: () => null },
    nav: { language: "fi-FI" },
  });
  assert.deepEqual(r, { lang: "fi", source: "nav" });
});

test("resolveLang: default EN when nothing matches", () => {
  const r = resolveLang({
    url: makeUrl(""),
    storage: { getItem: () => null },
    nav: { language: "en-US" },
  });
  assert.deepEqual(r, { lang: "en", source: "default" });
});

test("resolveLang: storage throwing falls through silently", () => {
  const throwing = {
    getItem: () => {
      throw new Error("quota");
    },
  };
  const r = resolveLang({
    url: makeUrl(""),
    storage: throwing,
    nav: { language: "fi-FI" },
  });
  assert.deepEqual(r, { lang: "fi", source: "nav" });
});

test("resolveLang: missing url/storage/nav all default EN", () => {
  const r = resolveLang({});
  assert.deepEqual(r, { lang: "en", source: "default" });
});

test("t: direct lookup", () => {
  assert.equal(t("pos.all", null, "en"), "All");
  assert.equal(t("pos.all", null, "fi"), "Kaikki");
});

test("t: variable interpolation", () => {
  assert.equal(
    t("banner.stale", { date: "Oct 2", time: "14:00" }, "en"),
    "Data may be out of date. Last updated Oct 2 at 14:00.",
  );
});

test("t: unknown key returns the key itself (no crash)", () => {
  assert.equal(t("does.not.exist", null, "en"), "does.not.exist");
});

test("renderName EN: default surname + default forename", () => {
  const row = {
    firstName: { default: "Andrei" },
    lastName: { default: "Vasilevskiy", fi: "Vasilevski", cs: "Vasilevskij" },
  };
  assert.equal(renderName(row, "en"), "Andrei Vasilevskiy");
});

test("renderName FI: partial-FI name — Vasilevskiy fixture (lastName.fi only)", () => {
  // ADR-018 gotcha: firstName has no fi key, lastName does. FI must render the FI surname
  // alongside the default forename, not fall back to the EN surname.
  const row = {
    firstName: { default: "Andrei" },
    lastName: { default: "Vasilevskiy", fi: "Vasilevski", cs: "Vasilevskij" },
  };
  assert.equal(renderName(row, "fi"), "Andrei Vasilevski");
});

test("renderName FI: Teräväinen (both fi keys present)", () => {
  const row = {
    firstName: { default: "Teuvo" },
    lastName: {
      default: "Teravainen",
      fi: "Teräväinen",
      cs: "Teräväinen",
      sk: "Teräväinen",
      sv: "Teräväinen",
    },
  };
  assert.equal(renderName(row, "fi"), "Teuvo Teräväinen");
  assert.equal(renderName(row, "en"), "Teuvo Teravainen");
});

test("renderName: extra cs/sk/sv keys ignored, no crash", () => {
  const row = {
    firstName: { default: "Olli", cs: "Olli", sk: "Olli", sv: "Olli" },
    lastName: {
      default: "Maatta",
      fi: "Määttä",
      cs: "Määttä",
      sk: "Määttä",
      sv: "Määttä",
    },
  };
  assert.equal(renderName(row, "fi"), "Olli Määttä");
  assert.equal(renderName(row, "en"), "Olli Maatta");
});

test("renderName: missing parts return empty gracefully", () => {
  assert.equal(renderName({}, "en"), "");
  assert.equal(renderName(null, "en"), "");
});

test("nameSortKey orders by last then first", () => {
  const row = {
    firstName: { default: "Andrei" },
    lastName: { default: "Vasilevskiy", fi: "Vasilevski" },
  };
  assert.equal(nameSortKey(row, "en"), "vasilevskiy andrei");
  assert.equal(nameSortKey(row, "fi"), "vasilevski andrei");
});
