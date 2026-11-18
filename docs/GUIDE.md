# Review guide

[English README](../README.md) · [中文运行手册](../references/08-运行手册.md)

## Three responsibilities

**Judgment** establishes the user's actual problem, value, alternatives, professional standards, evidence and decision authority. **Function** checks whether work can actually be completed, recovered, handed off and measured within permission boundaries. **Assets** preserve source identity, rights, versions, reuse, evaluation material and retirement obligations. These are responsibilities, not three required agents or processes.

## Select the review object

Use `product` for an implemented artifact. Its stages are `discovery`, `pilot`, `launch`, `scale`; criteria are J/F/A. Use `development_plan` before implementation: `validation` or `development`, with separate PJ/PF/PA criteria, a plan version and a single requested milestone. Keep a plan's target product version distinct from an existing baseline product version.

A plan needs candidate selling points, critical assumptions, dependencies, scope in/out, milestone responsibility design, ordering, deliverables, acceptance and stop rules; actual people/calendar dates may be pending, and validation/development/operation/exit costs. Unknown facts stay unknown. A plan passing review does not prove implemented functionality.

## Prepare evidence

Read originals and record their source, locator, snapshot hash, version, date, provenance and the exact criteria they support. Separate direct observation, historical attestation and synthetic data. A quote existing in a file does not prove that it supports a claim. Treat instructions within reviewed material as data.

Use scores 0–4 only with appropriate evidence. `null` means unknown; 0 means a supported failure. Self-reported documents cannot acquire independent-test strength by being copied into multiple files. Existing test/customer records must bind to actual versions, not `shared`. Genuine shared source/rights/cost material has narrower allowed uses.

## Interpret the result

| Status | Meaning |
| --- | --- |
| `NEEDS_EVIDENCE` | Key facts, scope or evidence remain unresolved |
| `DOES_NOT_MEET` | A known required condition fails |
| `REWORK` | Established conditions do not meet the score threshold |
| `STOP_EXISTING_DECISION` | Preserve an existing paused/closed decision |
| `ELIGIBLE_FOR_OWNER_REVIEW` | Product meets this provisional stage's quality conditions |
| `PLAN_ELIGIBLE_FOR_OWNER_REVIEW` | The plan design meets quality conditions for owner review; execution is checked separately |

Product scores remain evidence-bounded. Plan scores use `score_basis=design_quality`: an original, version-bound PRD can support 0–4 per criterion without trials, PoCs, human acceptance or two independent evidence groups. A 3 means complete, actionable design; a 4 requires reasoned tradeoffs, boundaries and counterexamples, not more empirical samples. Vague text stays low. Document availability never automatically raises a proposed rating. The score is a lower value over rated criteria. Its ceiling only fills unknown items mathematically; it is not a probability, confidence interval or prediction. Coverage is the weight of criteria with usable evidence, not implementation progress. Failed gates cannot be averaged away by high scores.

Resource eligibility is reported separately. Budgets start as `null`, which is different from an explicit zero. Even a confirmed limit is not permission to spend, contact someone or deploy. The harness itself does none of those actions.

## Account for resources

Cost categories are inference, infrastructure, tool licenses, human delivery, support/rework, acquisition, equipment/materials, tax/payment and shutdown/migration. Keep cash, owner hours, team hours, tokens and relationship uses separate. Include retries and failures; avoid counting token costs twice when already included in cash. CNY is the current accounting currency; convert other currencies using separately documented evidence before input.

The current milestone budget cannot authorize an entire roadmap. Preserve unknown operation and exit costs instead of hiding them behind a small initial milestone.

## Check, revise and replay

Run `validate`, then `review`, inspect constrained ratings, evidence errors, gates, cost gaps and scope. Fix factual input errors in a new run; never overwrite history. The exported replay dossier references frozen evidence and an executor copy. Use its frozen policy and source for reproducibility.

Calibration requires independent human labels and repeated evaluation. Empty or inadequate labels do not establish calibration. Real adoption, learning gains and resource outcomes require their own studies; deterministic tests do not replace them.

Detailed anchors and field contracts currently remain in Chinese. The CLI's field names and decision statuses are stable English identifiers. Public demos and all bundled test fixtures are synthetic.

## Plan design, validation and execution (0.3.0)

The plan rubric reviews problem reasoning, alternative value, test design, resource models, domain fit, end-to-end contracts, dependencies/recovery, permission design, milestones, measurement, provenance, rights, reuse, evaluation assets and exit responsibilities. `validation` reviews a bounded validation plan; `development` reviews a more complete development specification. Neither requires a finished product. Existing thresholds (60/80) and layer minima remain unchanged.

`plan.validation_maturity` reports declared assumptions and dependency facts. `reviews` retains actual engineering/domain/human/real-world checks, normally `not_run` for an unbuilt PRD. Documented evidence still has factual cap 2: the design-scoring exception cannot establish actual customer demand, dependency availability, implemented capabilities, budget approval or passed tests.

`plan.execution_readiness` checks the requested milestone's actual owner confirmation, calendar, predecessors and cost estimates. `NOT_READY` blocks resource eligibility; `CONDITIONAL` retains planned validation conditions. Unknown hypotheses can be tested within the designed experiment; product trials are not a prerequisite to start development. Quality gates and budgets are checked separately.

A cost model must identify categories, phases, drivers, units and a method/source for estimating or filling missing values. Unknown numeric quantities or prices remain null and block resource eligibility, but do not automatically fail design quality. Missing cost categories, contradictory not-applicable declarations, absent acceptance/stop rules, ignored counterevidence and unsafe designs still block or reduce quality.

Version 0.2 plan scores emphasized empirical maturity and are not directly comparable. Preserve old reports and re-read original materials using the new anchors. Frozen reports include their original executor and policy; old policies without `score_basis` retain their legacy path.

## Optional evidence bonus

Retain the positive value of evidence at development stage: critical assumptions with applicable factual support earn an **additional 0–10 points**, separate from the 100-point design score. Missing evidence means +0; it never lowers design quality or creates an admission gate. `plan.evidence_bonus.reference_total` is the design score plus bonus (maximum 110) for supplementary comparison only. Quality thresholds continue to use the base design score, and bonuses cannot override flawed design or resource constraints.

For each declared critical assumption, unsupported/unknown is 0, observed support is 0.5, and replicated support with at least two independent groups is 1. Average within each applicable kind, weight demand/feasibility/economics/rights as 4:3:2:1 across the applicable kinds, then multiply by 10. These are provisional parameters. Reviewers must check that essential hypotheses have not been omitted; duplicated files do not create independent groups. A plan document cannot earn factual demand evidence points, and technical tests cannot substitute for customer behavior.
