# Public source boundary / 公开源码范围

[English README](../README.md) · [中文README](../README.zh-CN.md)

This is a standalone public export of Hyper Quality 0.2.0. The original scoring runtime, adapter, templates and `policy.json` are unchanged. Publication changes cover documentation, examples, evaluation runners, source checks and packaging. / 本版独立发布现有0.2.0核心评分程序与规则，公开整理不改变评分语义。

## Included / 包含

- Runtime, policy, rubrics, reviewer prompts and assistant skill entry.
- Synthetic unit/behavior fixtures, an empty plan template and empty human-label template.
- An unchanged, attributed subset of Hyper Protocol and its original licenses.
- Bilingual entry/contribution/license documentation, CI and tracked-source packaging.

## Excluded / 排除

Private original evidence, real customer/project reviews, historical dossiers and output bundles, conversations, local source paths, credentials, relationship ledgers, databases, runtime logs, internal intake/seeding/self-review scripts, dependency/model caches and scanner binaries. / 私人原件、真实项目案例、历史报告和评审包、对话、个人路径、凭证、关系台账、数据库、运行日志、内部收资脚本和缓存均不分发。

The public eval runners use synthetic fixtures only and do not search outside this checkout for internal project history. No private compatibility-replay result is counted as public validation. / 公开eval不读取仓库外的历史项目，不把未分发的内部回放算成本轮公开验证。

## Updating or releasing / 后续发布

1. Review the tracked file list against `PUBLICATION.json`. An allowed directory is a scope boundary, not a blanket right to publish arbitrary files inside it.
2. Run `python tools/verify_public_source.py`, inspect credentials/private data, and verify rights for additions.
3. Run both eval suites in a clean checkout and keep results in ignored `runtime/`.
4. Commit reviewed changes. `python tools/package.py --out dist/Hyper-Quality-0.2.0.zip` requires a clean tracked tree and packages only tracked source, plus a per-file hash manifest.
5. Verify the actual uploaded asset's checksum and archive manifest. Keep credentials and audit logs outside the source distribution.

The built-in check is a path/pattern safeguard, not a complete secret scanner. Keep manual review and appropriate independent scanning. Git ignore rules do not sanitize already tracked files. / 内置检查不替代完整凭证扫描或人工复核，gitignore也不会清除已经跟踪的私人文件。

Runtime reports may embed original evidence. A repository license does not grant permission to publish that evidence. / 运行报告可能嵌入原件，仓库开源许可不构成公开原件的授权。
