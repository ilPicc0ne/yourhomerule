# HomeRule PRD

**Your rights as a renter, for your exact address.**
Demo headline: *A model has a training cutoff. A law has an effective date.*

The master document for scope, priorities and owners. The brief wins on rules; the how lives in [ARCHITECTURE.md](ARCHITECTURE.md). Updated Sun 04.10.2026 (feature status checked against `main` and the live site ~05:00 CEST). Submission 15:00 CEST, freeze 12:00.

## In one minute

- **What:** enter an address and see which housing rules apply there today and what is about to change: quoted, dated, with "unknown" where the data can't decide.
- **For whom:** renters first. Advocates get the affected-address lists for free. Small landlords get wording only.
- **How it's scored:** 75 points by script on three files (`rules.json`, `lookups.json`, `changes.json`), 25 by judges on the demo.
- **Our bet:** extract the law once into rule records and decide coverage in code, not by a model. Answers are reproducible, quoted, and stay "unknown" when a fact is missing.
- **Scope:** 3 states, 10 cities, 500 sample addresses; the landing page says so plainly. A new city = its law texts + one list entry.
- **Not:** legal advice, a compliance check, a chatbot, rent prices.

## What we must get right (scoring)

| Score | Pts | Owner | Must hold |
|---|---|---|---|
| Extraction | 25 auto | D | Automated from the corpus. Records join the key on jurisdiction + category + citation. Status (in force / not yet effective / pending / failed) and dates right. Never invent a rule |
| Address coverage | 20 auto | S | All 500 addresses. Legal city, not postal city. **Unknown instead of omitting** (a miss costs 2×). Superseded only when a stricter local rule governs |
| Citations | 15 auto | D | Every "applies" has a verbatim quote from the corpus |
| Change tracking | 15 auto | S (T6 ingest D) | T1–T5 from the pack, T6 = hour-16 ordinance, all through one engine |
| Plain language | 10 judges | S | The address page (below) |
| Responsible design | 10 judges | both | "Not legal advice" everywhere, as-of date on every answer, conflicts flagged not decided, audit log |
| Scalability | 5 judges | S | New city = documents + one list entry; hour 16 is the live proof |

