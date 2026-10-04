"""Engine tests (make test): adapter, determinism, guards on lookups.json, boundaries, the PRD journeys.

Runs against the committed I2/I3/I8 files; writes only to a temp dir.
"""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from engine import build as B, evaluate as E, explain as X, facts as F, rules as R
from extract import compile as C

AS_OF = "2026-10-01"
_CACHE = {}


def built(as_of=AS_OF):
    """(lookups.json content, full rows) for one as-of, built once per test run into a temp dir."""
    if as_of not in _CACHE:
        d = Path(tempfile.mkdtemp())
        full = B.run(as_of, out_dir=d, outputs_dir=d, with_changes=(as_of == AS_OF), quiet=True)
        _CACHE[as_of] = (json.loads((d / "lookups.json").read_text()), full, d)
    return _CACHE[as_of]


def rows(aid, as_of=AS_OF):
    return {r["team_rule_id"]: r for r in built(as_of)[0]["lookups"][aid]}


RULES = R.load()
BY_ID = {r["id"]: r for r in RULES}
ADDR = F.load()


class Adapter(unittest.TestCase):
    def test_from_node_inverts_to_node(self):
        for c in json.loads((R.OUT / "rules.compiled.json").read_text()):
            for key in ("applies_if", "exempt_if"):
                self.assertEqual(C.to_node(R.from_node(c[key])), c[key], (c["team_rule_id"], key))

    def test_dates_from_compiled_effective(self):
        for c in json.loads((R.OUT / "rules.compiled.json").read_text()):
            r = BY_ID[c["team_rule_id"]]
            self.assertEqual(r["eff"], c["effective"])
            self.assertEqual(E.start_date(r)[0], c["effective"]["from"])

    def test_bans_on_local_rules_detected(self):
        bars = {r["id"] for r in RULES if r["effect"] == "bars_or_limits_local_rules"}
        self.assertEqual(bars, {"MA-RENT-40P", "NJ-RENT-2A:42-84.5"})

    def test_i3_facts(self):
        f = F.address_facts(ADDR["A0016"])
        self.assertEqual(f["address.city"].values, ["San Francisco, CA"])
        self.assertEqual(f["address.state"].values, ["CA"])
        self.assertEqual((f["built"].lo, f["built"].hi), ("1926-01-01", "1926-12-31"))
        self.assertEqual((f["units"].lo, f["units"].hi), (21, 21))
        self.assertNotIn("owner_occupied", f)            # null in I3 -> missing -> unknown
        self.assertIn("year_built", f["built"].source)    # explanations cite the I3 source
        self.assertNotIn("subsidised", f)
        dorchester = next(a for a in ADDR.values() if a["postal_city"] == "Dorchester")
        self.assertEqual(F.address_facts(dorchester)["address.city"].values, ["Boston, MA"])

    def test_legacy_subsidy_assumption_is_unknown(self):
        for source, names in [("assumption", []), ("use_code", ["no_recorded_affordability_restriction"])]:
            with self.subTest(source=source, names=names):
                rec = copy.deepcopy(ADDR["A0016"])
                rec["facts"]["subsidised"] = False
                rec["source"]["subsidised"] = source
                rec["assumptions"] = names
                self.assertNotIn("subsidised", F.address_facts(rec))

    def test_explicit_subsidy_evidence_preserved(self):
        for value in (True, False):
            with self.subTest(value=value):
                rec = copy.deepcopy(ADDR["A0016"])
                rec["facts"]["subsidised"] = value
                rec["source"]["subsidised"] = "use_code"
                rec["source_detail"]["subsidised"] = "Explicit subsidy status in test source"
                rec["assumptions"] = []
                fact = F.address_facts(rec)["subsidised"]
                self.assertEqual(fact.values, [value])
                self.assertIsNone(fact.assumption)

    def test_missing_subsidy_changes_coverage_only_when_relevant(self):
        for aid, rid in [("A0023", "CA-RENT-1947.12"), ("A0036", "MA-BOSTON-EVICT-10-11.7")]:
            with self.subTest(address=aid, rule=rid):
                rec = copy.deepcopy(ADDR[aid])
                result = E.evaluate(RULES, F.address_facts(rec), AS_OF)
                self.assertEqual(result[rid]["result"], "unknown")
                explained = B.evaluate_address(RULES, rec, AS_OF, BY_ID)
                row = next(r for r in explained if r["team_rule_id"] == rid)
                self.assertIn("subsidised", row["missing"])
                self.assertIn("city housing department", row["explanation"])
                rec["facts"]["subsidised"] = False
                rec["source"]["subsidised"] = "use_code"
                rec["assumptions"] = []
                supported = E.evaluate(RULES, F.address_facts(rec), AS_OF)
                self.assertEqual(supported[rid]["result"], "applies")
                # The deposit rule is independent of this missing fact.
                deposit = "CA-DEP-1950.5" if aid == "A0023" else "MA-DEP-186"
                self.assertEqual(result[deposit]["result"], supported[deposit]["result"])

    def test_subsidised_housing_reads_as_apartment(self):
        rec = next(a for a in ADDR.values() if a["facts"]["use_class"] == "subsidised_housing")
        f = F.address_facts(rec)
        self.assertEqual(f["use_class"].values, ["apartment"])
        self.assertEqual(f["subsidised"].values, [True])


