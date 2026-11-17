# Contributing

**English** | [简体中文](CONTRIBUTING.zh-CN.md)

Keep changes tied to a concrete failure, missing capability or documentation problem. Explain the trigger, expected behavior, actual behavior and smallest reproducible **synthetic** example. Never submit client evidence, private conversations, credentials or real relationship ledgers in an issue, PR or test fixture.

## Local verification

Use Python 3.11+, install `requirements-validation.txt`, and run:

```sh
python tools/eval_suite.py --out runtime/contribution-product
python tools/plan_eval_suite.py --out runtime/contribution-plan
python tools/verify_public_source.py
```

Use new output paths on subsequent runs. The product suite includes unit tests. Add regression coverage for meaningful scoring, evidence or permission failures; do not equate additional test counts with business validity.

## Policy changes

Version the policy when weights, evidence semantics or release behavior change. Preserve old inputs/results, document before/after effects and counterexamples, and keep product and plan scoring independent. Independent review is appropriate for changes that materially affect eligibility. Do not tune thresholds merely to pass a preferred case.

Keep `null` distinct from zero, unknown distinct from failure, and quality eligibility distinct from spending/publication authorization. Never convert synthetic material into real-world evidence or override paused/closed project decisions.

Maintain both READMEs and contribution/license-scope notes when their content changes. Check the distributed archive as well as the checkout. Contributions use the applicable file-scope license described in [LICENSE-NOTE.md](LICENSE-NOTE.md); retain third-party notices and only contribute material you may distribute.
