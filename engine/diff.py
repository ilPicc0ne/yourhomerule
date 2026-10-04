"""Per-address diff (interface I6): one computation for the change log, the alert email and changes.json.

A change source is two engine evaluations (engine/build.py, the same rows as lookups.json):
- as_of:  the same rules at two as-of dates (the brief's as_of change tests, e.g. T3 2026-10-01 -> 2027-07-02,
          each rule end date effective.until ±1 day, e.g. 2029-12-31 -> 2030-01-02, and each rule start date
          effective.from ±1 day from a year before as_of, unless an earlier window already spans it);
- ingest: the rules without vs with one new document, at one as-of date (the hour-16 path; `make demo-change`).

Per address the listed rows are compared by team_rule_id:
- added    listed after, not before
- removed  listed before, not after
- changed  listed both times with a different result or conflict flag
Each change carries the old and new result, the conflict flags and the rule's title, citation, verbatim quote,
effective date and official source, so the change log and the email need nothing else.

out/changes.full.json (written by make build; make demo-change adds the demo ingest source):
  {not_legal_advice, as_of, sources: {source_id: {kind, title, before, after, document, demo_label,
                                                  affected_address_ids, rule_ids}},
   addresses: {address_id: {label, jurisdictions, entries: [{source, before_as_of, after_as_of, demo_label,
                                                              changes: [change]}]}}}
Only addresses with at least one change are listed. Deterministic: sorted keys and order, no timestamps.
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from engine.build_inputs import change_tests
DEMO_LABEL = "Demo: fictional ordinance"
RULE_FIELDS = ("title", "citation", "requirement_quote", "source_url", "jurisdiction_id", "category",
               "document_status", "origin")


def _side(row):
    return None if row is None else {"result": row["result"], "conflict_flag": row["conflict_flag"],
                                     "explanation": row["explanation"]}


def _rule_info(rule):
    info = {k: rule.get(k) for k in RULE_FIELDS}
    info["effective_from"] = (rule.get("eff") or {}).get("from")
    info["effective_until"] = (rule.get("eff") or {}).get("until")
    return info


def diff_rows(before, after, rules_by_id):
    """Two lists of engine rows for one address -> sorted changes (added / removed / changed)."""
    b = {r["team_rule_id"]: r for r in before}
    a = {r["team_rule_id"]: r for r in after}
    out = []
    for rid in sorted(set(b) | set(a)):
        rb, ra = b.get(rid), a.get(rid)
        if rb and ra and (rb["result"], rb["conflict_flag"]) == (ra["result"], ra["conflict_flag"]):
            continue
        kind = "added" if rb is None else "removed" if ra is None else "changed"
        out.append({"team_rule_id": rid, "change": kind, "before": _side(rb), "after": _side(ra),
                    "result_changed": (rb or {}).get("result") != (ra or {}).get("result"),
                    "conflict_flag_changed": bool((rb or {}).get("conflict_flag")) != bool((ra or {}).get("conflict_flag")),
                    "scored": (ra or rb)["scored"], **_rule_info(rules_by_id[rid])})
    return out


def diff_lookups(before_full, after_full, rules_by_id):
    """{address_id: rows} twice -> {address_id: changes} for addresses with at least one change."""
    out = {}
    from engine import score             # better / worse for the renter, per change (layer 2)
    for aid in sorted(set(before_full) | set(after_full)):
        ch = diff_rows(before_full.get(aid, []), after_full.get(aid, []), rules_by_id)
        if ch:
            out[aid] = score.annotate_changes(ch, before_full.get(aid, []), after_full.get(aid, []), rules_by_id)
    return out


def as_of_tests():
    """The brief's as_of change tests (T1, T3): the dates the demo and the scored file care about."""
    return [t for t in change_tests() if t["type"] == "as_of"]


def source(sid, kind, title, before_rules, after_rules, addresses, d0, d1, cache=None, document=None, demo=False,
           tags=("base", "base")):
    """One change source -> (id, meta, {address_id: changes}). cache: {(tag, date): rows}; tags name the two
    rule sets in it ("base" = the committed I2 rules), so evaluations are shared between sources."""
    from engine import build as B
    cache = {} if cache is None else cache

    def rows(tag, rules, d):
        if (tag, d) not in cache:
            cache[(tag, d)] = B.build_lookups(rules, addresses, d)
        return cache[(tag, d)]

    btag, atag = tags
    by_id = {r["id"]: r for r in before_rules + after_rules}
    changes = diff_lookups(rows(btag, before_rules, d0), rows(atag, after_rules, d1), by_id)
    meta = {"kind": kind, "title": title, "before": {"as_of": d0}, "after": {"as_of": d1},
            "document": document, "demo_label": DEMO_LABEL if demo else None,
            "affected_address_ids": sorted(changes),
            "rule_ids": sorted({c["team_rule_id"] for v in changes.values() for c in v})}
    return sid, meta, changes


def date_sources(rules, addresses, cache=None):
    """as_of sources from the brief's change tests, e.g. asof:2026-10-01..2027-07-02 (T3, J3)."""
    out = []
    for t in as_of_tests():
        sid = f"asof:{t['as_of_before']}..{t['as_of_after']}"
        sid, meta, ch = source(sid, "as_of", t["title"], rules, rules, addresses, t["as_of_before"],
                               t["as_of_after"], cache)
        meta["test_id"] = t["test_id"]
        out.append((sid, meta, ch))
    return out


