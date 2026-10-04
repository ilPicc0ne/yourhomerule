"""Engine CLI (interface I4): python -m engine.build --as-of 2026-10-01

Inputs: out/rules.compiled.json + out/rules.json + out/findings.json (I2, I8), out/addresses.resolved.json (I3).
Outputs (byte-deterministic: sorted keys and order, no timestamp but as_of):
- outputs/rules.json     out/rules.json for submission: source_doc_id null where the source isn't in the corpus manifest
- outputs/lookups.json   the template shape {as_of, lookups: {address_id: [{team_rule_id, result, explanation, conflict_flag}]}}
- outputs/changes.json   T1-T5 (T6 when an ingested document exists) via extract/changes.py, same evaluation
- out/lookups.full.json  the same results with confidence, missing facts, governed_by, conflict_with, value,
                         and the I8 findings per jurisdiction x category, for the web (ARCHITECTURE C)
- out/changes.full.json  the per-address diff (I6, engine/diff.py) for the change log and the alert email
- out/build_summary.json counts per city x result; the previous one is diffed on stdout

One evaluator (engine/evaluate.py, Dimitar's three-valued reference evaluator); this module only adapts its
inputs and words its outputs.
"""
import argparse
import datetime as dt
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from engine import evaluate as E, explain as X, facts as F, rules as R

ROOT = R.ROOT
OUTPUTS = ROOT / "outputs"
LISTED = ("applies", "unknown", "superseded", "not_yet_effective", "pending")
TEMPLATE_FIELDS = ("team_rule_id", "result", "explanation", "conflict_flag")


def _window_end(frm, precision):
    """Last day of the month/year a rule with that date precision takes effect in."""
    d = dt.date.fromisoformat(frm)
    if precision == "month":
        nxt = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        return (nxt - dt.timedelta(days=1)).isoformat(), f"{X.MONTHS[d.month - 1]} {d.year}"
    if precision == "year":
        return f"{d.year}-12-31", str(d.year)
    return None, None


def gate(rule, res, as_of):
    """Status gate on top of the evaluator (agreed on PR #30): a month/year-precision start date makes the
    whole month/year unknown ('takes effect during <month>'); before it not_yet_effective, after it normal."""
    eff = rule["eff"]
    if not eff.get("from") or eff.get("precision", "day") == "day" or rule["document_status"] != "enacted":
        return res, {}
    end, label = _window_end(eff["from"], eff["precision"])
    if eff["from"] <= as_of <= end and res["result"] in ("applies", "unknown", "superseded"):
        return {**res, "result": "unknown", "governed_by": None}, {"in_effective_month": label}
    return res, {}


def _trials(as_of):
    """Values to try for a missing building fact: one per way the law tends to split on it."""
    y = int(as_of[:4])
    return {"owner_occupied": [True, False], "subsidised": [True, False],
            "owner_type": ["individual", "corporation", "reit", "public"],
            "use_class": ["apartment", "condo", "co_op", "two_family", "single_family", "mixed_use"],
            "built": [{"from": f"{v}-01-01", "to": f"{v}-12-31"} for v in (1900, 1975, 1990, 2005, y - 1)],
            "units": [{"min": v, "max": v} for v in (1, 2, 3, 4, 5, 20, 100)]}


def deciding_facts(rules, rec, as_of, rows):
    """For each unknown row: the missing building facts that, answered alone, could change its result (the engine
    re-run with that fact set to each value it can take). `missing` keeps every unknown fact the evaluator met,
    including ones an and/or around them already settles (e.g. owner-occupied in a duplex-only exemption of a
    16-unit building); the page asks only about these."""
    unknown = [r for r in rows if r["result"] == "unknown"]
    trials = _trials(as_of)
    wanted = {m for r in unknown for m in r["missing"] if m in trials}
    results = {}
    for f in sorted(wanted):
        for v in trials[f]:
            r2 = copy.deepcopy(rec)
            r2["facts"][f] = v
            raw = E.evaluate(rules, F.address_facts(r2), as_of)
            results[(f, json.dumps(v))] = {rid: x["result"] for rid, x in raw.items()}
    for r in unknown:
        r["missing_deciding"] = sorted(
            m for m in r["missing"] if m in trials
            and any(results[(m, json.dumps(v))].get(r["team_rule_id"], "unknown") != "unknown" for v in trials[m]))
    return rows


