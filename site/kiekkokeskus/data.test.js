import { test } from "node:test";
import assert from "node:assert/strict";

import { loadData, isStale } from "./data.js";

function fakeResponse({ ok = true, status = 200, body = {}, bodyThrows = false } = {}) {
  return {
    ok,
    status,
    json: async () => {
      if (bodyThrows) throw new SyntaxError("Unexpected token");
      return body;
    },
  };
}

// --- loadData ---

test("loadData ok: returns { ok: true, data } on 200 + schema match", async () => {
  const result = await loadData("/data/kiekkokeskus/bolts.json", 1, {
    fetchFn: async () => fakeResponse({ body: { schemaVersion: 1, foo: "bar" } }),
  });
  assert.equal(result.ok, true);
  assert.equal(result.data.foo, "bar");
});

test("loadData schema mismatch: returns { ok: false, reason: 'schema' } without throwing", async () => {
  const result = await loadData("/x", 1, {
    fetchFn: async () => fakeResponse({ body: { schemaVersion: 2 } }),
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "schema");
  assert.deepEqual(result.detail, { expected: 1, got: 2 });
});

test("loadData fetch throws: returns { ok: false, reason: 'fetch' }", async () => {
  const result = await loadData("/x", 1, {
    fetchFn: async () => {
      throw new TypeError("Failed to fetch");
    },
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "fetch");
});

test("loadData non-2xx: returns { ok: false, reason: 'http' }", async () => {
  const result = await loadData("/x", 1, {
    fetchFn: async () => fakeResponse({ ok: false, status: 404 }),
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "http");
  assert.equal(result.detail, 404);
});

test("loadData invalid JSON: returns { ok: false, reason: 'json' }", async () => {
  const result = await loadData("/x", 1, {
    fetchFn: async () => fakeResponse({ bodyThrows: true }),
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, "json");
});

// --- isStale ---

test("isStale: false at 35h59m, true at 36h01m (boundary)", () => {
  const gen = new Date("2026-10-10T00:00:00Z");
  const under = new Date(gen.getTime() + (35 * 60 + 59) * 60_000);
  const over = new Date(gen.getTime() + (36 * 60 + 1) * 60_000);
  assert.equal(isStale(gen.toISOString(), under), false);
  assert.equal(isStale(gen.toISOString(), over), true);
});

test("isStale: false when exactly 36:00:00 old (strict >, not ≥)", () => {
  const gen = new Date("2026-10-10T00:00:00Z");
  const exact = new Date(gen.getTime() + 36 * 3_600_000);
  assert.equal(isStale(gen.toISOString(), exact), false);
});

test("isStale: false when generatedAt is missing or invalid", () => {
  assert.equal(isStale(null, new Date()), false);
  assert.equal(isStale("not-a-date", new Date()), false);
  assert.equal(isStale(undefined, new Date()), false);
});
