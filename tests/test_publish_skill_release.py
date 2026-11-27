import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import call, patch
from zipfile import ZipFile

from scripts import publish_skill_release as release


REPOSITORY = "example/init-mono"
CHECKED = "a" * 40
OTHER = "b" * 40
TAG = "v0.3.0"


def package_release(tag, digest):
    return {"tag_name": tag, "assets": [{"name": "init_mono.zip", "digest": digest}]}


class PublishSkillReleaseTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(self.sandbox.cleanup)
        self.package = Path(self.sandbox.name) / "init_mono.zip"
        with ZipFile(self.package, "w") as archive:
            archive.writestr("init_mono/VERSION", TAG + "\n")
        self.digest = "sha256:" + hashlib.sha256(self.package.read_bytes()).hexdigest()
        package_patch = patch.object(release, "PACKAGE", self.package)
        package_patch.start()
        self.addCleanup(package_patch.stop)

    def test_same_package_skips_publishing(self):
        with patch.object(release, "run", return_value=CHECKED) as commands, \
                patch.object(release, "api", side_effect=[
                    {"object": {"sha": CHECKED}}, package_release(TAG, self.digest),
                ]), redirect_stdout(io.StringIO()) as output:
            release.publish(REPOSITORY, CHECKED)

        commands.assert_called_once_with("git", "rev-parse", "HEAD")
        self.assertIn(f"{TAG} already contains", output.getvalue())

    def test_main_advancing_before_publication_does_not_create_tag(self):
        with patch.object(release, "run", return_value=CHECKED) as commands, \
                patch.object(release, "api", side_effect=[
                    {"object": {"sha": CHECKED}}, package_release("v0.2.0", "sha256:old"),
                    {"object": {"sha": OTHER}},
                ]), redirect_stdout(io.StringIO()):
            release.publish(REPOSITORY, CHECKED)

        commands.assert_called_once_with("git", "rev-parse", "HEAD")

    def test_new_package_publishes_checked_commit_using_embedded_tag(self):
        with patch.object(release, "run", side_effect=[
            CHECKED, "", "https://example.invalid/release",
        ]) as commands, patch.object(release, "api", side_effect=[
            {"object": {"sha": CHECKED}}, package_release("v0.2.0", "sha256:old"),
            {"object": {"sha": CHECKED}}, package_release(TAG, self.digest),
        ]), redirect_stdout(io.StringIO()) as output:
            release.publish(REPOSITORY, CHECKED)

        self.assertEqual(commands.call_args_list[1:], [
            call("git", "push", "origin", f"{CHECKED}:refs/tags/{TAG}"),
            call("gh", "release", "create", TAG, str(release.PACKAGE), "--repo", REPOSITORY,
                 "--verify-tag", "--latest", "--title", f"init_mono {TAG}", "--generate-notes"),
        ])
        self.assertIn(f"Published and verified {TAG}", output.getvalue())

    def test_changed_package_without_a_version_bump_is_rejected(self):
        with patch.object(release, "api", return_value=package_release(TAG, "sha256:old")):
            with self.assertRaisesRegex(ValueError, "bump VERSION"):
                release.release_plan(REPOSITORY)

    def test_an_identical_package_under_a_different_tag_is_rejected(self):
        with patch.object(release, "api", return_value=package_release("v0.2.0", self.digest)):
            with self.assertRaisesRegex(ValueError, "identical Release asset is tagged"):
                release.release_plan(REPOSITORY)