def evaluate_address(rules, rec, as_of, rules_by_id):
    facts = F.address_facts(rec)
    raw = E.evaluate(rules, facts, as_of)
    city = facts["address.city"].values[0]
    stack = [r for r in rules if r["jurisdiction"] in (facts["address.state"].values[0], city)]
    refs = E.local_refs(stack, city, facts, as_of)
    rows = []
    for rid in sorted(raw):
        rule = rules_by_id[rid]
        res, flags = gate(rule, raw[rid], as_of)
        if res["result"] not in LISTED:
            continue
        # conflicts: flagged on the rule that may preempt and on the local rules it names; never decided
        rows.append({"rule": rule, "res": res, "flags": flags})
    flagged = {c for row in rows for c in row["res"]["conflict_with"]} | \
              {row["rule"]["id"] for row in rows if row["res"]["conflict_with"]}
    out = []
    for row in rows:
        rule, res = row["rule"], row["res"]
        conf = (rule.get("confidence") or 0.5) * facts["address.city"].confidence
        used = set(res["missing"]) | {k for k in ("built", "units") if _uses(rule, k)}
        for k in ("built", "units"):
            if k in used and k in facts and facts[k].confidence:
                conf *= facts[k].confidence
        out.append({
            "team_rule_id": rule["id"], "result": res["result"],
            "explanation": X.explain(rule, res, facts, as_of, rules_by_id, refs, row["flags"]),
            "conflict_flag": rule["id"] in flagged,
            "jurisdiction": rule["jurisdiction_id"], "category": rule["category"], "scored": rule["scored"],
            "confidence": round(conf, 3), "missing": res["missing"], "assumptions": res["assumptions"],
            "governed_by": res["governed_by"], "conflict_with": sorted(res["conflict_with"]),
            "value": res["value"], "flags": row["flags"], "invalid": res["invalid"],
        })
    return deciding_facts(rules, rec, as_of, out)


def _uses(rule, key):
    def walk(n):
        if n.get("kind") in ("all", "any", "not"):
            return any(walk(c) for c in n.get("children") or [])
        return n.get("fact") == key or (key == "built" and n.get("kind") == "age_years")
    return walk(rule["applies_if"]) or walk(rule["exempt_if"])


def build_lookups(rules, addresses, as_of):
    by_id = {r["id"]: r for r in rules}
    return {aid: evaluate_address(rules, addresses[aid], as_of, by_id) for aid in sorted(addresses)}


def lookups_json(full, as_of):
    """The scored file: only rules present in rules.json (a verbatim quote), only the template fields."""
    return {"as_of": as_of,
            "lookups": {aid: [{k: row[k] for k in TEMPLATE_FIELDS} for row in rows if row["scored"]]
                        for aid, rows in full.items()}}


def rules_json():
    """The scored rules.json: out/rules.json, with source_doc_id null for a source outside corpus_manifest.csv (the
    schema's doc_id field). Such a rule (an official text we saved, e.g. a city ordinance the manifest lists as link
    only) keeps its source_url and verbatim quote; it doesn't count toward the citation metric (organizers, 04.10.)."""
    from engine.build_inputs import corpus_doc_ids
    corpus = corpus_doc_ids()
    recs = json.loads((R.OUT / "rules.json").read_text(encoding="utf-8"))
    for r in recs["rules"]:
        if r.get("source_doc_id") not in corpus:
            r["source_doc_id"] = None
    return recs


def full_json(full, rules, addresses, findings, as_of):
    scored_rules = {r["id"]: {k: r[k] for k in ("jurisdiction_id", "category", "citation", "title", "source_url",
                                                "source_doc_id", "requirement_quote", "retrieved", "eff",
                                                "document_status", "key_value", "tenant_conditions", "scored",
                                                "confidence", "origin")}
                    for r in rules}
    fby = defaultdict(list)
    for f in findings:
        fby[f["jurisdiction"]].append({k: f.get(k) for k in ("category", "kind", "citation", "quote", "note",
                                                              "source_doc_ids", "url")})
    return {
        "as_of": as_of, "not_legal_advice": True,
        "_comment": "Engine results for the web (docs/ARCHITECTURE.md C, I4). Generated by make build; do not edit.",
        "rules": scored_rules,
        "findings": {j: sorted(v, key=lambda f: (f["category"], f["kind"], f["citation"] or "")) for j, v in sorted(fby.items())},
        "addresses": {aid: {"stack": addresses[aid]["stack"], "jurisdictions": addresses[aid]["jurisdictions"],
                            "facts": addresses[aid]["facts"], "assumptions": addresses[aid]["assumptions"],
                            "review": addresses[aid]["review"], "results": rows}
                      for aid, rows in full.items()},
    }


