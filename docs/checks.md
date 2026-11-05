# 检查工具：能力、边界与退出码（v0.2）

## 接入与项目就绪

bootstrap仍为离线复制：不覆盖既有文件/治理包，拒绝符号链接目标，独占锁及写入，失败尽力回滚自己的文件和目录，保留既有内容。SIGKILL/断电后需人工检查，不能承诺多文件原子事务或抵御恶意并发路径替换。运行缓存/pyc不会被打包，固定版本及初始文件摘要写入manifest。

project_contract统一验证schema 2、ready、非占位项目/业务说明、技术栈及不适用理由、核心/适用规范、非空知识入口、业务边界、环境/Git/CI/测试清理策略、例外字段与source_paths。环境仅允许test/development且production_access=forbidden。全部检查组必须有合法命令或明确不适用理由，预检在任何命令之前完成。

这些是结构和声明检查，不能证明填写内容真实或端点确非生产。source_paths必须列出本次要绑定的实际源码/测试/配置，不接受整个根目录或符号链接；项目说明本身始终纳入摘要。未列入的文件不会自动纳入验证，需评审是否遗漏。

## verify：退出、资源与证据

每项检查须有稳定ID、argv、timeout_seconds（1..7200）、purpose和resources。grace_seconds为0..30，默认3。

- mode=none：必须解释为何不创建外部隔离资源，禁止偷偷附带清理hook。
- mode=isolated：必须写归属，以及各自有argv/timeout的cleanup和residual_check。两项hook在成功、失败、启动失败、超时和受控中断后都执行；清理失败或残留检查失败不能通过。hook需幂等、限定本轮归属，不得清空共享库。
- POSIX超时先向执行进程组发送SIGTERM，等待宽限期，再SIGKILL剩余进程；直接终止CLI的SIGTERM转为受控中断。Windows仅处理直接子进程，未验证完整后代回收。
- 代码修改命令若改变已声明源码/项目配置或本次规格，记录inputs-changed并失败；验证工具不替代格式化/修复阶段。

清理hook也有有限超时；这是受控本机执行，不是安全沙箱。用户显式配置shell、网络或危险动作仍可能产生副作用。SIGKILL/断电不能执行finally，外部操作也不能靠杀本地进程撤销；此时人工按归属复查。argv会保存在证据，禁止携带密码/Token；stdout/stderr继承终端，不自动归档正文，项目仍需脱敏。

```bash
python3 .engineering/tools/verify.py --project . --group offline --spec specs/changes/feature/spec.md --evidence-dir specs/changes/feature/evidence
```

成功0；命令/清理/残留/输入漂移失败1；预检/启动配置或证据写入不可用2；超时/受控中断124。自动证据为唯一文件名JSON，包含命令、返回码、时间、环境、源码/配置指纹、规格摘要及清理结果。没有--spec的普通检查可以执行，但它的记录不能用于声明某个变更completed。

## check：项目、链接和追踪

```bash
python3 .engineering/tools/check.py --project .
python3 .engineering/tools/check.py --docs .engineering --trace specs/changes/feature/change.json --project .
```

链接检查仍是简单内联相对文件目标，不验证锚点、外网或所有Markdown语法。schema 2追踪检查ID、覆盖、状态；ready/implementing/completed的需求不能是已识别占位符，completed需任务done且验收passed。

证据引用为对象：kind=automated/manual、path；自动记录另有check_id。证据必须非空JSON，时间含时区且有序，环境为非生产，规格摘要匹配；completed必须提供--project，核对当前声明源码与配置指纹。自动证据须记录实际命令成功、清理成功；手工记录须有责任人、步骤和观察。旧schema 1/纯文本路径不能静默完成，通过[迁移说明](maintenance.md)适配。

源指纹按相对路径与文件摘要计算，包含project.json，排除构建/缓存目录；Git revision/dirty另行记录。提交证据本身不会无限使摘要失效，但修改已声明源码/测试、规格或项目配置会失效。Git版本仅作为运行上下文，不强制HEAD相同，避免证据提交递归问题。

记录不是签名，无法抵御有意伪造或证明业务正确；源范围、命令有效性、人工观察与权限仍需评审。check成功0、发现问题1、参数错误2。

## 自动化状态

| 项目 | 当前状态 |
|---|---|
| 项目结构就绪、文件链接、有限追踪与证据绑定 | 已实现 |
| 初始化不覆盖、回滚、版本与缓存排除 | 已实现 |
| 优雅超时、清理hook、残留复查、结构化证据 | 已实现；项目需配置真实且安全的命令 |
| Java编译后部分直接分层依赖 | 可选jdeps适配；不含反射/循环/所有ORM |
| 前端迟到响应与dispose示例 | 可运行Node夹具；不代替应用浏览器验证 |
| PostgreSQL隔离入口 | 已实现保护和生命周期；真实库运行需显式启用 |
| CI/分支保护/审批/生产发布、证据真实性 | 未自动实现，仍按项目与用户授权 |


关闭过程持续权限拒绝或无法确认退出时，execution记录termination-failed/unconfirmed，仍尝试已声明清理/残留hook；即使hook通过，整体也不能通过。不能据此保证外部服务或未知后代已停止，须人工按资源归属核查。

## 文档治理覆盖

bootstrap在新docs中生成带未实现声明的分类索引，既有docs不改动；这是结构初始化，相关安全/兼容有离线回归。check.py仍只检查有限的Markdown文件目标，不校验全部标题锚点、目录/命名、过时语义或方案质量。三视角审视、现行知识整合、合并前重复/矛盾清理、实际diff规范复查及阶段性知识审计由流程和模板要求人工执行，不是自动CI、定时巡检或独立审批。
