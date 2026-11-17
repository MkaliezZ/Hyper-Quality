# Hyper Quality

**English** | [简体中文](README.zh-CN.md)

Evidence-bounded quality and resource reviews for products and development plans, built on the judgment, function and asset layers of [Hyper Protocol](https://github.com/MkaliezZ/Hyper-Protocol).

**Version 0.2.0 · provisional policy.** Review skills, bots, agents, courses, hardware and research products. Plans and implemented products receive separate scores. High scores never override failed gates, and missing budgets never become funding approval.

## What it does

- Scores 15 criteria per review object across **judgment (45%), function (35%), assets (20%)**.
- Records each layer's value, problems and next action, plus selling points, evidence and limitations.
- Checks evidence hashes, quotations, dates, versions, declared provenance and supported criteria.
- Applies separate product stages and plan milestones, assumptions, dependencies and stop conditions.
- Accounts for BOM and cash, owner/team hours, tokens and relationship uses; unknown values remain `null`.
- Writes a report, JSON result, execution receipt, Hyper Protocol bundle and portable replay with frozen source and policy.
- Computes calibration statistics from supplied human labels; it does not create labels or call a model.

An AI or human reviewer reads the sources and proposes ratings. The deterministic harness checks and constrains those proposals. It cannot establish source truth, scientific validity, customer demand or reviewer identity from a hash or declaration. The weights and thresholds have **not been validated against business outcomes**.

## Quick start

Python **3.11+**. Core scoring uses the standard library. Run from the repository root:

```sh
python harness.py init --id example --name "Example product" --profile agent --as-of 2026-11-17 --out runtime/product.json
python harness.py init --review-object development_plan --id example-plan --name "Example plan" --profile agent --as-of 2026-11-17 --out runtime/plan.json
python harness.py validate --input runtime/product.json
python harness.py review --input runtime/product.json --out runtime/product-review-1
```

Replace the date with the review date. Fill in actual sources, proposed ratings, BOM and scope before a real review. An empty template intentionally returns `NEEDS_EVIDENCE`. `validate` checks structure, not product quality. Each output directory must be new. Use `--evidence-root PATH` when evidence lives outside the checkout.

For a complete **synthetic demonstration** of both paths:

```sh
python tools/demo.py --out runtime/demo-1
```

The demo writes invented, explicitly synthetic fixtures. They are not customer evidence, human acceptance, real costs or a recommended budget. Default review budgets remain empty. Reports and the detailed rubric are primarily in Chinese; English interface and decision guidance is in [the guide](docs/GUIDE.md).

## Run the checks

The bundled protocol validator and tests additionally require `jsonschema`:

```sh
python -m pip install -r requirements-validation.txt
python tools/eval_suite.py --out runtime/product-eval-1
python tools/plan_eval_suite.py --out runtime/plan-eval-1
python tools/verify_bundle.py runtime/demo-1/product/task-bundle.json
python tools/verify_public_source.py
```

The product suite runs all unit tests plus 8 product scenarios. The plan suite checks 27 scenarios, including expected invalid inputs, 22 exported bundles and portable replay. These are engineering regressions, not AI judge calibration or market/teaching validation. Private historical reviews are excluded. See [validation scope](docs/VALIDATION.md).

## Replay and calibration

```sh
python runtime/demo-1/product/implementation/harness.py --policy runtime/demo-1/product/policy.json review --input runtime/demo-1/product/replay-dossier.json --evidence-root runtime/demo-1/product --out runtime/replayed-product-1
python harness.py calibrate --input examples/human-ratings-empty.json --out runtime/calibration.json
```

The empty calibration file correctly returns `NOT_CALIBRATED`. Keep development-plan and product labels separate. Review records are sensitive: they can contain evidence snapshots and source paths. Keep them local unless separately reviewed for publication.

## Documentation

| Entry | Purpose |
| --- | --- |
| [English guide](docs/GUIDE.md) | Review flow, score meanings and decision boundaries |
| [General rubric](references/00-评审总制度.md) | Three layers, evidence and stage gates |
| [Plan rubric](references/09-开发方案评审.md) | Separate plan criteria and milestone decisions |
| [BOM](references/04-资源与BOM.md) | Nine cost categories and five resource dimensions |
| [Input contract](references/06-输入契约.md) | Fields, evidence types and unknown values |
| [Calibration](references/05-校准与治理.md) | Human labels, counterexamples and policy revisions |
| [Skill entry](SKILL.md) | Instructions for an assistant reviewing a plan or product |
| [Publication scope](docs/PUBLICATION.md) | Included source and excluded private material |

## License and contributions

Code, JSON contracts, tests and tooling: **Apache-2.0**. Markdown documentation and review instructions: **CC BY 4.0**. See [license scope](LICENSE-NOTE.md), [third-party attribution](THIRD_PARTY_NOTICES.md), and [contributing](CONTRIBUTING.md). Your own reviews and data are not relicensed by using this tool.

The vendored Hyper Protocol subset is pinned to `v0.2.0-draft.3`, commit `5f5d4977a94ebe21ba83a50ef963bfbe92dd4173`. Hyper Quality's policy parameters are its own provisional choices, not an upstream certification.
