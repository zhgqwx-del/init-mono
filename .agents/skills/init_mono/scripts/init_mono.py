#!/usr/bin/env python3
"""Initialize shared context, local skills and independent project checkouts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "workspace"

sys.path.insert(0, str(ASSETS / "scripts"))
from mono_projects import attach, git, prepare_project, read_registry, text, write_project_index, write_registry


def array(obj, key, default=None):
    value = obj.get(key, default)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array")
    return value


def prepare(config, target):
    data = json.loads(config.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    for field in ("name", "summary"):
        text(data, field)
    data["owner"] = text(data, "owner", "待分配")
    data["kind"] = text(data, "kind", "directory")
    if data["kind"] not in {"directory", "repository", "process"}:
        raise ValueError("kind must be directory, repository, or process")
    projects = array(data, "projects")
    if len(projects) < 2:
        raise ValueError("provide at least two project entries")
    data["projects"] = [
        prepare_project(project, config.parent, target, data["owner"], data["kind"])
        for project in projects
    ]
    names = {project["name"] for project in data["projects"]}
    if len(names) != len(projects):
        raise ValueError("duplicate project name")
    for relation in array(data, "relationships", []):
        if not isinstance(relation, dict) or relation.get("from") not in names or relation.get("to") not in names:
            raise ValueError("relationship endpoints must name configured projects")
        text(relation, "description")
    for key in ("operations",):
        if not isinstance(data.get(key, {}), dict) or any(
            not isinstance(v, str) for v in data.get(key, {}).values()
        ):
            raise ValueError(f"{key} must be an object of strings")
    if any(not isinstance(v, str) for v in array(data, "context", [])):
        raise ValueError("context entries must be strings")
    data["schema_version"] = 1
    return data


def write_context(target, data):
    links = [
        f"# {data['name']} 系统关系", "", data["summary"], "",
        f"协作负责人为 {data['owner']}。", "",
        "## 项目入口", "", "当前清单见 [projects.md](projects.md)。以下为初始化快照。", "",
    ]
    for project in data["projects"]:
        location = project.get("path", project["source"])
        links.extend([
            f"### {project['name']}", "", f"- 位置为 {location}",
            f"- 职责为 {project['role']}", f"- 项目负责人为 {project['owner']}",
            f"- 基线为 {project.get('base_sha', '待核实')}，参考引用为 {project['ref']}",
            f"- 启动命令为 {project['commands'].get('start') or '待核实'}",
            f"- 仓内测试命令为 {project['commands'].get('test') or '待核实'}", "",
        ])
    links.extend(["## 项目之间的关系", ""])
    for relation in data.get("relationships", []):
        links.append(f"- {relation['from']} → {relation['to']}。{relation['description']}")
    if not data.get("relationships"):
        links.append("待核实调用方、提供方、共用契约和兼容要求。")
    links.extend(["", "## 其他上下文", "", *data.get("context", ["待接入现有业务与架构说明。"]), ""])
    (target / "docs/mono/system.md").write_text("\n".join(links), encoding="utf-8")
    ops = ["# 联调与发布", ""]
    titles = {
        "environment": "环境与依赖", "baseline": "基线验证",
        "fixtures": "测试数据与账号", "startup": "联调启动顺序",
        "logs": "诊断入口与访问范围", "release": "发布与审批",
        "rollback": "停止条件与恢复",
    }
    for key, title in titles.items():
        ops.extend([f"## {title}", "", data.get("operations", {}).get(key) or "待按现有项目核实并补充。", ""])
    (target / "docs/mono/operations.md").write_text("\n".join(ops), encoding="utf-8")


def initialize(config, target, dry_run):
    if target.exists() or target.is_symlink():
        raise ValueError(f"target already exists: {target}")
    data = prepare(config, target)
    if dry_run:
        print(json.dumps({"target": str(target), "kind": data["kind"],
                          "projects": data["projects"], "writes": "shared context, 3 skills, task tools"},
                         ensure_ascii=False, indent=2))
        return

    target.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ASSETS, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    write_registry(target, data)
    write_context(target, data)
    if data["kind"] == "repository":
        git(target, "init", "-q", "-b", "main")
    try:
        for project in data["projects"]:
            attach(target, project)
            write_registry(target, data)
    except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
        write_context(target, data)
        write_project_index(target, data)
        print(f"Partial workspace preserved at {target}. Inspect mono.json and git worktree list before retrying.",
              file=sys.stderr)
        raise
    write_context(target, data)
    write_project_index(target, data)
    print(f"Created {target}\nRead README.md, then use $mono-start for the first requirement.")


def upgrade(target):
    registry = read_registry(target)
    hashes = json.loads((ASSETS.parent / "upgrade-v1.json").read_text(encoding="utf-8"))
    files = [
        "scripts/mono.py", "scripts/mono_projects.py", "scripts/mono_stdd.py", "README.md",
        "docs/mono/stdd-sdd.md",
        *(f".agents/skills/{name}/SKILL.md" for name in ("mono-start", "mono-verify", "mono-wrap")),
    ]
    actions = []
    for name in files:
        source, path = ASSETS / name, target / name
        if not path.exists() and not path.is_symlink():
            actions.append((source, path))
        elif path.is_symlink() or not path.is_file():
            raise ValueError(f"review this customized path before upgrading: {path}")
        elif path.read_bytes() != source.read_bytes():
            if hashlib.sha256(path.read_bytes()).hexdigest() != hashes.get(name):
                # A team's README can be retained without blocking the tool upgrade.
                if name == "README.md":
                    print(f"Retaining customized README: {path}")
                    continue
                raise ValueError(f"review this customized file before upgrading: {path}")
            actions.append((source, path))
    for source, path in actions:
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, path)
    write_project_index(target, registry)
    print(f"Workspace tools available at {target}. See docs/mono/stdd-sdd.md.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("target", type=Path, nargs="?")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--upgrade", action="store_true", help="update tools in a generated workspace")
    args = parser.parse_args()
    try:
        if args.upgrade:
            if args.target or args.dry_run:
                parser.error("use --upgrade WORKSPACE")
            upgrade(args.input.resolve())
            return
        if args.target is None:
            parser.error("provide INPUT and TARGET")
        target = args.target.parent.resolve() / args.target.name
        initialize(args.input.resolve(), target, args.dry_run)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