Bonus the guide offers: show its four open legal questions (e.g. Berkeley's ban has two published effective dates) as flags with both sources.

## The product: one address page

**The six questions**, one tile each (= the six scored categories):

| Tile | Category |
|---|---|
| How much can my rent go up? | Rent increase limits |
| When can they end my tenancy? (reasons · notice · relocation money) | Just-cause eviction |
| How much deposit can they ask? | Security deposits; conditional limits and unresolved exception conditions (#136) |
| What can they charge me to apply? | Application and screening fees |
| What can they check about me? | Screening restrictions |
| Can rent-setting software be used on my rent? | Algorithmic rent-setting |

**Each tile is an accordion** (one open at a time):

| Level | Shows |
|---|---|
| Closed | Big title with icon · one plain answer · status mark + word + colour |
| Open | Plain explanation · **next step**: first a human contact (office, phone, "free") from `contracts/contacts.json`, then action helpers (J7) |
| "Show the law" (second toggle) | Verbatim quote · citation · dates · confidence · rules it replaces · link to the rule page |

**Status labels** (one meaning per colour; colours rate the renter's protection, never the building or landlord):
- **There's a rule** · green
- **We're missing one fact** · amber; names the fact and who can tell you
- **No local rule — state basics only** · grey, neutral mark
- Blue only for actions and dates.

**Words** (judged as Plain language; the legal-advice line):
- Reading level grade 6–8. Tenant facts (length of tenancy, etc.) are notes, never inputs.
- Never phrase a cap so it invites comparing the renter's own number: "The Rent Board can check your notice", not "max 3.4%: is yours higher?".
- State facts, let the reader conclude: "Public records list 21 units. The exception is for 4 units or fewer." Never apply the law to the case.
- Coverage is about the building: always "your unit may differ".
- Plain words instead of jargon: good cause → a reason the law accepts · struck → removed (say by whom) · in force → applies now · certificate of occupancy → the date the city first approved the building for living in · notice to quit → a letter telling you to move out · source of income → how you pay rent (e.g. a voucher) · algorithmic software → rent-setting software.

**Ask at any level: one search box, one hierarchy.** The search accepts an address, a city, a neighbourhood ("Dorchester"), a county or a state, and resolves it through the jurisdiction list (with aliases), so nobody has to know the exact name or ID.
- **Address** → the address page (below).
- **Jurisdiction page** for every level (`/j/<id>`): State › County › City as breadcrumbs, each level browsable. It shows the six questions with the rules for that level and everything above it, and *what they depend on* instead of a building result ("applies to buildings with a certificate of occupancy on or before 13.06.1979"). A state page lists its cities; a county page says it has no rules of its own and lists its cities.
- **Outside the scope** ("New York", "Austin") → "Not covered: HomeRule has law for 3 states and 10 cities", never a guess.

**Click any answer → the rule page** (one page per rule, shared by all addresses):
- **Source:** the verbatim quote highlighted in the source text, citation, **link to the official law** (`source_url`), retrieval date, effective date, status.
- **Audit trail:** what the model extracted (and its confidence), what the code decided (jurisdiction match, coverage test on this building's facts, precedence), with the line between the two shown ("reasoning boundary").
- **Impact map:** every sample address this rule touches, coloured by result (applies / unknown / not yet effective / pending), with the date slider. Moving the date flips the dots (e.g. FAIR Act on 02.07.2027). Built: the map and list for one as-of date; the slider is not built.
- This page is also the advocates' view: "which buildings does this law or bill reach?"

**Page, top to bottom (one view):**

1. **Sticky address bar:** address search (address, city, neighbourhood) + compact **"Get alerts" bell** that opens the email field in place; disabled until an address is found, then named after it ("Alerts for 3515 Fillmore St"). "Not legal advice" · as-of date in the header
2. **"Next change: <date> — <what>"**
3. **Small map** (P1): pin + legal-city outline, "Inside <city> city limits" (+ postal city when it differs); State › County › City; building facts (year, units, source), "unknown" shown plainly
4. **"At a glance":** one plain sentence; status tokens only when the tiles differ
5. **Now:** the six accordion tiles
6. **Coming up:** dated plain lines, change log old → new; undated bills as "Proposed, not law"
7. **Alerts:** signup and email preview
8. How this works · disclaimer

## Priorities and feature status

Architecture and the pipeline rows noted below were checked against `fcff56b` on 04.10.2026; older live-site observations retain their original timestamps. See [implementation boundaries](ARCHITECTURE.md#implementation-boundaries) for unmerged work.

This is the project's feature list; each build updates its status in the same commit. Statuses: built · partial · experimental · WIP (branch/PR) · planned · idea · not specified.

**No feature without asking first.** Nobody (person or agent) builds a feature that isn't in this table or its issue. A new idea goes into the table as `idea` and gets agreed before any code.

Checked Sun 04.10.2026 ~05:00 CEST against `origin/main` (043672e) and the live site. Production (`yourhomerule.com`) serves the `production` branch at 8e7c326 (#70), the same commit as `main`, so the live site = `main` for everything below (banner and icon rows updated after #67 and #70 merged). "Live:" names a URL that shows the feature today.

### Pipeline and scored files

| Prio | Feature | Owner | Status · evidence |
|---|---|---|---|
| P0 | Extraction → `out/rules.json` + `out/rules.compiled.json` | D | built (#30, #31, #35, #40, #46, #51): 54 scored rules in `out/rules.json` at `fcff56b`, quotes verbatim, `make eval`, audit trail `out/audit.json`; Santa Ana has no text in the corpus (a finding). Brief-named rule count and T1–T5 as reported by `make eval`, not re-run for this check |
| P0 | Stable extraction: three samples + majority vote, `make check` | D | built (merged #53): `Makefile`, `extract/vote.py`; three extraction/gate samples, majority selection and `out/vote.json` |
| P0 | Prompt lint + freeze (`make freeze`, `extract/PROMPTS.lock`) | D | built (#35, later prompt updates through #106): lint, vocabulary-drift check and committed lock; run `python -m extract.prompts` before hour 16 to verify the current digest. The earlier mismatch observation is historical, not a current check |
| P0 | Jurisdiction list + address resolution (Census geocoder, offline cache) | S | built (#29): `make resolve`, 500/500, `out/addresses.resolved.json`; subsidy correction (#134): 27 explicit positives, 473 unknown, legacy assumption rejected |
| P0 | Engine → `outputs/lookups.json`, `outputs/changes.json`, `out/lookups.full.json` | S | built (#36, #40, #47): `make build`, all 500 addresses, T1–T5 in `outputs/changes.json` (T6 needs the hour-16 document), J1–J3 + Dorchester as tests (`tests/test_engine.py`) |
| P0 | Conditional deposit amounts through compiler, engine and card | D | built, merged #128 (includes #138, closes #136; hosted verification pending before production): preserve supporting cap conditions and evidence; show possible amounts, keep owner-wide and tenant conditions unresolved, and score the range |
| P0 | Per-address diff (I6) → `out/changes.full.json` | S | built (#45, #113, #119): `engine/diff.py`; 9 as-of sources including rule start and end dates, 390 addresses with an entry, 1,514 changes at `fcff56b`; per-change verdict, `rating` (positive / neutral / negative) and why; `tests/test_diff.py` checks agreement with `changes.json` |
| P0 | `outputs/` holds the three scored files | S | built (#110): all three committed; `make build` writes all three on main. Its rules projection clears supplemental document IDs outside the starter manifest; do not overwrite it with `out/rules.json` |
| P0 | Hour-16 ingest in one command | D | built (#30): `make ingest`, `make rehearse`, `make rerun` |
| P0 | Demo change for beat 6: `make demo-change` (fictional X001 ingest → before/after → diff → web sync) | S | partial (#45): built, never run; X001 extraction needs `OPENROUTER_API_KEY` or a warm `build/cache`, so `out/changes.full.json` has no `ingest:` source yet |
| P0 | Live data sync: `npm run sync` copies contracts + `out/` into `web/` and builds `web/data/live/` (rules, findings, per-address results, quote excerpts ±320 chars), drift test | S | built (#41/#50, #54): `web/scripts/sync-contracts.ts`, `web/scripts/build-live.ts`, `web/tests/contracts-sync.test.ts`; header shows "Live" (one build = one source via `NEXT_PUBLIC_DATA_SOURCE`, the "Demo data" option is shown disabled) |
| P1 | Chatbot scoreboard: ~20 dated questions, plain vs web search vs HomeRule | D | built as a measurement (#39, #43, `scoreboard/`): plain 16/20 (4 wrong), plain + web search 20/20, HomeRule 18/20 (0 wrong); not a headline number, not on the site |
| P1 | Show the guide's four open legal questions as flags with both sources | D (data), S (display) | built (`out/findings.json` kind `open_question`, `extract/open_questions.py`; shown on the tiles) |
| P1 | Card answers per card question (`out/cards.json`) + card audit | D | WIP (PR #55): fixes wrong headline values, e.g. LA rent "3% for Jul 2025–Jun 2026" shown as current |
| P1 | Renter-protection score: impact per rule, one score with per-topic breakdown | D | built (#59): `renter_impact` per rule and per change (verdict better / worse / unchanged / unclear, `rating` positive / neutral / negative, `why`, `decided_by`); per address and date `change_from_previous.rating` (no weights: only which way the topics that surely moved went), `out/scores.json` per address / city / state and date with per-topic levels and "what would settle this"; display: S, the three-way rating only (no 0-100 number or per-topic weights on the page; Silvan 04.10.) |
| P1 | Change verdict on the page, change log and email: ↑ "adds renter protection" / ↓ "narrows" / grey "depends on a fact we don't have", from the diff's `renter_impact` (#72), and protections ending ("Ends: …" in the history, sunset sources in the diff, `effective_until` in rules and API, #71 + #77) | S | built (PR "Verdicts: #71 + #72 + #77 on #110"): `PAGE_BADGES` on; verdicts after rebuild 270 better · 28 worse · 838 unchanged · 98 unclear; Hoff St A0050 "Ends Jan 1, 2030" ↓, Newark FAIR Act ↑. Before production: Silvan's 15-badge hand check (`node web/scripts/verdict-split.ts`) |
| P1 | Extra data: next useful building fact + public evidence pilot | D | partial: review panel and pinned offline planner merged in #123, refreshed after #135; 209/500 sample addresses have a next-fact question. Full-address confirmation, public-record leads, discrepancies and request wording are built. Broader acquisition remains draft #68; no facts promoted |
| P1 | Official-source monitoring: discover law updates, preserve versions, extract changes and preview affected addresses | D | built, on `main` ([#60](https://github.com/ilPicc0ne/homerule-workspace/issues/60), [PR #75](https://github.com/ilPicc0ne/homerule-workspace/pull/75)): Newark prototype run by hand, review before publication; no scheduler, not deployed, not part of the scored outputs. See [Keeping the law data fresh](#keeping-the-law-data-fresh-issue-60) |
| P1 | Extra data sources (see [ARCHITECTURE](ARCHITECTURE.md#data-sources-and-remaining-expansion)) | D | partial (#22): approved supplemental law feeds extraction; the review-only panel and pinned building-record evidence are merged in #123. Acquisition tools remain draft #68; original California occupancy records are still missing and evidence is not promoted to I3. Map assets are separate |

### Keeping the law data fresh (issue #60)

The official-source monitor checks for new and revised housing-law documents so HomeRule can detect changes after the initial corpus was collected. **On `main` since [PR #75](https://github.com/ilPicc0ne/homerule-workspace/pull/75): a Newark prototype run by hand; not scheduled or deployed.**

1. **Check approved sources.** The current live-source pilot polls Newark's documented Legistar API every six hours while the worker is running. It revisits six known rent-control matters and discovers housing-related titles. This is bounded discovery, not complete coverage of Newark or all ten cities. Additional official text, HTML and embedded-text PDF routes can use the document adapter after source review.
2. **Preserve evidence and detect changes.** Keep immutable source snapshots and retrieval details, compare document versions, and queue new or changed text. Unchanged responses do not trigger extraction. Failed fetches and incomplete discovery stay visible in the report; old evidence is retained.
3. **Extract and preview the impact.** With extraction enabled, run the existing Jev/Luna pipeline on each changed whole document, check its supporting quotes, and evaluate candidate before/after rules across the 500 sample addresses. Show changed answers and coverage, including future effective and end dates. Also check accepted rules for date-driven changes without needing a new source publication.
4. **Review before publishing.** Candidate impacts require review and promotion through the existing corpus/build pipeline before reaching the site or alerts. A changed page is not proof that a law took effect; a missing provision is not proof of repeal. Keep discovery, publisher modification and legal effective dates separate. The monitor itself does not overwrite accepted rules or scored outputs, or send emails.

**Operation:** `make monitor` runs one bounded poll; `make monitor EXTRACT=1` also processes queued changes; `make monitor-watch EXTRACT=1` keeps the foreground worker running; `make monitor-report` opens access to its local report. No scheduler is installed automatically. Deploying an ongoing worker and adding reviewed sources are remaining rollout steps. Requests respect reviewed source routes, robots rules, rate limits and retry delays. Details: [monitor/README.md](../monitor/README.md).


### Site (live at yourhomerule.com)

| Prio | Feature | Owner | Status · evidence |
|---|---|---|---|
| P0 | Landing page: hero, search box, eight example addresses, six questions, scope line "3 states and 10 cities" | S | built (#28; was "coming soon" until then). Live: `/` |
| P0 | Search (one box): address, city, neighbourhood, county, state via the jurisdiction list + aliases; "Not covered" for anything outside | S | built (#29). Live: `/where?q=Dorchester` (→ Boston), `/where?q=Austin` (→ "Not covered"); `/api/resolve?q=`; landing search routes sample addresses to `/a/<id>` and places to `/j/<id>` |
| P0 | `/where`: jurisdiction tree Federal › State › County › City with coverage per level, autocomplete over sample addresses and places | S | built (#29). Live: `/where` |
| P0 | Address page v3, one view: sticky bar (search + "Get alerts"), next change, map, at a glance, six accordion tiles (plain answer · details · "Show the law"), coming up, alerts, how it works | S | built (#52, #54) for all 500 sample addresses. Live: `/a/A0016` |
| P0 | "At a glance": one plain sentence + six topic tokens | S | built (#52). Live: `/a/A0258` ("…missing one fact. For 2 topics, there's no local rule…") |
| P0 | "Next change" line in the header | S | partial (#52): shows the next dated change where the data has one (`/a/A0256`: Jul 1, 2027); "No changes scheduled" for SF/LA/Boston because no rule end dates are extracted |
| P0 | Typed address outside the 500 (`/a/at?q=`), resolved via Census, rules evaluated with unknown building facts | S | built (#52). Live: `/a/at?q=4801 E 3rd St, Los Angeles, CA` (unincorporated East LA: state rules only, "Los Angeles County's own rules … aren't in HomeRule") |
| P1 | Live address dates: exact-date API and clickable sample/typed timeline | D (review S) | built, merged #128 (includes #130; hosted verification pending before production): deterministic request-time evaluation; one clickable dot per date, grouped changes, expandable older history and dataset-date default/return; same-date-only sample fallback, explicit errors for unavailable dates. MCP remains on its published snapshot. |
| P1 | Live Python engine for non-sample typed addresses, with the existing provisional fallback | D (review S) | built, merged #128 (closes #127): exact sample parity, bundled stdlib-only endpoint, shared web row mapper, 3-second fallback. No live building-data lookup; hosted Vercel verification pending |
| P0 | JSON per address: `/api/address/[id]` (`not_legal_advice`, `as_of`, results with rule, quote, what next) | S | built (#52). Live: `/api/address/A0016` |
| P1 | Small real map: MapLibre GL + OpenFreeMap, pin, Census TIGER city outline, "Inside <city> city limits" / "Outside any city" caption | S | built (#49, #54). Live: `/a/A0016`; unincorporated caption via the typed East LA address (no sample address is unincorporated) |
| P2 | 3D map view behind a `Map · 3D` switch on the map card (Google Maps JS `Map3DElement`): fly-in from the legal-city outline to the address, same caption; `?map=` and the visitor's own choice win; falls back to MapLibre on no key, key error, load failure (5 s) or no WebGL. **Default view 3D (decided 04.10.2026 for production + preview; preview set 04.10.2026, production `NEXT_PUBLIC_DEFAULT_MAP_VIEW=3d` still to be set by Silvan: the agent was not permitted to write it); switch back by setting `NEXT_PUBLIC_DEFAULT_MAP_VIEW=map` and redeploying.** Every page view is then a Google load (cap 500/day, then the MapLibre fallback). Final shot centred at the target's ground elevation (`web/data/elevations.json`, Open-Meteo, 04.10.2026); typed addresses get a top-down final shot (fix for the off-target view on hills; at altitude 0, 214/492 sample addresses were > 50 m off). **Controls:** enlarge button (both views) opens the map full viewport (`<dialog>` modal, Esc / Close, page scroll locked); in 3D the same map element goes modal (no second Google load) with Google's zoom/tilt/rotate controls and plain scroll/drag gestures, the card stays cooperative without Google's controls (Google hides them at card size anyway); ↻ replays the fly-in (reduced motion: jumps back to the building); one-line gesture hint under the 3D card until the first interaction | S | experimental (#64, PR #82, not merged) |
| P2 | Address highlight: the OSM building only when the geocode lies inside its outline (`contains: true`, 21/500), extruded teal in 3D, outlined with a pin on its centroid in MapLibre, "Building outline © OpenStreetMap contributors"; every other address (nearest-building or no match) gets a soft ~25 m teal circle around the geocode and "Approximate location" in the caption. Data: `web/data/building-footprints.json` (`scripts/build-building-footprints.ts`, 473/500 within 30 m, `distance_m` kept) | S | experimental (#64, PR #82) |
| P0 | Coming up: dated plain lines, recently changed, undated bills as "Proposed, not law" with "Follow" links | S | built (#52, #56). Live: `/a/A0256` (FAIR Act Jul 1, 2027), `/a/A0010` (Mass. S.2983, H.5222) |
| P0 | Change log per address, old → new, dated, quoted; linked from Coming up ("See the full change log", "What changed, old → new") | S | built (#45, #56). Live: `/changes/A0256`. Addresses without a diff entry show an empty log (`/changes/A0010`) |
| P0 | Email preview on the change log (From, Subject, `List-Unsubscribe`, plain-text part; "Preview only, nothing is sent") | S | built (#45, #61). Live: `/changes/A0256` |
| P0 | Rule page: quote in a source excerpt, link to the official law, dates, status, "what it depends on", audit trail with "reasoning boundary" (model extracted vs code decided) | S (audit data D) | built (#41/#50). Live: `/r/MA-ALG-2983`; 64 rule pages (58 scored + unscored records) |
| P1 | Impact on the rule page: every sample address the rule reaches, coloured by result | S | partial: SVG dot map + address list for one as-of date (2026-10-01); **no date slider** (the live data has one as-of date). Live: `/r/MA-ALG-2983` (110 MA addresses, all pending) |
| P1 | Jurisdiction pages for every level (`/j/<id>`), rules by question with their conditions, list of sample addresses | S | built (#41/#50). Live: `/j/NJ-HOBOKEN`, `/j/CA` |
| P0 | Contacts per tile (J7): `contracts/contacts.json` (36 entries, all city × topic routes, source + retrieval date); first next step on each tile is a person | D (data), S (display) | built (data via #56 from the `d/contacts` work; display #56). Phones labelled "Number not yet checked by us". PR #48 is still open although the data is on `main` |
| P1 | Action helpers (J7): "Before you call, have ready" checklist, "Ask your landlord" ready email for a missing fact, Boston tenant-rights notice check | S | partial (#52): checklist on rent/eviction tiles, landlord email where a fact is missing (`/a/A0107`), Boston notice item (`/a/A0258`); not on every tile |
| P0 | Site-wide prototype banner ("Prototype built at a hackathon — not production-ready…"), same text in every email footer | S | built (#57; solid navy bar with info icon and bold "Not legal advice." since #67, live) |
| P0 | Scope disclaimer: full answers only for the 500 sample addresses (hackathon scope) — note under the landing search, "sample only" in search suggestions and no-match, "Provisional answer" banner on typed addresses (`/a/at`) | S | built (s/ui-polish) |
| P0 | Palette + header option A "Quiet": teal-derived accent, softer clay caution, slate-navy UI chrome | S | built (#58, #63) |
| P2 | Brand icon: roof-scales mark as favicon, apple-icon, site headers and email logo | S | built (#70, live in production 8e7c326) |
| P1 | As-of date navigation on the address page | D | built, merged #128: clickable timeline dots for known dates, grouped events and expandable older history; no separate slider or free-date input. Hosted verification pending before production |
| P2 | MCP server `/api/mcp` (issue #23): public, read-only, Streamable HTTP via `mcp-handler` 2.2.0, stateless (no Redis sessions). **Everything on the website, with the law's own words and links**, built from the same functions the pages render. Task-shaped (one call per question, measured: median 2 → 1 call over 26 renter questions): `get_place` (any address or place → address page `/a/[id]` / typed `/a/at`, provisional and labelled, or jurisdiction page `/j/[id]` with each rule's status, key value and quote; not covered says so), `compare_places` (two places side by side, J5 for chatbots; no ranking), `get_changes` (change log `/changes/[id]` with the renter-impact badge; for a city or state grouped by rule with affected and badge counts), `get_rule` (rule page incl. impact, for depth), `coverage` (landing). Every result: `not_legal_advice`, `as_of`, `retrieved`, data only (presentation rules in tool descriptions and server instructions, never inside results); one audit log line per call (tool, ids, as_of; no IP, no query text); 300 POSTs per IP per minute via Upstash | S | built (PR #98; parity tools in the "MCP: full parity" PR; preview only, **not in production** until Silvan pushes `production`). Address results exist for the one engine date (2026-10-01): another `as_of` answers for 2026-10-01 and says so. Task-shaped redesign on branch `s/mcp-eval` (not merged). Claude/ChatGPT can only reach production (previews are login-protected) |
| P2 | `/connect` page: "Make your chatbot rent-law aware", connector URL + copy, tabs Claude / ChatGPT / Developers (Claude Code command, Cursor + VS Code install links, JSON config), example prompt, disclaimer; linked from the landing page and the address page footer ("Ask your chatbot about this address" copies a prompt) | S | built (PR #98, preview only) |

### Alerts (email)

| Prio | Feature | Owner | Status · evidence |
|---|---|---|---|
| P1 | "Get alerts" form (bell in the sticky bar + Coming up link) → `POST /api/subscribe` (5 per IP per 10 min, never reveals an existing subscription) → `alerts:pending:<token>` (48 h) → confirmation email → `/confirm` page with a POST button → `alerts:sub:<address_id>` | S | built (#57, #62). Live: `/a/A0010` → "Get alerts" opens "Alerts for 134 Oxford St · Email me" (not submitted in this check) |
| P1 | Closed test: while the postal address in `web/lib/alerts/disclaimer.ts` is a placeholder, confirmation mails and alerts go only to subscribers the seed script marked `allowed` | S | built (#62); still in force (placeholder visible in the live email preview). The 04.10. rehearsal mails went to a seeded `allowed` + `demo` subscriber only |
| P1 | Unsubscribe: `/unsubscribe` page with one button + RFC 8058 one-click `POST /api/unsubscribe`, random per-subscription token stored on the subscriber (no server secret); landing pages `/alerts/confirmed`, `/alerts/unsubscribed`, `/alerts/invalid` | S | built (#57, #62) |
| P1 | Email delivery via Resend from `alerts@yourhomerule.com`, HTML + text, `List-Unsubscribe` headers, one shared layout | S | built (#57, #61); `RESEND_API_KEY` set in Vercel (production, preview). Deliverability warm-up: not documented as done |
| P1 | "See an example alert" overlay on the address page ("Preview — simulated, nothing is sent") | S | built (#57). Live: `/a/A0010` |
| P0 | Demo dispatch for beat 6 (issue #11): `make alert SOURCE=<id> [RESET=1]` → `POST /api/alerts/dispatch {source}` (Bearer `DEMO_TOKEN`) on production, retried until the deploy has the source; idempotent via `alerts:sent:…`; demo-labelled sources only to `demo`-flagged subscribers; `npm run seed-subscriber -- [--demo] <email> <ids>` | S | built, rehearsed on production twice 04.10. (#62, #65, #66): production `f8c33fd`, 04.10.2026: take 1 sent 07:45:23 CEST, take 2 07:50:26 CEST, each after a dry run showing exactly one recipient (demo inbox, address A0011, real NJ source `asof:2026-10-01..2027-07-02`); production answered "1 sent" within 1 s and both mails arrived on the demo phone [verified by owner]. `DEMO_TOKEN` and `ALERTS_SITE_URL` set in Vercel production only. Live take on demo day uses the hour-16 source (`make demo-change` still unrun) |
| P1 | `make notify [SEND=1]`: local dry run / send of change alerts without a token | S | built (#57) |
| P2 | Alert engine, after the freeze (critic verdict: don't build yet; partner test first, then yearly allowed-increase alerts): lifecycle triggers per address (new law found · 30 days before + in force · 30 days before + ending · correction), daily Vercel Cron over a build-time event calendar, per-rule approval queue, one digest per person per day, preferences | S | idea: [issue #83](https://github.com/ilPicc0ne/homerule-workspace/issues/83), plan in `notes/plan/alert-engine.md` (private); gated on a partner test (10 renters per city with a landlord letter), no demand evidence yet |

### Not built yet

| Prio | Feature | Owner | Status |
|---|---|---|---|
| P1 | Renter answers one missing building fact ("you told us", never in the scored files) | S | planned |
| P1 | Compare picked addresses (J5; no ranking, no rent levels, unknown counted apart) | S | planned |
| P1 | Renter-protection map: protection score as colours by **area**, unknown shown separately; never a per-building exemption map (see Never) | S | idea |
| P2 | Protection map over time (past, today, after 01.07.2027) | S | idea |
| P1 | Spanish card summaries (brief stretch goal; quotes stay English) | S | planned |
| P1 | "I rent / I own" wording toggle | S | planned |
| P2 | Legal-aid finder for the exact address | S | planned |
| P3 | ChatGPT custom GPT on the JSON endpoint | D | planned |
| Idea | Search typo tolerance ("Hobokn" → suggestion, never applied silently) | S | idea |
| Idea | Google Places autocomplete for any US address (attribution and Maps terms apply) | S | idea (`NEXT_PUBLIC_GOOGLE_MAPS_KEY` exists in Vercel; only the 3D map view reads it) |
| Idea | Own chatbot · neighbourhood comparison · repairs card | — | idea |

### Known gaps before the freeze

1. **Demo change X001 not run:** `make demo-change` needs `OPENROUTER_API_KEY` (or a warm `build/cache`); without it there is no `ingest:` source, so the live beat 6 has no hour-16 change to send. [verified: `out/changes.full.json` has only two `asof:` sources] The send path itself is rehearsed: twice on production 04.10. with the real NJ `asof:` source (see Demo dispatch row).
2. **Postal-address placeholder** in `web/lib/alerts/disclaimer.ts`: every email footer (and the live preview on `/changes/A0256`) shows `[PLACEHOLDER: HomeRule postal address — owner to fill in]`; this also keeps the closed test on. [verified]
3. **"Next change" empty where no end dates:** SF, LA, Boston and Cambridge addresses say "No changes scheduled" because rule end dates (e.g. SF's yearly 1.6% through Feb 2027) are not extracted. [verified on `/a/A0016`, `/a/A0107`]
4. **East LA is a stand-in:** the unincorporated case only shows for a typed address (`/a/at?q=4801 E 3rd St…`); no sample address is unincorporated and LA County's own ordinance (ch. 8.52) is not in HomeRule. [verified]
5. **Newark exception tagged as a core rule** in the extraction: `NJ-NEWARK-RENT-19:2-18.3` (initial rent of rehabilitated dwellings not restricted) is a `rent_increase_limits` rule, not an exemption. [verified in `out/rules.json`]
6. **Prompt lock mismatch:** current prompt digest ≠ `extract/PROMPTS.lock`. [verified]
7. **Stale headline values** until PR #55 lands: LA rent shows "3% for Jul 2025–Jun 2026" as current on 01.10.2026. [verified on `/a/A0107`]
8. **Address date navigation merged in #128:** its timeline dots run the engine for the selected date. Rule impact maps and MCP remain on their existing date behavior; there is no free-date slider.
9. Scored files are committed from main builds (#110, #139). After #128 merged, `make build` on main at `49a82cf` refreshed 250 conditional-deposit explanations without changing coverage statuses; never copy `out/rules.json` over the scored projection.
10. `DEMO_TOKEN` and `ALERTS_SITE_URL` are set in Vercel **production only**; `make alert` against a preview URL gets 401. [verified with `vercel env ls`]
11. Unmerged work remains separate: #55 and draft #68; #128, including #130 and #138, is merged into main at `49a82cf` after Silvan's approval and Dimitar's explicit waiver of the hosted check for the main merge. Hosted live/fallback verification remains required before production. Contacts #48 and neutral-badge #122 are closed as already integrated. #123's review panel, #135's subsidy correction and #129's video handoff are now on main; merge does not establish production deployment.

## User journeys

**J1 · What applies at my address?** (P0) Ana, 3515 Fillmore St, SF, just got a rent-increase notice.
1. Types "3515 Fill…", picks the suggestion.
2. Sees: California › San Francisco · built 1926 · 21 units · six tiles.
3. Opens "How much can my rent go up?": SF Rent Ordinance applies; the state cap is replaced by it; quote, citation, date.
- ✅ Done when: both rules show with the right result and a verbatim quote, in under 60 s.

**J2 · An honest unknown** (P0) Marco, 10635 Sherman Grove Ave, LA, built 1978.
1. Opens his address.
2. Rent tile says "We're missing one fact": whether the city first approved the building for living in on or before 01.10.1978. Who can tell you: LA Housing Department or your landlord.
3. (P1) Enters the date himself → tile updates, marked "you told us".
- ✅ Done when: the rule shows as unknown with the missing fact and where to check it, never hidden or guessed.

**J3 · What's coming?** (P0) A tenant at 327 Jackson St, Hoboken.
1. Scrolls to "Coming up": NJ FAIR Act takes effect 01.07.2027, may conflict with Hoboken's own ban.
2. Moves the date to 02.07.2027.
3. The tile flips to "There's a rule"; the conflict flag stays, undecided.
- ✅ Done when: the status flips at the date and the conflict is shown, not resolved.

**J4 · Tell me when the law changes** (P0 preview, P1 sending) A tenant at 134 Oxford St, Cambridge.
1. Taps the "Get alerts" bell in the address bar ("Alerts for 134 Oxford St"), enters an email and confirms.
2. A new ordinance is ingested (hour 16).
3. The change log shows old → new; the email shows the same: new rule, date, quote, "not legal advice".
- ✅ Done when: the ingest produces the change log and the matching email preview in under 10 min.

**J6 · Which buildings does this bill reach?** (P0 rule page, P1 map) An advocate in Boston.
1. Opens the rule page for MA S.2983 (from any Boston address, or search).
2. Sees: status "proposed, not law", the bill text quote, link to malegislature.gov, and all 110 MA sample addresses marked "pending".
3. Clicks one quote → sees what the model extracted and what the code decided.
- ✅ Done when: the affected list matches `changes.json` T4, every address says pending (never in force), and the law link opens the official source.

**J5 · Before I sign: compare before I move** (P1) Lena is moving to San Francisco and has two listings in a neighbourhood she doesn't know: 3515 Fillmore St (built 1926) and 36 Hoff St (built 1986). She wants to know what protections come with each apartment before she signs the lease.
1. Opens each address (one at a time): Fillmore has San Francisco rent control; at Hoff St, the state cap may apply, but coverage remains unknown until missing subsidy information is established (#135). Same city, different answer per building, with uncertainty visible.
2. Checks what's coming at each: e.g. the state cap's 2030 end date. The history keeps the building-specific impact and any uncertainty; a local protection can remain after the state rule ends.
3. (P1) Picks both and "compare": per category applies / unknown / coming, side by side.
4. A listing outside the sample: types the address, HomeRule resolves the legal city (Census) and says plainly which building facts it doesn't know.
- ✅ Done when: the comparison shows unknowns apart from "doesn't apply". No rent prices, no ranking, no area map of protection levels (Never: a landlord could use it to find the least-protected buildings).
- Idea (not planned): an area view for movers ("what applies in this neighbourhood") would be attractive, but it collides with the Ranking rule under Never. Only city-level rules are safe there; building-level coverage stays per picked address.

**J7 · Take action** (P0 contacts, P1 helpers) Marco, 10635 Sherman Grove Ave, LA, has just read his rent tile.
1. Opens the tile: the first next step is a person: "LA Housing Department · phone · free".
2. Taps "Ask your landlord": a ready email asking for the missing fact; copies it.
3. Taps "Before you call": checklist "have your notice, lease, move-in date". On the eviction tile, a check item: "Did your notice include the required tenant-rights form?"
- ✅ Done when: every tile has a contact from `contracts/contacts.json` and the renter can copy a ready email or open a checklist without leaving the page.

### Journey status on the live site (checked 04.10.2026)

Walked read-only on yourhomerule.com: no form submitted, no signup, no send.

| CUJ | Live demo URL | Status | Gap |
|---|---|---|---|
| J1 What applies at my address? | [/a/A0016](https://yourhomerule.com/a/A0016) (3515 Fillmore St) | walkable | None for the done-criterion: SF Rent Ordinance § 37.3 applies, Cal. Civ. Code § 1947.12 "replaced here by the city rule", quotes + dates, built 1926 · 21 units |
| J2 An honest unknown | [/a/A0107](https://yourhomerule.com/a/A0107) (10635 Sherman Grove Ave) | partly walkable | Rent tile says "We're missing one fact" and names the office (LA Housing Department) and a landlord email. But the named facts are "an exception in the law's text" and "whether the owner lives in the building", not the certificate-of-occupancy date the journey describes. Step 3 (renter enters the date, "you told us") not built |
| J3 What's coming? | [/a/A0256](https://yourhomerule.com/a/A0256), [/changes/A0256](https://yourhomerule.com/changes/A0256) | partly walkable | Coming up shows the FAIR Act on Jul 1, 2027 with the conflict flag "flagged for review, not decided"; the change log shows Enacted → Applies, still flagged. Step 2 (move the date to 02.07.2027, tile flips) not possible: no date picker or slider |
| J4 Tell me when the law changes | [/a/A0010](https://yourhomerule.com/a/A0010) ("Get alerts", "See an example alert"), [/changes/A0256](https://yourhomerule.com/changes/A0256) (email preview) | partly walkable; alert send built, rehearsed on production twice 04.10. | Signup form, double opt-in, confirm and unsubscribe are live but in the closed test (only `allowed` emails get mail; postal address still a placeholder). Alert email: dispatched on production `f8c33fd` twice on 04.10. (07:45:23 and 07:50:26 CEST) to the demo inbox for A0011 with the real NJ source `asof:2026-10-01..2027-07-02`, one recipient per dry run, "1 sent" within 1 s, both arrived [verified by owner]. /changes/A0010 is still empty (Cambridge has no change). The hour-16 ingest → change log → email path has not run; that is the live take |
| J5 Before I sign: compare before I move | [/a/A0016](https://yourhomerule.com/a/A0016), [/a/A0050](https://yourhomerule.com/a/A0050) | partly walkable | Address pages and dated history are built on main; step 3 side-by-side comparison in the UI remains planned (P1). After #135 deploys, Hoff St's state rent coverage stays unknown until subsidy information is established. Deployment is separate from merge. |
| J6 Which buildings does this bill reach? | [/r/MA-ALG-2983](https://yourhomerule.com/r/MA-ALG-2983?from=A0258) | walkable | "Proposed, not law", bill quote, link to malegislature.gov, 110 MA addresses all "Pending, not law", audit trail with the reasoning boundary. Impact is a dot map for one date (no slider) |
| J7 Take action | [/a/A0107](https://yourhomerule.com/a/A0107), [/a/A0258](https://yourhomerule.com/a/A0258) | mostly walkable | Contact first on each tile (phones marked "not yet checked by us"), "Before you call, have ready" checklist, "Ask your landlord" ready email, Boston tenant-rights notice item. Helpers are not on every tile |

## Demo (2:30)

| # | Beat | Shows | Time |
|---|---|---|---|
| 1 | **Chatbot scoreboard** (only with its method on screen: who wrote the questions, date, model and version, link to the question set; if not measured by 12:00, drop it and open on beat 2): "ChatGPT 9/20 · HomeRule 19/20" on dated questions (struck Boston ballot, NJ $50 fee cap) | The headline, as a number | 0:15 |
| 2 | **Ana's address, 3515 Fillmore St, SF:** six tiles; rent tile: SF ordinance applies, state cap superseded | The product | 0:30 |
| 3 | **Same question, two more buildings:** 10635 Sherman Grove Ave, LA → unknown with what to check; 471 Columbia Rd "Dorchester" → Boston, no rent cap | Honest unknown, postal ≠ legal city, no invented rules | 0:25 |
| 4 | **Click the answer → rule page:** quote in the law text, link to the official source, what the model extracted vs what the code decided | The AI and the responsible design, visible | 0:25 |
| 5 | **Date slider on the FAIR Act map:** NJ dots flip on 02.07.2027, conflict rings on Hoboken and Jersey City | Change tracking | 0:20 |
| 6 | **Hour-16 live:** ingest the new ordinance on camera with a clock, change log updates, the alert email arrives on a phone | Automation, the live proof | 0:30 |
| 7 | **Proof frame:** 500/500 addresses resolved · 38 postal-city corrections · 100% verbatim quotes · T1–T5 pass | Credibility | 0:05 |

The order of beats still holds with the one-view page (v3, live). The answers on the site now come from the engine; these addresses are also engine tests. There is no date slider (see Known gaps): beat 5 needs a stand-in, e.g. Coming up and the change log on `/a/A0256` → `/changes/A0256`. Beat 1's numbers are placeholders; the measured scoreboard is plain 16/20, web search 20/20, HomeRule 18/20.

## Owners and handoffs

| Dimitar | Silvan |
|---|---|
| Everything up to `rules.json`: triage, Jev classification, extraction, quote check, statuses | Jurisdiction list (13 IDs both sides use), address lookup, building facts |
| Hour-16 ingest, eval suite, audit log | Engine, lookups, changes, diff |
| Extra data sources (P1), ChatGPT GPT (P3) | MCP server + /connect (P2, #23) |
| | Page, change log, email + subscription store, score |
| Technical video | Submission package 12:00–15:00 (videos, method note, README) |

**First steps:**
- **Dimitar:** triage the 13 jurisdictions × 6 categories grid against the corpus; test Jev on 5 documents.
- **Silvan:** the jurisdiction list and the address lookup. Already measured: 500/500 jurisdictions.

The interfaces between us (file shapes, the jurisdiction list) are in [ARCHITECTURE.md](ARCHITECTURE.md#interfaces). Change them only via PR.

## Done by the 12:00 freeze

- `make eval` green:
  - ≥22 of the ~27 rules the brief names, with the right status and date;
  - every jurisdiction × category cell triaged;
  - T1–T5 right;
  - the demo addresses right;
  - 100% of quotes verbatim;
  - "not legal advice" found everywhere.
- J1–J4 work on the deployed page, on a phone, tried by someone outside the team.

## Submission checklist (12:00–15:00, lead: Silvan)

| Item | Owner | Done when |
|---|---|---|
| `rules.json`, `lookups.json`, `changes.json` committed in `outputs/` from a build on `main` | S | Schema-valid, all 500 addresses, T1–T5 present (no T6: the hour-16 ordinance was removed, organizers 04.10.) |
| Public GitHub repo with code, README (how to run), output files | S | A fresh clone runs `make all` |
| Live demo link (yourhomerule.com) | S | Works on a phone |
| Team video (Team Intro) | S | Both of us, ≤ 60 s ([docs/VIDEO.md](VIDEO.md)) |
| Demo video, with the scores on screen | S | ≤ 60 s, follows `notes/demo/video/STORY.md` cut to 60 s ([docs/VIDEO.md](VIDEO.md)) |
| Technical video (Teach): our own validation, the `make eval` report (no `score.py`: organizers 04.10.), T1–T5 results, the new-ordinance rehearsal (fictional X001, labelled), a live `make rerun DOC=` | D | ≤ 60 s, all four visible on screen ([docs/VIDEO.md](VIDEO.md)) |
| One-page method note | S | Sources, pipeline, what code decides vs the model, limits |

Teach handoff (#137) completed through #129: locked 107-word script, corrected engine/scaling visuals, and a three-second validation insert with its actual log under `notes/demo/video/assets/`. Final animation, voice, compositing, broader checklist coverage and upload remain part of submission issue #13. Current validation after #135: 26/27 assertions, 23/24 tuning coverage (Q2 correctly unknown with missing subsidy data), 16/16 holdout coverage, T1–T5 and 54/54 scored quotes pass. The benchmark expectations were not changed.

## Never

- **Advice and verdicts:** no legal advice, no "compliant" or "illegal", no comparing a user's rent to a cap (nor wording that invites it), no applying the law to the renter's case (state facts, let them conclude), no tips on avoiding a rule.
- **Inventions:** no invented rules or citations. Pending law is never shown as law.
- **Ranking:** no ranked list of least-protected buildings.
- **Data:** no non-public or pricing data; no scraping against site terms.

## Open questions

- ~~Will `score.py` and the dev key be released?~~ No (organizers 04.10.): videos show our own output and validation. How are unknowns scored? (Discord)
- ~~When exactly does the hour-16 ordinance drop?~~ It doesn't: removed in the v5 participant release; T1–T5 only (organizers 04.10.).
- How are the 19 "no rule" findings represented in `rules.json`?
- Jev access and quality (5-document test).
- Tagline: Dimitar may still argue for the provocative line, "Your landlord has a lawyer. You have the law."

Combined #128 validation (04.10.2026): `make check` passed with 120 Python tests, 500/500 bundled endpoint parity, zero engine/eval differences, T1–T5 and the ingestion rehearsal. Web tests: 302 passed, 5 skipped; TypeScript and changed-file lint passed. Coverage remains 23/24 tuning and 16/16 holdout; assertions 26/27, scored quotes 54/54. Flat-value checks are 1/3 and 1/2 because unresolved deposits now carry conditional amounts; expectations were not weakened. The evidence-date guard is tested, and its dataset projection was regenerated. Hosted verification remains pending before production; its pre-merge requirement was explicitly waived by Dimitar after Silvan approved the tested commit.

### Public build reproducibility

Public checkouts rebuild from committed intermediates plus `out/build_inputs.json` (corpus document IDs and T1–T5 scenario inputs, without source text or expected answers). The engine prefers the original starter files when present. `python3 -m engine.build_inputs` refreshes this metadata from the original pack. The starter pack is included at `data/realpage-starter/` at Dimitar's request. `make eval` and `make check` use that pack; a successful build alone does not independently verify source quotes.
