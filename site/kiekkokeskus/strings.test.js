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
