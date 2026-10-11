// Same-origin JSON loader + stale check. ADR-003: the browser never calls the NHL.

const STALE_HOURS = 36;

export async function loadData(path, expectedSchemaVersion, { fetchFn } = {}) {
  const fetchImpl = fetchFn ?? ((p) => fetch(p));

  let response;
  try {
    response = await fetchImpl(path);
  } catch (err) {
    console.error("loadData: fetch failed", err);
    return { ok: false, reason: "fetch", detail: String(err) };
  }

  if (!response || !response.ok) {
    const status = response?.status ?? "unknown";
    console.error("loadData: non-2xx", status);
    return { ok: false, reason: "http", detail: status };
  }

  let data;
  try {
    data = await response.json();
  } catch (err) {
    console.error("loadData: invalid JSON", err);
    return { ok: false, reason: "json", detail: String(err) };
  }

  if (data?.schemaVersion !== expectedSchemaVersion) {
    const got = data?.schemaVersion;
    console.error("loadData: schemaVersion mismatch", got, "expected", expectedSchemaVersion);
    return { ok: false, reason: "schema", detail: { expected: expectedSchemaVersion, got } };
  }

  return { ok: true, data };
}

// Pure. Takes `now` as a Date so the harness can inject ?now= and tests pin boundaries.
export function isStale(generatedAtIso, now) {
  if (!generatedAtIso || !now) return false;
  const gen = new Date(generatedAtIso);
  if (Number.isNaN(gen.getTime())) return false;
  const ageMs = now.getTime() - gen.getTime();
  return ageMs / 3_600_000 > STALE_HOURS;
}
