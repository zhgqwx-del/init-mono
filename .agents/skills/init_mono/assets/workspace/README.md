# Mono 协作空间

从 [系统关系](docs/mono/system.md) 了解已接入项目，从 [联调与发布](docs/mono/operations.md) 核对环境、数据、命令和访问范围。mono.json 是项目清单，repos/ 中是已接入的独立检出。Python 工具需要 Python 3.9 或以上版本以及 Git。

## 从一项需求开始

给 Agent 需求号、目标、涉及项目和验收判据，使用 $mono-start。也可以保存任务 JSON 并执行以下命令。

    python3 scripts/mono.py new /path/to/task.json --worktrees

任务输入包含 id、title、goal，可选 owner、projects、contract 和 acceptance。projects 引用 mono.json 中的项目名，acceptance 每项有 id、check、expected。验收规则未提供时创建待补的草稿。--worktrees 会在 work/需求号/ 下为已检出的项目创建独立任务分支，供 Agent 改动。暂未检出的项目通过原位置和说明接入。省略 --worktrees 时任务使用原有检出。

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
