# Hyper Quality · 三层品控与资源评审

[English](README.md) | **简体中文**

基于 [Hyper Protocol](https://github.com/MkaliezZ/Hyper-Protocol) 的判断、功能、资产三层，对**开发方案和实际产品分别评审**，为质量改进与现实资源分配提供可追溯依据。

**0.3.0 / 试行规则。** 支持 Skill、Bot、Agent、课程、硬件和研究型产品。方案通过不代表产品实现，高分不抵消硬门槛，预算未知不产生拨款或上线授权。

## PRD和产品分别评什么

**PRD评设计质量，不要求先有产品试用。** 一份充分的原始方案可以获得高分；产品验收则检查实际交付与效果证据。

| 层 | PRD／开发方案 | 已实现产品 |
| --- | --- | --- |
| 判断 | 用户任务、需求推理、卖点与替代方案、验证方法、资源取舍 | 真实需求、采用理由、实际效果与投入依据 |
| 功能 | 端到端开发逻辑、接口与状态、权限、依赖恢复、里程碑验收 | 功能能否完成任务、失败能否恢复、权限与交付是否成立 |
| 资产 | 来源与版本、权利取得路径、复用、评测材料和退出设计 | 实际资产是否可追溯、可使用、可复用、可维护 |

每层都给价值、问题和下一动作。方案的 `PJ/PF/PA` 与产品的 `J/F/A` 分开评分。

## 如何看方案得分

> 开发阶段鼓励关键假设已有适用证据；有则加分，无则不加分，不因缺证扣分、阻断或否决方案。

| 结果 | 口径 | 没有真实试用时 |
| --- | --- | --- |
| 设计质量分 | **满分100**；评需求、逻辑、验收、成本和资产设计 | 原始PRD可支持完整0—4分锚点，不因未实施降分 |
| 关键假设证据加分 | **额外0—10分**；仅奖励适用的事实证据 | 记为 **＋0**，不影响正常设计评分 |
| 实证成熟度 | 单列假设、依赖和实际评议状态 | 保留 `unknown`／`unverified`／`not_run` |
| 执行与资源资格 | 单列承接、排期、前置、BOM数值和预算 | 额度保持 `null`；设计通过不自动批准投入 |

例如，同一设计可以是“**85/100 ＋ 0/10**”，取得适用证据后成为“**85/100 ＋ 5/10**”。这是分数示意，不是实际评测结果。`score`和`scorecards`保留100分设计分，`plan.evidence_bonus.reference_total`提供加分后的参考总分，最高110。

设计门槛仍只看基础设计分：验证方案60分、开发方案80分，另有三层最低分及覆盖要求。证据加分不抵消设计硬伤；“没有试用结果”与“没有可执行的验证设计”分别处理。开发逻辑矛盾、验收设计缺失、成本遗漏、越权和未处理的已知反证仍严格评审。评分细则及加分算法见[方案制度](references/09-开发方案评审.md)。

产品评分规则保持不变。旧0.2.0方案分须重读原件后按新锚点评审，不能机械换算或直接与新分数排名。历史报告继续保留。

## 能做什么

- 方案和产品各有15项独立指标；判断45%、功能35%、资产20%，分别呈现价值、问题与下一动作。
- 输出卖点及证据边界，核查来源快照、引文、哈希、日期、对象版本和支持范围。
- 产品按发现、小试、上线、扩张评审；方案按验证、开发评审，并限定到一个请求里程碑。
- 记录关键假设、依赖、里程碑、成功与失败条件、停止线。
- 盘点BOM，以及现金、本人时间、团队时间、token和关系使用；未知保持 `null`。
- 导出报告、JSON结果、回执、Hyper Protocol任务包，以及带证据、代码和规则快照的可复放档案。
- 根据已提供的人类标签计算校准统计，不自动生成人工标签、不调用模型。

AI或评审者负责实际读材料并提出评分，程序负责校验、约束和计算。哈希不能证明来源真实，工程通过不能证明科学、市场或教学效果。**当前权重和阈值尚未经过真实经营结果校准。**

## 快速开始

需要 Python **3.11+**。核心评分仅用标准库，在仓库根目录运行：

```sh
python harness.py init --id example --name "待评产品" --profile agent --as-of 2026-11-18 --out runtime/product.json
python harness.py init --review-object development_plan --id example-plan --name "待评开发方案" --profile agent --as-of 2026-11-18 --out runtime/plan.json
python harness.py validate --input runtime/product.json
python harness.py review --input runtime/product.json --out runtime/product-review-1
python harness.py validate --input runtime/plan.json
python harness.py review --input runtime/plan.json --out runtime/plan-review-1
```

日期应改为实际评审日。正式评审前补充真实材料、评分提案、BOM和范围。空模板会得到 `NEEDS_EVIDENCE`，结构通过不代表产品通过。输出目录必须是新目录；其他位置的证据使用 `--evidence-root 路径`。

查看两条路径的完整**合成演示**：

```sh
python tools/demo.py --out runtime/demo-1
```

演示中的资料、评分和成本是明确标记的合成夹具，不是客户证据、人工认可、报价或建议预算。正式模板的预算五维保持空白。详细制度、提示和生成报告以中文为主；英文读者可查看 [English guide](docs/GUIDE.md)。

## 验证

协议校验与测试另需安装 `jsonschema`：

```sh
python -m pip install -r requirements-validation.txt
python tools/eval_suite.py --out runtime/product-eval-1
python tools/plan_eval_suite.py --out runtime/plan-eval-1
python tools/verify_bundle.py runtime/demo-1/product/task-bundle.json
python tools/verify_public_source.py
```

[v0.3.0发行验证](https://github.com/MkaliezZ/Hyper-Quality/releases/tag/v0.3.0)通过105项单元测试、8种产品场景和36种方案场景，其中31种方案生成协议包并检查复放。非法输入的预期拒绝也计入场景。CI覆盖Windows／Ubuntu与Python 3.11／3.13；当前提交的状态见[Actions](https://github.com/MkaliezZ/Hyper-Quality/actions)。

专项回归覆盖无试用PRD、证据加分、错误证据类型、缺失验收、已知设计错误及空预算。公开版不含私人历史案例；回归通过不代表AI评分、市场或教学已校准。[验证范围](docs/VALIDATION.md)

## 复放与校准

```sh
python runtime/demo-1/product/implementation/harness.py --policy runtime/demo-1/product/policy.json review --input runtime/demo-1/product/replay-dossier.json --evidence-root runtime/demo-1/product --out runtime/replayed-product-1
python harness.py calibrate --input examples/human-ratings-empty.json --out runtime/calibration.json
```

空标签文件会如实得到 `NOT_CALIBRATED`。方案和产品标签分别校准。报告会携带证据快照与来源定位，可能包含私人信息，默认保存在本地，不应直接公开。

## 制度入口

| 文件 | 用途 |
| --- | --- |
| [总制度](references/00-评审总制度.md) | 三层职责、阶段、权限与门槛 |
| [方案评审](references/09-开发方案评审.md) | PJ/PF/PA、假设、依赖、里程碑和停止线 |
| [判断层](references/01-判断层评审.md) | 需求、卖点、指标、资源取舍、专业与审美 |
| [功能层](references/02-功能层评审.md) | 实际完成、恢复、权限、交付与计量 |
| [资产层](references/03-资产层评审.md) | 来源、权利、复用、评测与生命周期 |
| [BOM与资源](references/04-资源与BOM.md) | 九类成本和五维资源 |
| [输入契约](references/06-输入契约.md) | 档案字段、证据与空值 |
| [运行手册](references/08-运行手册.md) | 从材料到报告 |
| [Skill入口](SKILL.md) | 给AI助手使用的评审流程 |
| [公开范围](docs/PUBLICATION.md) | 公开源码与排除的私人材料 |

## 开源许可与贡献

代码、JSON契约、测试和工具采用 **Apache-2.0**；Markdown制度、文档和提示采用 **CC BY 4.0**。详见 [许可范围](LICENSE-NOTE.zh-CN.md)、[第三方署名](THIRD_PARTY_NOTICES.md) 和 [贡献指南](CONTRIBUTING.zh-CN.md)。使用工具不会改变用户自己的数据、评审或第三方材料的权属。

内嵌Hyper Protocol固定为 `v0.2.0-draft.3`，commit `5f5d4977a94ebe21ba83a50ef963bfbe92dd4173`。本项目的严格起始参数是独立试行制度，不冒称上游协议认证。
