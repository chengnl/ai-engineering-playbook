# PostgreSQL隔离检查适配

前置：独立、明确授权的测试数据库与受限账号；客户端psql可用。禁止生产凭据，连接信息由环境或受限PGPASSFILE提供，不写入仓库或命令参数。

```bash
PLAYBOOK_ALLOW_TEST_DB=1 PGDATABASE=example_test python3 .engineering/adapters/postgresql/isolated_check.py
```

另通过PGHOST/PGPORT/PGUSER/PGPASSFILE配置连接；PLAYBOOK_PSQL可指定客户端可执行文件。库名只允许纯名称且以_test/_ci结尾，拒绝URI和service覆盖；这不是数据库身份的密码学证明，仍需人工确认端点和账号，不能只把生产库重命名后运行。

脚本仅操作本次生成的playbook_test_<uuid> schema，包含一张合成表。失败、异常也尝试DROP自身schema并查询pg_namespace复查；清理失败输出本次schema编号供人工核实，不批量删除其他schema。连接与SQL有等待预算，stderr不直接输出；权限不足或网络中断返回非零。SIGKILL/断电无法保证finally执行，仍须按打印的本次归属排查。

这是隔离生命周期冒烟，不是应用迁移、权限或SQL性能验证。将实际数据库回归拆分到自己的隔离夹具中。纳入verify时还要给外层resources声明cleanup/residual_check，或让测试框架自身受控清理并提供残留审计；不能设置none却实际创建共享资源。

本仓库默认回归用Fake runner验证保护、失败清理及复查路径，不自动连接数据库。真实隔离集群验证可通过tests/test_adapters.py中显式环境开关开启，未开启的运行不得报告真实PostgreSQL已验证。
