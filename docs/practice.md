# Mono 与 STDD/SDD 实践手册

Mono 把一个跨仓需求的上下文与交付结果放在同一处。STDD/SDD 在各业务仓内部维持规格、实现、测试和评审的对应关系。本手册适用于已有前后端仓库、希望一名需求负责人带着 Coding Agent 完成跨仓开发的团队。

## 选择接入方式

| 你手上的项目 | 入口 | 结果 |
|---|---|---|
| 已有本地 Git 克隆 | 填写仓库根路径，使用 auto 或 worktree | 在协作目录建立工作树，沿用源仓 Git 历史 |
| 有 GitHub/GitLab Git 地址 | 填写 Git 地址，使用 auto 或 clone | 独立克隆到 repos/项目 |
| 只有文档、本地资料或暂不可访问的仓库 | 使用 reference，或将整个空间设为 process | 记录位置、职责和待补信息 |
| 要让多项需求使用同一套记录 | kind 选 repository | 协调仓记录上下文和交付资料，业务代码各仓管理 |

初始化时提供项目名、地址或目录，能确认的职责、基线和启动命令一并填写。项目间依赖写进 mono.json 或 docs/mono/system.md。持久的契约取舍及其原因写进 docs/mono/decisions.md。运行方式、环境和测试数据记在 operations.md。源码保存在各业务仓的独立检出和任务工作树。

## 按 feature 工作

| 阶段 | Mono 的动作 | 业务仓的动作 |
|---|---|---|
| 开工 | $mono-start 定义任务、共同契约、受影响仓、集成验收判据 | 各仓读取本地 AGENTS.md 与规格，按 stdd-start 确认本仓基线、变更范围和实施计划 |
| 实现 | 同一任务号下建立各仓工作树，记录调用链与兼容约定 | 由 stdd-delivery 或仓内流程先写验收测试，再实现和复跑 |
| 验收 | $mono-verify 运行真实跨服务流程，记录各仓受测提交与 actual | 走原有测试入口，并用 stdd-test-report 整理本仓验证记录 |
| 交接 | $mono-wrap 汇总各仓 PR、合入与发布依赖、恢复方式 | 各仓按 stdd-wrap 整理规格、归档与候选 PR |

以登录需求为例，在 Mono 的 tasks/FEAT-LOGIN 写下共同接口、成功和失败行为以及兼容规则。前端可以使用 014-login，账号服务可以使用 021-login。两个 ID 都关联到同一个 Mono feature。每仓仍用自己的 REQ/AC 编号，联合验收可以链接到各仓用例。涉及第三个服务时，先明确它在调用链里的职责，再决定是否纳入本次工作树。[登录示例](../examples/stdd-feature/README.md)

### 仓内技能怎样使用

scripts/mono.py status 任务号 会报告工作树、分支、当前提交和发现的四个 STDD 入口 stdd-start、stdd-delivery、stdd-test-report、stdd-wrap。Coding Agent 进入对应工作树后读取各仓自己的技能。scripts/mono.py stdd 在该任务登记的分支调用原生 new_change.py 创建变更，或关联已有变更，关联保存在 tasks/任务号/stdd.json。

其余仓内技能按场景用。stdd-review 适用于候选 PR 和合入评审，stdd-diagnose 适用于复现缺陷和形成回归用例，stdd-release-notes 适用于已确定版本范围的发布说明。这三项由 Agent 按仓内流程读取。纯 SDD 或普通 Git 仓使用各自实际的规范和命令。[工具对接说明](../.agents/skills/init_mono/assets/workspace/docs/mono/stdd-sdd.md)

## 收集能复跑的证据

先用已知基线跑通真实依赖。变更后逐仓执行检查，再从用户入口跑到实际服务。例如登录应使用测试账号验证浏览器、认证服务以及受保护页面。记录实际结果、测试数据和环境版本，只有对应到真实断言的验证命令才关联该条验收判据。

scripts/mono.py run 记录受测状态、命令、退出情况和输出，scripts/mono.py check 核对回执是否仍匹配代码和规格。测试证据过期时，复跑受影响的用例。业务验收与上线结论由有权限的负责人记录。

发布顺序取决于兼容约定。可兼容旧客户端的服务端能力通常可以先发布，再切换调用方。停止条件、回滚动作和审批人沿用实际项目。生产日志、CI 和发布系统由团队按已有入口接入。

## 维护长期有效的协作空间

每项需求用自己的任务号与工作树。启动下一项需求前核对各仓合入目标，必要时刷新引用，再用 new 的 --base 和 --branch 选择基线与分支。追加项目后，更新调用关系；已有任务仍按其记录的范围验证。

共享文档记录需要跨仓复用的信息。各仓内部规则、测试计划和业务规格由该仓继续维护。复盘可以记录需求确认到验收的时间、人工投入、等待和返工，用后续需求判断跨仓交接有没有减少。

[快速上手](../QUICKSTART.md) · [示例导航](../examples/README.md) · [Manus Mono 官方复盘](https://www.manus.im/zh-cn/blog/rebuilding-manus-with-manus)
