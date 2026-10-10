# Fixtures

Real archived NHL payloads live here. **Never hand-write JSON.** Capture with
`scripts/fetch_fixture.py` (added by init-03). Naming and rules: see
[`../../docs/TESTING.md`](../../docs/TESTING.md) → "Fixtures".

## Provenance

| file | source URL | fetched at (UTC) | HTTP status | variant of | ADR |
|---|---|---|---|---|---|
| schedule__2026-10-01__2026-10-03.json.gz | https://api-web.nhle.com/v1/schedule/2026-10-01 | 2026-10-04T02:02:51Z | 200 | - | ADR-013,ADR-014 |
| schedule__2026-09-26__2026-10-03.json.gz | https://api-web.nhle.com/v1/schedule/2026-09-26 | 2026-10-04T02:02:51Z | 200 | - | ADR-013,ADR-014 |
| schedule__2026-12-15__2026-10-03.json.gz | https://api-web.nhle.com/v1/schedule/2026-12-15 | 2026-10-04T02:02:52Z | 200 | - | ADR-013 |
| standings__2026-04-01__2026-10-03.json.gz | https://api-web.nhle.com/v1/standings/2026-04-01 | 2026-10-04T02:02:53Z | 200 | - | ADR-009,ADR-015 |
| standings__2026-10-01__2026-10-03.json.gz | https://api-web.nhle.com/v1/standings/2026-10-01 | 2026-10-04T02:02:53Z | 200 | - | ADR-009,ADR-015 |
| standings__2026-10-02__2026-10-03.json.gz | https://api-web.nhle.com/v1/standings/2026-10-02 | 2026-10-04T02:02:54Z | 200 | - | ADR-009,ADR-015 |
| boxscore__2026020010__2026-10-03.json.gz | https://api-web.nhle.com/v1/gamecenter/2026020010/boxscore | 2026-10-04T02:02:54Z | 200 | - | ADR-012 |
| skater-bios-FIN__20262027__p0__2026-10-03.json.gz | https://api.nhle.com/stats/rest/en/skater/bios?cayenneExp=seasonId%3D20262027%20and%20nationalityCode%3D%22FIN%22&limit=1000&start=0 | 2026-10-04T02:02:55Z | 200 | - | ADR-010,ADR-011 |
| goalie-bios-FIN__20262027__p0__2026-10-03.json.gz | https://api.nhle.com/stats/rest/en/goalie/bios?cayenneExp=seasonId%3D20262027%20and%20nationalityCode%3D%22FIN%22&limit=1000&start=0 | 2026-10-04T02:02:56Z | 200 | - | ADR-010,ADR-011 |
| schedule__2026-10-01__2026-10-03__unknown-state.json.gz | (variant, hand-mutated) | 2026-10-04T02:03:06Z | 200 | schedule__2026-10-01__2026-10-03.json.gz | ADR-013 |
| scheduler-event__2026-10-04.json | CloudWatch log /aws/lambda/kiekkokeskus-collector (first scheduled run, 10:00 ET 2026-10-04) | 2026-10-04T14:00:36Z | n/a (AWS event) | - | ADR-032,ADR-033 |
