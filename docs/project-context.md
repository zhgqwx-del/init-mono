# 项目认知与维护指南

本文面向维护本脚手架的开发者与 Coding Agent，提供新会话接手所需的结构、机制和检查入口。面向使用者的操作说明见 [README](../README.md)、[快速上手](../QUICKSTART.md)与[实践手册](practice.md)。行为以当前源码和测试为准；结构、机制或维护约定变化时同步更新本文。

## 新会话如何接手

1. 读根目录 [AGENTS.md](../AGENTS.md) 和本文，运行 `git status --short`，核对当前分支及已有改动。
2. 从下方源码地图定位受影响的模块，再读对应的输入说明、模板与测试。维护脚手架和使用生成的 Mono 工作区是两类工作，先确认当前任务的目标。
3. 涉及使用流程时参考[快速上手](../QUICKSTART.md)；涉及完整跨仓行为时参考[三仓演练](../examples/three-services/README.md)；涉及发布时参考[发布步骤](github.md)。
4. 按改动范围完成检查，记录本次实际执行的验证及限制。历史验证结果只作为接手背景。

## 项目目标与职责分工

init_mono 从一组已有项目生成跨仓协作空间，让一项 feature 共用契约、隔离任务工作树、联合验收和交付记录。各业务仓继续保留独立的 Git 历史、评审、合入和发布流程。

| 位置 | 负责内容 |
|---|---|
| 本脚手架仓库 | 初始化技能、生成器、工作区模板、可重建示例、测试和发布包 |
| 生成的 Mono 工作区 | 项目清单、调用关系、共同契约、任务工作树入口、联合验收和交接 |
| 接入的业务仓 | 业务代码、本仓规格与测试，以及已有 STDD/SDD 或其他开发流程 |

STDD/SDD 是可接入的仓内流程，普通 Git 仓库也能使用 Mono。工具定位并复用各仓原生入口，共同契约与各仓规格通过任务关联。方法来源和能力边界见[方法说明](../.agents/skills/init_mono/references/method.md)。

## 源码与交付地图

下表路径相对仓库根目录；在下文中，“模板根”指 `.agents/skills/init_mono/assets/workspace/`。

| 入口 | 维护内容 |
|---|---|
| [.agents/skills/init_mono/SKILL.md](../.agents/skills/init_mono/SKILL.md) | 发布技能的入口与执行顺序；`agents/openai.yaml` 保存展示元数据 |
| [.agents/skills/init_mono/VERSION](../.agents/skills/init_mono/VERSION) | 打包时嵌入 ZIP 的 Release 标签，初始化、升级和发布共同使用 |
| [references/inputs.md](../.agents/skills/init_mono/references/inputs.md) | 工作区、项目、任务输入格式及命令约定 |
| [scripts/init_mono.py](../.agents/skills/init_mono/scripts/init_mono.py) | 输入校验、初始化、系统说明生成、客户端技能分发和已有工作区升级 |
| [模板根 scripts/mono_projects.py](../.agents/skills/init_mono/assets/workspace/scripts/mono_projects.py) | 项目接入、Git 基线、清单写入、STDD 入口发现；初始化器和工作区工具共同使用 |
| [模板根 scripts/mono.py](../.agents/skills/init_mono/assets/workspace/scripts/mono.py) | `version`、`add`、`repos`、`bootstrap`、`baselines`、`new`、`status`、`stdd`、`run`、`check` 命令 |
| [模板根 scripts/mono_stdd.py](../.agents/skills/init_mono/assets/workspace/scripts/mono_stdd.py) | 任务与本仓 STDD 变更的创建、关联和归档定位 |
| [模板根 AGENTS.md](../.agents/skills/init_mono/assets/workspace/AGENTS.md)及其 `docs/mono/`、`.agents/skills/` | 生成工作区的规则、系统文档和三个日常技能 |
| [assets/upgrade-v*.json](../.agents/skills/init_mono/assets/) | 升级时识别各已知旧版文件的摘要，三端的技能正文沿用同一模板路径 |
| [examples/](../examples/README.md) | 现有仓库配置、STDD 登录任务、纯流程输入和三仓演练 |
| [tests/test_scaffold.py](../tests/test_scaffold.py) | 项目接入、任务隔离、升级保护及验收证据有效性的行为测试 |
| [scripts/package_skill.py](../scripts/package_skill.py) | 将技能源码打包为根目录 `init_mono.zip`，或核对包与源码一致 |
| [scripts/publish_skill_release.py](../scripts/publish_skill_release.py) | 校验主分支 ZIP 的版本与最新 GitHub Release，按包内标签发布变更 |
| [.github/workflows/check.yml](../.github/workflows/check.yml) | CI 的单元测试、包校验、完整三仓 HTTP/浏览器演练及通过检查后的主分支发布 |

