# Mono 与各仓 STDD/SDD 的分工

Mono 根目录管理系统关系、跨仓契约、需求工作树、联合验收和交付。业务代码由各项目自己的 Git 仓库管理。work/任务号 下的每个项目有独立分支和提交。repos/ 是已接入的基线入口。

| 层级 | 负责内容 | 记录 |
|---|---|---|
| Mono feature | 用户目标、受影响仓库、接口与兼容、端到端判据、上线依赖 | tasks/任务号 下的 task、plan、verification、delivery |
| 单个 STDD 仓库 | 该仓行为、实施方案、原生测试、规格归档和 PR | 仓内 AGENTS.md、specs/、changes/ 和项目原有命令 |
| 带 SDD 或其他流程的仓库 | 该仓自己的规范、设计与测试流程 | 仓内实际发现的入口 |

## 日常 feature

1. 从 Mono 根打开 Agent。用 mono-start 查看调用链、确认受影响仓库和各自合入目标。保留需求负责人已确认的决策。
2. 为选中的仓库建工作树。new --worktrees 默认查询各仓的目标分支并获取新提交，以此建立独立任务工作树。项目可在 mono.json 设置 target_branch。省略时使用已登记的 origin 分支或远端默认分支。没有远端的本地仓使用当前 HEAD。需要复现历史版本或离线启动时，用 --base 项目=已存在的Git引用。repos/ 的当前检出及已有任务工作树保持原状。
3. 运行 `python3 -B scripts/mono.py status 任务号`。在每个项目下查看 `path` 和 `stdd.skills_by_agent`，按 `codex`、`claude` 或 `qoder` 选择现有的技能。打开对应工作树，读取该仓的 `AGENTS.md`、`docs/stdd/project.md` 和技能文件。
4. STDD 仓库可用 mono.py stdd 创建或关联变更。用仓库规定的编号。例如 frontend 用 014-login，auth-api 用 021-login。同一 Mono 需求可映射不同本地编号。关联写到 tasks/任务号/stdd.json。
5. 按该仓的 stdd-start、stdd-delivery 和已有确认记录推进，更新本仓的 spec、tasks、verification。纯 SDD 仓按自身入口执行。Mono 的联调判据链接各仓行为，避免把同一份完整规格复制到多仓。
6. 用 mono-verify 运行原有仓内检查及真实跨服务验证。用 mono-wrap 记录各仓 PR 或候选提交以及合入和部署依赖，并按各仓约定处理归档。

下面示例在协作根目录运行。

    python3 -B scripts/mono.py status FEAT-LOGIN
    python3 -B scripts/mono.py stdd FEAT-LOGIN frontend 014-login --title "登录页面"
    python3 -B scripts/mono.py stdd FEAT-LOGIN auth-api 021-login --title "登录接口" --design

`stdd.skills_by_agent` 按客户端列出工作树里实际存在的 `stdd-*` 技能，路径相对该工作树。某客户端没有匹配项时返回空对象。原有 `stdd.skills` 字段继续给出常用技能的单一路径，依次优先选择 Codex、Claude Code 和 Qoder 目录。

stdd 命令仅在选定任务分支中创建仓内文档。存在同编号变更时只关联，归档后 status 会定位到归档路径。该命令使用业务仓自己的 scripts/new_change.py 和模板。没有这个入口的仓库可以直接按其实际规则操作。

## 添加更多仓库

    python3 -B scripts/mono.py add profile-api git@gitlab.example.com:team/profile-api.git --role "用户资料" --ref origin/main
    python3 -B scripts/mono.py repos

同样支持 HTTPS 地址与本地路径。补充系统关系与接口依赖时编辑 docs/mono/system.md 或 mono.json 中的 relationships。新 feature 的 projects 列表明确选择用到的项目。已存在的任务保留自己原有的范围与候选版本。

## 验收与交付

联合测试应实际经过调用链，并绑定各仓受测版本。发布顺序取决于本次接口兼容性。例如新客户端开始调用额外接口时，可先发布兼容的服务端，再部署客户端。评审和发布分别沿用各仓约定，交付记录保存在 Mono。
