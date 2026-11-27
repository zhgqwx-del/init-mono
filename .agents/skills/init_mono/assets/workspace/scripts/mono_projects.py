"""Repository registration shared by the Mono initializer and workspace CLI."""
from contextlib import contextmanager
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit


STDD_SKILLS = ("stdd-start", "stdd-delivery", "stdd-test-report", "stdd-wrap")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def text(obj, key, default=None):
    value = obj.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a nonempty string")
    return value.strip()


def remote(value):
    return "://" in value or re.match(r"^[\w.-]+@[\w.-]+:", value)


def project_name(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError(f"invalid project name: {value}")
    return value


def head(root, ref):
    return git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")


def git_root(path):
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def shared_origin(checkout):
    # Read the stored fetch URL before any machine-specific Git URL rewrites.
    result = subprocess.run(
        ["git", "-C", str(checkout), "config", "--local", "--null", "--get-all", "remote.origin.url"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    origin = result.stdout.split("\0", 1)[0].strip()
    if re.fullmatch(r"[\w.-]+@[\w.-]+:\S+", origin):
        return origin
    try:
        url = urlsplit(origin)
    except ValueError:
        return None
    if (url.scheme not in {"https", "http", "ssh", "git"} or not url.hostname
            or not url.path.strip("/") or url.query or url.fragment or re.search(r"\s", origin)):
        return None
    if url.scheme in {"https", "http"}:
        return url._replace(netloc=url.netloc.rsplit("@", 1)[-1]).geturl()
    return origin if url.password is None else None


def branch_ref(root, branch):
    ref = "refs/heads/" + branch
    if branch.startswith(("-", "refs/")) or branch == "HEAD" or subprocess.run(
        ["git", "-C", str(root), "check-ref-format", ref], capture_output=True,
    ).returncode:
        raise ValueError(f"invalid target branch: {branch}")
    return ref


def prepare_project(raw, basedir, root, owner, kind):
    if not isinstance(raw, dict):
        raise ValueError("project must be an object")
    name, source = project_name(text(raw, "name")), text(raw, "source")
    mode = text(raw, "mode", "auto")
    local = None if remote(source) else (basedir / Path(source).expanduser()).resolve()
    if kind == "process":
        mode = "reference"
    if mode == "auto":
        if local is None:
            mode = "clone"
        elif not local.is_dir():
            raise ValueError(f"{name}: source directory does not exist: {local}")
        else:
            mode = "worktree" if git_root(local) == local else "reference"
    if mode not in {"worktree", "clone", "reference"}:
        raise ValueError(f"{name}: unsupported mode {mode}")
    if mode != "reference" and local and root.is_relative_to(local):
        raise ValueError(f"{name}: put the workspace outside its repository")
    commands = raw.get("commands", {})
    if not isinstance(commands, dict) or any(not isinstance(v, str) for v in commands.values()):
        raise ValueError(f"{name}: commands must be an object of strings")
    project = {
        "name": name, "source": str(local) if local else source, "mode": mode,
        "role": text(raw, "role", name), "owner": text(raw, "owner", owner),
        "ref": text(raw, "ref", "HEAD"), "commands": commands,
    }
    if mode != "reference" and "target_branch" in raw:
        branch = text(raw, "target_branch")
        branch_ref(basedir, branch)
        project["target_branch"] = branch
    if mode != "reference" and "clone_source" in raw:
        clone_source = text(raw, "clone_source")
        if not remote(clone_source):
            raise ValueError(f"{name}: clone_source must be a Git URL")
        project["clone_source"] = clone_source
    if mode == "worktree":
        if not local or git_root(local) != local:
            raise ValueError(f"{name}: worktree mode needs the root of a local Git checkout")
        project["base_sha"] = head(local, project["ref"])
        if "clone_source" not in project:
            origin = shared_origin(local)
            if origin:
                project["clone_source"] = origin
    return project


def task_base(checkout, project):
    """Resolve a remote branch tip and make its exact commit available locally."""
    name = project["name"]
    branch = project.get("target_branch")
    registered_ref = project["ref"].removeprefix("refs/remotes/")
    if not branch and registered_ref.startswith("origin/") and registered_ref != "origin/HEAD":
        branch = registered_ref.removeprefix("origin/")
    # A linked checkout may belong to a fork; a standalone clone uses its actual origin.
    source = project.get("clone_source") if (checkout / ".git").is_file() else None
    if not source:
        remotes = git(checkout, "remote").splitlines()
        if "origin" in remotes:
            source = "origin"
        elif len(remotes) == 1:
            source = remotes[0]
        elif branch or remotes:
            raise ValueError(f"{name}: no default Git remote; set origin or pass --base {name}=REF")
        else:
            return "HEAD", head(checkout, "HEAD")
    query = branch_ref(checkout, branch) if branch else "HEAD"
    options = ("-c", "protocol.ext.allow=never")
    try:
        advertised = git(checkout, *options, "ls-remote", "--symref", "--exit-code", "--", source, query)
        values = [value for value, _, ref in (line.partition("\t") for line in advertised.splitlines())
                  if ref == query]
        tip = next((value for value in values if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value)), None)
        target = query if branch else next((value[len("ref: "):] for value in values
                                           if value.startswith("ref: refs/heads/")), None)
        if tip and target:
            if subprocess.run(["git", "-C", str(checkout), "cat-file", "-e", tip + "^{commit}"],
                              capture_output=True).returncode:
                # Fetch objects without moving the checkout or writing shared FETCH_HEAD state.
                git(checkout, *options, "fetch", "--no-tags", "--no-recurse-submodules",
                    "--no-write-fetch-head", "--refmap=", "--", source, target)
                head(checkout, tip)
            return target, tip
    except subprocess.CalledProcessError as error:
        raise ValueError(f"{name}: could not refresh {query}; check the remote and branch or pass --base {name}=REF") from error
    raise ValueError(f"{name}: cannot resolve {query}; set target_branch or pass --base {name}=REF")


def attach(root, project):
    mode = project["mode"]
    if mode == "reference":
        return
    destination = root / "repos" / project["name"]
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"checkout already exists: {destination}")
    destination.parent.mkdir(exist_ok=True)
    if mode == "worktree":
        git(project["source"], "worktree", "add", "--detach", str(destination), project["base_sha"])
    else:
        # Publish a standalone clone only after checkout of the requested ref succeeds.
        with tempfile.TemporaryDirectory(prefix=".mono-clone-", dir=destination.parent) as tmp:
            clone = Path(tmp) / "repo"
            git(root, "-c", "protocol.ext.allow=never", "clone", "--no-hardlinks",
                "--", project["source"], str(clone))
            project["base_sha"] = head(clone, project["ref"])
            git(clone, "switch", "--detach", project["base_sha"])
            clone.rename(destination)
    project["path"] = str(destination.relative_to(root))


def stdd_profile(checkout):
    skills = {}
    for name in STDD_SKILLS:
        for directory in (".agents/skills", ".claude/skills", ".qoder/skills"):
            path = f"{directory}/{name}/SKILL.md"
            if (checkout / path).is_file():
                skills[name] = path
                break
    return {
        "project": "docs/stdd/project.md" if (checkout / "docs/stdd/project.md").is_file() else None,
        "scaffold": "scripts/new_change.py" if (checkout / "scripts/new_change.py").is_file() else None,
        "skills": skills,
    }


def write_registry(root, data):
    path = root / "mono.json"
    with tempfile.NamedTemporaryFile(mode="w", dir=root, delete=False, encoding="utf-8") as output:
        tmp = Path(output.name)
        try:
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.close()
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)


