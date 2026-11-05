# 完整可运行的轻量SDD教学闭环

本例不会预填通过证据。运行时建立一个全新合成项目，包含纯内存范围过滤和页大小修复；不是Java/Spring业务服务，不验证真实账号、HTTP权限或数据库。

```bash
python3 examples/complete/run_demo.py --destination ../playbook-teaching-demo
```

目标必须不存在或为空。初始化治理包、填写有效profile，建立源码、真实单测、规格和任务：

1. 范围列表：R-01只返回管理范围，R-02空范围返回空；运行两项实际AccessTests。
2. 修复案例：先运行页大小回归并确认失败，保留失败记录；修复zero/negative后重跑通过。
3. 每次执行自动保存命令、时间、环境、源码/配置指纹、规格摘要和返回结果。
4. 两个变更分别建立completed追踪，仅引用真实passed记录；使用同一项目上下文检查当前源码与规格绑定。
5. 将最终行为整合到生成项目docs/modules/scoped-list.md，并维护模块及总入口索引，保留修复前失败证据而不当成当前通过。

示例第一次出现测试FAIL是受控复现步骤，不代表最终示例失败。工具最后返回0才代表闭环成功；目标目录保留供阅读，用户可在确认仅属演示后删除。仓库回归在TemporaryDirectory中运行同一流程，结束自动清理。

在生成项目中复查（把实际路径替换为你的目标）：

```bash
python3 .engineering/tools/check.py --project . --trace specs/changes/scoped-list/change.json
python3 .engineering/tools/check.py --project . --trace specs/changes/page-size/change.json
```

后续修改src/tests或project.json会使旧证据过期，需要真实重跑对应检查；修改spec.md也会使旧规格摘要失效。记录不是签名，不能抵御有意伪造，仍需责任人评审。

示例规格含业务/产品/技术审视和最小推荐；这是已声明的教学设计，不是脚本自动评判方案质量。现行知识与变更证据分开，根入口不再用历史流水覆盖分类导航。
