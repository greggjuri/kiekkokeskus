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
| standings__2026-10-08__2026-10-09.json.gz | https://api-web.nhle.com/v1/standings/2026-10-08 | 2026-10-10T02:47:13Z | 200 | - | ADR-009,ADR-036 |
| club-stats-TBL__20262027__2__2026-10-09.json.gz | https://api-web.nhle.com/v1/club-stats/TBL/20262027/2 | 2026-10-10T02:47:14Z | 200 | - | ADR-015,ADR-017,ADR-018,ADR-035 |
| club-schedule-season-TBL__20262027__2026-10-09.json.gz | https://api-web.nhle.com/v1/club-schedule-season/TBL/20262027 | 2026-10-10T02:47:15Z | 200 | - | ADR-014 |
| skater-summary-TBL__20262027__2026-10-09.json.gz | https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=gameTypeId%3D2%20and%20teamAbbrevs%3D%22TBL%22%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-10T02:47:15Z | 200 | - | ADR-035 |
| skater-realtime-TBL__20262027__2026-10-09.json.gz | https://api.nhle.com/stats/rest/en/skater/realtime?cayenneExp=gameTypeId%3D2%20and%20teamAbbrevs%3D%22TBL%22%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-10T02:47:16Z | 200 | - | ADR-035 |
| skater-faceoff-TBL__20262027__2026-10-09.json.gz | https://api.nhle.com/stats/rest/en/skater/faceoffpercentages?cayenneExp=gameTypeId%3D2%20and%20teamAbbrevs%3D%22TBL%22%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-10T02:47:16Z | 200 | - | ADR-035 |
| team-summary__20262027__2026-10-09.json.gz | https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=gameTypeId%3D2%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-10T02:47:17Z | 200 | - | ADR-036 |
| club-stats-TBL__20262027__2__2026-10-09__goalie-no-shots.json.gz | (variant, hand-mutated) | 2026-10-10T02:47:36Z | 200 | club-stats-TBL__20262027__2__2026-10-09.json.gz | ADR-015 |
| skater-realtime-TBL__20262027__2026-10-09__player-missing.json.gz | (variant, hand-mutated) | 2026-10-10T02:47:36Z | 200 | skater-realtime-TBL__20262027__2026-10-09.json.gz | ADR-035 |
| skater-summary-FIN__20262027__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=gameTypeId%3D2%20and%20nationalityCode%3D%22FIN%22%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-11T02:39:26Z | 200 | - | ADR-037 |
| skater-realtime-FIN__20262027__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/skater/realtime?cayenneExp=gameTypeId%3D2%20and%20nationalityCode%3D%22FIN%22%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-11T02:39:27Z | 200 | - | ADR-037 |
| skater-faceoff-FIN__20262027__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/skater/faceoffpercentages?cayenneExp=gameTypeId%3D2%20and%20nationalityCode%3D%22FIN%22%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-11T02:39:28Z | 200 | - | ADR-037 |
| goalie-summary-FIN__20262027__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/goalie/summary?cayenneExp=gameTypeId%3D2%20and%20nationalityCode%3D%22FIN%22%20and%20seasonId%3D20262027&limit=1000&start=0 | 2026-10-11T02:39:30Z | 200 | - | ADR-037 |
| skater-rookies-FIN__20262027__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=gameTypeId%3D2%20and%20nationalityCode%3D%22FIN%22%20and%20seasonId%3D20262027%20and%20isRookie%3D1&limit=1000&start=0 | 2026-10-11T02:39:30Z | 200 | - | ADR-037 |
| goalie-rookies-FIN__20262027__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/goalie/summary?cayenneExp=gameTypeId%3D2%20and%20nationalityCode%3D%22FIN%22%20and%20seasonId%3D20262027%20and%20isRookie%3D1&limit=1000&start=0 | 2026-10-11T02:39:31Z | 200 | - | ADR-037 |
| skater-bios-FIN__20262027__p0__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/skater/bios?cayenneExp=seasonId%3D20262027%20and%20nationalityCode%3D%22FIN%22&limit=1000&start=0 | 2026-10-11T02:39:32Z | 200 | - | ADR-011,ADR-037 |
| goalie-bios-FIN__20262027__p0__2026-10-10.json.gz | https://api.nhle.com/stats/rest/en/goalie/bios?cayenneExp=seasonId%3D20262027%20and%20nationalityCode%3D%22FIN%22&limit=1000&start=0 | 2026-10-11T02:39:33Z | 200 | - | ADR-011,ADR-037 |
| schedule__2026-10-09__2026-10-10.json.gz | https://api-web.nhle.com/v1/schedule/2026-10-09 | 2026-10-11T02:39:34Z | 200 | - | ADR-033,ADR-014 |
| standings__2026-10-09__2026-10-10.json.gz | https://api-web.nhle.com/v1/standings/2026-10-09 | 2026-10-11T02:39:35Z | 200 | - | ADR-009,ADR-036 |
| boxscore__2026020025__2026-10-10.json.gz | https://api-web.nhle.com/v1/gamecenter/2026020025/boxscore | 2026-10-11T02:39:35Z | 200 | - | ADR-037 |
| boxscore__2026020065__2026-10-10.json.gz | https://api-web.nhle.com/v1/gamecenter/2026020065/boxscore | 2026-10-11T02:39:36Z | 200 | - | ADR-037 |
| boxscore__2026020066__2026-10-10.json.gz | https://api-web.nhle.com/v1/gamecenter/2026020066/boxscore | 2026-10-11T02:40:09Z | 200 | - | ADR-012,ADR-037 |
| boxscore__2026020067__2026-10-10.json.gz | https://api-web.nhle.com/v1/gamecenter/2026020067/boxscore | 2026-10-11T02:40:10Z | 200 | - | ADR-012,ADR-037 |
| boxscore__2026020068__2026-10-10.json.gz | https://api-web.nhle.com/v1/gamecenter/2026020068/boxscore | 2026-10-11T02:40:10Z | 200 | - | ADR-012,ADR-037 |
| boxscore__2026020069__2026-10-10.json.gz | https://api-web.nhle.com/v1/gamecenter/2026020069/boxscore | 2026-10-11T02:40:11Z | 200 | - | ADR-012,ADR-037 |
| club-stats-ANA__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/ANA/20262027/2 | 2026-10-11T02:43:31Z | 200 | - | ADR-037 |
| club-stats-BUF__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/BUF/20262027/2 | 2026-10-11T02:43:32Z | 200 | - | ADR-037 |
| club-stats-CAR__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/CAR/20262027/2 | 2026-10-11T02:43:32Z | 200 | - | ADR-037 |
| club-stats-CHI__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/CHI/20262027/2 | 2026-10-11T02:43:33Z | 200 | - | ADR-037 |
| club-stats-COL__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/COL/20262027/2 | 2026-10-11T02:43:33Z | 200 | - | ADR-037 |
| club-stats-DAL__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/DAL/20262027/2 | 2026-10-11T02:43:35Z | 200 | - | ADR-037 |
| club-stats-EDM__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/EDM/20262027/2 | 2026-10-11T02:43:35Z | 200 | - | ADR-037 |
| club-stats-FLA__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/FLA/20262027/2 | 2026-10-11T02:43:36Z | 200 | - | ADR-037 |
| club-stats-LAK__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/LAK/20262027/2 | 2026-10-11T02:43:37Z | 200 | - | ADR-037 |
| club-stats-MIN__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/MIN/20262027/2 | 2026-10-11T02:43:37Z | 200 | - | ADR-037 |
| club-stats-NSH__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/NSH/20262027/2 | 2026-10-11T02:43:38Z | 200 | - | ADR-037 |
| club-stats-NYI__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/NYI/20262027/2 | 2026-10-11T02:43:39Z | 200 | - | ADR-037 |
| club-stats-NYR__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/NYR/20262027/2 | 2026-10-11T02:43:40Z | 200 | - | ADR-037 |
| club-stats-OTT__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/OTT/20262027/2 | 2026-10-11T02:43:40Z | 200 | - | ADR-037 |
| club-stats-PHI__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/PHI/20262027/2 | 2026-10-11T02:43:41Z | 200 | - | ADR-037 |
| club-stats-PIT__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/PIT/20262027/2 | 2026-10-11T02:43:41Z | 200 | - | ADR-037 |
| club-stats-SEA__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/SEA/20262027/2 | 2026-10-11T02:43:42Z | 200 | - | ADR-037 |
| club-stats-VAN__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/VAN/20262027/2 | 2026-10-11T02:43:42Z | 200 | - | ADR-037 |
| club-stats-WPG__20262027__2__2026-10-10.json.gz | https://api-web.nhle.com/v1/club-stats/WPG/20262027/2 | 2026-10-11T02:43:43Z | 200 | - | ADR-037 |
