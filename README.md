# HomeRule

**Your rights as a renter, for your exact address.**

> **Not legal advice.** HomeRule shows which published housing rules may apply to an address, with quotes and dates. It does not tell anyone what to do and is not a compliance certification.

**A model has a training cutoff. A law has an effective date.**

HomeRule compiles state, county and city housing law into checkable, dated rules. Every address gets a quoted answer (applies, superseded, not yet effective, pending) or one honest question when a fact is missing. The same engine serves renters on the web and AI assistants through MCP.

Built at Hack-Nation 7 (Zurich hub, 03.–04.10.2026) for the RealPage challenge "Rental Housing Law Navigator" by Silvan Geser and Dimitar Dimitrov.

## Try it

- **Live:** [yourhomerule.com](https://yourhomerule.com). Pick a sample address or type one in California, New Jersey or Massachusetts.
- **In a chatbot:** add `https://yourhomerule.com/api/mcp` as a custom connector in Claude (or any MCP client). Instructions: [yourhomerule.com/connect](https://yourhomerule.com/connect).
- **Coverage:** 3 states (CA, NJ, MA) and 10 cities (Boston, Cambridge, San Francisco, Los Angeles, San Diego, Berkeley, Santa Ana, Newark, Jersey City, Hoboken); six topics: rent increases, eviction protection, rent-setting software, deposits, application fees, screening.

## Submission files

| File | What |
|---|---|
| [`outputs/rules.json`](outputs/rules.json) | Extracted rules: requirement, coverage, exemptions, dates, status, citation, verbatim quote |
| [`outputs/lookups.json`](outputs/lookups.json) | All 500 sample addresses: applies / unknown / superseded / not yet effective / pending, per rule |
| [`outputs/changes.json`](outputs/changes.json) | Change tests T1–T5: affected addresses, before and after (T6, the hour-16 ordinance, is in [docs/HOUR16.md](docs/HOUR16.md)) |

## How it works

1. **Extract (model, once per document):** each law becomes a dated rule with its exact quote. Quotes are checked verbatim against the source.
2. **Resolve (code):** each address gets its jurisdiction stack (state, county, city) and public building facts (year built, units, use).
3. **Apply (code, no model calls):** per address and date, each rule applies, is not yet effective, pending, superseded by a local rule, or unknown. Unknown names the missing fact and who can confirm it. Conflicts between state and city law are flagged, not decided.
4. **Track changes:** a new or changed law re-evaluates every address and records before and after.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · method and evaluation: [docs/METHOD.md](docs/METHOD.md) · decisions: [docs/decisions/](docs/decisions/README.md) · product requirements: [docs/PRD.md](docs/PRD.md).

## Evaluation

From [docs/METHOD.md](docs/METHOD.md) (`make check`): brief-named rules 26/27 (the miss, Santa Ana, has no text in the corpus and is recorded as a finding); change tests T1–T5 pass; a new-ordinance rehearsal on fictional text 45/45 addresses; address questions 23/24 on the tuning set and 16/16 on a held-out set never used for tuning; scored quotes 100% verbatim. Limits are listed in the same file.

## Run it

```bash
make build      # engine -> outputs/*.json from the committed rules and resolved addresses
make eval       # uses the included starter pack for independent quote verification
make test       # engine unit tests

cd web && npm ci && npm run dev   # the website and MCP route on localhost:3000
```

The RealPage starter pack is included at `data/realpage-starter/`; its own notices and terms apply separately from the repository code license. `make build` recomputes results from the committed intermediates and the pack metadata. It can also run without the pack using `out/build_inputs.json` (document IDs and change scenarios, no expected answers). Refresh that fallback with `python3 -m engine.build_inputs` when the pack changes. Full extraction and evaluation use the included pack; extraction also needs model credentials.

## Repository layout

| Path | What |
|---|---|
| `extract/` | Rule extraction from the law corpus (Python) |
| `engine/` | Rule engine: coverage, dates, statuses, precedence (Python) |
| `out/` | Intermediates: compiled rules, findings, resolved addresses |
| `outputs/` | The three submission files |
| `web/` | Renter website and MCP server (Next.js on Vercel) |
| `tests/`, `scoreboard/` | Engine tests, journeys, chatbot comparison |
| `monitor/` | Official-source change monitor |
| `docs/` | Architecture, method, requirements, decision records |

## Responsible design

- Every answer quotes the law and shows its date and the date it was checked.
- Pending bills are shown as proposed, never as law.
- When a fact is missing, the answer says unknown and names who can confirm it, instead of guessing.
- No verdicts: no "legal", "illegal" or "compliant", and no comparison of a renter's own numbers against a cap.

## License

Copyright (c) 2026 Silvan Geser and Dimitar Dimitrov. All rights reserved. The code is public to read and evaluate, not to reuse: see [LICENSE](LICENSE).
