# 本项目AI研发规范入口（v0.3）

先读project.json，完成业务、技术栈/none理由、适用规范、非生产环境、知识入口、source_paths、Git授权、测试资源与检查命令适配。默认needs-adaptation不是可交付业务工程。

## 日常流程

每次新会话读本入口、project.json、[协作规则](../standards/collaboration.md)、适用技术规则及[轻量SDD](../workflows/sdd.md)。简化变更合并记录即可；标准/增强从templates复制spec和schema 2 change.json到specs/changes/<id>/，关联R、T、A与实际JSON证据。知识按[文档规范](../standards/documentation.md)维护：当前主题整合更新，设计/验收/发布保留历史和替代关系；合并前清理本轮重复、矛盾、过时描述和失效引用。新项目docs带分类索引，尚无业务正文；已有docs完全保留，需人工适配。

## 检查命令

ready前所有组须配置检查或`{"not_applicable_reason":"具体理由"}`。单个不适用组不执行，all可跳过已声明不适用组但至少要运行一条真实命令。

无外部资源示例（须审查真实测试内容）：

```json
{"id":"java-unit","argv":["./mvnw","-B","clean","test"],"timeout_seconds":900,"grace_seconds":3,"purpose":"已拆分的离线Java测试","resources":{"mode":"none","reason":"数据库/真实模型用例独立，仅本地构建产物"}}
```

若创建schema/容器等，resources必须为isolated，包含ownership、cleanup和residual_check；两个hook分别有argv、timeout_seconds，可有grace_seconds。清理按本次资源归属，不能DROP业务库或清空共享目录。环境与端点声明由项目审查，工具不是安全沙箱。

```bash
python3 .engineering/tools/check.py --project .
python3 .engineering/tools/verify.py --project . --group offline --spec specs/changes/feature/spec.md --evidence-dir specs/changes/feature/evidence
python3 .engineering/tools/check.py --docs .engineering --trace specs/changes/feature/change.json --project .
```

路径示意必须替换为实际变更。自动证据记录命令、时间、环境、返回码、资源结果、源码/配置和规格摘要；A.evidence写`{"kind":"automated","check_id":"java-unit","path":"evidence/实际文件.json"}`。手工验收参照manual-evidence.json填写责任人、步骤和观察，不得标榜为自动测试。

## 版本与能力

规范、模板、工具、adapters按固定版本复制，manifest保存初始摘要；本地适配不自动覆盖。schema 1需显式迁移，新工具不会默认接受旧completed。没有自动CI/部署/模型调用；可选适配包在adapters，必须按实际项目绑定。

结构校验不证明业务正确；证据不是签名，不抵御有意伪造。source_paths漏列的文件不被指纹覆盖，需要评审；外部副作用不会随本地取消自动撤销。SIGKILL/断电后仍需人工按本次归属检查残留。

## 方案与知识复查

出方案前先审视业务目标/规则/例外/衡量、产品流程/交互/状态/恢复、技术架构/兼容/成本/可靠性/测试/回退，记录综合推荐、主要取舍和验证标准。小改动可简写，不为实现增加无必要复杂度，不额外增加审批或多代理要求。

交付前复查实际diff工程符合性，不以测试通过代替规范自查。发布、里程碑或方案替代时人工复查受影响知识及历史链接，记录发现、处理、遗留及复查条件；没有自动巡检或语义审核。
