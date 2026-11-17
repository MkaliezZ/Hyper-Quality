# 贡献指南

[English](CONTRIBUTING.md) | **简体中文**

围绕具体失败、缺失能力或文档问题提交修改，说明触发条件、预期与实际行为，以及最小**合成**复现。Issue、PR和测试夹具不得包含客户证据、私人对话、凭证或真实关系台账。

## 本地验证

使用Python 3.11+，安装`requirements-validation.txt`后运行：

```sh
python tools/eval_suite.py --out runtime/contribution-product
python tools/plan_eval_suite.py --out runtime/contribution-plan
python tools/verify_public_source.py
```

重复运行使用新目录。产品eval包含单元测试。对影响评分、证据或权限的实质问题补回归，不把测试数量当作经营有效性。

## 修改规则

修改权重、证据语义或放行行为时升规则版本，保留旧输入/结果，说明前后变化和反例，方案与产品评分继续独立。显著影响资格判定的改动应安排独立复核，不能为了让偏好的案例过关而调阈值。

保留null与0、未知与失败、质量资格与支出/发布授权的区别。不把合成材料改成真实证据，不覆盖项目暂停或结项决定。

相关内容变化时同步维护中英文README、贡献指南和许可范围；检查实际分发包。贡献按[对应文件许可](LICENSE-NOTE.zh-CN.md)分发，保留第三方署名，只提交自己有权分发的材料。