日常修改以技能源码和模板为入口，再重建 ZIP。根目录 `scripts/` 当前负责发布打包，生成工作区的日常工具位于模板根 `scripts/`，排查问题时注意区分。

## 从初始化到交付的执行链路

### 初始化与项目接入

初始化器读取 JSON，校验项目与关系，复制模板，生成 `mono.json`、系统关系、联调说明和项目索引，再接入项目。至少需要两个项目。

| 维度 | 可选值与行为 |
|---|---|
| 工作区 `kind` | `directory` 创建普通目录；`repository` 额外初始化 Git 协调仓库；`process` 只登记引用与协作流程 |
| 项目 `mode` | `auto` 根据来源判断；`worktree` 接入本地 Git 根目录；`clone` 建立独立克隆；`reference` 保存项目或资料入口 |

本地 Git 默认通过 detached worktree 接入 `repos/项目`，远端 Git 地址默认独立 clone。初始化输入中的相对路径以 JSON 所在目录解析，`mono.py add` 的相对路径以调用时的当前目录解析。接入时的 `ref` 默认是 `HEAD`，创建工作树时读取的远端目标由下文的任务规则决定。

初始化目标必须是新目录；`--dry-run` 校验并展示计划。Git 接入中途失败时保留上下文和已成功接入的状态，按输出提示检查 `mono.json`、项目路径与 `git worktree list`。追加项目使用 `mono.py add`，保留已有手写系统说明，更新清单和生成索引。

### 团队成员克隆协调仓

协调仓提交工具、清单、文档和任务记录。模板忽略 `repos/` 与 `work/`，业务代码分别由各仓管理。成员克隆协调仓后用 `mono.py bootstrap` 恢复登记的 Git 业务仓，也可以指定项目名只恢复所选仓库。开展 feature 时，`mono-start` 用 `baselines --sync` 获取候选仓的目标提交，根据系统关系和目标版本的代码判断范围。

`bootstrap` 从 `clone_source` 或 Git URL 形式的 `source` 克隆缺失项目，检出清单记录的 `base_sha`。本地 worktree 接入时，优先用显式提供的 `clone_source`，其次从本地业务仓的 `origin` 读取远端地址。读取的是仓库配置中存储的地址，HTTP(S) 用户信息会去掉，本地路径和 file URL 保留为纯本地场景。旧清单支持用 `--source PROJECT=GIT_URL` 临时指定地址。该命令保留已有检出和共享记录，允许失败后重跑。新任务仍可用 `--base` 选择更新的引用。

### 任务与三个日常技能

日常顺序为 `mono-start` → 各仓实现 → `mono-verify` → `mono-wrap`。技能正文统一维护在模板根 `.agents/skills/` 下的同名目录。初始化器默认分发到协调根的 `.agents/skills/`、`.claude/skills/` 和 `.qoder/skills/`，也可用 `--agent` 选择。Codex 布置 `agents/openai.yaml`，Claude Code 布置引用 `AGENTS.md` 的 `CLAUDE.md`。

