# 初始化输入

Python 3.9 或以上版本和 Git 可直接运行生成器。默认生成普通目录，可通过 kind 生成 Git 协调仓库或仅包含流程的空间。项目数量不限于前后端，API、移动端、数据项目和共享文档都可以接入。

## 最小输入

    {
      "name": "运营平台协作",
      "summary": "联合维护运营界面与活动服务。",
      "projects": [
        {"name": "ops-web", "source": "/work/ops-web", "role": "运营界面"},
        {"name": "ops-api", "source": "/work/ops-api", "role": "活动接口"}
      ]
    }

name、summary、projects 必填，每项目必填 name、source。最低提供两个项目。未指定 mode 时采用 auto。远端 Git 地址用 clone，本地 Git 根目录用 worktree，普通目录用 reference。role 缺省使用项目名。未知的负责人与运行条件保留为待核实，可继续完善。

## 完整接入

- kind 为 directory 时创建普通目录。repository 额外初始化根 Git 并忽略独立的 repos/ 和 work/。process 生成流程及共享说明，各项目都作为 reference 记录。
- owner 是协作负责人。项目也可以单独指定 owner。
- source 是本地仓库目录或 Git URL。相对路径以输入 JSON 所在目录为准，~ 指向用户目录。
- mode 为 worktree 时从现有本地克隆创建 detached worktree，mode 为 clone 时检出独立副本，两种方式都记录基线 SHA。reference 保存项目路径、代码 URL 或文档链接。
- ref 缺省为 HEAD。需要远端最新版本时按现有流程先 fetch，再指定已准备的 ref。
- commands.start 与 commands.test 是各仓原有命令，脚本只把它们写入说明。Agent 实际使用时先读项目规则与依赖。
- relationships 每项用 from、to、description 描述调用或协作关系，两端引用项目 name。
- context 用字符串列表链接其他上下文。
- operations 用字符串填写 environment、baseline、fixtures、startup、logs、release、rollback。生成器把它们写入联调手册。

命令为 python3 scripts/init_mono.py INPUT TARGET。TARGET 使用新目录，--dry-run 检查输入与本地基线并展示计划。中途 Git 接入失败时保留已生成的上下文、mono.json 和检出，按输出路径检查实际状态后继续处理。

## 需求输入

初始化后使用生成工作区的 mono-start。结构化任务输入如下。

    {
      "id": "OPS-218",
      "title": "活动状态筛选",
      "goal": "运营按活动状态与关键词定位活动。",
      "projects": ["ops-web", "ops-api"],
      "contract": "status 可选，省略时兼容旧调用。",
      "acceptance": [
        {"id": "AC01", "check": "查询春季加进行中", "expected": "只返回 A102，总数为 1。"}
      ]
    }

id、title、goal 必填。owner 默认使用协作负责人。projects 默认所有已接入项目，可只选受影响项目。contract 和 acceptance 可在初始化任务后根据代码和业务补全。task.json 为结构化判据，task.md 补充上下文，修改时保持一致。

在协作根目录运行 python3 scripts/mono.py new INPUT --worktrees。新任务使用 mono/任务号 分支，已有分支或任务目录会明确提示，接手时读取原记录。--worktrees 用于在隔离分支上实施，省略时复用已接入的检出。

## 追加项目与升级

在生成的工作区执行 python3 -B scripts/mono.py add NAME SOURCE --role 职责。可选 --mode、--ref 和 --owner。该命令不会覆盖同名项目，保留当前手写系统说明，并更新清单。add 的相对地址从当前目录解析。process 模式仍只登记引用。

旧工作区从最新版技能运行 python3 -B scripts/init_mono.py --upgrade WORKSPACE。工具检查待替换文件与已知旧版一致，保留业务目录、任务与手写系统说明。若检测到本地改过的技能或脚本，请先比对再合并。

日常需求可传多组 --base PROJECT=REF 和 --branch PROJECT=BRANCH，基线需先在对应 Git 仓库中可解析。接入 STDD/SDD 后，打开生成工作区的 docs/mono/stdd-sdd.md。