class Determinism(unittest.TestCase):
    def test_two_runs_byte_identical(self):
        outs = []
        for _ in range(2):
            d = Path(tempfile.mkdtemp())
            B.run(AS_OF, out_dir=d, outputs_dir=d, quiet=True)
            outs.append({n: (d / n).read_bytes() for n in ("lookups.json", "changes.json", "lookups.full.json")})
        self.assertEqual(outs[0], outs[1])


class Guards(unittest.TestCase):
    """Acceptance guards on the scored file."""

    def test_rule_jurisdictions_exist(self):
        for r in RULES:
            self.assertIn(r["jurisdiction_id"], R.JUR, r["id"])

    def test_every_sample_city_has_listed_rules(self):
        lk = built()[0]["lookups"]
        cities = {a["jurisdictions"]["city"] for a in ADDR.values()}
        self.assertEqual(len(cities), 9)       # Santa Ana has no sample addresses
        for city in cities:
            n = sum(len(lk[a]) for a, rec in ADDR.items() if rec["jurisdictions"]["city"] == city)
            self.assertGreater(n, 0, city)
            if any(r["jurisdiction_id"] == city for r in RULES):
                self.assertTrue(any(BY_ID[x["team_rule_id"]]["jurisdiction_id"] == city
                                    for a, rec in ADDR.items() if rec["jurisdictions"]["city"] == city
                                    for x in lk[a]), city)

    def test_all_500_template_fields_only(self):
        doc = built()[0]
        self.assertEqual(set(doc), {"as_of", "lookups"})
        self.assertEqual(doc["as_of"], AS_OF)
        self.assertEqual(sorted(doc["lookups"]), sorted(ADDR))
        self.assertEqual(len(doc["lookups"]), 500)
        scored = {r["team_rule_id"] for r in json.loads((R.OUT / "rules.json").read_text())["rules"]}
        for aid, rs in doc["lookups"].items():
            for x in rs:
                self.assertEqual(set(x), set(B.TEMPLATE_FIELDS))
                self.assertIn(x["result"], B.LISTED)
                self.assertIsInstance(x["conflict_flag"], bool)
                self.assertIn(x["team_rule_id"], scored)

    def test_explanation_wording(self):
        bad = re.compile(r"\b(compliant|illegal|you should|legal advice)\b", re.I)
        for rs in built()[0]["lookups"].values():
            for x in rs:
                self.assertTrue(x["explanation"].strip(), x)
                self.assertIsNone(bad.search(x["explanation"]), x["explanation"])
                self.assertLessEqual(len(x["explanation"]), 600, x["explanation"])

    def test_unknown_never_omitted(self):
        """Coverage unknown for an in-force rule in the address's stack -> listed (unknown, or superseded
        when a local rule that covers the unit governs), never dropped."""
        lk = built()[0]["lookups"]
        for aid, rec in ADDR.items():
            facts = F.address_facts(rec)
            city, state = facts["address.city"].values[0], facts["address.state"].values[0]
            got = {x["team_rule_id"]: x["result"] for x in lk[aid]}
            for r in RULES:
                if r["jurisdiction"] not in (state, city) or not r["scored"] \
                        or r["effect"] == "bars_or_limits_local_rules" or E.status(r, AS_OF)[0] != "in_force":
                    continue
                stack = [o for o in RULES if o["jurisdiction"] in (state, city)]
                cov = E.coverage(r, E.Ctx(facts, AS_OF, E.local_refs(stack, city, facts, AS_OF)))
                if cov is None:
                    self.assertIn(got.get(r["id"]), ("unknown", "superseded"), (aid, r["id"]))
                elif cov is True:
                    self.assertIn(got.get(r["id"]), ("applies", "superseded", "unknown"), (aid, r["id"]))

    def test_superseded_pending_failed(self):
        for as_of in (AS_OF, "2027-07-02", "2030-01-02"):
            full = built(as_of)[1]
            for aid, rs in full.items():
                res = {x["team_rule_id"]: x for x in rs}
                for x in rs:
                    rule = BY_ID[x["team_rule_id"]]
                    if x["result"] == "superseded":
                        self.assertEqual(res.get(x["governed_by"], {}).get("result"), "applies", (aid, x))
                    if rule["document_status"] == "pending":
                        self.assertEqual(x["result"], "pending")
                    self.assertNotEqual(rule["document_status"], "failed")
                    until = rule["eff"]["until"]
                    self.assertTrue(until is None or until > as_of, (aid, x["team_rule_id"], as_of))
                    self.assertNotEqual(rule["effect"], "bars_or_limits_local_rules")