`mono.py new INPUT --worktrees` 为输入 `projects` 选中的项目创建 `work/任务号/项目`，默认分支为 `mono/任务号`。首先采用显式的 `--base 项目=引用`，否则查询项目的 `target_branch`、登记的 origin 分支或远端默认分支。需要时获取对应提交，将远端分支及确切 SHA 固定到任务记录。当远端刷新失败时停止创建任务，只在没有指定目标且没有远端的本地仓采用接入检出的 HEAD。

首次接入的 `repos/项目` 负责长期保存业务检出及创建任务的 Git 入口。由独立克隆创建的任务工作树还依赖该目录下的 Git 数据。`baselines` 返回候选仓的目标分支和 SHA，带 `--sync` 时快进干净的 detached 检出。本地改动、本地分支和已分叉的检出会保留，Agent 可直接从 Git 读取目标提交。新工作树使用分析过的 SHA，已有任务工作树保留各自版本。可以用 `--branch 项目=分支` 为新任务选择分支；省略 `--worktrees` 时复用接入的检出。

| 任务目录中的文件 | 用途 |
|---|---|
| `task.json`、`task.md` | 结构化验收判据与共同契约、补充上下文，两者修改时保持一致 |
| `projects.json` | 本次参与仓、实际路径及创建任务时的基线和分支 |
| `plan.md` | 实际入口、影响范围、实施顺序和测试映射 |
| `stdd.json` | 使用 STDD 关联命令后生成的各仓变更编号映射 |
| `verification.json`、`evidence/` | 验收状态、实际结果、人工判断和运行回执 |
| `delivery.md` | 候选提交或 PR、发布恢复安排和复盘 |

`status` 报告实际工作树、分支与 SHA。`stdd.skills_by_agent` 按客户端列出各工作树里的 `stdd-*` 技能，原有 `stdd.skills` 字段保留常用技能的单一路径。`stdd` 只在登记的 feature 工作树及预期分支操作，调用该仓自己的 `scripts/new_change.py` 创建变更，或关联已有变更；归档后仍可定位。具体规则见[生成工作区的 STDD/SDD 对接说明](../.agents/skills/init_mono/assets/workspace/docs/mono/stdd-sdd.md)。

### 联合验收与证据有效性

`mono.py run` 实际执行传入命令，保存输出、退出码、超时状态、运行前后各仓 SHA、文件内容摘要及规格摘要。文件摘要覆盖 Git 跟踪文件和未忽略的未跟踪文件，并处理权限、符号链接和已初始化子模块内容。运行期间代码或规格改变会使回执不稳定。

`mono.py check` 核对 AC 与报告、实际结果、回执覆盖范围、执行成功状态，以及回执是否仍匹配当前代码和规格。未接入项目、缺少证据、失败、超时或过期回执都不能通过检查。当前回执为 version 2，同时保留 version 1 的规格摘要校验路径。

维护时保留这两个边界：

- `--ac` 声明命令实际覆盖的判据，业务断言由具体测试实现。摘要与退出码只能核对记录的一致性。
- `check` 输出 `human_decision`，当前不会以人工判断是否通过作为退出码门槛。机器证据通过后，业务结论、评审和发布仍按实际项目流程处理。

### 已有工作区升级

`init_mono.py --upgrade WORKSPACE` 更新列入升级范围的工具和文档，默认补齐协调根的三套技能入口。`--agent` 可限定本次技能分发范围。旧文件与已知版本匹配时可以更新，自定义 README、`CLAUDE.md`、Claude Code 或 Qoder 技能以及 Codex 展示元数据会保留。其余待替换文件有自定义内容时，升级会提示先比对。协调根 `AGENTS.md`、任务、业务目录和手写系统说明继续保留，已有验证回执仍按原规格核对。

协调仓的 `mono-version.json` 保存初始化 Release、当前 Release 和按顺序追加的升级记录。`mono.py version` 输出该记录。升级成功后才更新版本，重复升级到同一版本不会追加历史。旧协调仓第一次升级会补记当前版本，未记录过的历史版本保留为未知。

