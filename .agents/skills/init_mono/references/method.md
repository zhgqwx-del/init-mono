# 方法来源与具体落点

Manus 公开复盘把 Mono 描述为其内部统一入口，代码仍分仓。它向 Agent 提供仓库关系和架构决定，逐步补上本地验证、生产问题诊断、发布执行和真实端到端测试。人保留业务取舍、合并和发布判断。团队也披露了并行过多与决策积压的问题。[Manus 官方复盘](https://www.manus.im/zh-cn/blog/rebuilding-manus-with-manus)

本脚手架依据这些实践设计。下表对应本实现的交付内容。

| 方法 | 脚手架落点 |
|---|---|
| 给 Agent 系统上下文并按需读取 | AGENTS.md、mono.json、docs/mono/system.md 与各仓规则 |
| 保存决策原因并跨会话复用 | docs/mono/decisions.md 与来源链接 |
| 按需求对结果负责并减少反复交接 | 任务规格、mono-start、人和 Agent 分工、plan.md 及接手记录 |
| Git 隔离与按需接入 | worktree、clone、reference，独立任务工作树和各仓版本 |
| 本地快速验证及真实流程 | 联调手册、mono-verify、既有项目测试和跨项目断言 |
| 受限的生产诊断入口 | 联调手册中的日志、配置、账号与实际访问范围 |
| 发布、审批及恢复 | mono-wrap、项目既有流程、delivery.md |
| 版本与验收证据一致 | 命令回执、SHA、文件摘要及规格摘要检查 |
| 让知识沉淀并跟踪真实收益 | 复盘周期、人工投入、等待返工及共享文档更新 |

项目自身的启动、数据、日志、CI、发布系统和权限需要按已有能力接入。初始化会建立这些能力的说明入口，实际可执行程度取决于提供的项目及环境。验收命令应包含业务断言，回执检查用于核对记录与版本，人工判断仍写明结论与负责人。

OpenAI 关于 Agent 工程的实践同样强调短入口、结构化知识与可重复反馈。当前技能目录及按需加载行为可参照官方说明。[Harness Engineering](https://openai.com/index/harness-engineering/)，[技能说明](https://learn.chatgpt.com/docs/build-skills)
