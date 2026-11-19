# 示例导航

| 示例 | 起点 | 能获得什么 |
|---|---|---|
| [已有 STDD 仓与登录需求](stdd-feature/README.md) | 自己的前端和账号服务 | 接入配置、共同契约的起草方式和各仓变更映射 |
| [活动名额三仓实操](three-services/README.md) | 自带的旧项目种子和合成数据 | 从旧基线到完整 feature 的实现、HTTP 验收与浏览器复跑 |
| [只生成协作流程](process-only.json) | 项目职责和调用关系 | 系统关系、联调和交付说明，以及后续任务入口 |
| [已有双仓配置模板](ops-workspace.json) | 自己的运营前端和后端 | 接入配置与[活动筛选任务样例](ops-task.json) |

## 直接体验完整三仓流程

先克隆脚手架仓库，在仓库根运行。新目标目录由 setup 创建。verify 默认检查 feature。

~~~sh
python3 -B examples/three-services/demo.py setup ../mono-use-demo
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage baseline
~~~

此时运行以下命令，应看到新验收在批量名额接口处失败，返回 HTTP 404。

~~~sh
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage feature
~~~

应用三个仓库的参考实现，然后复跑验收。

~~~sh
python3 -B examples/three-services/demo.py apply ../mono-use-demo
python3 -B examples/three-services/demo.py verify ../mono-use-demo --stage feature
python3 -B examples/three-services/demo.py serve ../mono-use-demo
~~~

启动后打开 [活动列表](http://127.0.0.1:4280/)。选择仅看可报名并查询，应看到活动 A102 与剩余名额 3。Ctrl+C 停止。浏览器的第 8 项验收、受测记录和提交顺序见 [完整操作](three-services/README.md)及[实际验收结果](three-services/evidence/result.json)。

登录示例与三仓演练用途不同。登录示例给出可替换的项目配置、任务输入与仓内变更步骤，业务认证仍需基于实际仓库实现。活动名额示例提供自包含代码和真实运行结果，适合先熟悉 Mono 的交付方式。
