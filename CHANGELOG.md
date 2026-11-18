# Changelog / 版本记录
## 0.3.0 · 2026-11-18 · PRD设计质量与实证成熟度分离

保留“关键假设已有证据”的正向作用：设计100分之外增加最高10分奖励。缺证仅+0，不扣分或阻断；设计门槛与资源资格不使用奖励分抵消。

修复0.2.0把产品验证标准套用PRD的问题。十五项PJ/PF/PA锚点改评设计的完整、可执行、取舍与边界；有效原始方案可支持0—4分，不再要求先有试用、PoC或两组独立实证。实际假设/依赖、工程/真人结果仍保持事实证据约束。

分开输出design_quality、validation_maturity、execution_readiness和资源资格；具体人选/日历/前置完成与已盘点成本的数值未知不自动否决设计。设计门槛、已知反证、权限、验收、成本构成、停止线、产品规则和空预算阻断保持。

新增无试用PRD正例、空泛设计、事实冒充、成本遗漏/未知分离等回归。旧报告不覆盖；旧policy不带score_basis时保留旧路径。旧方案分须重读原件后重新评分，不能与新口径直接排名。


## 0.2.0 — Public source publication / 公开发行 — 2026-11-17

Publish the existing 0.2.0 runtime and policy without changing scoring semantics. Add bilingual entry, contribution and licensing documentation, synthetic demos, public-only evaluation runners, CI and tracked-source packaging. Exclude all private evidence, real review dossiers, historical outputs and internal collection scripts. Public tests do not claim to reproduce the excluded internal history.

公开现有0.2.0核心程序与规则，评分语义不变。新增中英文入口/贡献/许可说明、合成演示、仅使用公开夹具的eval、CI及跟踪源码打包。私人证据、真实评审档案、历史输出和内部收资脚本不分发。

## 0.2.0 — Review engine / 评审引擎 — 2026-11-12

Add separate development-plan criteria, validation/development stages, hypotheses, dependencies, single-milestone scope, four-phase BOM and stop conditions. Keep product scores separate; preserve schema 1.0 product compatibility. Reject shared version-sensitive evidence. Future claims remain candidates. Budgets default to null.

## 0.1.1 — Review engine / 评审引擎 — 2026-11-11

Prevent known failures from being averaged away, distinguish negative evidence from missing evidence, use decimal resource accounting, reject conflicting calibration labels, and preserve portable evidence/executor snapshots.

Earlier internal evaluations are not redistributed and are not treated as new public validation. All policy parameters remain provisional and not business-validated.
