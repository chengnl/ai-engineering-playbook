# 本项目AI研发规范入口

先读project.json，完成技术栈、角色/数据边界、现行知识、环境与Git授权、测试资源清理和检查命令适配。默认needs-adaptation不是可以交付的业务工程。

## 日常使用

每次新会话读本入口、project.json、[协作规则](../standards/collaboration.md)、适用技术规则及[轻量SDD](../workflows/sdd.md)。

- 简化变更：问题/预期/范围/实际验证合在一份记录。
- 标准或增强：从templates复制spec及change.json到specs/changes/<id>/，关联R需求、T任务、A验收和真实证据；示例占位不得当成通过。
- 按项目知识入口同步最终行为，历史变更记录保留；提交/合并前核对README、索引和实际检查结果。

## 命令适配

project.json的checks按组填写argv数组、timeout_seconds与明确的purpose；只执行已审查的项目本机测试命令，不放密码、生产端点或模型付费脚本。例如：

```json
{"argv": ["mvn", "-B", "test"], "timeout_seconds": 600, "purpose": "本项目离线Java测试"}
```

示例不证明目标项目全部测试离线；数据库或真实模型测试需自行拆分隔离。status完成适配后显式改为ready；工具不能判断环境声明是否真实。

```bash
python3 .engineering/tools/check.py --docs .engineering --trace specs/changes/<id>/change.json
python3 .engineering/tools/verify.py --project . --group offline
```

未配置、未适配、非法命令、非零退出或超时不会记成功。不增加生产保护或OS沙箱，执行前人工/AI审阅配置。日志由命令自己控制，不输出真实客户数据。

## 版本与能力边界

manifest.json记录采用版本和复制文件的初始摘要；本地修改不自动被覆盖。新版本从规范库比较差异后手动迁移并验证，禁止直接重跑bootstrap覆盖。没有自动CI/部署、模型或网络调用。

链接检查只校验相对Markdown目标文件，不验证外网、锚点或业务一致性；JSON追踪检查只验证关联、状态和证据文件存在，不证明证据真实。技术规范仍需项目评审和对应测试工具。
