import hashlib
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import call, patch

from scripts import publish_skill_release as release


REPOSITORY = "example/init-mono"
CHECKED = "a" * 40
OTHER = "b" * 40
DIGEST = "sha256:" + hashlib.sha256(release.PACKAGE.read_bytes()).hexdigest()


def package_release(tag, digest):
    return {"tag_name": tag, "assets": [{"name": "init_mono.zip", "digest": digest}]}


class PublishSkillReleaseTests(unittest.TestCase):
    def test_same_package_skips_publishing(self):
        with patch.object(release, "run", return_value=CHECKED) as commands, \
                patch.object(release, "api", side_effect=[
                    {"object": {"sha": CHECKED}}, package_release("v0.2.0", DIGEST),
                ]), redirect_stdout(io.StringIO()) as output:
            release.publish(REPOSITORY, CHECKED)

        commands.assert_called_once_with("git", "rev-parse", "HEAD")
        self.assertIn("v0.2.0 already contains", output.getvalue())

    def test_main_advancing_before_publication_does_not_create_tag(self):
        with patch.object(release, "run", side_effect=[CHECKED, ""]) as commands, \
                patch.object(release, "api", side_effect=[
                    {"object": {"sha": CHECKED}}, package_release("v0.2.0", "sha256:old"),
                    {"object": {"sha": OTHER}},
                ]), redirect_stdout(io.StringIO()):
            release.publish(REPOSITORY, CHECKED)

        self.assertEqual(commands.call_args_list, [
            call("git", "rev-parse", "HEAD"),
            call("git", "ls-remote", "--tags", "--refs", "origin", "refs/tags/v0.2.*"),
        ])

    def test_new_package_publishes_checked_commit_with_unused_patch_tag(self):
        with patch.object(release, "run", side_effect=[
            CHECKED, f"{OTHER}\trefs/tags/v0.2.1", "", "https://example.invalid/release",
        ]) as commands, patch.object(release, "api", side_effect=[
            {"object": {"sha": CHECKED}}, package_release("v0.2.0", "sha256:old"),
            {"object": {"sha": CHECKED}}, package_release("v0.2.2", DIGEST),
        ]), redirect_stdout(io.StringIO()) as output:
            release.publish(REPOSITORY, CHECKED)

        self.assertEqual(commands.call_args_list[2:], [
            call("git", "push", "origin", f"{CHECKED}:refs/tags/v0.2.2"),
            call("gh", "release", "create", "v0.2.2", str(release.PACKAGE), "--repo", REPOSITORY,
                 "--verify-tag", "--latest", "--title", "init_mono v0.2.2", "--generate-notes"),
        ])
        self.assertIn("Published and verified v0.2.2", output.getvalue())
