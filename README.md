# init_mono 跨项目协作脚手架

用一个需求入口接手多个独立项目，让同一个 feature 的规格、接口、实现和验收贯穿各仓库。init_mono 根据项目输入生成系统上下文、联调手册、隔离任务工作树，以及后续开发和验收技能。

本项目借鉴 Manus Mono 的共享上下文与端到端交付实践。方法与实现的对应关系见[说明](.agents/skills/init_mono/references/method.md)。

## 日常使用

一个 Mono 根目录接入一组可以持续协作的项目。远端 GitHub/GitLab 地址会独立 clone，已有本地 Git 仓库通过 worktree 接入，普通资料目录登记为 reference。Git 协调仓库记录系统关系、需求与联合验收，业务仓独立管理版本。

- 初始化与升级使用 init_mono。已有工作区可运行初始化脚本的 --upgrade WORKSPACE，保留项目与需求记录。
- 新项目用 scripts/mono.py add NAME SOURCE 登记，无需重建。scripts/mono.py repos 查看清单。
- 每个 feature 选参与仓库，在 work/需求号/ 下建立各仓工作树。支持按仓指定 --base 和 --branch。
- 业务仓的 STDD/SDD 继续负责单仓规格、变更、测试和归档。status 读取各仓入口，stdd 调用原生变更模板或关联已有变更。Mono 记录共同契约、实际跨服务验收和发布依赖。

[现有 STDD 仓库接入与登录需求示例](examples/stdd-feature/README.md)


## 先跑一个前端加两个后端的 feature

[三仓实操教程](examples/three-services/README.md) 以活动名额为例，演示接手已有项目后，新增「展示剩余名额并筛选可报名活动」。

| 仓库 | 负责的改动 |
|---|---|
| portal-web | 名额列、筛选和翻页交互 |
| campaign-api | 聚合名额，筛选后计数和分页 |
| capacity-api | 批量名额、数据隔离与错误行为 |

旧项目种子、参考补丁和测试工具都在本仓库，应用运行需要 Python 3.9+ 和 Git。目标目录用新位置。

~~~sh
python3 -B examples/three-services/demo.py setup ../mono-use-demo
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage baseline
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage feature
~~~

第三条此时应失败，因为旧系统尚无批量名额能力。再由 Agent 跨仓开发，或应用参考实现。

~~~sh
python3 -B examples/three-services/demo.py apply ../mono-use-demo
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage feature
python3 -B examples/three-services/demo.py serve ../mono-use-demo
~~~

打开 [本机活动列表](http://127.0.0.1:4280/)。HTTP 验收覆盖两个后端和前端代理。需要真实浏览器操作时，按教程准备 Node、Playwright 和 Chromium，再运行 browser 与 check。可以查看[已完成的实际结果](examples/three-services/evidence/result.json)。

![三仓 feature 的真实浏览器结果](examples/three-services/evidence/feature-desktop.png)

## 四个技能怎样配合

| 技能 | 输入 | 输出 |
|---|---|---|
| init_mono | 项目清单、职责、调用关系和运行信息 | 协作目录、Git 协调仓库或流程 |
| mono-start | 一个 feature 或已有任务 | 共用规格、影响分析、实施计划和各仓任务分支 |
| mono-verify | 规格、改动和测试环境 | 实际结果、各仓版本回执及旧证据检查 |
| mono-wrap | 验收与评审结果 | 交接、发布恢复、复盘及知识更新 |

在 Agent 中打开生成的 workspace，使用 $mono-start 开始需求。三个工作区技能按需读取系统地图、各仓规则和历史决定。源码在 [.agents/skills/init_mono](.agents/skills/init_mono/SKILL.md)，可直接分发的技能包是 [init_mono.zip](init_mono.zip)。

## 接入自己的项目

将[三项目输入模板](examples/three-services/adopt-existing.json)中的路径、职责、基线与调用关系换成实际值，也可以直接向 Agent 提供这些信息。

> 用 $init_mono 在 /work/product-mono 创建协作仓库。前端在 /work/frontend，后端一在 /work/backend-one，后端二在 /work/backend-two。前端调用后端一，后端一聚合后端二。接入各仓规则与运行方式，并为第一个 feature 创建共同规格、任务工作树和联合验收流程。

也可以从仓库外运行脚本，INPUT 和 TARGET 替换成实际路径。

~~~sh
python3 -B .agents/skills/init_mono/scripts/init_mono.py INPUT TARGET --dry-run
python3 -B .agents/skills/init_mono/scripts/init_mono.py INPUT TARGET
~~~

[输入说明](.agents/skills/init_mono/references/inputs.md) 覆盖 worktree、clone、reference，以及 directory、repository、process 三种输出。暂时只有流程资料时可使用[流程输入示例](examples/process-only.json)，它生成共享说明与技能，未知的运行条件保留待补。

~~~sh
python3 -B .agents/skills/init_mono/scripts/init_mono.py examples/process-only.json ../mono-process-demo
~~~

生成后共享知识在 docs/mono，各需求在 tasks，各仓独立任务工作树在 work。新任务以当前接入版本为基线，开工前核对并按需要更新到已合并版本。

## 仓库与发布

~~~text
.agents/skills/init_mono/       技能源码与生成模板
examples/three-services/        三仓旧代码 参考补丁 教程与验收
examples/stdd-feature/          STDD 仓库接入与登录需求输入
examples/process-only.json     仅流程的输入例子
scripts/package_skill.py       可重现的技能 ZIP 打包
tests/                         脚手架行为测试
.github/workflows/check.yml    推送和 PR 的验证流程
~~~

本地演练产生的 Git 工作树和机器路径不进入本仓库。setup 会从种子重建它们。技能 ZIP 可解压到项目的 .agents/skills，或在项目外运行其中的初始化器。

~~~sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/package_skill.py --check
~~~

[GitHub 发布步骤](docs/github.md) 包含创建远端、推送和发布技能 ZIP 的命令。[初始版本说明](docs/release-notes.md) 可作为发布内容。GitHub Actions 配置会在推送后运行；当前验证结果来自本地实际执行。

## 运行能力的接入

脚手架保存共同契约、决定与可复跑验证。生产日志、CI、发布系统和权限使用各项目已有入口。自动回执核对结果所对应的代码和规格，产品判断和上线结论由相应负责人记录。
