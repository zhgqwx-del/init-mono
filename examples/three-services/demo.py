#!/usr/bin/env python3
"""Reproduce a feature across Web, campaign API and capacity API repositories."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PROJECTS = ("portal-web", "campaign-api", "capacity-api")
TASK = "FEAT-301"


def run(*args, cwd=None, **kwargs):
    return subprocess.run([str(a) for a in args], cwd=cwd, check=True, **kwargs)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def paths(root):
    marker = json.loads((root / "demo.json").read_text())
    if marker.get("example") != "three-services" or marker.get("task") != TASK:
        raise ValueError("target is not a generated three-service example")
    space = root / "workspace"
    return space, space / "work" / TASK, space / "tasks" / TASK


def setup(root):
    root.mkdir(parents=True, exist_ok=False)
    sources = root / "sources"
    for name in PROJECTS:
        destination = sources / name
        shutil.copytree(HERE / "seed" / name, destination)
        git(destination, "init", "-q", "-b", "main")
        git(destination, "add", ".")
        git(destination, "-c", "user.name=Mono Example", "-c", "user.email=mono-example@example.invalid",
            "commit", "-qm", "Baseline before FEAT-301")
    write_json(root / "demo.json", {"example": "three-services", "task": TASK})
    config = {
        "name": "活动报名协作", "summary": "一个页面通过活动服务聚合名额服务。",
        "owner": "活动功能负责人", "kind": "repository",
        "projects": [
            {"name": name, "source": str(sources / name), "ref": "main", "mode": "worktree",
             "role": role, "commands": {"start": command, "test": "在协调工作区运行 demo/verify.py"}}
            for name, role, command in zip(PROJECTS, (
                "前端筛选、分页与名额展示", "后端一负责活动查询、聚合及权限", "后端二负责名额数据与批量接口"
            ), (
                "python3 server.py --port 4280 --api-port 4281",
                "python3 server.py --port 4281 --capacity-port 4282",
                "python3 server.py --port 4282",
            ))
        ],
        "relationships": [
            {"from": "portal-web", "to": "campaign-api", "description": "活动列表请求走同源开发代理，附本地演示身份。"},
            {"from": "campaign-api", "to": "capacity-api", "description": "新 feature 通过租户隔离的 HTTP 批量请求聚合剩余名额。"}
        ],
        "operations": {
            "environment": "应用运行只需 Python 3.9+。浏览器验证另需 Node、Playwright 与 Chromium。",
            "baseline": "先运行 demo/verify.py 的 baseline 阶段，再验证 feature 尚未具备。",
            "fixtures": "两个租户五条合成活动。名额包含草稿、进行中有余量、已满、超额记录。",
            "startup": "先启动 capacity-api，再启动 campaign-api，最后启动 portal-web。demo/serve.py 可一起启动。",
            "logs": "三个服务的本机标准错误输出与任务命令回执。",
            "release": "后端二的批量能力先发布，再发布后端一的可选聚合，最后发布前端界面。沿用实际项目审批。",
            "rollback": "先撤回前端新调用，再按需恢复后端一。后端二保留兼容旧单活动接口。"
        },
    }
    write_json(root / "workspace-input.json", config)
    initializer = REPO / ".agents/skills/init_mono/scripts/init_mono.py"
    run(sys.executable, "-B", initializer, root / "workspace-input.json", root / "workspace")
    space, work, task = paths(root)
    shutil.copyfile(HERE / "task.json", root / "task-input.json")
    run(sys.executable, "-B", space / "scripts/mono.py", "new", root / "task-input.json", "--worktrees")
    shutil.copytree(HERE / "tools", space / "demo")
    shutil.copytree(HERE / "feature", root / "feature-patches")
    (task / "plan.md").write_text(
        "# FEAT-301 跨仓实施计划\n\n"
        "前端在 public/index.html 增加可报名筛选和名额列，在 public/app.js 发新参数并保留已提交筛选。\n\n"
        "后端一在 server.py 聚合后端二，先按租户与旧条件过滤，再取名额、判定可报名、计数和分页。"
        "省略新参数时保留旧路径。后端二增加批量接口，计算零下限，并对整批执行可见性检查。\n\n"
        "AC01 验证后端二，AC02–AC04 验证真实聚合，AC05–AC07 复测兼容、隔离和依赖失败，"
        "AC08 用 Chromium 从页面操作到两个后端。先在基线上看到新用例失败，实施后按同一判据重跑。\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# 三仓 feature 演练\n\nsources 中三个 main 是接手的旧项目，workspace 是 Mono 协调仓库，"
        "workspace/work/FEAT-301 是当前 feature 的三个独立任务工作树。\n\n"
        "从脚手架仓库执行 examples/three-services/demo.py 的 verify、apply、browser 或 serve 子命令，"
        "末尾传入本目录路径。运行说明在脚手架 examples/three-services/README.md。"
        "共同规格与证据位于 workspace/tasks/FEAT-301。\n",
        encoding="utf-8",
    )
    print(f"Ready {root}")


def apply_feature(root):
    space, work, task = paths(root)
    for name in PROJECTS:
        if git(work / name, "status", "--porcelain"):
            raise ValueError(f"{name} has edits. Preserve your work; the reference patch expects the clean baseline.")
        run("git", "-C", work / name, "apply", "--check", root / "feature-patches" / (name + ".patch"))
    for name in PROJECTS:
        run("git", "-C", work / name, "apply", root / "feature-patches" / (name + ".patch"))
    for name in PROJECTS:
        git(work / name, "add", ".")
        git(work / name, "-c", "user.name=Mono Example", "-c", "user.email=mono-example@example.invalid",
            "commit", "-qm", "Implement FEAT-301 in " + name)
    (space / "docs/mono/decisions.md").write_text(
        "# FEAT-301 跨服务决定\n\n"
        "采用后端二批量查询，避免列表逐条调用。可报名过滤在后端一分页前完成，保证 total 正确。\n\n"
        "新聚合采用可选参数，保留旧调用的原字段与依赖关系。"
        "名额错误时新路径返回 503，避免把未知名额当成可报名。身份贯穿两后端，批量查询含不可见记录时整体 404。\n\n"
        "来源为 tasks/FEAT-301/task.json 的预先确定契约，本演练用例据此实现。",
        encoding="utf-8",
    )
    print("Feature implemented and committed independently in three task repositories.")


def update_results(task, rows, receipt):
    report_path = task / "verification.json"
    report = json.loads(report_path.read_text())
    actual = {row["id"]: row for row in rows}
    for item in report["checks"]:
        if item["id"] in actual:
            item.update(
                status="passed",
                actual=json.dumps(actual[item["id"]]["actual"], ensure_ascii=False),
                evidence=[str(receipt.relative_to(task))],
            )
    write_json(report_path, report)


def verify(root, stage):
    space, work, task = paths(root)
    result = task / "evidence" / (stage + "-http.json")
    command = [sys.executable, "-B", space / "scripts/mono.py", "run", TASK]
    if stage == "feature":
        for number in range(1, 8):
            command.extend(["--ac", f"AC{number:02}"])
    command.extend(["--", sys.executable, "-B", space / "demo/verify.py", work,
                    "--stage", stage, "--output", result])
    run(*command)
    if stage == "feature":
        receipt = max((task / "evidence").glob("run-*.json"), key=lambda p: p.stat().st_mtime)
        update_results(task, json.loads(result.read_text()), receipt)


def browser(root):
    space, work, task = paths(root)
    node = os.environ.get("NODE_BIN") or shutil.which("node")
    if not node:
        raise ValueError("Set NODE_BIN or install Node.js for the optional browser acceptance.")
    env = os.environ.copy()
    local_playwright = HERE / "node_modules/playwright"
    if not env.get("PLAYWRIGHT_MODULE") and local_playwright.is_dir():
        env["PLAYWRIGHT_MODULE"] = str(local_playwright)
    result_dir = task / "evidence/browser"
    run(sys.executable, "-B", space / "scripts/mono.py", "run", TASK, "--ac", "AC08", "--",
        node, space / "demo/browser.cjs", work, result_dir, env=env)
    receipt = max((task / "evidence").glob("run-*.json"), key=lambda p: p.stat().st_mtime)
    update_results(task, [json.loads((result_dir / "result.json").read_text())], receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("setup", "apply", "verify", "browser", "serve", "check"):
        child = commands.add_parser(name)
        child.add_argument("target", type=Path)
        if name == "verify":
            child.add_argument("--stage", choices=("baseline", "feature"), default="feature")
        if name == "serve":
            child.add_argument("--web-port", type=int, default=4280)
    args = parser.parse_args()
    root = args.target.resolve()
    try:
        if args.operation == "setup":
            setup(root)
        elif args.operation == "apply":
            apply_feature(root)
        elif args.operation == "verify":
            verify(root, args.stage)
        elif args.operation == "browser":
            browser(root)
        elif args.operation == "serve":
            space, work, task = paths(root)
            run(sys.executable, "-B", space / "demo/serve.py", work, "--web-port", args.web_port)
        else:
            space, work, task = paths(root)
            run(sys.executable, "-B", space / "scripts/mono.py", "check", TASK)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
