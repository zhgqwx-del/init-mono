#!/usr/bin/env python3
"""Task worktrees and command evidence for a Mono workspace. Python 3.9+."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import uuid

from mono_projects import (
    attach, git_root, head, prepare_project, project_name, read_registry, read_workspace_version,
    remote, task_base, write_lock, write_project_index, write_registry,
)
from mono_stdd import bind, describe

ROOT = Path(__file__).resolve().parent.parent


def write_json(path, value):
    # Each invocation uses its own receipt ID. Task creation uses an exclusive mkdir.
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise ValueError(f"invalid task ID: {value}")
    return value


def required(obj, name):
    value = obj.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value.strip()


def task_dir(task_id):
    return ROOT / "tasks" / identifier(task_id)


def key_values(values, projects, label):
    entries = {}
    for value in values:
        name, separator, ref = value.partition("=")
        if not separator or name not in projects or not ref or name in entries:
            raise ValueError(f"invalid or repeated {label}: {value}; use PROJECT=VALUE")
        entries[name] = ref
    return entries


def add_project(args):
    with write_lock(ROOT / ".mono-registry.lock"):
        registry = read_registry(ROOT)
        raw = {key: value for key, value in {
            "name": args.name, "source": args.source, "mode": args.mode, "ref": args.ref,
            "role": args.role, "owner": args.owner, "clone_source": args.clone_source,
            "target_branch": args.target_branch,
        }.items() if value is not None}
        project = prepare_project(raw, Path.cwd(), ROOT, registry["owner"], registry["kind"])
        if any(row["name"] == project["name"] for row in registry["projects"]):
            raise ValueError(f"project already registered: {project['name']}")
        attach(ROOT, project)
        registry["projects"].append(project)
        write_registry(ROOT, registry)
        write_project_index(ROOT, registry)
        print(json.dumps(project, ensure_ascii=False, indent=2))


def bootstrap_projects(names, source_args):
    with write_lock(ROOT / ".mono-registry.lock"):
        projects = {project["name"]: project for project in read_registry(ROOT)["projects"]}
        selected = names or list(projects)
        unknown = set(selected) - projects.keys()
        if unknown:
            raise ValueError("unknown projects: " + ", ".join(sorted(unknown)))
        overrides = key_values(source_args, selected, "source")
        if (ROOT / "repos").is_symlink():
            raise ValueError("repos/ must be a directory inside the workspace")
        for name in dict.fromkeys(selected):
            project = projects[project_name(name)]
            if project["mode"] == "reference":
                print(f"Reference only: {name}")
                continue
            relative = Path("repos") / name
            base = project.get("base_sha", "")
            if (Path(project.get("path", "")) != relative
                    or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", base)):
                raise ValueError(f"{name}: missing checkout path or baseline; review its registration in mono.json")
            destination = ROOT / relative
            if destination.exists() or destination.is_symlink():
                if destination.is_symlink() or git_root(destination) != destination:
                    raise ValueError(f"{name}: {relative} already exists and is not a project checkout")
                print(f"Already checked out: {relative}")
                continue
            source = overrides.get(name) or project.get("clone_source")
            if not source and remote(project["source"]):
                source = project["source"]
            if not source:
                raise ValueError(f"{name}: set clone_source in mono.json or pass --source {name}=GIT_URL")
            if not remote(source):
                raise ValueError(f"{name}: bootstrap source must be a Git URL")
            try:
                attach(ROOT, dict(project, mode="clone", source=source, ref=base))
            except subprocess.CalledProcessError as error:
                raise ValueError(
                    f"{name}: could not restore {base}. Verify repository access and that the commit is published."
                ) from error
            print(f"Restored {relative} at {base}")


def project_checkout(project):
    path = project.get("path")
    if not path:
        return None
    location = ROOT / path
    if git_root(location) != location.resolve():
        name = project["name"]
        raise ValueError(f"{name}: missing Git checkout at {path}; run mono.py bootstrap {name}")
    return location


def sync_baseline(location, sha):
    if git(location, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        return "local_changes"
    current = head(location, "HEAD")
    if current == sha:
        return "current"
    if git(location, "branch", "--show-current").strip():
        return "local_branch"
    try:
        git(location, "merge-base", "--is-ancestor", current, sha)
    except subprocess.CalledProcessError as error:
        return "diverged" if error.returncode == 1 else "blocked"
    try:
        git(location, "switch", "--detach", "--no-overwrite-ignore", "--no-recurse-submodules", sha)
    except subprocess.CalledProcessError:
        return "blocked"
    return "updated"


def project_baselines(names, sync=False):
    projects = {project["name"]: project for project in read_registry(ROOT)["projects"]}
    selected = dict.fromkeys(names) if names else projects
    unknown = selected.keys() - projects.keys()
    if unknown:
        raise ValueError("unknown projects: " + ", ".join(sorted(unknown)))
    baselines = {}
    for name in selected:
        project = projects[name]
        if project["mode"] == "reference":
            continue
        location = project_checkout(project)
        if location is None:
            raise ValueError(f"{name}: missing Git checkout registration; review mono.json")
        ref, sha = task_base(location, project)
        baselines[name] = {"path": project["path"], "base_ref": ref, "base_sha": sha}
    if sync:
        for baseline in baselines.values():
            baseline["checkout_state"] = sync_baseline(ROOT / baseline["path"], baseline["base_sha"])
    print(json.dumps(baselines, ensure_ascii=False, indent=2))


def create_task(input_path, use_worktrees, base_args=(), branch_args=()):
    spec = read_json(input_path)
    if not isinstance(spec, dict):
        raise ValueError("task input must be an object")
    task_id = identifier(spec.get("id"))
    for key in ("title", "goal"):
        required(spec, key)
    registry = read_json(ROOT / "mono.json")
    spec["owner"] = required(spec, "owner") if "owner" in spec else registry["owner"]
    names = spec.get("projects", [project["name"] for project in registry["projects"]])
    if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names) or len(set(names)) != len(names):
        raise ValueError("projects must be a nonempty list of unique project names")
    known = {p["name"]: p for p in registry["projects"]}
    if set(names) - known.keys():
        raise ValueError("task refers to unknown projects")
    bases = key_values(base_args, names, "base")
    branches = key_values(branch_args, names, "branch")
    if (bases or branches) and not use_worktrees:
        raise ValueError("--base and --branch require --worktrees")
    acceptance = spec.get("acceptance", [])
    if not isinstance(acceptance, list) or any(not isinstance(a, dict) for a in acceptance):
        raise ValueError("acceptance must be an array of objects")
    check_ids = set()
    for item in acceptance:
        ac_id = required(item, "id")
        if ac_id in check_ids:
            raise ValueError(f"duplicate acceptance ID: {ac_id}")
        check_ids.add(ac_id)
        required(item, "check")
        required(item, "expected")
    spec["acceptance"] = acceptance
    spec["contract"] = required(spec, "contract") if "contract" in spec else "待确认"
    destination = task_dir(task_id)
    if destination.exists() or destination.is_symlink() or (ROOT / "work" / task_id).exists():
        raise ValueError(f"task/work directory already exists: {task_id}")

    state = {}
    branch_keys = set()
    for name in names:
        project = known[name]
        location = project_checkout(project)
        entry = {"path": project.get("path", ""), "source": project.get("clone_source", project["source"])}
        if not location and (name in bases or name in branches):
            raise ValueError(f"{name}: attach a Git checkout before selecting a base or branch")
        if use_worktrees and location:
            branch = branches.get(name, "mono/" + task_id)
            if git(location, "check-ref-format", "--branch", branch).decode().strip() != branch:
                raise ValueError(f"{name}: supply a literal branch name")
            if git(location, "branch", "--list", branch).strip():
                raise ValueError(f"{name}: task branch already exists: {branch}")
            common = git(location, "rev-parse", "--git-common-dir").decode().strip()
            key = ((location / common).resolve(), branch)
            if key in branch_keys:
                raise ValueError("the same source repository appears twice with the same task branch")
            branch_keys.add(key)
            ref, sha = (bases[name], head(location, bases[name])) if name in bases else task_base(location, project)
            entry.update(branch=branch, base_ref=ref, base_sha=sha,
                         base_path=entry["path"], path="")
        state[name] = entry
    destination.parent.mkdir(exist_ok=True)
    destination.mkdir(exist_ok=False)
    write_json(destination / "task.json", spec)
    write_json(destination / "projects.json", state)
    (destination / "task.md").write_text(
        f"# {task_id} {spec['title']}\n\n{spec['goal']}\n\n"
        f"负责人为 {spec['owner']}。\n\n## 共享契约\n\n{spec['contract']}\n\n"
        "## 验收判据\n\n以 task.json 中的 acceptance 为结构化记录。"
        "每条包含初始状态、动作和预期，未确定的规则在此补全并同步该记录。\n\n"
        "## 待决问题\n\n核对接口兼容、错误处理、数据权限、测试数据和成功判定。\n",
        encoding="utf-8",
    )
    (destination / "plan.md").write_text(
        "# 跨项目实施计划\n\n## 影响范围\n\n逐仓定位实际文件、入口与调用路径，关联验收编号。\n\n"
        "## 实施与验证\n\n按依赖顺序列出改动、仓内测试、联调与恢复步骤。"
        "记录采用过的业务和技术决策，必要时更新 ../../docs/mono/decisions.md。\n",
        encoding="utf-8",
    )
    write_json(destination / "verification.json", {
        "checks": [{"id": item["id"], "status": "pending", "actual": "", "evidence": []}
                   for item in acceptance],
        "human_decision": {"status": "pending", "reviewer": "", "note": ""},
    })
    (destination / "delivery.md").write_text(
        "# 交付与复盘\n\n## 受测版本与评审\n\n填写各仓 SHA、PR 和相关验证记录。\n\n"
        "## 发布与恢复\n\n引用现有发布流程，记录兼容顺序、审批责任、上线冒烟、停止条件和恢复步骤。\n\n"
        "## 复盘\n\n记录需求确认到验收的时间、人工投入、等待、返工、缺陷、模型成本和需更新的共享知识。\n",
        encoding="utf-8",
    )
    if use_worktrees:
        try:
            for name, entry in state.items():
                if not entry.get("base_path"):
                    continue
                worktree = ROOT / "work" / task_id / name
                worktree.parent.mkdir(parents=True, exist_ok=True)
                git(ROOT / entry["base_path"], "worktree", "add", "--no-track", "-b",
                    entry["branch"], str(worktree), entry["base_sha"])
                entry["path"] = str(worktree.relative_to(ROOT))
                write_json(destination / "projects.json", state)
        except (OSError, subprocess.CalledProcessError, KeyboardInterrupt):
            print(f"Partial task preserved at {destination}; inspect projects.json and git worktree list.",
                  file=sys.stderr)
            raise
    print(f"Created {destination}\nContinue with $mono-start.")


def content_digest(root):
    digest = hashlib.sha256()
    files = sorted(set(git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")) - {b""})
    for raw in files:
        path = root / os.fsdecode(raw)
        digest.update(raw + b"\0")
        if path.exists() or path.is_symlink():
            digest.update(str(path.lstat().st_mode).encode() + b"\0")
        if path.is_symlink():
            digest.update(b"link\0" + os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif path.is_dir():
            nested_root = Path(git(path, "rev-parse", "--show-toplevel").decode().strip()).resolve()
            if nested_root != path.resolve():
                raise ValueError(f"initialize the submodule before verification: {path}")
            digest.update(git(path, "rev-parse", "HEAD") + content_digest(path).encode())
        else:
            digest.update(b"deleted\0")
        digest.update(b"\0")
    return digest.hexdigest()


def snapshot(task):
    result = {}
    for name, entry in read_json(task / "projects.json").items():
        location = entry["path"]
        if not location:
            result[name] = {"available": False, "source": entry["source"]}
            continue
        root = ROOT / location
        result[name] = {
            "available": True, "sha": git(root, "rev-parse", "HEAD").decode().strip(),
            "files_sha256": content_digest(root),
        }
    return result


def spec_digest(task, version=2):
    digest = hashlib.sha256()
    paths = [task / "task.json", task / "task.md", ROOT / "AGENTS.md",
             *(path for path in (ROOT / "docs/mono").glob("*.md")
               if path.name not in {"projects.md", "stdd-sdd.md"})]
    if version == 1:
        paths.append(ROOT / "mono.json")
    else:
        states = read_json(task / "projects.json")
        registry = read_registry(ROOT)
        context = {
            "projects": [p for p in registry["projects"] if p["name"] in states],
            "relationships": [r for r in registry.get("relationships", [])
                              if r["from"] in states and r["to"] in states],
        }
        digest.update(json.dumps(context, sort_keys=True, ensure_ascii=False).encode())
        paths.append(task / "projects.json")
        bindings = task / "stdd.json"
        if bindings.exists():
            paths.append(bindings)
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def execute(args):
    task = task_dir(args.task)
    spec = read_json(task / "task.json")
    known = {item["id"] for item in spec["acceptance"]}
    if set(args.ac) - known:
        raise ValueError("unknown acceptance ID")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("provide the executable and its arguments after --")
    before, spec_before = snapshot(task), spec_digest(task)
    start = datetime.now(timezone.utc).isoformat()
    options = {"start_new_session": True} if os.name == "posix" else {}
    with subprocess.Popen(command, cwd=(ROOT / args.cwd).resolve(), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, **options) as process:
        timed_out = False
        try:
            output = process.communicate(timeout=args.timeout)[0]
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            output = process.communicate()[0]
    after, spec_after = snapshot(task), spec_digest(task)
    receipt = {
        "version": 2, "task_id": args.task, "covers": args.ac, "command": command,
        "cwd": str((ROOT / args.cwd).resolve()), "started": start,
        "finished": datetime.now(timezone.utc).isoformat(),
        "exit_code": process.returncode, "timed_out": timed_out,
        "before": before, "after": after, "spec_digest": spec_before,
        "stable": before == after and spec_before == spec_after,
        "output": output.decode("utf-8", errors="replace"),
    }
    directory = task / "evidence"
    directory.mkdir(exist_ok=True)
    path = directory / ("run-" + uuid.uuid4().hex[:12] + ".json")
    write_json(path, receipt)
    print(receipt["output"], end="")
    print(f"\nReceipt {path.relative_to(task)}")
    return 1 if timed_out or process.returncode or not receipt["stable"] else 0


def check(task_id):
    task = task_dir(task_id)
    spec = read_json(task / "task.json")
    report = read_json(task / "verification.json")
    current, signature = snapshot(task), spec_digest(task)
    errors = []
    expected_ids = [item["id"] for item in spec["acceptance"]]
    rows = report["checks"]
    actual_ids = [row["id"] for row in rows]
    if not expected_ids or sorted(expected_ids) != sorted(actual_ids):
        errors.append("acceptance/check IDs are empty, missing, or duplicated")
    for name, version in current.items():
        if not version["available"]:
            errors.append(f"{name}: project not attached; functional verification remains pending")
    for row in rows:
        label = row["id"]
        if row["status"] != "passed" or not str(row["actual"]).strip() or not row["evidence"]:
            errors.append(f"{label}: actual result and passing evidence required")
            continue
        for entry in row["evidence"]:
            path = (task / entry).resolve()
            if not path.is_relative_to((task / "evidence").resolve()):
                raise ValueError("evidence must be inside the task evidence directory")
            if not path.is_file():
                errors.append(f"{label}: missing {entry}")
                continue
            receipt = read_json(path)
            if (receipt.get("task_id") != task_id or label not in receipt.get("covers", [])
                    or receipt.get("exit_code") != 0 or receipt.get("timed_out")
                    or receipt.get("stable") is not True
                    or receipt.get("before") != current or receipt.get("after") != current
                    or receipt.get("spec_digest") != (
                        signature if receipt.get("version") == 2 else spec_digest(task, version=1)
                    )):
                errors.append(f"{label}: failed, unrelated, or outdated evidence {entry}")
    for error in errors:
        print("PENDING " + error)
    if not errors:
        print("Evidence matches the current specification and project contents.")
    print("Human decision", json.dumps(report.get("human_decision", {}), ensure_ascii=False))
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    new = commands.add_parser("new")
    new.add_argument("input", type=Path)
    new.add_argument("--worktrees", action="store_true")
    new.add_argument("--base", action="append", default=[], metavar="PROJECT=REF")
    new.add_argument("--branch", action="append", default=[], metavar="PROJECT=BRANCH")
    add = commands.add_parser("add", help="register and attach another repository")
    add.add_argument("name")
    add.add_argument("source")
    for option in ("role", "ref", "owner", "mode", "clone-source", "target-branch"):
        add.add_argument("--" + option)
    bootstrap = commands.add_parser("bootstrap", help="restore registered project checkouts after cloning the workspace")
    bootstrap.add_argument("projects", nargs="*", metavar="PROJECT")
    bootstrap.add_argument("--source", action="append", default=[], metavar="PROJECT=GIT_URL")
    commands.add_parser("repos", help="list registered repositories")
    commands.add_parser("version", help="show the scaffold Release versions and upgrade history")
    baselines = commands.add_parser("baselines", help="resolve and fetch target commits for feature planning")
    baselines.add_argument("projects", nargs="*", metavar="PROJECT")
    baselines.add_argument("--sync", action="store_true", help="fast-forward clean detached base checkouts")
    commands.add_parser("status", help="list task checkouts and their STDD entry points").add_argument("task")
    stdd = commands.add_parser("stdd", help="create or link a native STDD change for a project")
    stdd.add_argument("task")
    stdd.add_argument("project")
    stdd.add_argument("change")
    stdd.add_argument("--title")
    stdd.add_argument("--design", action="store_true")
    run = commands.add_parser("run")
    run.add_argument("task")
    run.add_argument("--ac", action="append", default=[])
    run.add_argument("--cwd", default=".")
    run.add_argument("--timeout", type=float, default=600)
    # Parse command tail explicitly so options before -- remain options.
    commands.add_parser("check").add_argument("task")
    args_list = sys.argv[1:]
    command = []
    if args_list[:1] == ["run"] and "--" in args_list:
        marker = args_list.index("--")
        command, args_list = args_list[marker + 1:], args_list[:marker]
    args = parser.parse_args(args_list)
    try:
        if args.operation == "new":
            create_task(args.input.resolve(), args.worktrees, args.base, args.branch)
            return 0
        if args.operation == "add":
            add_project(args)
            return 0
        if args.operation == "bootstrap":
            bootstrap_projects(args.projects, args.source)
            return 0
        if args.operation == "repos":
            print(json.dumps(read_registry(ROOT)["projects"], ensure_ascii=False, indent=2))
            return 0
        if args.operation == "version":
            print(json.dumps(read_workspace_version(ROOT), ensure_ascii=False, indent=2))
            return 0
        if args.operation == "baselines":
            project_baselines(args.projects, args.sync)
            return 0
        if args.operation in {"status", "stdd"}:
            task = task_dir(args.task)
            states = read_json(task / "projects.json")
            if args.operation == "status":
                print(json.dumps(describe(ROOT, task, states), ensure_ascii=False, indent=2))
            else:
                bind(ROOT, task, args.project, states[args.project], args.change, args.title, args.design)
            return 0
        if args.operation == "run":
            args.command = command
            if args.timeout <= 0:
                raise ValueError("timeout must be positive")
            return execute(args)
        return check(args.task)
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
