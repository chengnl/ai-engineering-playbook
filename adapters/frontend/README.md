# 前端适配

适用原生JS、Vue、React等；业务项目自己选择框架和固定依赖，不能只跑教学夹具就声称应用验证完成。

可运行的框架无关例子：

```bash
node --check .engineering/adapters/frontend/fixtures/latest-loader.mjs
node --test .engineering/adapters/frontend/fixtures/latest-loader.test.mjs
```

两个用例分别检查旧响应不覆盖新结果、dispose后不回写。没有启动浏览器、没有验证UI或后端权限。错误反馈、取消外部请求、键盘/焦点、手机、跨页选择和未知写结果仍需项目自己的浏览器/接口测试。

绑定真实应用时，以`npm ci --ignore-scripts`或项目已审查的依赖策略保证锁文件可复现；把格式/语法、单测、浏览器分别配置。浏览器进程若创建临时账号/目录，resources使用isolated并提供归属清理/复查；不允许通过清空生产或共享数据实现隔离。项目没有浏览器场景可写明确不适用理由，不能留空组后称all通过。
