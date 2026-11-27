# 团队快速上手 init_mono

一个协作工作区接入一组长期配合的仓库。平时每项 feature 只为实际受影响的仓库建任务工作树。以你们的 STDD/SDD 团队为例，先确认前端与后端已有 Git 仓库，各有 AGENTS.md、开发规范和可运行的测试入口。需要补齐单仓规范时，用 [init-stdd](https://github.com/zhgqwx-del/stdd-sdd) 初始化。Mono 的 Git 接入也支持已有普通仓库。

## 一 下载与初始化

需要 Python 3.9+、Git 和 macOS/Linux 的 unzip。下载 [init_mono.zip](https://github.com/zhgqwx-del/init-mono/releases/latest/download/init_mono.zip)。仓库权限沿用本机的 Git SSH 或 HTTPS 凭据。

### 用 Coding Agent 初始化

已安装 $init_mono 时，直接在 Coding Agent 中给出实际仓库信息。也可以在你希望调用初始化技能的项目根执行以下命令，然后打开该目录。

~~~sh
mkdir -p .agents/skills
unzip -n "$HOME/Downloads/init_mono.zip" -d .agents/skills
~~~

> 用 $init_mono 创建一个名为 account-mono 的 Git 协作空间。前端位于 /path/to/frontend，后端的 Git 地址是 git@github.com:my-team/auth-api.git。两仓都已有 STDD。把协作空间放在业务仓之外，核对各仓基线、调用关系、启动和测试入口。

### 用终端初始化

从 [三仓配置示例](examples/three-services/adopt-existing.json)或[登录项目配置示例](examples/stdd-feature/workspace.example.json)填入实际数据，保存为 workspace.json。相对项目路径以这个 JSON 文件的位置为准。下面的 mono_config 指向该文件，mono_target 指向一个还未创建的独立目录。

~~~sh
mono_bundle="$(mktemp -d)"
unzip "$HOME/Downloads/init_mono.zip" -d "$mono_bundle"
mono_script="$mono_bundle/init_mono/scripts/init_mono.py"
mono_config="/path/to/workspace.json"
mono_target="/path/to/account-mono"
python3 -B "$mono_script" "$mono_config" "$mono_target" --dry-run
python3 -B "$mono_script" "$mono_config" "$mono_target"
~~~

kind 选 repository 会初始化 Git 协调仓库，选 directory 生成普通目录，选 process 只登记引用和流程。脚本把启动、测试与权限约定写入说明，具体命令由 Agent 按实际环境执行。[输入字段与模式](.agents/skills/init_mono/references/inputs.md)

协调根默认安装 Codex、Claude Code 和 Qoder 的三个日常技能。只需一个客户端时，在初始化命令后加 `--agent codex`、`--agent claude` 或 `--agent qoder`。

## 二 发布并克隆团队协调仓

初始化团队协调仓时选择 `kind: repository`。每个业务仓的 `source` 可填团队有权限访问的 Git URL，也可填本地仓库路径以使用 worktree。用本地 worktree 时，脚手架会从业务仓已配置的 `origin` 取得远端地址并将其记为 `clone_source`。如果 `origin` 缺失、指向本机，或是队友无法访问的个人 fork，可以显式填写团队的共享地址。各仓登记的基线提交需要能从对应远端克隆得到。

创建者将协调仓的清单、工具和共享文档提交到 GitHub 或 GitLab。生成的 `.gitignore` 会忽略 `repos/` 和 `work/`。团队成员分别克隆协调仓，使用自己的业务仓权限恢复检出。

~~~sh
git clone git@gitlab.example.com:team/demo-harness.git
cd demo-harness
python3 -B scripts/mono.py bootstrap
~~~

`bootstrap` 默认在 `repos/<项目>` 恢复清单中所有登记了基线的 Git 业务仓，已有检出会保留。初次接手可以先拉齐全部业务仓。已知范围时，也可以指定项目名，例如 `bootstrap child-repo1 child-repo2`。此前生成的协调仓可按第四节升级。已有清单如果只记录了本地路径，可补填共享的 `clone_source`，或临时传入 `--source 项目=Git_URL`。

## 三 从协作根启动一个需求

在 Agent 中打开协调仓根目录。先看 AGENTS.md、mono.json、docs/mono/system.md 和 operations.md，核对调用关系、联调配置及测试数据来源。

| 客户端 | 协调根技能目录 | 日常调用 |
|---|---|---|
| Codex | `.agents/skills/` | `$mono-start`、`$mono-verify`、`$mono-wrap` |
| Claude Code | `.claude/skills/` | `/mono-start`、`/mono-verify`、`/mono-wrap` |
| Qoder | `.qoder/skills/` | `/mono-start`、`/mono-verify`、`/mono-wrap` |

### Mono 与 STDD 使用顺序

~~~mermaid
flowchart TD
    Start["协调仓 · mono-start<br/>对齐共同契约和验收判据，准备任务工作树"]
    Work["各参与仓在自己的任务工作树推进，可并行"]
    Stdd["stdd-start → stdd-delivery<br/>复用任务分支，确认仓内规格和方案后写测试、实现"]
    Native["按本仓流程开发和测试"]
    Local["仓内验收记录与交付<br/>stdd-test-report、stdd-review、stdd-wrap"]
    Candidate["已有可联调的版本组合"]
    Verify["协调仓 · mono-verify<br/>运行仓内检查和跨服务联调，记录受测版本和证据"]
    Wrap["协调仓 · mono-wrap<br/>核对联合验收回执，汇总各仓候选提交或 PR、发布依赖"]

    Start --> Work
    Work -->|STDD 仓| Stdd
    Work -->|其他仓| Native
    Stdd --> Candidate
    Native --> Candidate
    Stdd -. 按各仓约定 .-> Local
    Candidate --> Verify
    Verify --> Wrap
    Local -. 提供各仓交付信息 .-> Wrap
    Wrap -. 回执与候选版本或规格不符时复验 .-> Verify
~~~

有可联调的版本组合就可以开始 `mono-verify`。单仓报告、评审和收尾按各仓约定推进。最终回执要匹配交付候选版本和共同规格。同步分支、更新仓内报告或归档后，如果已有回执过期，就回到 `mono-verify` 复验。[STDD 使用顺序](https://github.com/zhgqwx-del/stdd-sdd/blob/main/stdd-use-demo/docs/stdd/workflows.md#使用顺序)

> 用 mono-start 开始 FEAT-101，给活动列表新增筛选。先更新候选仓的目标版本，再根据代码判断影响范围，只为需要任务版本的仓库建立工作树。

1. 用 `mono-start` 写共同契约和验收场景，为参与仓建立 `work/需求号` 下的工作树。各业务仓有自己的分支和合入目标。
2. 用 `python3 -B scripts/mono.py status FEAT-101` 查看 `stdd.skills_by_agent` 中各客户端的仓内技能路径，在对应工作树按本仓流程开发。`scripts/mono.py stdd` 可以调用业务仓模板创建变更，也可关联已有变更。
3. 用 `mono-verify` 跑仓内检查，再跑真实跨服务测试，记录实际受测版本和结果。
4. 用 `mono-wrap` 对齐各仓候选提交或 PR、发布顺序和后续接手信息。评审、权限和发布沿用各仓安排。

以 `FEAT-LOGIN` 为例，在协调根运行 `python3 -B scripts/mono.py status FEAT-LOGIN`，找到前端和认证后端的任务工作树。各仓在自己的 `verification.md` 记录仓内结果。浏览器到认证后端的登录联调结果记入协调仓的 `tasks/FEAT-LOGIN/verification.json`。[FEAT-LOGIN 输入与操作示例](examples/stdd-feature/README.md)

手头暂时没有业务仓时，可以先用 [三仓演练](examples/three-services/README.md)创建并跑通一组本地仓库。

成员用各自的任务号开工，例如 FEAT-101 和 FEAT-102。每项 feature 将 `tasks/<任务号>/` 的共有记录提交到协调仓，把 `work/<任务号>/<项目>/` 中的代码提交并推送到对应业务仓。协调仓和各业务仓的 PR 可用任务号互相引用。

命令行开工时，在任务 JSON 中显式填写 `projects`。例如已经拉齐三个业务仓，FEAT-101 只涉及两个，可以填 `"projects": ["child-repo1", "child-repo2"]`，再执行 `python3 -B scripts/mono.py new /path/to/feat-101.json --worktrees`。第三个仓仍可从 `repos/` 查阅或按基线运行。

### 下一项 feature 从最新目标分支开始

`mono-start` 会先用 `baselines --sync` 查询候选仓的远端目标分支并获取提交。命令快进干净的 detached `repos/` 检出。遇到本地改动、正在使用的本地分支、历史分叉或切换受阻时，Agent 会直接读取目标提交。确定范围后，Agent 使用分析过的 SHA 为参与仓创建新工作树。

团队可在 `mono.json` 为每个项目设置 `target_branch`，例如 `child-repo1` 用 `main`，`child-repo2` 用 `develop`。省略时沿用接入时登记的 `origin/<分支>`，其余用远端默认分支。范围明确时可以运行 `python3 -B scripts/mono.py baselines --sync child-repo1 child-repo2`；省略仓名时处理全部已登记的 Git 业务仓。

直接运行 `new --worktrees` 时，工具会获取新工作树所需的目标提交。复现或离线时可以传 `--base child-repo1=HEAD` 或指定本地已有的 SHA。已有任务保留各自的工作树，已结束任务可以按协调仓 README 清理。

## 四 后续添加仓库或升级工具

### 追加项目

在已生成的 Mono 根追加新项目。

~~~sh
python3 -B scripts/mono.py add profile-api git@gitlab.example.com:team/profile-api.git --ref origin/main --role "用户资料服务"
python3 -B scripts/mono.py repos
~~~

### 升级已有协调仓

用新版脚手架的初始化器，将已有协调仓根目录传给 `--upgrade`。如果在新版 init-mono 源码仓根目录操作，可以运行下面的命令。

~~~sh
mono_workspace="/path/to/demo-harness"
python3 -B .agents/skills/init_mono/scripts/init_mono.py --upgrade "$mono_workspace"
git -C "$mono_workspace" status --short
git -C "$mono_workspace" diff
~~~

使用新版 ZIP 时，把命令里的脚本路径换成解压所得的 `init_mono/scripts/init_mono.py`。

在协调仓根目录运行 `python3 -B scripts/mono.py version`，查看初始化时的 Release、当前 Release 和升级历史。新建或升级成功后会将记录写入 `mono-version.json`，可随协调仓提交。早期协调仓首次升级会补记本次安装版本，无法追溯的初始版本会显示为 `null`。

升级会更新工具、重新生成项目索引 `docs/mono/projects.md`，并为协调根补齐三个客户端的技能入口。要指定单个客户端，可在命令后加 `--agent codex`、`--agent claude` 或 `--agent qoder`。已有 `mono.json`、任务、业务仓检出、任务工作树、共享规则和手写系统说明会保留。

升级会保留自定义 README、`CLAUDE.md` 及自定义 Claude Code 和 Qoder 技能。如果团队维护自己的 `CLAUDE.md`，可在其中添加 `@AGENTS.md` 来加载共享规则。受管理的脚本或 Codex 技能正文有冲突时，升级器会在写入前提示待比对的路径。

团队维护者审阅差异后，把升级改动提交并合入协调仓的共享分支。其他成员拉取协调仓更新即可使用新版工具。如果是为旧协调仓首次接入 `bootstrap`，且 `mono.json` 只记录了创建者的本地路径，维护者在共享清单中一次性补齐队友可访问的 `clone_source`，确认已登记的基线提交能从该远端获取，再把清单随升级一起提交。[项目认知与维护指南](docs/project-context.md)