class Boundaries(unittest.TestCase):
    def test_on_effective_from_is_in_force(self):
        hob = "A0256"
        self.assertEqual(rows(hob, "2027-06-30")["NJ-ALG-56:9-23"]["result"], "not_yet_effective")
        self.assertEqual(rows(hob, "2027-07-01")["NJ-ALG-56:9-23"]["result"], "applies")

    def test_on_until_not_listed(self):
        sf = "A0016"
        self.assertEqual(rows(sf, "2029-12-31")["CA-RENT-1947.12"]["result"], "superseded")
        self.assertNotIn("CA-RENT-1947.12", rows(sf, "2030-01-01"))

    def test_t1_dates(self):
        ca = [a for a, r in ADDR.items() if r["jurisdictions"]["state"] == "CA"]
        for a in ca:
            self.assertEqual(rows(a, "2025-12-31")["CA-ALG-16729"]["result"], "not_yet_effective")
            self.assertEqual(rows(a, "2026-01-02")["CA-ALG-16729"]["result"], "applies")

    def test_month_precision_gate(self):
        r = copy.deepcopy(BY_ID["CA-ALG-16729"])
        r["eff"] = {"from": "2026-03-01", "until": None, "precision": "month", "derived": None}
        res = {"result": "applies", "governed_by": None}
        self.assertEqual(B.gate(r, res, "2026-03-15")[0]["result"], "unknown")
        self.assertEqual(B.gate(r, res, "2026-03-15")[1], {"in_effective_month": "March 2026"})
        self.assertEqual(B.gate(r, res, "2026-04-01")[0]["result"], "applies")

    def test_changes_json(self):
        ch = json.loads((built()[2] / "changes.json").read_text())
        self.assertEqual(sorted(ch), ["T1", "T2", "T3", "T4", "T5"])
        state = lambda s: sorted(a for a, r in ADDR.items() if r["jurisdictions"]["state"] == s)
        city = lambda c: sorted(a for a, r in ADDR.items() if r["jurisdictions"]["city"] == c)
        self.assertEqual(ch["T1"]["affected_address_ids"], state("CA"))
        self.assertEqual(ch["T2"]["affected_address_ids"], sorted(city("NJ-HOBOKEN") + city("NJ-JERSEY-CITY")))
        self.assertEqual(ch["T3"]["affected_address_ids"], state("NJ"))
        self.assertEqual(ch["T3"]["conflict_flag_address_ids"], sorted(city("NJ-HOBOKEN") + city("NJ-JERSEY-CITY")))
        self.assertEqual(ch["T4"]["affected_address_ids"], state("MA"))
        self.assertEqual(ch["T5"]["affected_address_ids"], [])
        for v in ch.values():
            self.assertEqual(set(v), {"affected_address_ids", "conflict_flag_address_ids", "notes"})


class ValueBranches(unittest.TestCase):
    """key_value_conditions: a branch whose condition is unknown never yields a flat value."""
    SMALL = {"kind": "all", "children": [
        {"kind": "fact", "fact": "owner_type", "op": "eq", "value": "natural_person"},
        {"kind": "fact", "fact": "units", "op": "le", "value": 4}]}

    def rule(self, *branches):
        r = copy.deepcopy(BY_ID["CA-DEP-1950.5"])
        r["key_value_conditions"] = [{"value": v, "when": w, "tenant_note": None} for v, w in branches]
        return r

    def run_rule(self, rule, aid):
        facts = F.address_facts(ADDR[aid])
        res = E.evaluate([rule], facts, AS_OF)[rule["id"]]
        return res, X.explain(rule, res, facts, AS_OF, {rule["id"]: rule})

    def test_open_branch_makes_value_conditional(self):
        # A0398: TIC building, units null after a CSV/use-code conflict, owner unknown
        res, text = self.run_rule(self.rule(("Two months' rent", self.SMALL)), "A0398")
        self.assertEqual(res["result"], "applies")
        self.assertIsInstance(res["value"], dict)
        self.assertEqual(res["value"]["conditional"][1], "Two months' rent")
        self.assertEqual(res["value"]["depends_on"], ["owner_type", "units"])
        self.assertIn("amount is not settled", text)
        self.assertIn("who owns the building", text)
        self.assertIn("the unit count", text)

    def test_decided_branches_stay_flat(self):
        r = self.rule(("Two months' rent", self.SMALL))
        res, text = self.run_rule(r, "A0016")          # 21 units: the branch is false whoever owns it
        self.assertEqual(res["value"], r["key_value"])
        self.assertNotIn("not settled", text)
        res, _ = self.run_rule(self.rule(("X", {"kind": "always"})), "A0398")
        self.assertEqual(res["value"], "X")

    def test_open_branch_before_true_one_is_conditional(self):
        res, _ = self.run_rule(self.rule(("Two months' rent", self.SMALL), ("X", {"kind": "always"})), "A0398")
        self.assertEqual(res["value"]["conditional"], ["X", "Two months' rent"])
        res, _ = self.run_rule(self.rule(("X", {"kind": "always"}), ("Two months' rent", self.SMALL)), "A0398")
        self.assertEqual(res["value"], "X")             # first true branch wins; later ones are never reached


