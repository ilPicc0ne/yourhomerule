"""I6 tests (make test): the per-address diff, its agreement with changes.json, J3, the demo-change path.

Runs against the committed I2/I3/I8 files; writes only to temp dirs. The ingest cases use a test-only rule
built in memory from an existing Cambridge record (never written to out/ or outputs/): they test the diff
mechanics, not any extraction.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from engine import build as B, demo_change as DC, diff as D, facts as F, rules as R
from extract import changes as CH

AS_OF = "2026-10-01"
RULES = R.load()
BY_ID = {r["id"]: r for r in RULES}
ADDR = F.load()
FINDINGS = R.load_findings()
_BUILT = {}


def built():
    """One build into a temp dir: (changes.json, changes.full.json)."""
    if not _BUILT:
        d = Path(tempfile.mkdtemp())
        B.run(AS_OF, out_dir=d, outputs_dir=d, quiet=True)
        _BUILT["v"] = (json.loads((d / "changes.json").read_text()), json.loads((d / "changes.full.json").read_text()))
    return _BUILT["v"]


def test_rule(eff_from="2027-03-01", unit="XTEST"):
    """A test-only ingested rule: a copy of a Cambridge record under a new ID, starting at eff_from."""
    src = next(r for r in RULES if r["jurisdiction_id"] == "MA-CAMBRIDGE" and r["scored"])
    r = copy.deepcopy(src)
    r.update(id="MA-CAMBRIDGE-TEST-" + unit, unit=unit, origin="ingested", category="application_screening_fees",
             eff={"from": eff_from, "until": None, "precision": "day", "derived": None},
             events=[{"kind": "effective", "date": eff_from, "relative_rule": "none", "n": None}])
    return r


def mapped(test_id):
    t = next(t for t in D.change_tests() if t["test_id"] == test_id)
    return t, [i for k in t["rule_ids"] for i in CH.map_key_id(k, RULES, FINDINGS)[0]]


def source_changes(full, sid, ids):
    """address -> changes of the given rules in one source, from changes.full.json."""
    out = {}
    for aid, rec in full["addresses"].items():
        for e in rec["entries"]:
            if e["source"] == sid:
                ch = [c for c in e["changes"] if c["team_rule_id"] in ids]
                if ch:
                    out[aid] = ch
    return out


class Diff(unittest.TestCase):
    def test_diff_rows_kinds(self):
        row = lambda rid, res, flag=False: {"team_rule_id": rid, "result": res, "conflict_flag": flag,
                                            "explanation": "x", "scored": True}
        rid = RULES[0]["id"]
        rid2 = RULES[1]["id"]
        self.assertEqual(D.diff_rows([row(rid, "applies")], [row(rid, "applies")], BY_ID), [])
        ch = D.diff_rows([row(rid, "not_yet_effective")], [row(rid, "applies"), row(rid2, "unknown")], BY_ID)
        self.assertEqual([(c["team_rule_id"], c["change"]) for c in ch], sorted([(rid, "changed"), (rid2, "added")]))
        gone = D.diff_rows([row(rid, "applies", True)], [], BY_ID)[0]
        self.assertEqual((gone["change"], gone["after"]), ("removed", None))
        flag = D.diff_rows([row(rid, "applies")], [row(rid, "applies", True)], BY_ID)[0]
        self.assertTrue(flag["conflict_flag_changed"])
        self.assertFalse(flag["result_changed"])
        for k in ("title", "citation", "requirement_quote", "source_url", "effective_from"):
            self.assertIn(k, flag)

    def test_shape_and_determinism(self):
        _, full = built()
        self.assertTrue(full["not_legal_advice"])
        self.assertEqual(full["as_of"], AS_OF)
        self.assertEqual(sorted(full["sources"]), ["asof:2017-09-24..2017-09-26", "asof:2024-10-07..2024-10-09",
                                                   "asof:2025-10-14..2025-10-16", "asof:2025-12-31..2026-01-02",
                                                   "asof:2026-02-28..2026-03-02", "asof:2026-04-30..2026-05-02",
                                                   "asof:2026-06-08..2026-06-10", "asof:2026-10-01..2027-07-02",
                                                   "asof:2029-12-31..2030-01-02"])   # T1, T3, rule end and start dates
        d = Path(tempfile.mkdtemp())
        B.run(AS_OF, out_dir=d, outputs_dir=d, quiet=True)
        self.assertEqual(json.loads((d / "changes.full.json").read_text()), full)
        for aid, rec in full["addresses"].items():
            self.assertTrue(rec["entries"], aid)
            for e in rec["entries"]:
                self.assertIn(aid, full["sources"][e["source"]]["affected_address_ids"])

    def test_j3_hoboken_fair_act(self):
        _, full = built()
        e = next(e for e in full["addresses"]["A0256"]["entries"] if e["source"] == "asof:2026-10-01..2027-07-02")
        c = next(c for c in e["changes"] if c["team_rule_id"] == "NJ-ALG-56:9-23")
        self.assertEqual((c["before"]["result"], c["after"]["result"]), ("not_yet_effective", "applies"))
        self.assertTrue(c["before"]["conflict_flag"] and c["after"]["conflict_flag"])      # flagged, never decided
        self.assertEqual(c["effective_from"], "2027-07-01")
        self.assertTrue(c["requirement_quote"] and c["source_url"].startswith("https://"))
        self.assertEqual(full["addresses"]["A0256"]["label"], "327 Jackson St, Hoboken, NJ")


class AgreesWithChangesJson(unittest.TestCase):
    """changes.json (extract/changes.py) and the diff come from the same engine evaluation; they must agree."""

    def test_t1_t3_affected_and_flags(self):
        ch, full = built()
        for tid in ("T1", "T3"):
            t, ids = mapped(tid)
            got = source_changes(full, f"asof:{t['as_of_before']}..{t['as_of_after']}", ids)
            affected = sorted(a for a, cs in got.items() if any(c["result_changed"] for c in cs))
            self.assertEqual(affected, ch[tid]["affected_address_ids"], tid)
            flagged = sorted(a for a, cs in got.items() if any((c["after"] or {}).get("conflict_flag") for c in cs))
            self.assertEqual(flagged, ch[tid]["conflict_flag_address_ids"], tid)

    def test_t2_is_the_before_side(self):
        """T2 is a boundary at 2026-10-01, not a change: the diff's before side shows the same applies set."""
        ch, _ = built()
        t, ids = mapped("T2")
        now = B.build_lookups(RULES, ADDR, t["as_of"])
        applies = sorted(a for a, rows in now.items() if any(r["team_rule_id"] in ids and r["result"] == "applies"
                                                             for r in rows))
        self.assertEqual(applies, ch["T2"]["affected_address_ids"])

    def test_t4_pending_never_changes_by_date(self):
        ch, full = built()
        _, ids = mapped("T4")
        for sid in full["sources"]:
            self.assertEqual(source_changes(full, sid, ids), {}, sid)       # pending stays pending: no flip to law
        self.assertEqual(len(ch["T4"]["affected_address_ids"]), 110)

    def test_t5_no_rent_cap_change_in_ma(self):
        ch, full = built()
        self.assertEqual(ch["T5"]["affected_address_ids"], [])
        for aid, rec in full["addresses"].items():
            if rec["jurisdictions"]["state"] == "MA":
                for e in rec["entries"]:
                    self.assertFalse([c for c in e["changes"] if c["category"] == "rent_increase_limits"], aid)

    def test_t6_ingest_agrees(self):
        """Ingest mechanics with a test-only rule: changes.py's T6 set == the diff at the same date."""
        new = test_rule()
        rules = RULES + [new]
        date = D.add_day(new["eff"]["from"])
        facts = {a: F.address_facts(r) for a, r in ADDR.items()}
        t6 = CH.run_tests([{"test_id": "T6", "type": "ingest", "rules_before": RULES, "rules_after": rules,
                            "dates": [date], "effective": new["eff"]["from"]}],
                          RULES, FINDINGS, sorted(ADDR), B.E.evaluate, lambda a: facts[a])["T6"]
        _, meta, changes = D.ingest_source(RULES, [new], ADDR, date, {"doc_id": "XTEST"})
        affected = sorted(a for a, cs in changes.items() if any(c["result_changed"] for c in cs))
        self.assertTrue(affected)
        self.assertEqual(affected, t6["affected_address_ids"])


