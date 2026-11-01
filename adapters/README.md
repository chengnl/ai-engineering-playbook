# 技术栈适配包

适配包提供可执行样例和检查配置，不是自动建立业务框架或证明全规范符合。初始化会复制到目标`.engineering/adapters`，不自动安装JDK/Node/PostgreSQL、不配置CI、不连接数据库。

- [Java / Spring职责边界](java-spring/README.md)：JDK jdeps直接依赖门禁，须先clean编译。
- [前端](frontend/README.md)：Node语法/单测及迟到响应/销毁的可运行夹具，浏览器测试由项目绑定。
- [PostgreSQL](postgresql/README.md)：显式授权、专用测试库名、唯一临时schema及finally清理/复查；不读取任何业务库配置。

project.json要补业务信息、适用规范、知识、环境与source_paths；检查片段不能直接将项目标ready。暂不适用的技术/检查组必须写理由，不把空数组当通过。
