# Java工程开发规范

适用：采用Java的项目；Spring/JDBC例子不是对所有项目的技术栈规定。MUST必须；SHOULD应当，偏离需登记原因。规则尚需绑定项目检查，不因本文件存在就自动生效。

## 模块与职责

- **JAVA-01 MUST** 按业务模块组织，再按controller/service/repository/policy/model/dto/adapter/job/config等实际职责分包；测试与职责包对应。不创建空层，不为改包批量扩大public。
- **JAVA-02 MUST** Controller适配协议/参数/身份并调用用例；Service组织业务、访问范围和事务；Repository处理SQL/映射/分页/锁。Service不执行SQL，Controller不越层调用Repository，Repository不调用业务Service或模型。
- **JAVA-03 SHOULD** 独立纯规则提取Policy；真正的可替换边界才建接口，不机械建立Service/ServiceImpl。跨模块写入走明确用例入口，禁止业务循环依赖。
- **JAVA-04 MUST** 数据库事务中不等待模型/长外部HTTP。准备、外调、短事务重验并写入；重验权限、归属、状态和版本，防止过期结果覆盖。

## 编码与契约

- **JAVA-05 MUST** 对外DTO明确字段类型、可空、默认值和校验；禁止由客户端绑定角色/owner等服务端字段。状态集中定义，业务错误与内部异常分离，提供安全的追踪编号。
- **JAVA-06 SHOULD** 构造器注入、不可变值对象、明确资源生命周期；Optional用于可缺失返回值，不滥用为所有字段。集合不返回含义不明的null，可变集合边界有说明；泛型不退化为无校验Object。
- **JAVA-07 SHOULD** 命名体现职责、使用统一格式化工具；避免星号导入和超长混合类。类约400行、方法约60行、构造依赖约6项触发职责复查，是评审信号而非机械拆分目标。
- **JAVA-08 MUST** 异常不静默吞掉；保留安全分类和必要原因，不泄漏SQL、凭据或客户正文。文件/连接等资源使用明确关闭机制，异步上下文结束清理。
- **JAVA-09 MUST** 外部调用说明次数、并发、deadline、连接/读取超时、重试、取消和结果未知。虚拟线程不是容量限制；不能承诺cancel后供应商一定停止计费。
- **JAVA-10 MUST** 重复提交/并发写有版本、唯一约束或适当锁及固定锁顺序；请求编号不是幂等键。网络未知结果不自动盲重发。

## 工具与检查

- **JAVA-11 MUST** 项目记录JDK、构建工具、依赖版本及升级验证；禁止动态latest依赖。改包做clean构建并检查旧类不残留。
- **JAVA-12 SHOULD** 配置格式、单测、真实数据库和编译后分层门禁。基线例外精确到职责和范围，不能全仓豁免。

正例：订单Service短事务检查版本后保存；通知外调在事务外执行。反例：Controller直接拼SQL，Repository反调Service，或在持有订单行锁时等待模型。