class Until(unittest.TestCase):
    """Rule end dates (effective.until, sunsets and repeals) are compared like start dates (issue #69)."""

    def test_until_dates_from_rules(self):
        dates = D.until_dates(RULES)
        self.assertEqual(dates["2030-01-01"], ["CA-EVICT-1946.2", "CA-RENT-1947.12"])
        self.assertEqual(sorted(dates), sorted({r["eff"]["until"] for r in RULES if r["eff"].get("until")}))

    def test_each_until_is_a_source(self):
        _, full = built()
        for until, ids in D.until_dates(RULES).items():
            sid = f"asof:{D.add_day(until, -1)}..{D.add_day(until)}"
            self.assertIn(sid, full["sources"])
            meta = full["sources"][sid]
            self.assertEqual((meta["kind"], meta["before"]["as_of"], meta["after"]["as_of"]),
                             ("as_of", D.add_day(until, -1), D.add_day(until)))
            self.assertEqual(meta["ending_rule_ids"], ids)

    def test_ca_sunset_removes_both_rules(self):
        _, full = built()
        sid = "asof:2029-12-31..2030-01-02"
        meta = full["sources"][sid]
        self.assertEqual(meta["rule_ids"], ["CA-EVICT-1946.2", "CA-RENT-1947.12"])
        ch = source_changes(full, sid, set(meta["rule_ids"]))
        self.assertEqual(sorted(ch), meta["affected_address_ids"])
        for aid, cs in ch.items():
            self.assertEqual(full["addresses"][aid]["jurisdictions"]["state"], "CA", aid)
            for c in cs:
                self.assertEqual((c["change"], c["after"], c["effective_until"]), ("removed", None, "2030-01-01"))

    def test_no_duplicate_with_test_sources(self):
        rules = copy.deepcopy(RULES)
        r = next(r for r in rules if r["id"] == "CA-ALG-16729")
        r["eff"] = {**r["eff"], "until": "2026-01-01"}                   # same window as T1
        sids = [s for s, _, _ in D.until_sources(rules, {}, skip={"asof:2025-12-31..2026-01-02"})]
        self.assertNotIn("asof:2025-12-31..2026-01-02", sids)
        self.assertIn("asof:2029-12-31..2030-01-02", sids)


