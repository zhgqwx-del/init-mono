"""Expose each task's native STDD/SDD entry points without copying repo rules."""
import json
import re
import subprocess
import sys

from mono_projects import git, git_root, stdd_profile, write_lock


def change_directory(checkout, change_id):
    for parent in ("changes", "changes/archive"):
        candidate = checkout / parent / change_id
        if (candidate / "change.md").is_file():
            return candidate
    return None


def load_bindings(task):
    path = task / "stdd.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def describe(root, task, states):
    bindings = load_bindings(task)
    result = {}
    for name, state in states.items():
        checkout = root / state["path"] if state["path"] else None
        entry = dict(state)
        if checkout and checkout.is_dir():
            if "branch" in state:
                entry["task_branch"] = state["branch"]
            entry.update(
                branch=git(checkout, "branch", "--show-current"),
                sha=git(checkout, "rev-parse", "HEAD"),
                stdd=stdd_profile(checkout),
            )
            if name in bindings:
                change_id = bindings[name]
                change = change_directory(checkout, change_id)
                entry["stdd_change"] = {
                    "id": change_id,
                    "path": str(change.relative_to(checkout)) if change else None,
                }
        result[name] = entry
    return result


def bind(root, task, project, state, change_id, title, design):
    if not re.fullmatch(r"[0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*", change_id):
        raise ValueError("STDD change ID must look like 014-login")
    task_work = root / "work" / task.name
    checkout = root / state["path"] if state["path"] else None
    if checkout is None or checkout.resolve().parent != task_work.resolve():
        raise ValueError(f"{project}: use a feature checkout under work/{task.name} (new --worktrees)")
    if git_root(checkout) != checkout.resolve():
        raise ValueError(f"{project}: feature checkout is missing its own Git repository")
    expected = state.get("branch", "mono/" + task.name)
    current = git(checkout, "branch", "--show-current")
    if current != expected:
        raise ValueError(f"{project}: checkout is on {current or 'detached HEAD'}, expected {expected}")
    with write_lock(task / ".mono-stdd.lock"):
        bindings = load_bindings(task)
        if project in bindings and bindings[project] != change_id:
            raise ValueError(f"{project} already maps to STDD change {bindings[project]}")
        change = change_directory(checkout, change_id)
        if change is None:
            scaffold = stdd_profile(checkout)["scaffold"]
            if not scaffold:
                raise ValueError(f"{project}: no STDD new_change.py; follow the repo's own process")
            if not title or not title.strip() or len(title.strip().splitlines()) != 1:
                raise ValueError("provide a nonempty single-line --title for a new STDD change")
            cmd = [sys.executable, "-B", scaffold, change_id, title, "--roles"]
            if design:
                cmd.append("--design")
            subprocess.run(cmd, cwd=checkout, check=True)
            change = change_directory(checkout, change_id)
            if change is None:
                raise ValueError(f"{project}: native script did not produce change.md")
            with (change / "change.md").open("a", encoding="utf-8") as out:
                out.write(f"\n## 跨仓需求\n\nMono 工单为 {task.name}。本仓规格与验收见同目录记录。\n")
        bindings[project] = change_id
        (task / "stdd.json").write_text(
            json.dumps(bindings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{project}: {change}")
