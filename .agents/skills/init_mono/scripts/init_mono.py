#!/usr/bin/env python3
"""Initialize shared context, local skills and independent project checkouts."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "workspace"


def git(*args):
    return subprocess.check_output(["git", *(str(a) for a in args)], text=True).strip()


def text(obj, key, default=None):
    value = obj.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a nonempty string")
    return value.strip()


def array(obj, key, default=None):
    value = obj.get(key, default)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array")
    return value


def url(value):
    return "://" in value or re.match(r"^[\w.-]+@[\w.-]+:", value)


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
    names = set()
    for project in projects:
        if not isinstance(project, dict):
            raise ValueError("project must be an object")
        name = text(project, "name")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) or name in names:
            raise ValueError(f"invalid or duplicate project name: {name}")
        names.add(name)
        project["name"] = name
        for key in ("source", "role"):
            project[key] = text(project, key)
        project["mode"] = text(project, "mode", "reference")
        if project["mode"] not in {"worktree", "clone", "reference"}:
            raise ValueError(f"{name}: unsupported mode")
        if data["kind"] == "process":
            project["mode"] = "reference"
        project["owner"] = text(project, "owner", data["owner"])
        project["ref"] = text(project, "ref", "HEAD")
        source = project["source"]
        if not url(source):
            source = str((config.parent / Path(source).expanduser()).resolve())
        project["source"] = source
        project["commands"] = project.get("commands", {})
        if not isinstance(project["commands"], dict) or any(
            not isinstance(v, str) for v in project["commands"].values()
        ):
            raise ValueError(f"{name}: commands must be an object of strings")
        if project["mode"] == "worktree":
            root = Path(git("-C", source, "rev-parse", "--show-toplevel")).resolve()
            if Path(source) != root or target.is_relative_to(root):
                raise ValueError(f"{name}: use a repository root outside the new workspace")
            project["base_sha"] = git("-C", source, "rev-parse", "--verify",
                                      "--end-of-options", project["ref"] + "^{commit}")
        elif project["mode"] == "clone" and not url(source) and target.is_relative_to(Path(source)):
            raise ValueError(f"{name}: target must be outside the clone source")
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


def write_registry(target, data):
    path = target / "mono.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_context(target, data):
    links = [
        f"# {data['name']} 系统关系", "", data["summary"], "",
        f"协作负责人为 {data['owner']}。", "",
        "## 项目入口", "",
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
    shutil.copytree(ASSETS, target, dirs_exist_ok=True)
    write_registry(target, data)
    write_context(target, data)
    if data["kind"] == "repository":
        git("-C", target, "init", "-q", "-b", "main")
    try:
        for project in data["projects"]:
            if project["mode"] == "reference":
                continue
            destination = target / "repos" / project["name"]
            destination.parent.mkdir(exist_ok=True)
            if project["mode"] == "worktree":
                git("-C", project["source"], "worktree", "add", "--detach",
                    destination, project["base_sha"])
            else:
                git("-c", "protocol.ext.allow=never", "clone", "--no-hardlinks",
                    "--", project["source"], destination)
                project["base_sha"] = git("-C", destination, "rev-parse", "--verify",
                                           "--end-of-options", project["ref"] + "^{commit}")
                git("-C", destination, "switch", "--detach", project["base_sha"])
            project["path"] = str(destination.relative_to(target))
            write_registry(target, data)
    except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
        write_context(target, data)
        print(f"Partial workspace preserved at {target}. Inspect mono.json and git worktree list before retrying.",
              file=sys.stderr)
        raise
    write_context(target, data)
    print(f"Created {target}\nRead README.md, then use $mono-start for the first requirement.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        target = args.target.parent.resolve() / args.target.name
        initialize(args.input.resolve(), target, args.dry_run)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
