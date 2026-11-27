"""Behavioral checks for multi-repository generation and acceptance freshness."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

INIT = Path(__file__).resolve().parents[1] / ".agents/skills/init_mono/scripts/init_mono.py"
WORKSPACE_TEMPLATE = INIT.parents[1] / "assets/workspace"
CLIENT_SKILL_DIRS = {"codex": ".agents/skills", "claude": ".claude/skills", "qoder": ".qoder/skills"}
MONO_SKILLS = {"mono-start", "mono-verify", "mono-wrap"}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


class ScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mono-tests-")
        self.root = Path(self.temp.name).resolve()
        self.sources = []
        for name in ("web", "api"):
            source = self.root / name
            source.mkdir()
            git(source, "init", "-q", "-b", "main")
            (source / "app.txt").write_text("baseline\n")
            git(source, "add", ".")
            git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-qm", "Baseline")
            self.sources.append(source)
        self.config = {
            "name": "Test", "summary": "Cross-project behavior", "kind": "repository",
            "projects": [
                {"name": name, "source": str(source), "role": name,
                 "mode": mode, "ref": "main"}
                for name, source, mode in zip(("web", "api"), self.sources, ("worktree", "clone"))
            ],
        }
        self.input = self.root / "input.json"
        self.task = self.root / "task.json"
        self.task.write_text(json.dumps({
            "id": "CAT-42", "title": "Search", "goal": "Find an item",
            "acceptance": [{"id": "AC01", "check": "Query", "expected": "one item"}],
        }))

    def tearDown(self):
        self.temp.cleanup()

    def call(self, *args, ok=True, env=None):
        process = subprocess.run([sys.executable, "-B", *(str(a) for a in args)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        if ok:
            self.assertEqual(process.returncode, 0, process.stdout)
        else:
            self.assertNotEqual(process.returncode, 0, process.stdout)
        return process

    def init(self, target=None, *, agent=None, **updates):
        self.config.update(updates)
        self.input.write_text(json.dumps(self.config))
        space = target or self.root / "space"
        self.call(INIT, self.input, space, *(("--agent", agent) if agent else ()))
        return space

    def assert_client_skills(self, space, agent):
        source = WORKSPACE_TEMPLATE / ".agents/skills"
        destination = space / CLIENT_SKILL_DIRS[agent]
        self.assertEqual({path.parent.name for path in destination.glob("*/SKILL.md")}, MONO_SKILLS)
        for name in MONO_SKILLS:
            self.assertEqual((destination / name / "SKILL.md").read_bytes(),
                             (source / name / "SKILL.md").read_bytes())
            self.assertEqual((destination / name / "agents/openai.yaml").is_file(), agent == "codex")

    def task_space(self):
        space = self.init()
        self.call(space / "scripts/mono.py", "new", self.task, "--worktrees")
        return space

    def run_receipt(self, space, *command, ok=True):
        task = space / "tasks/CAT-42"
        before = set((task / "evidence").glob("*.json")) if (task / "evidence").exists() else set()
        self.call(space / "scripts/mono.py", "run", "CAT-42", "--ac", "AC01",
                  "--", *command, ok=ok)
        receipt = (set((task / "evidence").glob("*.json")) - before).pop()
        report = json.loads((task / "verification.json").read_text())
        report["checks"][0].update(status="passed", actual="one item",
                                  evidence=[str(receipt.relative_to(task))])
        (task / "verification.json").write_text(json.dumps(report))
        return receipt

    def test_generation_independent_git_and_dirty_source_preserved(self):
        (self.sources[0] / "app.txt").write_text("user changes\n")
        space = self.task_space()
        self.assertEqual((self.sources[0] / "app.txt").read_text(), "user changes\n")
        for name, source in zip(("web", "api"), self.sources):
            self.assertEqual((space / "work/CAT-42" / name / "app.txt").read_text(), "baseline\n")
            self.assertEqual(git(source, "branch", "--show-current"), "main")
            self.assertEqual(git(space / "work/CAT-42" / name, "branch", "--show-current"), "mono/CAT-42")
            self.assertEqual(git(source, "rev-parse", "HEAD"),
                             git(space / "work/CAT-42" / name, "rev-parse", "HEAD"))
        self.assertEqual(git(space, "rev-parse", "--show-toplevel"), str(space))
        self.assertEqual(git(space, "check-ignore", "repos/web/", "work/CAT-42/web/"),
                         "repos/web/\nwork/CAT-42/web/")
        for agent in CLIENT_SKILL_DIRS:
            self.assert_client_skills(space, agent)
        self.assertEqual((space / "CLAUDE.md").read_text(), "@AGENTS.md\n")
        for name in ("web", "api"):
            for directory in CLIENT_SKILL_DIRS.values():
                self.assertFalse((space / "work/CAT-42" / name / directory).exists())

    def test_single_client_initialization_uses_its_own_skill_directory(self):
        for agent in CLIENT_SKILL_DIRS:
            with self.subTest(agent=agent):
                space = self.init(self.root / agent, agent=agent, kind="process")
                self.assert_client_skills(space, agent)
                for other, directory in CLIENT_SKILL_DIRS.items():
                    if other != agent:
                        self.assertFalse((space / directory).exists())
                self.assertEqual((space / "CLAUDE.md").is_file(), agent == "claude")

    def test_team_clones_start_separate_features_from_current_targets(self):
        web, api = self.sources
        web_remote, api_remote = self.root / "web.git", self.root / "api.git"
        for source, remote in ((web, web_remote), (api, api_remote)):
            git(self.root, "clone", "--bare", "-q", str(source), str(remote))
        web_url = "https://git.example.invalid/team/web.git"
        git(web, "remote", "add", "origin", "https://dev:fixture-token@git.example.invalid/team/web.git")
        self.config["projects"][1].update(source=api_remote.as_uri(), mode="auto")
        # Simulate a team Git remote with a local bare repository and no network access.
        env = dict(os.environ, GIT_CONFIG_COUNT="1", GIT_ALLOW_PROTOCOL="file",
                   GIT_CONFIG_KEY_0=f"url.{web_remote.as_uri()}.insteadOf", GIT_CONFIG_VALUE_0=web_url)
        self.input.write_text(json.dumps(self.config))
        space = self.root / "space"
        self.call(INIT, self.input, space, env=env)
        manifest = (space / "mono.json").read_text()
        self.assertEqual(json.loads(manifest)["projects"][0]["clone_source"], web_url)
        self.assertNotIn("fixture-token", manifest)
        git(space, "add", ".")
        git(space, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Publish coordination context")
        baseline = git(web, "rev-parse", "HEAD")
        (web / "app.txt").write_text("new main\n")
        git(web, "add", "app.txt")
        git(web, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Advance remote main")
        git(web, "push", "-q", str(web_remote), "main")

        for task_id in ("CAT-42", "CAT-43"):
            member = self.root / task_id
            git(self.root, "clone", "-q", str(space), str(member))
            cli = member / "scripts/mono.py"
            self.assertFalse((member / "repos").exists())
            missing = self.call(cli, "new", self.task, "--worktrees", ok=False)
            self.assertIn("mono.py bootstrap", missing.stdout)
            self.assertFalse((member / "tasks").exists())
            self.call(cli, "bootstrap", env=env)
            self.assertEqual(git(member, "status", "--porcelain"), "")
            self.assertEqual(git(member / "repos/web", "rev-parse", "HEAD"), baseline)
            self.assertNotEqual(git(member / "repos/web", "rev-parse", "origin/main"), baseline)
            spec = json.loads(self.task.read_text())
            spec["id"] = task_id
            task_input = self.root / (task_id + ".json")
            task_input.write_text(json.dumps(spec))
            self.call(cli, "new", task_input, "--worktrees", env=env)
            for name in ("web", "api"):
                checkout = member / "work" / task_id / name
                self.assertEqual(git(checkout, "branch", "--show-current"), f"mono/{task_id}")
                expected = "new main" if name == "web" else "baseline"
                self.assertEqual((checkout / "app.txt").read_text(), expected + "\n")
            git(member, "add", ".")
            tracked = git(member, "ls-files", "--stage").splitlines()
            self.assertTrue(any(line.endswith(f"\ttasks/{task_id}/projects.json") for line in tracked))
            self.assertFalse(any(line.startswith("160000 ") or "\trepos/" in line or "\twork/" in line
                                 for line in tracked))
        (self.root / "CAT-42/work/CAT-42/web/app.txt").write_text("member one edit\n")
        self.assertEqual((self.root / "CAT-43/work/CAT-43/web/app.txt").read_text(), "new main\n")

    def test_bootstrap_recovers_after_failure_and_preserves_existing_checkouts(self):
        git(self.sources[0], "remote", "add", "origin", self.sources[1].as_uri())
        space = self.init()
        self.assertNotIn("clone_source", json.loads((space / "mono.json").read_text())["projects"][0])
        member = self.root / "member"
        git(space, "add", ".")
        git(space, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Publish existing manifest")
        git(self.root, "clone", "-q", str(space), str(member))
        cli = member / "scripts/mono.py"
        empty = self.root / "empty.git"
        git(self.root, "init", "--bare", "-q", str(empty))
        missing = self.call(cli, "bootstrap", ok=False)
        self.assertIn("web: set clone_source", missing.stdout)
        failed = self.call(cli, "bootstrap", "--source", f"web={self.sources[0].as_uri()}",
                           "--source", f"api={empty.as_uri()}", ok=False)
        self.assertIn("api: could not restore", failed.stdout)
        self.assertFalse((member / "repos/api").exists())
        existing = member / "repos/web/app.txt"
        existing.write_text("local edit\n")
        self.call(cli, "bootstrap", "api", "--source", f"api={self.sources[1].as_uri()}")
        self.call(cli, "bootstrap")
        self.assertEqual(existing.read_text(), "local edit\n")
        self.assertEqual(git(member, "status", "--porcelain"), "")

    def test_worktree_uses_ssh_origin_and_allows_shared_url_override(self):
        web, api = self.sources
        web_url = "git@gitlab.example.invalid:team/web.git"
        api_url = "ssh://git@gitlab.example.invalid/team/api.git"
        git(web, "remote", "add", "origin", web_url)
        git(api, "remote", "add", "origin", "git@gitlab.example.invalid:fork/api.git")
        self.config["projects"][1].update(mode="worktree", clone_source=api_url)
        space = self.init()
        projects = json.loads((space / "mono.json").read_text())["projects"]
        self.assertEqual([p["clone_source"] for p in projects], [web_url, api_url])
        self.assertTrue(all((space / p["path"] / ".git").is_file() for p in projects))

    def test_dry_run_and_input_errors_write_nothing(self):
        self.input.write_text(json.dumps(self.config))
        output = self.root / "preview"
        plan = json.loads(self.call(INIT, self.input, output, "--dry-run").stdout)
        self.assertEqual(plan["skill_directories"], CLIENT_SKILL_DIRS)
        plan = json.loads(self.call(INIT, self.input, output, "--dry-run", "--agent", "qoder").stdout)
        self.assertEqual(plan["skill_directories"], {"qoder": ".qoder/skills"})
        self.assertFalse(output.exists())
        self.config["projects"][1]["name"] = "web"
        self.input.write_text(json.dumps(self.config))
        self.call(INIT, self.input, output, ok=False)
        self.assertFalse(output.exists())

    def test_process_without_checkouts_and_minimal_input(self):
        space = self.init(kind="process")
        self.assertFalse((space / "repos").exists())
        self.assertFalse((space / ".git").exists())
        self.assertTrue((space / "docs/mono/operations.md").exists())
        self.call(space / "scripts/mono.py", "new", self.task)
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)

    def test_auto_sources_and_add_preserve_context_and_existing_evidence(self):
        self.config["projects"][0].pop("mode")
        self.config["projects"][1].update(source=self.sources[1].as_uri(), mode="auto")
        space = self.task_space()
        cli = space / "scripts/mono.py"
        self.run_receipt(space, sys.executable, "-c", "assert True")
        context_path = space / "docs/mono/system.md"
        context = context_path.read_bytes()
        docs = self.root / "docs"
        docs.mkdir()
        self.call(cli, "add", "docs", docs)
        source = self.root / "identity"
        git(self.root, "clone", "-q", str(self.sources[1]), str(source))
        failed = self.call(cli, "add", "identity", source.as_uri(), "--ref", "missing", ok=False)
        self.assertFalse((space / "repos/identity").exists(), failed.stdout)
        self.call(cli, "add", "identity", source.as_uri(), "--ref", "origin/main")
        self.call(cli, "add", "web", source, ok=False)
        self.call(cli, "check", "CAT-42")
        self.assertEqual(context_path.read_bytes(), context)
        projects = json.loads(self.call(cli, "repos").stdout)
        self.assertEqual([p["mode"] for p in projects], ["worktree", "clone", "reference", "clone"])
        self.assertIn("repos/identity", (space / "docs/mono/projects.md").read_text())
        self.assertFalse((space / ".gitmodules").exists())

    def test_new_with_custom_branch_and_fresh_ref_leaves_attach_base(self):
        space = self.init()
        source = self.sources[0]
        (source / "app.txt").write_text("next merged base\n")
        git(source, "add", "app.txt")
        git(source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "New baseline")
        cli = space / "scripts/mono.py"
        self.call(cli, "new", self.task, "--worktrees", "--base", "web=main",
                  "--branch", "web=feat/catalog-search")
        rows = json.loads(self.call(cli, "status", "CAT-42").stdout)
        self.assertEqual(rows["web"]["branch"], "feat/catalog-search")
        self.assertEqual(rows["web"]["sha"], git(source, "rev-parse", "HEAD"))
        self.assertEqual(rows["api"]["branch"], "mono/CAT-42")
        self.assertEqual((space / "repos/web/app.txt").read_text(), "baseline\n")
        self.assertEqual((space / "work/CAT-42/web/app.txt").read_text(), "next merged base\n")

    def test_new_refreshes_target_branch_without_moving_existing_checkouts(self):
        api = self.sources[1]
        git(api, "branch", "develop")
        self.config["projects"][1]["target_branch"] = "develop"
        space = self.task_space()
        old = space / "work/CAT-42/api"
        (old / "app.txt").write_text("local work still in progress\n")
        original = git(old, "rev-parse", "HEAD")
        git(api, "switch", "develop")
        (api / "app.txt").write_text("latest develop\n")
        git(api, "add", "app.txt")
        git(api, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Advance the target branch")
        latest = git(api, "rev-parse", "HEAD")
        base_checkout = space / "repos/api"
        self.assertNotEqual(git(base_checkout, "rev-parse", "origin/develop"), latest)
        self.assertNotEqual(git(api, "rev-parse", "main"), latest)
        (base_checkout / "app.txt").write_text("local base edit\n")
        task = json.loads(self.task.read_text())
        task.update(id="CAT-43", projects=["api"])
        self.task.write_text(json.dumps(task))
        self.call(space / "scripts/mono.py", "new", self.task, "--worktrees")
        state = json.loads((space / "tasks/CAT-43/projects.json").read_text())
        self.assertEqual(state["api"]["base_ref"], "refs/heads/develop")
        self.assertEqual(state["api"]["base_sha"], latest)
        self.assertEqual((space / "work/CAT-43/api/app.txt").read_text(), "latest develop\n")
        self.assertEqual(git(base_checkout, "rev-parse", "HEAD"), original)
        self.assertEqual((base_checkout / "app.txt").read_text(), "local base edit\n")
        self.assertEqual(git(old, "rev-parse", "HEAD"), original)
        self.assertEqual((old / "app.txt").read_text(), "local work still in progress\n")

    def test_missing_remote_target_blocks_task_and_explicit_base_works_offline(self):
        self.config["projects"][1]["target_branch"] = "missing"
        space = self.init()
        task = json.loads(self.task.read_text())
        task["projects"] = ["api"]
        self.task.write_text(json.dumps(task))
        cli = space / "scripts/mono.py"
        failed = self.call(cli, "new", self.task, "--worktrees", ok=False)
        self.assertIn("api: could not refresh refs/heads/missing", failed.stdout)
        self.assertFalse((space / "tasks/CAT-42").exists())
        self.assertFalse((space / "work/CAT-42").exists())
        self.call(cli, "new", self.task, "--worktrees", "--base", "api=HEAD")
        self.assertTrue((space / "work/CAT-42/api/app.txt").is_file())

    def test_planning_syncs_clean_baseline_and_pins_the_inspected_commit(self):
        api = self.sources[1]
        space = self.init()
        cli, checkout = space / "scripts/mono.py", space / "repos/api"
        original = git(checkout, "rev-parse", "HEAD")
        (api / "new_caller.txt").write_text("Calls the web repository\n")
        git(api, "add", "new_caller.txt")
        git(api, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Add a caller after the coordinator was initialized")

        report = json.loads(self.call(cli, "baselines", "api").stdout)
        self.assertEqual(set(report), {"api"})
        inspected = report["api"]["base_sha"]
        self.assertEqual(inspected, git(api, "rev-parse", "HEAD"))
        self.assertEqual(report["api"]["base_ref"], "refs/heads/main")
        self.assertEqual(git(checkout, "show", f"{inspected}:new_caller.txt"), "Calls the web repository")
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), original)
        self.assertFalse((checkout / "new_caller.txt").exists())

        synced = json.loads(self.call(cli, "baselines", "--sync", "api").stdout)["api"]
        self.assertEqual(synced["checkout_state"], "updated")
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), inspected)
        self.assertTrue((checkout / "new_caller.txt").is_file())
        self.assertFalse((space / "work").exists())
        self.assertFalse((space / "tasks").exists())

        (checkout / "app.txt").write_text("local baseline edit\n")
        (api / "new_caller.txt").write_text("Another upstream change\n")
        git(api, "add", "new_caller.txt")
        git(api, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Advance while the feature scope is being analyzed")
        next_report = json.loads(self.call(cli, "baselines", "api", "--sync").stdout)["api"]
        self.assertEqual(next_report["checkout_state"], "local_changes")
        self.assertEqual(next_report["base_sha"], git(api, "rev-parse", "HEAD"))
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), inspected)
        self.assertEqual((checkout / "app.txt").read_text(), "local baseline edit\n")

        git(checkout, "add", "app.txt")
        git(checkout, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Save a local baseline change on detached HEAD")
        local = git(checkout, "rev-parse", "HEAD")
        diverged = json.loads(self.call(cli, "baselines", "api", "--sync").stdout)["api"]
        self.assertEqual(diverged["checkout_state"], "diverged")
        self.assertEqual(git(checkout, "rev-parse", "HEAD"), local)

        spec = json.loads(self.task.read_text())
        spec["projects"] = ["api"]
        self.task.write_text(json.dumps(spec))
        self.call(cli, "new", self.task, "--worktrees", "--base", f"api={inspected}")
        self.assertEqual({p.name for p in (space / "work/CAT-42").iterdir()}, {"api"})
        self.assertEqual(git(space / "work/CAT-42/api", "rev-parse", "HEAD"), inspected)

    def test_stdd_existing_changes_resolve_when_archived_and_base_is_protected(self):
        space = self.task_space()
        cli = space / "scripts/mono.py"
        work = space / "work/CAT-42/web"
        change = work / "changes/014-login"
        change.mkdir(parents=True)
        (change / "change.md").write_text("Existing STDD change\n")
        self.call(cli, "stdd", "CAT-42", "web", "014-login")
        self.call(cli, "stdd", "CAT-42", "web", "015-login", ok=False)
        archive = work / "changes/archive"
        archive.mkdir()
        change.rename(archive / change.name)
        rows = json.loads(self.call(cli, "status", "CAT-42").stdout)
        self.assertEqual(rows["web"]["stdd_change"]["path"], "changes/archive/014-login")
        self.assertEqual((archive / change.name / "change.md").read_text(), "Existing STDD change\n")
        git(work, "switch", "-qc", "unexpected/branch")
        response = self.call(cli, "stdd", "CAT-42", "web", "014-login", ok=False)
        self.assertIn("expected mono/CAT-42", response.stdout)
        spec = json.loads(self.task.read_text())
        spec["id"] = "CAT-43"
        self.task.write_text(json.dumps(spec))
        self.call(cli, "new", self.task)
        self.call(cli, "stdd", "CAT-43", "web", "014-login", "--title", "Login", ok=False)
        self.assertFalse((space / "repos/web/changes").exists())

    def test_status_lists_stdd_skills_per_client_with_legacy_paths(self):
        space = self.task_space()
        work = space / "work/CAT-42/web"
        skills = {"codex": ("stdd-start", "stdd-review"), "claude": ("stdd-start", "stdd-delivery"),
                  "qoder": ("stdd-start", "stdd-wrap")}
        expected = {}
        for agent, names in skills.items():
            expected[agent] = {}
            for name in names:
                path = f"{CLIENT_SKILL_DIRS[agent]}/{name}/SKILL.md"
                (work / path).parent.mkdir(parents=True)
                (work / path).write_text(f"# {agent} {name}\n")
                expected[agent][name] = path
        ignored = work / ".qoder/skills/review/SKILL.md"
        ignored.parent.mkdir()
        ignored.write_text("# Other workflow\n")
        rows = json.loads(self.call(space / "scripts/mono.py", "status", "CAT-42").stdout)
        self.assertEqual(rows["web"]["stdd"]["skills_by_agent"], expected)
        self.assertEqual(rows["web"]["stdd"]["skills"], {
            "stdd-start": expected["codex"]["stdd-start"],
            "stdd-delivery": expected["claude"]["stdd-delivery"],
            "stdd-wrap": expected["qoder"]["stdd-wrap"],
        })
        self.assertEqual(rows["api"]["stdd"]["skills_by_agent"], {agent: {} for agent in CLIENT_SKILL_DIRS})

    def test_upgrade_backfills_client_skills_and_preserves_custom_entries_and_evidence(self):
        space = self.init(agent="codex")
        cli = space / "scripts/mono.py"
        self.call(cli, "new", self.task, "--worktrees")
        shared_rules = space / "AGENTS.md"
        shared_rules.write_text("# Team rules\n")
        self.run_receipt(space, sys.executable, "-c", "assert 1 == 1")
        claude_rules = space / "CLAUDE.md"
        claude_rules.write_text("# Team Claude rules\n")
        custom = space / ".claude/skills/mono-start/SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("# Team Claude skill\n")

        self.call(INIT, "--upgrade", space, "--agent", "claude")
        for name in ("mono-verify", "mono-wrap"):
            self.assertEqual((space / f".claude/skills/{name}/SKILL.md").read_bytes(),
                             (space / f".agents/skills/{name}/SKILL.md").read_bytes())
        self.assertFalse((space / ".qoder").exists())

        self.call(INIT, "--upgrade", space)
        self.call(INIT, "--upgrade", space)
        self.assert_client_skills(space, "qoder")
        self.assertEqual(claude_rules.read_text(), "# Team Claude rules\n")
        self.assertEqual(custom.read_text(), "# Team Claude skill\n")
        self.assertEqual(shared_rules.read_text(), "# Team rules\n")
        self.call(cli, "check", "CAT-42")

    def test_upgrade_leaves_linked_client_directories_in_place(self):
        space = self.init(agent="codex", kind="process")
        external = self.root / "custom-client"
        external.mkdir()
        (space / ".qoder").symlink_to(external, target_is_directory=True)
        self.call(INIT, "--upgrade", space)
        self.assertTrue((space / ".qoder").is_symlink())
        self.assertEqual(list(external.iterdir()), [])
        self.assert_client_skills(space, "claude")
        self.assertEqual((space / "CLAUDE.md").read_text(), "@AGENTS.md\n")

    def test_upgrade_refuses_custom_scripts_before_writing(self):
        space = self.init()
        cli = space / "scripts/mono.py"
        cli.write_text("# customized implementation\n")
        before = (space / "mono.json").read_bytes()
        version = (space / "mono-version.json").read_bytes()
        self.call(INIT, "--upgrade", space, ok=False)
        self.assertEqual(cli.read_text(), "# customized implementation\n")
        self.assertEqual((space / "mono.json").read_bytes(), before)
        self.assertEqual((space / "mono-version.json").read_bytes(), version)

    def test_release_version_is_recorded_and_preserved_through_upgrade(self):
        space = self.task_space()
        cli = space / "scripts/mono.py"
        bundle = INIT.parents[1]
        version = (bundle / "VERSION").read_text().strip()
        self.assertEqual(json.loads(self.call(cli, "version").stdout), {
            "initialized_version": version, "current_version": version, "upgrades": [],
        })
        upgraded_bundle = self.root / "next-bundle"
        shutil.copytree(bundle, upgraded_bundle)
        major, minor, patch_number = version[1:].split(".")
        next_version = f"v{major}.{minor}.{int(patch_number) + 1}"
        (upgraded_bundle / "VERSION").write_text(next_version + "\n")
        newer = upgraded_bundle / "scripts/init_mono.py"
        registry = (space / "mono.json").read_bytes()
        task = space / "tasks/CAT-42/task.md"
        task_before = task.read_bytes()

        self.call(newer, "--upgrade", space)
        self.call(newer, "--upgrade", space)
        self.assertEqual(json.loads(self.call(cli, "version").stdout), {
            "initialized_version": version, "current_version": next_version,
            "upgrades": [{"from": version, "to": next_version}],
        })
        self.assertEqual((space / "mono.json").read_bytes(), registry)
        self.assertEqual(task.read_bytes(), task_before)
        before = (space / "mono-version.json").read_bytes()
        downgrade = self.call(INIT, "--upgrade", space, ok=False)
        self.assertIn(f"already uses {next_version}", downgrade.stdout)
        self.assertEqual((space / "mono-version.json").read_bytes(), before)

    def test_upgrade_backfills_a_legacy_workspace_without_guessing_initial_version(self):
        space = self.init(kind="process")
        record = space / "mono-version.json"
        record.unlink()
        self.assertIsNone(json.loads(self.call(space / "scripts/mono.py", "version").stdout)["current_version"])
        tag = (INIT.parents[1] / "VERSION").read_text().strip()
        self.call(INIT, "--upgrade", space)
        self.assertEqual(json.loads(record.read_text()), {
            "initialized_version": None, "current_version": tag, "upgrades": [{"from": None, "to": tag}],
        })

    def test_failure_and_changed_code_cannot_pass(self):
        space = self.task_space()
        self.run_receipt(space, sys.executable, "-c", "raise SystemExit(3)", ok=False)
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)
        self.run_receipt(space, sys.executable, "-c", "assert 2 + 2 == 4")
        self.call(space / "scripts/mono.py", "check", "CAT-42")
        (space / "work/CAT-42/web/app.txt").write_text("new behavior\n")
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)

    def test_changed_spec_and_deleted_evidence_cannot_pass(self):
        space = self.task_space()
        receipt = self.run_receipt(space, sys.executable, "-c", "assert True")
        self.call(space / "scripts/mono.py", "check", "CAT-42")
        spec = space / "tasks/CAT-42/task.md"
        content = spec.read_text()
        spec.write_text(content + "\nUpdated business rule\n")
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)
        spec.write_text(content)
        receipt.unlink()
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)

    def test_edited_during_run_and_existing_targets(self):
        space = self.task_space()
        file = space / "work/CAT-42/api/app.txt"
        self.run_receipt(space, sys.executable, "-c",
                         "from pathlib import Path; Path(" + repr(str(file)) + ").write_text('changed')",
                         ok=False)
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)
        self.call(INIT, self.input, space, ok=False)
        self.call(space / "scripts/mono.py", "new", self.task, "--worktrees", ok=False)
        self.assertEqual(file.read_text(), "changed")

    def test_second_project_failure_preserves_actionable_state(self):
        self.config["projects"][1]["ref"] = "does-not-exist"
        self.input.write_text(json.dumps(self.config))
        space = self.root / "partial"
        self.call(INIT, self.input, space, ok=False)
        self.assertTrue((space / "repos/web/.git").exists())
        registry = json.loads((space / "mono.json").read_text())
        self.assertEqual(registry["projects"][0]["path"], "repos/web")
        self.assertIn("repos/web", (space / "docs/mono/system.md").read_text())

    def test_timeout_and_unknown_acceptance(self):
        space = self.task_space()
        self.call(space / "scripts/mono.py", "run", "CAT-42", "--ac", "UNKNOWN",
                  "--", sys.executable, "-c", "assert True", ok=False)
        self.assertFalse((space / "tasks/CAT-42/evidence").exists())
        self.call(space / "scripts/mono.py", "run", "CAT-42", "--ac", "AC01",
                  "--timeout", "0.1", "--", sys.executable, "-c",
                  "import time; time.sleep(5)", ok=False)
        receipt = json.loads(next((space / "tasks/CAT-42/evidence").glob("*.json")).read_text())
        self.assertTrue(receipt["timed_out"])
        self.assertNotEqual(receipt["exit_code"], 0)

    def test_file_mode_changes_invalidate_evidence(self):
        space = self.task_space()
        self.run_receipt(space, sys.executable, "-c", "assert True")
        file = space / "work/CAT-42/web/app.txt"
        file.chmod(file.stat().st_mode | 0o100)
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)

    def test_submodule_content_is_part_of_evidence(self):
        web, api = self.sources
        git(web, "-c", "protocol.file.allow=always", "submodule", "add", str(api), "vendor")
        git(web, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Add submodule")
        space = self.task_space()
        work = space / "work/CAT-42/web"
        git(work, "-c", "protocol.file.allow=always", "submodule", "update", "--init")
        self.run_receipt(space, sys.executable, "-c", "assert True")
        self.call(space / "scripts/mono.py", "check", "CAT-42")
        (work / "vendor/app.txt").write_text("nested change\n")
        self.call(space / "scripts/mono.py", "check", "CAT-42", ok=False)


if __name__ == "__main__":
    unittest.main()
