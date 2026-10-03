# Kiekkokeskus

Two static NHL stat pages on [jurigregg.com](https://jurigregg.com):
[`/bolts`](https://jurigregg.com/bolts) follows the Tampa Bay Lightning, and
[`/leijonat`](https://jurigregg.com/leijonat) follows every Finnish player in the NHL.

## How it works

A Lambda runs once a day at 10:00 ET, fetches the NHL's public (undocumented) API, archives the
raw responses, and writes JSON into the site's S3 bucket. The pages read only that JSON — the
browser never talks to the NHL. See [`docs/PLANNING.md`](docs/PLANNING.md) for the full picture
and [`docs/DECISIONS.md`](docs/DECISIONS.md) for the architectural choices.

## Local development

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
ruff check . && ruff format --check . && pytest --cov=kiekkokeskus
```

## Repo map

- [`docs/`](docs/) — planning, decisions (ADRs), task tracker, testing standards
- [`initials/`](initials/) — feature specs (`init-nn-{slug}.md`)
- [`prps/`](prps/) — implementation plans (`prp-nn-{slug}.md`)
- [`src/kiekkokeskus/`](src/kiekkokeskus/) — the daily collector (Python 3.13, Lambda arm64)
- [`tests/`](tests/) — pytest; `tests/fixtures/` holds real archived NHL payloads

## Disclaimer

> Kiekkokeskus is a personal, non-commercial project. It is not affiliated with, endorsed
> by, or sponsored by the National Hockey League, the Tampa Bay Lightning, or any NHL team.
> Team and league names are trademarks of their respective owners. Data comes from publicly
> accessible NHL endpoints.
