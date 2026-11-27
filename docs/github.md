# GitHub 发布

本仓库包含技能源码、生成模板、实操教程、三个服务的旧项目种子、feature 参考补丁和验收工具。运行生成的业务 Git 仓库和本机工作树保存在演练目录。拥有仓库访问权限的读者可在克隆后通过 setup 重建。

## 发布前验证

在仓库根运行以下命令，并按 examples/three-services/README.md 跑完一次基线、新用例失败、三仓实现和联合验收。

~~~sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/package_skill.py --check
git status --short
~~~

.github/workflows/check.yml 在 GitHub 推送和 PR 上复跑脚手架测试、打包校验及三仓演练，包括 HTTP 和浏览器验收。

## 创建远端并推送

将 OWNER/REPO 替换为实际账号及仓库名。已存在远端时按团队方式添加 origin 并推送。

~~~sh
gh repo create OWNER/REPO --public --source . --remote origin --push
~~~

## 发布技能 ZIP

修改技能后，运行 `python3 -B scripts/package_skill.py` 重建根目录的 `init_mono.zip`，把源码和 ZIP 放在同一个提交里。合入 `main` 后，CI 通过才会比较该 ZIP 与最新 Release 的 SHA-256。如果内容不同，工作流会为通过检查的提交发布下一个补丁版本，上传当次提交的 ZIP，并验证新 Release 的附件。内容相同时跳过发布。README 和快速上手使用同一个 latest 下载地址，发布完成后自动指向新包。

检查失败或尚未结束时，latest 下载地址仍提供上一个通过检查的版本。发布失败可在 GitHub Actions 中查看发布步骤并重跑。历史版本的下载附件会保留在各自的 Release。

需要指定版本号时，可从已通过 CI 的 `main` 提交手动发布。以下命令从该提交的检出目录运行，替换版本号及发布说明路径。

~~~sh
python3 -B scripts/package_skill.py --check
git rev-parse HEAD
gh release create v0.3.0 init_mono.zip \
  --target "<通过 CI 的提交 SHA>" \
  --title "init_mono v0.3.0" \
  --notes-file /path/to/release-notes.md --latest
~~~

发布包见 [Releases](https://github.com/zhgqwx-del/init-mono/releases)。使用方法见 [团队快速上手](../QUICKSTART.md)。
