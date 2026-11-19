# init_mono 脚手架仓库

新会话先读 [项目认知与维护指南](docs/project-context.md)，再按任务读取对应源码与示例。项目结构、关键机制或维护约定变化时，同步更新该指南。

.agents/skills/init_mono 是发布技能的源码，assets/workspace 包含生成的工作区技能与工具。examples/three-services 是完整的三仓 feature 演练，seed 保存旧代码，feature 保存参考补丁。

- 改动生成器或模板后运行 python3 -B -m unittest discover -s tests -v。
- 改动技能后运行 python3 -B scripts/package_skill.py --check，发布包为根目录 init_mono.zip。
- 示例运行用新目标目录，避免覆盖用户已实现的演练。在生成的三个任务仓库中改动业务代码，共同规格和证据归协调工作区。
- ops218-space 是历史本地演练，未纳入本仓库版本管理。公开内容应能在全新克隆中按 README 重现。