class Starts(unittest.TestCase):
    """#117: a law starting gets its own window, unless an earlier window (a brief test, an end date) spans it."""
    @classmethod
    def setUpClass(cls):
        cls.srcs = D.build_sources(RULES, ADDR, AS_OF)
        cls.by_id = {sid: (m, ch) for sid, m, ch in cls.srcs}

    def test_berkeley_ban_has_its_own_entry(self):
        m, ch = self.by_id["asof:2026-02-28..2026-03-02"]
        self.assertIn("CA-BERKELEY-ALG-13.63.030", m["starting_rule_ids"])
        self.assertIn("CA-BERKELEY-ALG-13.63.030", {c["team_rule_id"] for c in ch["A0373"]})

    def test_no_window_inside_an_earlier_one(self):
        tests = [(m["before"]["as_of"], m["after"]["as_of"]) for _, m, _ in self.srcs if m.get("test_id")]
        for sid, m, _ in self.srcs:
            if "starting_rule_ids" in m:
                frm = D.add_day(m["before"]["as_of"])
                self.assertFalse(any(b < frm <= a for b, a in tests), sid)
        self.assertNotIn("asof:2027-06-30..2027-07-02", self.by_id)      # FAIR Act: inside T3


class DemoChange(unittest.TestCase):
    def test_demo_source_labelled_and_today(self):
        new = test_rule()
        full, (sid, meta, changes) = DC.apply([new], {"doc_id": "XTEST", "fictional": True}, AS_OF, True,
                                              addresses=ADDR)
        self.assertEqual(sid, "ingest:XTEST@2026-10-01")
        self.assertEqual(meta["demo_label"], "Demo: fictional ordinance")
        self.assertIn("A0010", changes)                                  # 134 Oxford St, Cambridge
        c = changes["A0010"][0]
        self.assertEqual((c["change"], c["before"], c["after"]["result"]), ("added", None, "not_yet_effective"))
        e = next(e for e in full["addresses"]["A0010"]["entries"] if e["source"] == sid)
        self.assertEqual(e["demo_label"], "Demo: fictional ordinance")
        self.assertFalse([a for a in changes if ADDR[a]["jurisdictions"].get("city") != "MA-CAMBRIDGE"])
        self.assertIn("asof:2026-10-01..2027-07-02", full["sources"])     # the build's sources stay

    def test_fixture_is_fictional(self):
        self.assertTrue(DC.is_fictional(DC.DEFAULT_DOC))


if __name__ == "__main__":
    unittest.main()
