"""Minimal build metadata for public checkouts; original starter inputs take precedence."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STARTER = ROOT / "data" / "realpage-starter"
BUNDLE = ROOT / "out" / "build_inputs.json"
TEST_FIELDS = {"test_id", "title", "type", "rule_ids", "as_of", "as_of_before", "as_of_after"}


def bundled():
    if not BUNDLE.exists():
        raise FileNotFoundError("Build requires out/build_inputs.json or the RealPage starter pack at data/realpage-starter/")
    data = json.loads(BUNDLE.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported build_inputs.json schema_version")
    return data


def corpus_doc_ids():
    manifest = STARTER / "corpus" / "corpus_manifest.csv"
    if manifest.exists():
        with manifest.open(encoding="utf-8") as source:
            return {row["doc_id"] for row in csv.DictReader(source)}
    return set(bundled()["corpus_doc_ids"])


def change_tests():
    path = STARTER / "dev" / "change_tests.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return bundled()["change_tests"]


def main():
    # Never silently refresh from the old bundle when the source pack is missing.
    for path in (STARTER / "corpus" / "corpus_manifest.csv", STARTER / "dev" / "change_tests.json"):
        if not path.exists():
            raise FileNotFoundError(f"Refresh requires the original starter pack: {path}")
    data = {"schema_version": 1,
            "description": "Build metadata only; no corpus text, expected answers or address data. Refresh from the starter pack with python3 -m engine.build_inputs.",
            "corpus_doc_ids": sorted(corpus_doc_ids()),
            "change_tests": [{k: v for k, v in t.items() if k in TEST_FIELDS} for t in change_tests()]}
    BUNDLE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
