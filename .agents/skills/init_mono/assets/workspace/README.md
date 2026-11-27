# Mono 协作空间

从 [系统关系](docs/mono/system.md) 了解已接入项目，从 [联调与发布](docs/mono/operations.md) 核对环境、数据、命令和访问范围。mono.json 是项目清单，repos/ 中是已接入的独立检出。Python 工具需要 Python 3.9 或以上版本以及 Git。

## 克隆协调仓后恢复项目

从协调仓根目录运行：

    python3 -B scripts/mono.py bootstrap

默认恢复 mono.json 中所有登记了基线的 Git 业务仓，按各仓的 `base_sha` 检出到 `repos/<项目>`。首次接手可直接拉齐全部业务仓，再按任务选开发范围。指定项目名时只恢复所选项目，例如 `bootstrap frontend auth-api`。重跑会保留已有检出。各成员使用自己的 Git 凭据和业务仓权限。清单的克隆入口来自 `clone_source` 或 Git URL 形式的 `source`。旧清单可用 `--source 项目=Git_URL` 临时指定克隆入口。

每位成员用自己的任务号创建 feature。协调仓提交和共享 `tasks/<任务号>/` 中的契约与证据，业务改动在各自的任务工作树提交并推送到各业务远端。根目录的 `.gitignore` 已忽略 `repos/` 和 `work/`。

## 从一项需求开始

在协调仓根目录给 Agent 需求号、目标和验收判据，使用 $mono-start。Agent 会通过 `python3 -B scripts/mono.py baselines --sync` 获取候选仓的最新目标提交，快进干净的 detached `repos/` 检出，然后根据目标版本的代码确定影响范围。命令可指定候选项目，省略项目名时处理已登记的 Git 业务仓。有本地改动、正在使用本地分支、历史已分叉或 Git 阻止切换时，Agent 会从 Git 读取已获取的目标提交。Agent 为需要任务版本的仓库建工作树并使用分析时的 SHA。

也可以保存任务 JSON 并直接执行以下命令。

    python3 scripts/mono.py new /path/to/task.json --worktrees

任务输入包含 id、title、goal，可选 owner、projects、contract 和 acceptance。显式填写 projects 可限定参与仓，省略时采用清单中的所有项目。acceptance 每项有 id、check、expected，未提供验收规则时会创建待补的草稿。--worktrees 在 work/需求号/ 下为参与的 Git 项目建立独立任务工作树，省略时任务使用原有检出。

普通新任务会查询参与仓的远端目标分支，并获取所需提交。可在 mono.json 为项目设置 `target_branch`，如 `develop`。省略时沿用已登记的 `origin/<分支>`，其余使用远端默认分支。远端访问或目标分支有问题时会停止创建。只在本地运行且没有远端的项目使用接入检出的 HEAD。用 `--base 项目=引用` 可以固定到本地已有提交，适用于复现和离线开发。

`repos/` 是业务仓的长期接入入口。新任务的 Git worktree 从这里创建，独立克隆模式下还共享这里的 Git 数据。`baselines --sync` 会尝试移动接入检出。已有任务工作树保留各自版本，省略 `--worktrees` 创建的任务仍引用共享的接入检出。任务完成后的清理范围是已交付任务的工作树。

## 技能顺序

| 技能 | 输入 | 产出 |
|---|---|---|
| mono-start | 需求目标或已有任务目录 | 共同规格、影响面、接口决定、实施与测试计划、任务工作树 |
| mono-verify | 同一规格、各项目当前改动和测试环境 | 实际结果、命令回执、受测版本、复跑结果及待决事项 |
| mono-wrap | 评审与验收结果、项目发布规则 | 交接或交付记录、发布恢复安排、复盘和知识更新 |

[工作流程](docs/mono/workflow.md) 写明各角色如何参与。只需创建协作流程时，可以先补充这些文档和项目入口。

## 记录一次真实验证

从根目录执行测试，把命令放在 -- 后面，参数会原样传给该命令。--cwd 指定命令的运行目录，相对值以工作区根目录为准。下面的路径和 AC 编号按实际需求填写。

    python3 scripts/mono.py run OPS-218 --ac AC01 --cwd work/OPS-218/ops-api -- python3 -m unittest

回执保存在 tasks/OPS-218/evidence/ 中，包含命令、输出、退出码、各项目提交和文件摘要。只有命令断言确实覆盖的 AC 才传 --ac，可以多次传入。

将 verification.json 中对应项填为 passed，写出实际结果，并引用回执相对路径，如 evidence/run-xxxx.json。执行以下命令核对证据与当前规格及代码是否仍相符。

    python3 scripts/mono.py check OPS-218

退出码为零表示结构化证据与当前版本相符。业务判断和代码评审由相应负责人确认，记入 human_decision。初次生成的判据状态为 pending。新改动、失败测试、缺失证据和未接入项目会在核对时列为待验证。

## 持续维护

把有复用价值的系统知识和决定写回 docs/mono。新的需求使用新的任务号和工作树。已有任务接手时读取任务、计划、验收和交付记录，记录当前阻塞及下一步。清理工作树前确认改动已保存，使用对应项目的 git worktree remove，保留任务记录。

## 追加项目与对接 STDD/SDD

在协作根运行 python3 -B scripts/mono.py add NAME SOURCE --role "职责"。SOURCE 可为 GitHub 或 GitLab 的 Git 地址、已有本地 Git 仓库、普通资料目录。运行 python3 -B scripts/mono.py repos 查看已接入项目。[仓库清单](docs/mono/projects.md) 会随登记更新。

从 [STDD/SDD 对接说明](docs/mono/stdd-sdd.md) 获取完整示例。new 支持 --base 项目=Git引用 和 --branch 项目=分支名。status 任务号 显示任务工作树、实际 SHA 和仓内入口。需要生成 STDD 变更时，用 stdd 任务号 项目名 本仓变更ID --title "标题" 调用本仓模板，已有变更用原 ID 直接关联。
