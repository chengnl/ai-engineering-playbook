# 版本、适配与升级

采用时记录VERSION和来源Git提交/tag，manifest保留初始复制文件摘要，不是自动升级器。项目可适配规则，例外写明rule/reason/scope/risk/compensation/review_condition。

## v0.1 → v0.2迁移

这是显式契约升级，不能只将版本号改为0.2.0：

1. 先提交/备份已有治理资料；在新的空目录生成v0.2包，与原版本、本地适配三方对比，不直接重跑bootstrap覆盖原工程。
2. 审阅并迁移全部工具模块（project_contract/process_runner/evidence/verify/check）、规范和入口。AGENTS保持原项目规则与用户授权约定。
3. project.json升为schema_version=2，填写业务说明、技术栈对象/none理由、适用规范、环境声明、知识和source_paths；各组配置命令或不适用理由，不能留空。
4. 每条命令增加稳定ID、资源声明；隔离资源补cleanup/residual_check。迁移后先保持needs-adaptation，审阅实际环境和命令，再改ready。
5. 活跃变更的change.json升为schema_version=2，证据改对象引用；重新执行适用检查生成带规格与源码摘要的JSON。不能把旧空文件或历史文字包装成新通过记录。
6. 旧已归档schema 1是历史事实，保留原文并注明版本，不批量改写历史验收。新门禁只针对当前采用schema 2的变更。
7. 执行项目就绪、链接、追踪、适用业务回归和临时资源复查，更新现行知识、README、索引及采用版本。bootstrap仍拒绝已有治理包，v0.2没有自动升级/三方合并功能。

## 后续维护

规则编号避免无理由重用，改变强制程度/结构/工具行为须写兼容影响；重大选择记录ADR。模板和工具同轮更新，区分规范、检查与证据。源摘要只覆盖配置的source_paths，评审时检查是否遗漏关键源码。

先在另一个实际工程试用，再决定增加更多语言、CI或Skill；不把示例通过当成所有技术栈验证。不要复制来源项目的生产路径、角色、历史测试数量或CI暂停决定。
