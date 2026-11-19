# 一个 feature 贯穿前端和两个后端

FEAT-301 为活动列表增加剩余名额，并筛选可报名活动。已有前端和两个后端分别维护。Mono 提供共同规格、系统关系、隔离任务工作树和联合验收，三个项目继续独立提交。

## 从接手旧项目开始

| 仓库 | 旧能力 | 本次改动 |
|---|---|---|
| portal-web | 关键词、状态和分页 | 展示名额，增加可报名筛选，提交新参数 |
| campaign-api | 活动、租户范围、列表与总数 | 聚合名额，按可报名条件过滤后再计数和分页 |
| capacity-api | 单活动名额查询 | 增加批量接口，计算剩余名额并校验整批可见范围 |

~~~mermaid
sequenceDiagram
    participant W as portal-web
    participant A as campaign-api
    participant C as capacity-api
    W->>A: 列表查询与可报名条件
    A->>C: 按身份批量查询活动名额
    C-->>A: 每个活动的剩余名额
    A->>A: 判定可报名 过滤 计数 分页
    A-->>W: 当前页与匹配总数
~~~

## 一 初始化三个真实 Git 仓库与协作空间

在脚手架仓库根运行，需要 Python 3.9+ 和 Git。目标目录用新位置，路径可包含空格。

~~~sh
python3 -B examples/three-services/demo.py setup ../mono-use-demo
~~~

生成结果如下。

~~~text
mono-use-demo/
  sources/                 接手时已有的三个独立 Git 仓库
    portal-web/
    campaign-api/
    capacity-api/
  workspace/               init_mono 生成的 Git 协调仓库
    docs/mono/             系统关系 决定 联调与发布
    .agents/skills/        mono-start mono-verify mono-wrap
    repos/                 接入的旧基线
    work/FEAT-301/         三个独立任务分支
    tasks/FEAT-301/         共用契约 计划 实际结果与回执
~~~

sources 的 main 保留旧代码。feature 在 work/FEAT-301 的各仓中开发。workspace 只版本管理共享上下文和任务记录。目录里的 Git 关系由 setup 实际创建，不需要先在 GitHub 建四个远程仓库。

## 二 在一个入口接手

在 Agent 中打开 workspace，读 AGENTS.md，再用下面的输入。示例已经预设业务规则，真实项目中的未定规则应交给相应负责人判断。

> 用 $mono-start 接手 FEAT-301。前端、活动服务和名额服务已经接入。请从共同规格定位三仓改动，核对可报名的定义、名额不足与越权行为、过滤和分页顺序，并按 plan.md 的验收编号推进。

本例业务约定如下。

- remaining 为 capacity 减 reserved，最低为零。只有 ACTIVE 且 remaining 大于零才可报名。
- 关键词、状态、可报名、租户范围共同决定匹配集合。先过滤，再计数与分页。
- 新聚合用可选参数启用。旧调用保持原字段，且继续在名额服务离线时正常查询。
- 新路径遇到名额服务离线或响应错误时返回受控的 503。
- 页面点查询才提交条件，翻页沿用已提交条件。

人确认这些规则及产品结果。Agent 跨三个任务工作树实现并测试，各项目负责人按现有规则评审。一次调用经过三仓，验收也绑定三仓实际版本。

## 三 先确认旧系统可运行 再看到新用例失败

在脚手架仓库根执行。

~~~sh
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage baseline
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage feature
~~~

第一条应通过。第二条此时应失败，批量名额接口返回 404，验收期望 200。运行回执保留真实失败，说明旧实现尚未满足新判据。

## 四 跨三个仓库开发

可以让 Agent 根据 task.json、plan.md 和三个项目的 AGENTS.md 完成改动。也可以应用本仓库提供的参考补丁，复现已经验证的实现。

~~~sh
python3 -B examples/three-services/demo.py apply ../mono-use-demo
~~~

该命令核对三个任务工作树仍是干净的基线，分别应用 feature/ 中的补丁，并在三个仓库各自提交。若已经手动开发，继续验收自己的实现。

后端二新增批量接口，后端一调用这个接口，前端启用可选聚合与筛选。完整 diff 在 feature/ 下，可以逐仓阅读。

## 五 按共同规格联合验收

~~~sh
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage feature
~~~

七项真实 HTTP 验收覆盖剩余名额、聚合、过滤分页、组合条件、旧调用兼容、租户隔离及依赖异常。测试会实际启动三服务并让请求经过前端代理和两个后端。

合成数据中，A101 是草稿，剩余 10；A102 是进行中，剩余 3；A103 是进行中但已满；A104 已结束且原始已预订数超额，显示零。筛选可报名只应得 A102，total 为 1。租户 B 的 B105 不能进入租户 A 的列表或计数。

## 六 用真实浏览器完成界面验收

这一步需要 Node 18+、Playwright 和 Chromium。在脚手架仓库根准备依赖。

~~~sh
npm install --prefix examples/three-services
npx --prefix examples/three-services playwright install chromium
python3 -B examples/three-services/demo.py browser ../mono-use-demo
python3 -B examples/three-services/demo.py check ../mono-use-demo
~~~

已有环境可用 NODE_BIN、PLAYWRIGHT_MODULE、CHROME_PATH 指定可执行文件或模块。browser 检查名额列、可报名筛选、未提交条件的翻页、空态和恢复查询，并保存桌面与移动端截图。check 应确认八条判据的回执与当前三个仓库及规格相符。人工业务结论单独保存在 human_decision。

## 七 打开页面并交接

~~~sh
python3 -B examples/three-services/demo.py serve ../mono-use-demo
~~~

打开 http://127.0.0.1:4280/。在列表查看名额，选择仅看可报名并点查询。Ctrl+C 停止。

用 $mono-wrap 整理三仓受测 SHA、PR 关系和发布恢复安排。兼容发布顺序是后端二、后端一、前端。恢复时先停止前端新调用，再按项目情况回退后端一。共同决定和联调说明随需求沉淀，下一次接手可复用。

## 替换成团队现有仓库

[adopt-existing.json](adopt-existing.json) 提供同样的三项目输入。替换 source、项目职责、实际启动测试命令后，运行初始化器或把文件交给 $init_mono。已有仓库的 Git 历史和团队规则随接入保留。

已有协作空间的下一项需求通过 mono-start 创建，只列实际受影响项目即可。新任务基于已经接入的检出版本，先核对是否需要更新到最新已合并基线，再建立任务工作树。
