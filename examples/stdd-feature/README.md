# 给已有 STDD 仓库接入一项登录功能

此例给出接入和协作输入。示例用前端与认证后端两个仓，也可按实际调用链增补资料或权限服务。使用各仓现有认证能力、测试数据和确认过的接口规则。

## 组织仓库

复制 [workspace.example.json](workspace.example.json) 为自己使用的配置，替换 Git 地址、本地 Git 根目录、负责人和调用关系。路径相对于输入文件解析。省略 mode 时，远端地址独立 clone，本地 Git 工作区通过 Git worktree 接入。认证由本机已有的 Git 凭据和 SSH 配置提供。

~~~sh
python3 -B .agents/skills/init_mono/scripts/init_mono.py your-workspace.json /path/to/account-mono --dry-run
python3 -B .agents/skills/init_mono/scripts/init_mono.py your-workspace.json /path/to/account-mono
~~~

有新服务参与后续功能时，在协作根目录追加登记。

~~~sh
python3 -B scripts/mono.py add profile-api git@gitlab.example.com:team/profile-api.git --ref origin/main --role "用户资料服务"
python3 -B scripts/mono.py repos
~~~

需要改变调用关系时补充系统关系或 mono.json。流程类项目可登记本地资料目录。当中只有两仓影响登录时，这个 feature 的 projects 仍只列两仓。

## 开始 feature

在 Coding Agent 中打开 account-mono 根目录，给它一条明确的任务。

> 用 $mono-start 开始 FEAT-LOGIN。前端和认证后端都已有 STDD。读取各仓的规范、当前接口和测试入口，记录合入目标与本仓变更编号。先对齐共同契约和测试账号上的成功、失败场景，再在任务工作树分别按 STDD 流程推进。使用 $mono-verify 跑一次真实前后端联调，保存两仓版本和验收结果。

终端也可以直接用 [login.task.json](login.task.json) 建任务。若团队需要最新已合并版本，先按仓约定 fetch，再指定 --base。分支命名按各仓实际要求调整。

~~~sh
python3 -B scripts/mono.py new /path/to/login.task.json --worktrees --base auth-api=origin/main
python3 -B scripts/mono.py status FEAT-LOGIN
python3 -B scripts/mono.py stdd FEAT-LOGIN frontend 014-login --title "登录页面"
python3 -B scripts/mono.py stdd FEAT-LOGIN auth-api 021-login --title "登录接口" --design
~~~

已有 change 时使用该仓现有编号并省略 --title。status 显示准确的技能路径，避免把前端的 stdd-start 或测试约定用到后端。关联会写入 tasks/FEAT-LOGIN/stdd.json。

## 完成开发、验证与交付

Mono 的 task.md、task.json 和 plan.md 记录共同契约、影响仓与端到端判据。各业务仓继续在自己的 changes/ 填写 spec、tasks 和 verification，并按自己的 stdd-start、stdd-delivery、stdd-wrap 或 SDD 流程推进。属于单仓的 REQ 和 AC 保留本仓编号，联合验收映射到 Mono 判据。

使用 mono-verify 从两个工作树运行原有检查，再用实际测试账号验证浏览器到后端的调用。各仓测试输出与页面验证分别记录，只有实际联调覆盖的判据才关联联合回执。使用 mono-wrap 汇总各仓候选提交或 PR、部署依赖以及恢复方式。评审和权限沿用各项目配置。
