# Validation scope / 验证范围

Release: **0.3.0**, public source, 2026-11-18. The policy remains provisional and not business-validated.

## Reproduce / 复现

```sh
python -m pip install -r requirements-validation.txt
python tools/eval_suite.py --out runtime/product-eval
python tools/plan_eval_suite.py --out runtime/plan-eval
python tools/demo.py --out runtime/demo
python tools/verify_bundle.py runtime/demo/product/task-bundle.json
python tools/verify_bundle.py runtime/demo/plan/task-bundle.json
python tools/verify_public_source.py
```

Use new directories for each run. Product eval includes unit tests and 8 behavioral cases. Plan eval contains 36 cases, including 5 expected invalid inputs and 31 bundle/replay checks. No private historical dossier is distributed or counted.

CI runs the same source on Ubuntu and Windows with Python 3.11 and 3.13. Consult the workflow result for the exact commit; the existence of this file is not proof that a run passed.

Engineering checks cover scoring, evidence constraints, stage gates, failure/unknown distinction, product/plan separation, BOM accounting, scope, exported bundle structure and portable replay. They do not prove source truth, AI semantic agreement, professional/aesthetic acceptance, market demand, teaching gains or actual resource savings.

工程检查和合成用例不等于真实产品验收。公开版不包含私人历史回放；AI语义一致性、专业/审美、人类接受与现实效果需独立评议。空标签校准输出应为 `NOT_CALIBRATED`，空额度仍阻断现实资源资格。

Source publication uses a reviewed file allowlist and selected credential/private-path checks. Release-time independent scanner results, archive hashes and the exact tested revision are recorded in the GitHub release. No scanner proves that every possible sensitive datum has been identified.

Version 0.3.0 regression includes a single-document PRD with no trials, weak-design ratings, missing acceptance, known scope failure, future-outcome overclaims, contradictory costs and unknown numeric costs. Passing these cases proves the specified computation and gates, not that an AI grader agrees with human design judgments.

0.3.0专项覆盖无试用的单一PRD、空泛设计、验收缺失、已知范围错误、未来效果冒充事实、成本冲突和数值未知。方案原文允许高设计分，但未知事实与空预算保持原状态。
