---
name: mono-start
description: 在 Mono 工作区开始或接手一个跨项目需求，核对系统关系、共享规格、接口、实施与测试计划，并按需建立隔离任务工作树。
---

# 推进跨项目需求

读根目录 AGENTS.md、mono.json 和系统关系。已有任务先读取 tasks/需求号 下的规格、计划、验证与交付记录，再到对应工作树核对任务版本、项目规则和当前改动。

成员刚克隆协调仓、还不熟悉业务仓时，运行 python3 -B scripts/mono.py bootstrap，将清单内的 Git 业务仓恢复到 repos/。已知只需要哪些项目时，可以在 bootstrap 后指定项目名。具体用法见根 README.md。

启动新任务时，从 mono.json 和系统关系找候选仓。范围不明确时，运行 python3 -B scripts/mono.py baselines --sync 获取全部已登记 Git 仓的目标提交并快进干净的 detached 接入检出；范围较明确时可以指定候选项目。它返回 path、base_ref、base_sha 和 checkout_state。跟踪调用链发现新的候选仓时，补查其目标提交。

以目标提交的项目规则、代码入口、接口和测试判断影响范围。checkout_state 为 current 或 updated 时，可从 PATH 阅读并核对 HEAD 等于 base_sha。其余状态表示有本地改动、本地分支、历史分叉或 Git 拒绝切换，保留检出，在 Git 里直接读目标提交。用 git -C PATH ls-tree -r --name-only SHA 定位目录，用 git -C PATH grep -n PATTERN SHA 和 git -C PATH show SHA:文件路径 阅读内容。远端查询失败时，先解决访问或目标分支问题。用户明确复现历史版本或离线开工时，可以用约定的本地提交做同样的分析。

新任务把用户目标整理成 id、title、goal、owner、projects、contract 和 acceptance 的 JSON。projects 显式列出需要改动或需要单独任务版本的仓库。未知的业务取舍可以先记录为待决事项。用 scripts/mono.py new INPUT --worktrees 为参与仓创建工作树，并由 Agent 为各仓传入 --base 项目=已分析的SHA。把分析所用的目标分支和提交记入 plan.md，使分析与开工使用同一版本。联调时记录各依赖的实际受测版本。

每项新需求使用团队内唯一的任务号。纯流程或无需独立分支时省略 --worktrees。目标已存在时继续已有任务，共有记录提交到协调仓，业务分支推送到各自的业务仓。

在 task.md 和 task.json 中统一规格，给验收条目编号并描述初始数据、操作和可观察的预期。在 plan.md 定位各仓实际入口，说明共用契约、改动、测试映射、兼容顺序及失败恢复。先用现有测试与已知基线核对环境，再按已获授权实现。只有涉及未决定的业务规则或需要额外授权的动作才等待用户输入，其余在范围内继续。

Agent 负责跨仓实现和验证。需求负责人协调取舍及结果，代码评审和发布沿用项目安排。遇到诊断任务记录复现与日志证据。阶段结束或交接时写明已完成事项、工作树位置、相关版本、下一步和待决问题。联合验收时读取 mono-verify。

仓库有 STDD/SDD 时，读取 docs/mono/stdd-sdd.md。用 scripts/mono.py status 任务号 找到各仓的工作树与技能路径，按各仓实际规范确认基线、合入目标和本地变更编号。new 的 --base 和 --branch 支持逐仓选择。用 scripts/mono.py stdd 任务号 项目名 本仓变更ID --title 标题 调用仓内原生模板或关联已有变更，再按该仓 stdd-start、stdd-delivery 或相应 SDD 流程推进。各仓的规格和确认按其规则记录，全链路契约写入 Mono。
