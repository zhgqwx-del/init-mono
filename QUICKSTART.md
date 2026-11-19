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

## 二 从协作根启动一个需求

在 Agent 中打开生成的 account-mono。先看 AGENTS.md、mono.json、docs/mono/system.md 和 operations.md，核对调用关系、联调配置及测试数据来源。

1. 用 $mono-start 写共同契约和验收场景，为参与仓建立 work/需求号 下的工作树。各业务仓有自己的分支和合入目标。
2. 在对应工作树按仓内 STDD 技能开发。scripts/mono.py stdd 可调用该仓的原生模板创建变更，也可把已有变更关联到同一 Mono 工单。
3. 用 $mono-verify 跑仓内检查，再跑真实跨服务测试，记录实际受测版本和结果。
4. 用 $mono-wrap 对齐各仓候选提交或 PR、发布顺序和后续接手信息。评审、权限和发布沿用各仓安排。

第一项任务可以用 [FEAT-LOGIN 输入与操作示例](examples/stdd-feature/README.md)。手头暂时没有业务仓时，可以先用 [三仓演练](examples/three-services/README.md)创建并跑通一组本地仓库。

## 三 后续添加仓库或升级工具

在已生成的 Mono 根追加新项目。

~~~sh
python3 -B scripts/mono.py add profile-api git@gitlab.example.com:team/profile-api.git --ref origin/main --role "用户资料服务"
python3 -B scripts/mono.py repos
~~~

针对新 feature 选择需要参与的仓库，按各仓约定核对基线。使用最新版 ZIP 解压得到的脚本升级已有协作目录。

~~~sh
python3 -B "$mono_script" --upgrade "$mono_target"
~~~

升级会核对生成的旧版工具文件，保留业务仓、已有任务和手写系统说明。遇到团队改过的工具时，先比对再合并。[实践手册](docs/practice.md)