class Journeys(unittest.TestCase):
    def test_j1_fillmore_sf_ordinance_applies_state_cap_superseded(self):
        r = rows("A0016")
        self.assertEqual(r["CA-SAN-FRANCISCO-RENT-37.3"]["result"], "applies")
        self.assertIn("1926", r["CA-SAN-FRANCISCO-RENT-37.3"]["explanation"])
        self.assertIn("June 13, 1979", r["CA-SAN-FRANCISCO-RENT-37.3"]["explanation"])
        self.assertEqual(r["CA-RENT-1947.12"]["result"], "superseded")
        full = {x["team_rule_id"]: x for x in built()[1]["A0016"]}
        self.assertEqual(full["CA-RENT-1947.12"]["governed_by"], "CA-SAN-FRANCISCO-RENT-37.3")

    def test_j2_sherman_grove_la_rso_unknown(self):
        r = rows("A0107")
        x = r["CA-LOS-ANGELES-RENT-151.06"]
        self.assertEqual(x["result"], "unknown")
        self.assertIn("1978", x["explanation"])
        self.assertIn("October 1, 1978", x["explanation"])
        self.assertIn("certificate-of-occupancy", x["explanation"])
        self.assertEqual(r["CA-RENT-1947.12"]["result"], "unknown")      # state cap: depends on the RSO

    def test_dorchester_lists_boston_rules(self):
        for aid, rec in ADDR.items():
            if rec["postal_city"] != "Dorchester":
                continue
            ids = set(rows(aid))
            self.assertTrue(any(i.startswith("MA-BOSTON-") for i in ids), aid)
            self.assertFalse(any(BY_ID[i]["category"] == "rent_increase_limits" and rows(aid)[i]["result"]
                                 in ("applies", "unknown", "superseded") for i in ids), aid)   # T5: no rent cap

    def test_j3_hoboken_fair_act(self):
        now, later = rows("A0256"), rows("A0256", "2027-07-02")
        self.assertEqual(now["NJ-ALG-56:9-23"]["result"], "not_yet_effective")
        self.assertTrue(now["NJ-ALG-56:9-23"]["conflict_flag"])
        self.assertEqual(later["NJ-ALG-56:9-23"]["result"], "applies")
        self.assertTrue(later["NJ-ALG-56:9-23"]["conflict_flag"])
        self.assertTrue(later["NJ-HOBOKEN-ALG-Hobokenordin"]["conflict_flag"])
        self.assertEqual(later["NJ-HOBOKEN-ALG-Hobokenordin"]["result"], "applies")   # flagged, not decided


class ScoredRules(unittest.TestCase):
    def test_source_doc_id_is_a_manifest_doc_or_null(self):
        from engine.build_inputs import corpus_doc_ids
        corpus = corpus_doc_ids()
        src = {r["team_rule_id"]: r for r in json.loads((R.OUT / "rules.json").read_text())["rules"]}
        out = json.loads((built()[2] / "rules.json").read_text())["rules"]
        self.assertEqual(sorted(src), sorted(r["team_rule_id"] for r in out))
        for r in out:
            d = src[r["team_rule_id"]]["source_doc_id"]
            self.assertEqual(r["source_doc_id"], d if d in corpus else None, r["team_rule_id"])
            self.assertEqual({k: v for k, v in r.items() if k != "source_doc_id"},
                             {k: v for k, v in src[r["team_rule_id"]].items() if k != "source_doc_id"})


if __name__ == "__main__":
    unittest.main()
