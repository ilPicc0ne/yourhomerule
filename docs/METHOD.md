# HomeRule: method note

**What it answers.** For any of the 500 sample addresses (and typed addresses in the covered cities): which rules on
rent increases, eviction, deposits, application fees, tenant screening and rent-setting software apply on a given
date, with a verbatim quote, the official source and its dates, and *unknown* when the data can't decide.
Not legal advice; every page and email says so.

**Sources.** The starter corpus plus supplemental official texts cleared for extraction (site terms checked; held
or restricted sources stay out). Every document is pinned by hash; every quote is located word for word in it.
47 of the 54 scored rules cite the supplied corpus. 7 cite official texts we saved because the corpus lists them as
link only (the Hoboken and Jersey City rent-setting software bans that T2 and T3 need, Hoboken rent control, three
Newark rules): each keeps its official URL, retrieval date and verbatim quote, with `source_doc_id` null in
`rules.json` (it isn't a manifest document), and doesn't count toward the citation metric.

**Pipeline.**
1. *Resolve:* Census geocoder, legal city (not postal city), state › county › city stack; building facts (year
   built, units, use, subsidy) from the address data. A missing fact stays missing.
2. *Extract:* a classifier (Jev) labels each section's topic and kind; an LLM (Luna) writes rule records: the
   requirement, a verbatim quote, coverage and exemptions in a fixed vocabulary of building facts, and dates *as
   written*. Code checks every record (quote found, value in its quote, operator matches the wording); Jev
   cross-checks; one targeted repair call fixes what fails; a gate re-checks quote support, start date, status,
   which government enacted it and whether the provision regulates its topic.
3. *Vote:* three independent extractions; a rule is kept when most samples have it, choosing the version whose
   results across all 500 addresses and four dates agree with the others most.
4. *Compile (code):* dates from the text or statutory defaults (e.g. California's January 1 rule), versions of a
   law chained in time, an amendment or a yearly rate date never counted as a law's start, exemptions normalised.
5. *Apply (code):* a three-valued evaluator per address and date: applies / not yet effective / pending /
   superseded by a stricter local rule / unknown (naming the missing fact and where to check it). A state law
   that may override a city's rule is flagged, never decided.
6. *Track:* the same engine at two dates, or without and with a new document, gives the per-address change log
   and alerts; a new ordinance is one command (`make ingest`), no code or prompt change. Each change is rated for renters
   positive / neutral / negative, with one sentence why: positive when a protection got stronger and none weaker
   (a part that depends on a missing fact is named), negative the reverse, neutral otherwise. No weights between
   topics.

**Reasoning boundary.** The model reads: it extracts text and labels with probabilities. Code decides: status,
dates, coverage, precedence, and whether a change is better or worse for renters. Every model call is logged with
its request hash; each rule's audit trail shows quote, checks, gate answers and calls.

**Evaluation** (`make check`, every change): brief-named rules 26/27 (the miss, Santa Ana, has no text in the
corpus and is recorded as a finding); change tests T1–T5 pass, a new-ordinance rehearsal (fictional text) 45/45 addresses; address
questions 23/24 on the tuning set and 16/16 on a held-out set never used for tuning; scored quotes 100% verbatim.
Prompts are linted (no test-suite value may appear in a prompt) and frozen by hash.

**Limits.** Fresh re-extractions score lower than the shipped one (tuning 20–24/24, held-out 14–16/16): which
provision counts as a law's main rule and some coverage conditions vary between runs; the three-sample vote reduces,
not removes, this. Building facts are often missing (no year built for Berkeley and San Diego), so many answers
are honestly unknown; facts about the tenant (length of tenancy, household) are notes, never inputs. Coverage is
3 states, 10 cities. Building-level answers exist for the 500 sample addresses only: their building facts come from the
challenge's sample file. Any other address in the three states is resolved to its legal city live and gets the
state and city rules, but with every building fact unknown. Fixable without changing the engine: the sample was
drawn from public parcel datasets (New Jersey's covers the whole state), and a parcel lookup at the address gives
the same facts the engine already evaluates.
