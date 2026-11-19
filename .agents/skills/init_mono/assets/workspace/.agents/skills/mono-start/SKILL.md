---
name: mono-start
description: 在 Mono 工作区开始或接手一个跨项目需求，核对系统关系、共享规格、接口、实施与测试计划，并按需建立隔离任务工作树。
---

# 推进跨项目需求

读根目录 AGENTS.md、mono.json、系统关系和相关项目规则。已有任务先读取 tasks/需求号 下的规格、计划、验证与交付记录，核对当时的版本和当前改动。

新任务把用户目标整理成 id、title、goal、owner、projects、contract 和 acceptance 的 JSON。projects 只列涉及项目。未知的业务取舍进入待决列表，可按已有资料先生成任务草稿。用 scripts/mono.py new INPUT --worktrees 创建新任务及任务工作树，纯流程或无需独立分支时省略 --worktrees。目标已存在时继续已有任务。

在 task.md 和 task.json 中统一规格，给验收条目编号并描述初始数据、操作和可观察的预期。在 plan.md 定位各仓实际入口，说明共用契约、改动、测试映射、兼容顺序及失败恢复。先用现有测试与已知基线核对环境，再按已获授权实现。只有涉及未决定的业务规则或需要额外授权的动作才等待用户输入，其余在范围内继续。

Agent 负责跨仓实现和验证。需求负责人协调取舍及结果，代码评审和发布沿用项目安排。遇到诊断任务记录复现与日志证据。阶段结束或交接时写明已完成事项、工作树位置、相关版本、下一步和待决问题。联合验收时读取 mono-verify。

仓库有 STDD/SDD 时，读取 docs/mono/stdd-sdd.md。用 scripts/mono.py status 任务号 找到各仓的工作树与技能路径，按各仓实际规范确认基线、合入目标和本地变更编号。new 的 --base 和 --branch 支持逐仓选择。用 scripts/mono.py stdd 任务号 项目名 本仓变更ID --title 标题 调用仓内原生模板或关联已有变更，再按该仓 stdd-start、stdd-delivery 或相应 SDD 流程推进。各仓的规格和确认按其规则记录，全链路契约写入 Mono。
