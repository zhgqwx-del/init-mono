# Mono 工作入口

先看 mono.json 与 docs/mono/system.md，了解项目职责、位置、关系及基线。进入各应用目录后读取其 AGENTS.md 等项目规范。

- 新需求或接手已有需求使用 .agents/skills/mono-start/SKILL.md。同一需求的规格、版本、实施与验证记录在 tasks/需求号 中。
- 联调、复跑和验收使用 .agents/skills/mono-verify/SKILL.md。
- 交接、发布准备与复盘使用 .agents/skills/mono-wrap/SKILL.md。
- 系统知识与架构决定查 docs/mono/decisions.md。启动、测试数据、日志和恢复查 docs/mono/operations.md。按需读取相关项目与资料。
- 在根目录管理共享上下文，进入具体项目目录再提交应用代码。用一个需求负责人协调跨项目结果，沿用现有项目的评审和权限安排。