def read_registry(root):
    return json.loads((root / "mono.json").read_text(encoding="utf-8"))


def write_project_index(root, data):
    lines = ["# 仓库清单", "", "此页由 mono.json 生成。系统约定和决定见 system.md 与 decisions.md。", ""]
    for project in data["projects"]:
        lines.extend([
            f"## {project['name']}", "", f"- 职责为 {project['role']}，负责人为 {project['owner']}。",
            f"- 入口为 {project.get('path', project['source'])}，模式为 {project['mode']}。",
            f"- 接入基线为 {project.get('base_sha', '待核实')}，引用为 {project['ref']}。",
        ])
        if project.get("target_branch"):
            lines.append(f"- 新任务目标分支为 {project['target_branch']}。")
        if project.get("path"):
            profile = stdd_profile(root / project["path"])
            if profile["project"]:
                lines.append(f"- STDD 项目入口为 {profile['project']}，在对应业务仓库内读取。")
        for key, label in (("start", "启动"), ("test", "仓内测试")):
            if project["commands"].get(key):
                lines.append(f"- {label}命令为 {project['commands'][key]}。")
        lines.append("")
    (root / "docs/mono/projects.md").write_text("\n".join(lines), encoding="utf-8")


@contextmanager
def write_lock(path):
    try:
        path.mkdir()
    except FileExistsError as error:
        raise ValueError(f"another update holds {path}; inspect active processes before removing a stale lock") from error
    try:
        yield
    finally:
        path.rmdir()
