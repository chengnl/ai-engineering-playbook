# Java / Spring适配

前置：项目选定JDK及Maven/Gradle，具有实际业务测试。版本、格式化插件和构建配置由项目固定；此适配不安装Spring或指定统一框架版本。

1. 配置Maven Wrapper并按项目选择格式化工具；使用clean test保证旧class不残留。格式化插件未配置时不得照搬fmt:check当作已检查。
2. 按职责包组织controller/service/repository/policy；将JAVA-01～12逐项绑定测试或人工检查。
3. clean编译后运行直接依赖检查：

```bash
python3 .engineering/adapters/java-spring/check_layers.py --classes target/classes --base-package com.example
```

检查controller→repository/JDBC、service→JDBC、repository→service/ModelGateway及policy→repository/JDBC/ModelGateway；缺class、错误包名或空依赖均不通过。它使用JDK jdeps，不需要ArchUnit依赖；反射、间接依赖、循环依赖、ORM调用和SQL字符串不在自动覆盖范围，仍需测试/评审。不能把该门禁等同完整Spring架构审核。

配置例（合并到项目checks，不是可直接运行的完整profile）：

```json
{"id":"java-unit","argv":["./mvnw","-B","clean","test"],"timeout_seconds":900,"purpose":"已拆分的离线Java测试","resources":{"mode":"none","reason":"数据库/真实模型测试已独立分组；仅本地构建产物"}}
```

若实际Maven test包含数据库/模型，这个声明就不成立，必须拆分用例并配置隔离资源。分层门禁应作为另一个check在编译之后执行，使用不同稳定ID。
