---
name: init_mono
description: 根据项目和仓库信息初始化或扩展 Mono 跨项目协作目录、协调仓库或流程，生成系统上下文、联调手册及需求推进、联合验收、交付复盘技能。用于接入多个已有项目或搭建类似 Manus Mono 的协作脚手架。
---

# 初始化与维护 Mono 协作空间

以用户提供的项目和仓库为基础，让跨项目工作共享系统上下文、可追溯的决策和可复跑的验证。用户指定入口名称为 init_mono。

1. 读取 [输入格式](references/inputs.md)。从现有项目资料补全项目职责、相互调用、仓库位置、基线、命令和负责人。已有业务契约、发布和权限规则优先采用项目事实。仅提供项目清单也能生成框架，未知项明确标记。
2. 根据目标选择 directory、repository 或 process。worktree 接入本地 Git，clone 获取独立副本，reference 记录暂未检出的项目或资料。先读取已有 AGENTS.md 等规则，确定工作区放在哪个项目外目录。默认按地址或路径自动选择接入方式。已有 Mono 协作根用 scripts/mono.py add NAME SOURCE 追加仓库；旧版生成目录用初始化器的 --upgrade WORKSPACE 安全更新生成工具。
3. 将整理的输入写入 JSON，运行 scripts/init_mono.py INPUT TARGET。默认给 Codex、Claude Code 和 Qoder 安装三个工作区技能。只使用一个客户端时可加 --agent codex、--agent claude 或 --agent qoder。需要预览时加 --dry-run。生成器创建共享文档、记录所选基线，并保留应用仓库的独立 Git 历史。
4. 核对生成的系统关系与联调手册，补充实际代码入口、契约位置、测试数据、日志访问方式及发布恢复步骤。用户只要求初始化时交付此处。若已要求首项需求，继续读取生成工作区中的 mono-start，按已获授权推进至约定的验收终点。

[方法覆盖说明](references/method.md) 解释资料来源、各项实践的具体落点，以及需要按项目接入的运行能力。生成工作区的 docs/mono/workflow.md 是后续执行入口。

需要演示一个 feature 贯穿前端与多个后端时，读取 [三仓接手示例](references/feature-walkthrough.md)，据此组织实际项目的共同契约、影响面与端到端验收。

若业务仓已使用 STDD/SDD，保留其规范和工具。初始化后从 docs/mono/stdd-sdd.md 进入各仓原有流程。在新的 feature 工作树中使用 scripts/mono.py stdd 关联仓内变更，再用 status 获取该仓的工作树、变更路径和各客户端的技能路径。
