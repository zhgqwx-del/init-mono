# GitHub 发布

本仓库包含技能源码、生成模板、实操教程、三个服务的旧项目种子、feature 参考补丁和验收工具。运行生成的业务 Git 仓库和本机工作树保存在演练目录。拥有仓库访问权限的读者可在克隆后通过 setup 重建。

## 发布前验证

在仓库根运行以下命令，并按 examples/three-services/README.md 跑完一次基线、新用例失败、三仓实现和联合验收。

~~~sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/package_skill.py --check
git status --short
~~~

.github/workflows/check.yml 会在后续 GitHub 推送和 PR 上复跑脚手架测试及三仓示例。仓库需要公共或私有由创建者选择。

## 创建远端并推送

将 OWNER/REPO 替换为实际账号及仓库名。已存在远端时按团队方式添加 origin 并推送。

~~~sh
gh repo create OWNER/REPO --public --source . --remote origin --push
~~~

## 发布技能 ZIP

版本号按实际发布填写，发布分支的 workflow 通过后上传对应提交的 ZIP。读者可从 [Releases](https://github.com/zhgqwx-del/init-mono/releases) 下载该版本，首次使用见 [团队快速上手](../QUICKSTART.md)。

~~~sh
python3 -B scripts/package_skill.py
gh release create v0.1.0 init_mono.zip \
  --title "init_mono v0.1.0" \
  --notes-file docs/release-notes.md
~~~
