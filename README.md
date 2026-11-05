# AI Engineering Playbook

AI工程研发规范与实践模板。把“先明确行为、再实现、用证据验收、同步知识”落实到可版本化的仓库文件，适用于AI辅助研发的新项目及已有项目。

当前版本：**0.3.0**。Python **3.10+**，仅标准库，无需安装第三方包。没有模型调用、云端依赖、自动部署或默认启用的CI。

## 从哪里开始

1. 阅读[使用指南](docs/getting-started.md)，了解新项目/已有项目接入。
2. 阅读[规则分层与适配](docs/architecture.md)，选择适用规范，不照搬技术栈。
3. 按[轻量SDD](workflows/sdd.md)选择简化、标准或增强流程。
4. 填写项目情况、检查命令、权限边界；让AI分析并初始化业务工程。
5. 按任务执行并记录需求到测试的对应关系；交付前更新知识。

```bash
git clone https://github.com/chengnl/ai-engineering-playbook.git
cd ai-engineering-playbook
python3 tools/bootstrap.py --destination ../my-project --name my-project
```

这条命令只创建研发治理骨架，**不创建Java/Vue业务应用、数据库或远端仓库**。业务代码应在读规范、明确项目约定后再建立。

已有工程如果已有AGENTS.md，先安全接入再人工/AI合并入口，不覆盖原规则：

```bash
python3 tools/bootstrap.py --destination ../existing-project --name existing-project --no-agent-entry
```

在目标工程执行：

```bash
python3 .engineering/tools/check.py --docs .engineering
python3 .engineering/tools/verify.py --project . --group offline
```

建立实际变更记录后，使用`--trace specs/changes/<id>/change.json --project .`检查需求与结构化证据绑定；初始化不会自动生成已完成的业务规格。检查命令默认未配置，verify会非零退出，**不会空跑后显示成功**。

## 内容

| 目录 | 内容 |
|---|---|
| standards/ | [协作](standards/collaboration.md)、[文档治理](standards/documentation.md)、[Java](standards/java.md)、[前端](standards/frontend.md)、[数据库](standards/database.md)、[测试](standards/testing.md)、[安全与运行](standards/security-operations.md) |
| workflows/ | [轻量SDD总流程](workflows/sdd.md)、[开发/修复/重构](workflows/development.md)、[集成/发布](workflows/integration-release.md) |
| templates/ | AI入口、项目情况、变更规格/追踪、技术决策、验收、发布和知识入口模板 |
| tools/ | 安全接入、项目契约、优雅退出/清理、结构化证据、链接/需求追踪检查 |
| adapters/ | [Java/Spring、前端、PostgreSQL可选适配](adapters/README.md)，不自动安装或连接数据库 |
| examples/ | [draft结构示例](examples/change/README.md)及[真实执行的完整教学闭环](examples/complete/README.md) |
| tests/ | 工具的离线回归，临时文件自动清理 |
| docs/ | 接入说明、架构、检查能力与边界、版本维护、实际验收 |

## 使用要点

- 方案先审视业务/产品/技术，给出推荐、取舍和验证；整合当前知识，历史/实验独立，合并前清理、阶段性人工复查。
- 新docs可生成分类索引骨架；已有docs完整保留，不自动迁移或补分类，具体规则见[文档规范](standards/documentation.md)。
- 项目和追踪契约采用schema 2，ready会检查完整资料；技术/检查组不适用须写理由。
- 超时先TERM宽限再强杀；隔离资源始终执行清理和残留检查，失败不能通过。
- 自动生成实际命令、环境、时间、源码/规格摘要及资源结果的JSON证据；拒绝空记录及过期证据。
- [版本迁移说明](docs/maintenance.md)；不覆盖既有包，不将旧证据伪装为本轮通过。

## 验证本仓库

```bash
python3 tools/check.py --docs . --trace examples/change/change.json
python3 -m unittest discover -s tests -v
```

无需生产配置、数据库或付费模型。初始化不会自动git init/commit/push，不会改变原工程CI。规则“已写明”和检查“已自动执行”是不同状态，见[能力边界](docs/checks.md)。

## 使用边界

这是团队流程基线和模板，不是AI永久记忆，也不是安全沙箱。每次新会话按项目AGENTS.md读取当前规则、规格和模块知识。用户当前明确授权优先；模板不能额外授权合并、发布、删除真实数据或调用付费服务。

业务规则必须由项目确认。没有统一的“所有项目必须Spring/Vue/PostgreSQL”要求；不将本模板仓库的验证命令冒充目标业务工程的测试。规范采用固定版本，升级需审阅差异和项目例外，见[版本维护](docs/maintenance.md)。
