"""Behavioral checks for multi-repository generation and acceptance freshness."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

INIT = Path(__file__).resolve().parents[1] / ".agents/skills/init_mono/scripts/init_mono.py"


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

    def call(self, *args, ok=True):
        process = subprocess.run([sys.executable, "-B", *(str(a) for a in args)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if ok:
            self.assertEqual(process.returncode, 0, process.stdout)
        else:
            self.assertNotEqual(process.returncode, 0, process.stdout)
        return process

    def init(self, target=None, **updates):
        self.config.update(updates)
        self.input.write_text(json.dumps(self.config))
        space = target or self.root / "space"
        self.call(INIT, self.input, space)
        return space

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
        self.assertEqual(len(list((space / ".agents/skills").glob("*/SKILL.md"))), 3)

    def test_dry_run_and_input_errors_write_nothing(self):
        self.input.write_text(json.dumps(self.config))
        output = self.root / "preview"
        self.call(INIT, self.input, output, "--dry-run")
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
