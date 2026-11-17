"""Hyper Protocol 0.2-draft task-record export, pinned at draft.3."""
from pathlib import Path
import hashlib
import json


def export_bundle(dossier, policy, result, receipt, out):
    from plan_review import policy_for
    policy = policy_for(policy, result['review_object'])
    out = Path(out)
    stamp = receipt["ended_at"]
    refs = lambda ids: [{"asset_id": i, "version": "1"} for i in ids]
    pref = [{"id": "hyper.quality", "version": policy["version"]}]
    assets = []
    for name in ("dossier.json", "policy.json", "result.json", "report.md", "receipt.json"):
        raw = (out / name).read_bytes()
        assets.append({"asset_id": name, "version": "1", "asset_type": "review_artifact",
                       "nature": "run_log" if name == "receipt.json" else "derived", "source": "local review execution",
                       "locator": name, "sha256": hashlib.sha256(raw).hexdigest(), "subject_scope": dossier["product"]["id"],
                       "usage_scope": "internal review", "availability": "available", "snapshot_at": stamp,
                       "derived_from": [], "content": None, "extensions": {}})
    for eid, e in result["evidence_checks"].items():
        assets.append({"asset_id": eid, "version": "1", "asset_type": e["kind"],
                       "nature": "synthetic" if e["provenance"] == "synthetic" else "source", "source": e["locator"],
                       "locator": receipt.get("source_locations", {}).get(eid, e["path"]), "sha256": e["sha256"], "subject_scope": e["product_version"],
                       "usage_scope": "internal review snapshot; no new redistribution rights", "availability": "available" if e["usable"] else "not_checked",
                       "snapshot_at": stamp, "derived_from": [], "content": e["quote"], "extensions": {"provenance": e["provenance"], "semantic_review": e["semantic_status"]}})
    authorization = {"status": "granted", "basis": "用户请求建立并试评本地品控harness", "scope": ["compute_local_review", "read_local_evidence", "write_local_report"], "checked_at": stamp}
    rules = [{"rule_id": g["id"], "kind": "hard_gate", "when": dossier["stage"], "requirement": g["name"],
              "rationale": "支撑当前阶段的可核对价值与限制", "evidence_required": ["档案字段与本地检查结果" if g.get('computed') else "当前适用的证据及评议"], "evaluation_method": "deterministic" if g.get('computed') else "mixed",
              "positive_example": "证据支持且条件满足", "counterexample": "文档自报通过替代真实结果", "missing_behavior": "保留unknown并限制相关资格"} for g in result["gates"]]
    reviews = {k: {"status": r["status"], "scope": result['review_object'] + ' ' + (dossier['plan']['version'] if result['plan'] else dossier["product"]["version"]), "evidence_refs": refs(r["evidence_refs"]),
                   "reviewer_kind": r["reviewer_kind"], "reason": r["reason"]} for k, r in result["reviews"].items()}
    js = {"ELIGIBLE_FOR_OWNER_REVIEW": "meets_conditions", "PLAN_ELIGIBLE_FOR_OWNER_REVIEW": "meets_conditions", "NEEDS_EVIDENCE": "needs_evidence", "REWORK": "does_not_meet",
          "DOES_NOT_MEET": "does_not_meet", "STOP_EXISTING_DECISION": "does_not_meet"}[result["verdict"]]
    gaps = [{"code": "EVIDENCE_MISSING", "description": g["name"] + ": " + g["reason"],
             "affected_actions": [dossier["stage"]], "next_action": "补充该项证据后创建新评审"} for g in result["gates"] if g["status"] == "unknown"]
    return {
        "protocol_version": "0.2-draft", "bundle_id": dossier["product"]["id"] + "-" + result['review_object'] + "-" + dossier["as_of"],
        "nature": "synthetic_example" if dossier["purpose"] == "synthetic" else "task_record",
        "scenario": {"scenario_id": dossier["product"]["id"] + "-quality", "subjects": [dossier["product"]["name"]],
                     "problem": "当前证据是否支持阶段资格和资源请求", "goal": "交付可追溯候选评审；不执行上线与资源分配", "deliverables": ["report.md", "result.json"],
                     "constraints": ["规则仍为试行版", "预算资格与评分分离"], "acceptance_level": "draft_output", "required_reviews": [], "current_state": "deliver", "extensions": {}},
        "policy_packs": [{"policy_id": "hyper.quality", "version": policy["version"], "status": "draft", "adoption": "selected_for_task",
                          "maintainer": "product owner", "selection_basis": "本轮用户明确请求三层严格评审制度", "scope": {"subjects": [dossier["product"]["profile"]], "tasks": [dossier["stage"]], "conditions": ["证据可回查"], "exclusions": ["实际拨款与发布"]},
                          "goals": ["证据约束评分", "现实资源品控"], "priorities": ["硬门槛优先于总分", "未知与失败分开"], "rules": rules,
                          "quality_dimensions": [{"dimension_id": m["id"], "criterion": m["name"]} for m in policy["metrics"]], "preferences": [],
                          "decision_authority": {"automated_scope": ["compute_recommendation"], "reserved_decisions": ["release", "funding", "relationship_use"]},
                          "revisions": [policy["version"] + " provisional policy; see CHANGELOG.md"], "extensions": {"upstream_commit": policy["protocol_commit"]}}],
        "capabilities": [{"capability_id": "hyper.quality.review", "version": receipt["harness_version"], "action": "compute_local_review", "inputs": ["dossier.json", "policy.json"],
                          "outputs": ["result.json", "report.md"], "preconditions": ["输入结构有效"], "policy_refs": pref, "authorization": authorization,
                          "side_effects": ["创建新的本地运行目录"], "implementation": "Python standard library", "limits": result["limits"],
                          "failure_and_recovery": "保留输入，修复后写新运行目录", "completion_conditions": ["输出报告和回执"], "extensions": {}}],
        "assets": assets,
        "decisions": [{"decision_id": "quality-decision", "subject_refs": refs(["dossier.json"]), "policy_refs": pref, "judgment_status": js,
                       "scope": result['review_object'] + ' ' + result['decision_scope'] + " 候选资格；非上线或现实拨款授权", "rationale": result["verdict"],
                       "evidence_refs": refs(list(result["evidence_checks"])),
                       "rule_checks": [{"rule_id": g["id"], "result": g["status"], "evidence_refs": refs(g["evidence_refs"] or (["dossier.json","result.json"] if g.get('computed') else [])), "reason": g["reason"]} for g in result["gates"]],
                       "reviews": reviews, "unknowns": result["resource_reasons"], "next_actions": ["按缺口执行最小验证，再由用户决定资源"],
                       "extensions": {"hyper_quality": {"score": result["score"], "score_kind":result['score_kind'], "scorecards":result['scorecards'], "decision_scope":result['decision_scope'], "coverage": result["coverage"], "resource_status": result["resource_status"]}}}],
        "runs": [{"run_id": "review-run", "capability_ref": {"id": "hyper.quality.review", "version": receipt["harness_version"]}, "policy_refs": pref,
                  "execution_status": "succeeded", "executor": "local Python", "implementation_version": receipt["harness_version"], "authorization_snapshot": authorization,
                  "input_refs": refs(["dossier.json", "policy.json"]), "output_refs": refs(["result.json", "report.md"]), "runtime_evidence_refs": refs(["receipt.json"]),
                  "started_at": receipt["started_at"], "ended_at": stamp, "failure": None, "extensions": {}}],
        "delivery": {"status": "completed", "scope": "候选评审已生成；被评产品未因此获批", "artifact_refs": refs(["report.md", "result.json"]), "decision_refs": ["quality-decision"],
                     "blocking_gaps": [], "remaining_items": gaps, "claims": [], "next_actions": ["人工校准评分与补充业务证据"]},
        "extensions": {"hyper_quality": {"policy_sha256": result["policy_sha256"], "dossier_sha256": result["dossier_sha256"], "calibration": result["calibration"]}}
    }