def until_dates(rules):
    """Each distinct effective.until (sunset or repeal) date -> the rules ending that day, sorted by date."""
    out = {}
    for r in rules:
        until = (r.get("eff") or {}).get("until")
        if until:
            out.setdefault(until, []).append(r["id"])
    return {d: sorted(ids) for d, ids in sorted(out.items())}


def until_sources(rules, addresses, cache=None, skip=()):
    """as_of sources across every rule end date, one day before -> one day after (asof:2029-12-31..2030-01-02),
    so protections ending show up in the same diff as rules starting. skip: source IDs already computed."""
    out = []
    for until, ids in until_dates(rules).items():
        d0, d1 = add_day(until, -1), add_day(until)
        sid = f"asof:{d0}..{d1}"
        if sid in skip:
            continue
        cites = sorted({next(r for r in rules if r["id"] == i).get("citation") or i for i in ids})
        sid, meta, ch = source(sid, "as_of", f"Rules end on {until}: {'; '.join(cites)}", rules, rules, addresses,
                               d0, d1, cache)
        meta["ending_rule_ids"] = ids
        out.append((sid, meta, ch))
    return out


START_LOOKBACK_DAYS = 365      # rule start dates this far before as_of (and every later one) get a window


def start_dates(rules, as_of):
    """Each distinct effective.from date from a year before as_of on -> the rules starting that day."""
    first = add_day(as_of, -START_LOOKBACK_DAYS)
    out = {}
    for r in rules:
        frm = (r.get("eff") or {}).get("from")
        if frm and frm >= first:
            out.setdefault(frm, []).append(r["id"])
    return {d: sorted(ids) for d, ids in sorted(out.items())}


def start_sources(rules, addresses, as_of, cache=None, covered=()):
    """as_of sources across every rule start date, one day before -> one day after, so a law starting (e.g. a
    city ban two months after the state's) has its own history entry and verdict. covered: (before, after) dates
    of the sources already computed; a start date inside one of them is already in that diff and is skipped."""
    out = []
    for frm, ids in start_dates(rules, as_of).items():
        if any(b < frm <= a for b, a in covered):
            continue
        d0, d1 = add_day(frm, -1), add_day(frm)
        cites = sorted({next(r for r in rules if r["id"] == i).get("citation") or i for i in ids})
        sid, meta, ch = source(f"asof:{d0}..{d1}", "as_of", f"Rules start on {frm}: {'; '.join(cites)}", rules,
                               rules, addresses, d0, d1, cache)
        meta["starting_rule_ids"] = ids
        out.append((sid, meta, ch))
    return out


def ingest_source(base_rules, new_rules, addresses, as_of, document, demo=False, cache=None):
    """Before/after one new document at one as-of date (both sides evaluated at as_of)."""
    sid = f"ingest:{document['doc_id']}@{as_of}"
    title = f"New document {document['doc_id']}" + (f": {document['title']}" if document.get("title") else "")
    before = [r for r in base_rules if r.get("unit") != document["doc_id"]]
    after = before + list(new_rules)
    tags = (f"without:{document['doc_id']}", f"with:{document['doc_id']}")
    return source(sid, "ingest", title, before, after, addresses, as_of, as_of, cache, document, demo, tags)


def ingested_documents(rules):
    """Rules from an ingested document already in I2 (origin 'ingested'; the real hour-16 path), by document."""
    docs = {}
    for r in rules:
        if r.get("origin") == "ingested":
            docs.setdefault(r.get("unit") or r.get("source_doc_id"), []).append(r)
    return docs


def assemble(sources, addresses, as_of):
    """Sources -> the out/changes.full.json content."""
    by_addr = {}
    meta = {}
    for sid, m, changes in sorted(sources, key=lambda s: s[0]):
        meta[sid] = m
        for aid, ch in changes.items():
            by_addr.setdefault(aid, []).append({"source": sid, "kind": m["kind"], "title": m["title"],
                                                "before_as_of": m["before"]["as_of"],
                                                "after_as_of": m["after"]["as_of"],
                                                "demo_label": m["demo_label"], "changes": ch})
    return {
        "_comment": "Per-address diff (docs/ARCHITECTURE.md D, I6). Generated by make build / make demo-change; do not edit.",
        "not_legal_advice": True, "as_of": as_of,
        "sources": meta,
        "addresses": {aid: {"label": label(addresses[aid]), "jurisdictions": addresses[aid]["jurisdictions"],
                            "entries": entries}
                      for aid, entries in sorted(by_addr.items())},
    }


def label(rec):
    i = rec["input"]
    street = " ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in i["street_address"].split())
    return f"{street}, {rec.get('legal_city') or rec['postal_city']}, {i['state']}"


def build_sources(rules, addresses, as_of, base_full=None):
    """Everything make build precomputes: the as_of tests, each rule end date (effective.until) ±1 day, each
    rule start date (effective.from, from a year before as_of) not already inside one of those, plus any
    ingested document already in I2."""
    cache = {("base", as_of): base_full} if base_full is not None else {}
    out = date_sources(rules, addresses, cache)
    out += until_sources(rules, addresses, cache, skip={sid for sid, _, _ in out})
    out += start_sources(rules, addresses, as_of, cache,
                         covered=[(m["before"]["as_of"], m["after"]["as_of"]) for _, m, _ in out])
    for doc_id, new in sorted(ingested_documents(rules).items()):
        base = [r for r in rules if r.get("unit") != doc_id]
        out.append(ingest_source(base, new, addresses, as_of, {"doc_id": doc_id}, cache=cache))
    return out


def dump(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def add_day(d, n=1):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()
