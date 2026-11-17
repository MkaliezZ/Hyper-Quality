"""Run public synthetic regression cases. Private historical dossiers are excluded."""
import copy
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from harness import evaluate, export_report, read_json, write_json, calibrate, digest, VERSION
from test_harness import synthetic_fixture


def run(out):
    out = Path(out)
    if out.exists():
        raise ValueError("输出目录已存在；用新版本目录")
    out.mkdir(parents=True)
    policy = read_json(ROOT / "policy.json")
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (out / "unit-tests.txt").write_text(stream.getvalue(), encoding="utf-8")
    validator_path = ROOT / "vendor/hyper-protocol/tools/validate_bundle.py"
    spec = importlib.util.spec_from_file_location("hpvalidator", validator_path)
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    historical = []  # Private histories are not part of the public distribution.
    synthetic_root = out / "synthetic-inputs"
    synthetic_root.mkdir()
    base = synthetic_fixture(synthetic_root, policy)
    cases = []
    def add(name, mutate, expected):
        d = copy.deepcopy(base)
        mutate(d)
        write_json(synthetic_root / (name + ".json"), d)
        r = export_report(d, policy, out / "synthetic-results" / name, synthetic_root)
        errors = validator.validate_bundle(read_json(out / "synthetic-results" / name / "task-bundle.json"))
        cases.append({"id": name, "purpose": "synthetic", "expected": expected, "actual": r["verdict"], "matched": r["verdict"] == expected,
                      "score": r["score"], "resource_status": r["resource_status"], "protocol_errors": errors})
    add("complete-evidence", lambda d: None, "ELIGIBLE_FOR_OWNER_REVIEW")
    add("perfect-score-failed-rights", lambda d: d["gates"]["G_RIGHTS"].update(status="not_met"), "DOES_NOT_MEET")
    add("missing-demand", lambda d: d["gates"].pop("G_DEMAND"), "NEEDS_EVIDENCE")
    add("closed-project", lambda d: d["product"].update(lifecycle="closed"), "STOP_EXISTING_DECISION")
    add("weak-critical-layer", lambda d: [v.update(score=0) for k, v in d["ratings"].items() if k.startswith("J")], "DOES_NOT_MEET")
    add("unknown-cash", lambda d: d["bom"]["lines"][0]["per_quantity"]["cash"].update(high=None), "NEEDS_EVIDENCE")
    add("counterevidence", lambda d: d["claims"][0].update(counterevidence_refs=["counterevidence-a"]), "DOES_NOT_MEET")
    add("source-duplicates", lambda d: [e.update(independence_group="one-source") for e in d["evidence"]], "REWORK")
    write_json(out / "calibration.json", calibrate([], policy))
    passed = result.wasSuccessful() and all(x["matched"] and not x["protocol_errors"] for x in historical + cases)
    verification = {"version": VERSION, "checked_at": datetime.now(timezone.utc).isoformat(),
                    "engineering": {"status": "passed" if passed else "failed", "unit_tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                                    "behavior_scenarios": len(cases), "historical_replays": len(historical), "protocol_bundles": len(cases) + len(historical)},
                    "historical": historical, "synthetic": cases,
                    "reviews": {"domain": "not_run", "aesthetic": "not_run", "human_acceptance": "not_run", "real_world": "not_run"},
                    "ai_judge_calibration": "not_run_no_independent_human_labels", "parameter_business_validity": "not_established",
                    "source_hashes": {p.name: digest(p.read_bytes()) for p in [ROOT / n for n in ('harness.py','plan_review.py','templates.py','policy.json','protocol_adapter.py')]},
                    "limits": ["历史回放不是当前产品复测", "合成样例不是市场样本", "程序通过不证明AI语义判断正确", "未实际拨款/联系他人/部署产品"]}
    write_json(out / "verification.json", verification)
    lines = ["# Public product regression · " + VERSION, "", "Only synthetic fixtures are used. No private history or business calibration is included.", "", f"Tests: {result.testsRun}; scenarios: {len(cases)}; passed: {passed}.", "", "| Scenario | Expected | Actual | Matched |", "|---|---|---|---|"]
    lines += [f"| {c['id']} | {c['expected']} | {c['actual']} | {c['matched']} |" for c in cases]
    (out / "portfolio.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "tests": result.testsRun, "historical": historical, "synthetic_scenarios": len(cases)}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    raise SystemExit(run(ap.parse_args().out))