修改模板工具时，需要同时考虑新生成工作区和已有工作区的升级路径。新增可升级版本时记录该版本的旧文件摘要，并保留之前可识别的版本。

## 三仓示例与可重现性

完整演练位于 `examples/three-services/`，对应 FEAT-301“活动列表展示剩余名额并筛选可报名活动”。

- `seed/` 保存旧项目代码，`feature/*.patch` 保存三仓参考实现。
- `demo.py setup` 在新目标中创建三个源 Git 仓库、协调仓和任务工作树；`apply` 校验工作树为干净基线后应用补丁并分别提交。
- `tools/verify.py` 通过前端代理和两个后端运行 7 项真实 HTTP 验收；`tools/browser.cjs` 使用 Playwright 验证第 8 项界面行为。
- `evidence/` 保存已提交的示例截图和结果摘要，新的演练回执保存在目标工作区的任务目录中。

主要调用链为 `portal-web` → `campaign-api` → `capacity-api`。关键契约包括剩余名额零下限、可报名过滤发生在计数分页前、租户隔离、旧调用兼容及新依赖异常返回受控 503。基线应通过，新 feature 在实施前应因缺少批量接口返回 404 而失败，实施后再按同一判据复跑。

改动示例时同时核对种子、补丁、任务判据和验收工具，确保参考补丁仍能应用到干净基线。完整命令见[三仓演练说明](../examples/three-services/README.md)。每次使用新目标目录，业务改动在生成的任务仓进行，共同规格和证据归协调工作区。

## 修改后如何验证

核心运行依赖为 Python 3.9+ 和 Git；HTTP 演练需要允许监听本机回环端口；浏览器演练另需 Node、Playwright 和 Chromium。

在仓库根运行脚手架测试和现有发布包核对：

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/package_skill.py --check
```

技能目录中的文件发生变化时，先重建发布包，再核对：

```sh
python3 -B scripts/package_skill.py
python3 -B scripts/package_skill.py --check
```

| 改动范围 | 验证重点 |
|---|---|
| 生成器或工作区模板 | 运行单元测试；确认初始化、既有状态保护及相关命令行为 |
| 技能源码与模板资产 | 重建 ZIP 并执行 `--check`，保持根目录发布包与源码同步 |
| 三仓种子、补丁、验收工具或影响其行为的生成逻辑 | 在新目录复跑基线、预期 404 失败、应用补丁及 HTTP 验收；涉及界面时复跑浏览器验收 |
| 发布 | 按[发布步骤](github.md)完成完整三仓演练及检查，核对待发布提交的 CI 结果 |
| 仅修改仓库说明 | 核对相对链接、命令、源码描述和 `git diff --check` |

测试覆盖项目自动接入与追加、源仓未提交改动保护、独立任务分支、自定义基线、STDD 关联与归档、升级拒绝覆盖自定义工具，以及代码、规格、权限、子模块、运行中修改、超时和缺失证据引起的验收失效。新增行为应在对应链路验证。

## 独立 clone 与首次梳理记录

本仓曾在其他本地目录开发，现作为独立 clone 维护。公开文档与示例应能在全新克隆中重建，避免引入旧机器的绝对路径。`ops218-space` 是未纳入 Git 的历史本地演练，不能作为公开功能或验收的必要依赖。

2026-11-19 首次梳理基于提交 `896f1ab` 的内容，记录如下：

- 14 项脚手架单元测试通过，发布 ZIP 与技能源码一致。
- 在新临时目录完成三仓生成、旧基线通过、新 feature 预期 HTTP 404 失败、参考补丁应用及 7 项 HTTP 验收通过。
- 本次未复跑浏览器验收；仓库自带浏览器结果属于历史示例证据。
- 当时检查的仓库文本未发现旧 Desktop 路径硬编码。

以上是带日期的历史检查结果。后续接手仍按当前任务和改动范围验证，不把它们视为当前版本已通过的证明。
