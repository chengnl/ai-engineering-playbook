# 规则、项目与工具的边界

## 分层

1. standards：通用协作/文档治理及Java/前端/数据库/测试技术规则；适用技术栈按项目选择。
2. workflows：分级轻量SDD，以及开发、修复、重构、集成、发布步骤。
3. templates：AI入口、项目说明、规格/任务/验收、技术决策和发布记录。
4. tools：bootstrap安全复制；project_contract校验配置与源码指纹；process_runner执行/终止；evidence校验证据；verify编排检查和资源hook；check负责文档与追踪。
5. adapters：可选Java/前端/数据库适配；数据库入口只有显式选择和配置后才连接隔离测试库。
6. 项目自身：业务、框架、环境、权限、构建和测试实现。规范库不携带某业务工程的角色、服务器或密钥。

## 接入后的结构

```text
project/
├── AGENTS.md                 # 新建，或由snippet人工合入原文件
├── .engineering/
│   ├── README.md
│   ├── project.json          # 项目适配；默认needs-adaptation
│   ├── manifest.json         # 初始采用版本与复制文件摘要
│   ├── standards/
│   ├── workflows/
│   ├── templates/
│   ├── adapters/
│   └── tools/
└── docs/                     # 已有则整体保留；新建只生成索引骨架
    ├── README.md
    ├── modules/、ai/、operations/、guides/、experiments/
    └── architecture/、plans/、acceptance/、releases/、deployment/、incidents/
```

业务源码不由接入命令创建。业务知识主入口由project.json指定；变更目录建议specs/changes/<id>/，不是初始化强制生成的业务规格。

## 关键决策

- 使用版本化文件复制而非远程动态加载：可离线、可审查、无客户端锁定；代价是升级需显式比较本地适配差异。
- 结构检查与命令执行分开：check无业务命令副作用，verify仅执行已配置命令；命令仍可能有副作用，配置须评审，执行器不是安全沙箱。
- 不生成CI、业务框架或Skill安装器：减少隐式授权和环境假设。后续扩展需由第二个项目的实际接入验证驱动。
- 规范是团队约定，只有已实现检查能阻断对应机械问题；不伪称完整架构审查、语义验收或强制审批已自动生效。

## v0.2决策

将项目/追踪schema升为2以显式拒绝旧的宽松完成条件；使用源范围与规格摘要约束证据漂移，不强制当前HEAD相同以避免提交证据递归失效。默认不归档stdout/stderr，减少客户数据泄漏；命令argv仍可能敏感，项目必须禁止内联凭据。

清理hook由显式资源声明驱动，不猜测并自动删除资源；其副作用和生产保护需项目审查。结构化记录不是签名，源范围选择和业务正确性保留评审责任。


## 文档治理决策

通用目录规范集中在standards/documentation.md，项目按实际情况确定根总览和裁剪分类，不复制来源工程八份根文档。新项目只有分类索引和未实现声明，业务主题按需建立；既有docs不移动/覆盖，缺入口时仅创建不假设分类存在的README。模板不更新已有.engineering包，安全拒绝和回滚语义保持。

方案三视角、知识语义、实际diff规范复查及发布/里程碑阶段审查进入流程与模板，仍是人工责任。schema 2追踪未新增自动“业务评审通过”字段，check.py不会据文字出现就声称方案合格。0.2项目显式升级规范/模板，旧契约不批量改写。


退出探测被临时拒绝时只在原grace内等待可确认结果，不把拒绝等同于退出。持续拒绝则终止状态unconfirmed、整体失败，仍运行已声明清理与残留hook；不会因为hook成功而把未知关闭改成通过，未知后代或外部副作用仍需人工确认。
