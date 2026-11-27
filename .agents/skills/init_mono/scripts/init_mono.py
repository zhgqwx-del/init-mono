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
from mono_projects import (
    AGENT_SKILL_DIRS, VERSION_RECORD, attach, git, prepare_project, read_registry, read_workspace_version,
    release_version, text, write_json_atomic, write_lock, write_project_index, write_registry,
)

MONO_SKILLS = ("mono-start", "mono-verify", "mono-wrap")


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


def bundle_version():
    tag = (ASSETS.parent.parent / "VERSION").read_text(encoding="utf-8").strip()
    release_version(tag)
    return tag


def workspace_skill_files(agents):
    files = {}
    for agent in agents:
        for name in MONO_SKILLS:
            source = ASSETS / AGENT_SKILL_DIRS["codex"] / name
            destination = f"{AGENT_SKILL_DIRS[agent]}/{name}"
            files[f"{destination}/SKILL.md"] = source / "SKILL.md"
            if agent == "codex":
                files[f"{destination}/agents/openai.yaml"] = source / "agents/openai.yaml"
    if "claude" in agents:
        files["CLAUDE.md"] = ASSETS / "CLAUDE.md"
    return files


def copy_files(actions):
    for source, path in actions:
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, path)


def initialize(config, target, dry_run, agents):
    if target.exists() or target.is_symlink():
        raise ValueError(f"target already exists: {target}")
    data = prepare(config, target)
    tag = bundle_version()
    if dry_run:
        print(json.dumps({"target": str(target), "kind": data["kind"],
                          "scaffold_version": tag,
                          "skill_directories": {agent: AGENT_SKILL_DIRS[agent] for agent in agents},
                          "projects": data["projects"], "writes": "shared context, 3 skills, task tools"},
                         ensure_ascii=False, indent=2))
        return

    target.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ASSETS, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".agents", "CLAUDE.md"))
    copy_files((source, target / name) for name, source in workspace_skill_files(agents).items())
    write_json_atomic(target / VERSION_RECORD, {
        "initialized_version": tag, "current_version": tag, "upgrades": [],
    })
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
    print(f"Created {target}\nRead README.md for your agent's mono-start command.")


def upgrade(target, agents):
    with write_lock(target / ".mono-registry.lock"):
        upgrade_workspace(target, agents)


def upgrade_workspace(target, agents):
    registry = read_registry(target)
    tag = bundle_version()
    record = read_workspace_version(target)
    current = record["current_version"]
    if current is not None and release_version(current) > release_version(tag):
        raise ValueError(f"workspace already uses {current}; use that version or a newer bundle")
    versions = [json.loads(path.read_text(encoding="utf-8"))
                for path in ASSETS.parent.glob("upgrade-v*.json")]
    files = {name: ASSETS / name for name in (
        "scripts/mono.py", "scripts/mono_projects.py", "scripts/mono_stdd.py", "README.md",
        "docs/mono/stdd-sdd.md",
    )}
    skill_files = workspace_skill_files(agents)
    files.update(skill_files)
    codex_skills = {f"{AGENT_SKILL_DIRS['codex']}/{name}/SKILL.md" for name in MONO_SKILLS}
    preserve_custom = {"README.md"} | (skill_files.keys() - codex_skills)
    actions = []
    for name, source in files.items():
        path = target / name
        parents = (target / parent for parent in reversed(Path(name).parents))
        blocked_parent = any(parent.is_symlink() or (parent.exists() and not parent.is_dir())
                             for parent in parents)
        if blocked_parent or path.is_symlink() or (path.exists() and not path.is_file()):
            if name in preserve_custom:
                print(f"Retaining customized path: {path}")
                continue
            raise ValueError(f"review this customized path before upgrading: {path}")
        if not path.exists():
            actions.append((source, path))
            continue
        content = path.read_bytes()
        if content != source.read_bytes():
            digest = hashlib.sha256(content).hexdigest()
            source_name = source.relative_to(ASSETS).as_posix()
            if not any(digest == hashes.get(source_name) for hashes in versions):
                if name in preserve_custom:
                    print(f"Retaining customized file: {path}")
                    continue
                raise ValueError(f"review this customized file before upgrading: {path}")
            actions.append((source, path))
    copy_files(actions)
    write_project_index(target, registry)
    if current != tag:
        record["upgrades"].append({"from": current, "to": tag})
        record["current_version"] = tag
        write_json_atomic(target / VERSION_RECORD, record)
    print(f"Workspace tools {tag} available at {target}. See docs/mono/stdd-sdd.md.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("target", type=Path, nargs="?")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--upgrade", action="store_true", help="update tools in a generated workspace")
    parser.add_argument("--agent", choices=("all", *AGENT_SKILL_DIRS), default="all",
                        help="client skill layout to install (default: all)")
    args = parser.parse_args()
    agents = tuple(AGENT_SKILL_DIRS) if args.agent == "all" else (args.agent,)
    try:
        if args.upgrade:
            if args.target or args.dry_run:
                parser.error("use --upgrade WORKSPACE [--agent AGENT]")
            upgrade(args.input.resolve(), agents)
            return
        if args.target is None:
            parser.error("provide INPUT and TARGET")
        target = args.target.parent.resolve() / args.target.name
        initialize(args.input.resolve(), target, args.dry_run, agents)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
