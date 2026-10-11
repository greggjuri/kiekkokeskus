import { test } from "node:test";
import assert from "node:assert/strict";

import { STRINGS, SUPPORTED_LANGS } from "./strings.js";

test("every EN key exists in FI and vice versa", () => {
  const en = new Set(Object.keys(STRINGS.en));
  const fi = new Set(Object.keys(STRINGS.fi));

  const missingInFi = [...en].filter((k) => !fi.has(k));
  const missingInEn = [...fi].filter((k) => !en.has(k));

  assert.deepEqual(missingInFi, [], `keys missing in fi: ${missingInFi.join(", ")}`);
  assert.deepEqual(missingInEn, [], `keys missing in en: ${missingInEn.join(", ")}`);
});

test("every string is non-empty", () => {
  for (const lang of SUPPORTED_LANGS) {
    for (const [key, value] of Object.entries(STRINGS[lang])) {
      assert.ok(typeof value === "string", `${lang}.${key} not a string`);
      assert.ok(value.length > 0, `${lang}.${key} empty`);
    }
  }
});

test("FI position codes match ADR-038 Liiga glossary", () => {
  assert.equal(STRINGS.fi["posCode.C"], "KH");
  assert.equal(STRINGS.fi["posCode.L"], "VL");
  assert.equal(STRINGS.fi["posCode.R"], "OL");
  assert.equal(STRINGS.fi["posCode.D"], "P");
  assert.equal(STRINGS.fi["posCode.G"], "MV");
});

test("EN disclaimer matches README.md verbatim (ADR-002)", () => {
  const expected =
    "Kiekkokeskus is a personal, non-commercial project. It is not affiliated with, endorsed by, or sponsored by the National Hockey League, the Tampa Bay Lightning, or any NHL team. Team and league names are trademarks of their respective owners. Data comes from publicly accessible NHL endpoints.";
  assert.equal(STRINGS.en["footer.disclaimer"], expected);
});

// --- init-07 pins ---

test("FI division names pinned (liiga.fi + Finnish NHL coverage)", () => {
  assert.equal(STRINGS.fi["div.A"], "Atlantin divisioona");
  assert.equal(STRINGS.fi["div.M"], "Metropolitanin divisioona");
  assert.equal(STRINGS.fi["div.C"], "Keskinen divisioona");
  assert.equal(STRINGS.fi["div.P"], "Tyynenmeren divisioona");
});

test("FI conference names pinned", () => {
  assert.equal(STRINGS.fi["conf.E"], "Itä");
  assert.equal(STRINGS.fi["conf.W"], "Länsi");
});

test("FI streak suffixes pinned (Liiga glossary)", () => {
  assert.equal(STRINGS.fi["streak.W"], "V{n}");
  assert.equal(STRINGS.fi["streak.L"], "H{n}");
  assert.equal(STRINGS.fi["streak.OT"], "JH{n}");
});

test("FI decided suffixes pinned (Liiga glossary)", () => {
  assert.equal(STRINGS.fi["decided.OT"], "JA");
  assert.equal(STRINGS.fi["decided.SO"], "VL");
});

test("page.bolts.subtitle contains the {season} placeholder in both langs", () => {
  assert.ok(STRINGS.en["page.bolts.subtitle"].includes("{season}"));
  assert.ok(STRINGS.fi["page.bolts.subtitle"].includes("{season}"));
});

test("page.bolts.subtitleNoSeason contains NO placeholder (shown during load / on error)", () => {
  for (const lang of SUPPORTED_LANGS) {
    const s = STRINGS[lang]["page.bolts.subtitleNoSeason"];
    assert.ok(!s.includes("{"), `${lang} subtitleNoSeason leaks a placeholder: ${s}`);
    assert.ok(!s.includes("}"), `${lang} subtitleNoSeason leaks a placeholder: ${s}`);
  }
});