def changes(rules, findings, addresses):
    """changes.json via extract/changes.py, driven with I3 facts and the same evaluator."""
    from extract import changes as CH
    from engine.build_inputs import change_tests
    tests = change_tests()
    base = [r for r in rules if r["origin"] != "ingested"]
    ingested = [r for r in rules if r["origin"] == "ingested"]
    if ingested:    # T6: the hour-16 document, compared at the day after its effective date
        eff = min(r["eff"]["from"] or "9999-12-31" for r in ingested)
        tests.append({"test_id": "T6", "type": "ingest", "rules_before": base, "rules_after": rules,
                      "dates": [(dt.date.fromisoformat(eff) + dt.timedelta(days=1)).isoformat()], "effective": eff})
    facts = {a: F.address_facts(r) for a, r in addresses.items()}
    out = CH.run_tests(tests, base, findings, sorted(addresses), E.evaluate, lambda a: facts[a])
    return {t: {"affected_address_ids": v["affected_address_ids"],
                "conflict_flag_address_ids": v["conflict_flag_address_ids"], "notes": v["notes"]}
            for t, v in sorted(out.items())}


def summary(full, addresses):
    s = defaultdict(Counter)
    for aid, rows in full.items():
        city = addresses[aid]["jurisdictions"].get("city") or addresses[aid]["jurisdictions"]["state"]
        s[city]["addresses"] += 1
        for row in rows:
            if row["scored"]:
                s[city][row["result"]] += 1
                s[city]["conflict_flag"] += row["conflict_flag"]
    return {c: dict(sorted(v.items())) for c, v in sorted(s.items())}


def print_summary(cur, prev):
    cols = ["addresses", *LISTED, "conflict_flag"]
    print(f"{'city':<22}" + "".join(f"{c[:11]:>12}" for c in cols))
    for city, v in cur.items():
        line = f"{city:<22}"
        for c in cols:
            n = v.get(c, 0)
            d = n - (prev or {}).get(city, {}).get(c, 0) if prev is not None else 0
            line += f"{(f'{n} ({d:+d})' if d else str(n)):>12}"
        print(line)
    if prev is not None:
        drops = [(c, k, prev[c].get(k, 0), cur.get(c, {}).get(k, 0)) for c in prev for k in prev[c]
                 if prev[c].get(k, 0) and cur.get(c, {}).get(k, 0) <= prev[c][k] // 2]
        for c, k, a, b in drops:
            print(f"WARNING: {c} {k} {a} -> {b}")


def dump(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def run(as_of, out_dir=None, outputs_dir=None, with_changes=True, quiet=False):
    out_dir, outputs_dir = Path(out_dir or R.OUT), Path(outputs_dir or OUTPUTS)
    rules = R.load()
    findings = R.load_findings()
    addresses = F.load()
    full = build_lookups(rules, addresses, as_of)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (outputs_dir / "lookups.json").write_text(dump(lookups_json(full, as_of)), encoding="utf-8")
    (outputs_dir / "rules.json").write_text(json.dumps(rules_json(), indent=1, ensure_ascii=False),
                                             encoding="utf-8")      # out/rules.json's format
    (out_dir / "lookups.full.json").write_text(dump(full_json(full, rules, addresses, findings, as_of)), encoding="utf-8")
    if with_changes:
        (outputs_dir / "changes.json").write_text(dump(changes(rules, findings, addresses)), encoding="utf-8")
        from engine import diff as D     # I6: the per-address diff for the change log and the email
        srcs = D.build_sources(rules, addresses, as_of, base_full=full)
        (out_dir / "changes.full.json").write_text(D.dump(D.assemble(srcs, addresses, as_of)), encoding="utf-8")
    cur = summary(full, addresses)
    sp = out_dir / "build_summary.json"
    prev = json.loads(sp.read_text(encoding="utf-8"))["cities"] if sp.exists() else None
    sp.write_text(dump({"as_of": as_of, "cities": cur}), encoding="utf-8")
    if not quiet:
        print(f"as_of {as_of}: {len(full)} addresses, {sum(len(v) for v in full.values())} results")
        print_summary(cur, prev)
    return full


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--as-of", default="2026-10-01")
    p.add_argument("--no-changes", action="store_true")
    a = p.parse_args(argv)
    dt.date.fromisoformat(a.as_of)
    run(a.as_of, with_changes=not a.no_changes)


if __name__ == "__main__":
    sys.exit(main())
