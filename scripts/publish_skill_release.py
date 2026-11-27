#!/usr/bin/env python3
"""Publish the tested skill ZIP when it differs from the latest GitHub Release."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "init_mono.zip"


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def api(repository, path):
    return json.loads(run("gh", "api", f"repos/{repository}/{path}"))


def current_main(repository):
    return api(repository, "git/ref/heads/main")["object"]["sha"]


def has_package(release, digest):
    return any(asset["name"] == PACKAGE.name and asset.get("digest") == digest
               for asset in release["assets"])


def next_patch_tag(latest_tag):
    match = re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", latest_tag)
    if not match:
        raise ValueError(f"latest Release must use a vMAJOR.MINOR.PATCH tag: {latest_tag}")
    major, minor, patch = match.groups()
    prefix = f"v{major}.{minor}."
    used = [int(patch)]
    # An interrupted publication may have reserved a tag before uploading its asset.
    refs = run("git", "ls-remote", "--tags", "--refs", "origin", f"refs/tags/{prefix}*")
    for line in refs.splitlines():
        ref = line.split("\t", 1)[1]
        if match := re.fullmatch("refs/tags/" + re.escape(prefix) + r"(0|[1-9][0-9]*)", ref):
            used.append(int(match[1]))
    return f"{prefix}{max(used) + 1}"


def publish(repository, commit):
    if run("git", "rev-parse", "HEAD") != commit:
        raise ValueError("the checked-out commit does not match the tested commit")
    if current_main(repository) != commit:
        print("main advanced since this run started. Its newer CI run will handle publishing.")
        return

    digest = "sha256:" + hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
    latest = api(repository, "releases/latest")
    if has_package(latest, digest):
        print(f"{latest['tag_name']} already contains the ZIP from main.")
        return

    tag = next_patch_tag(latest["tag_name"])
    if current_main(repository) != commit:
        print("main advanced before publishing. Its newer CI run will handle publishing.")
        return
    # A non-forced tag push binds the release to the exact commit that passed CI.
    run("git", "push", "origin", f"{commit}:refs/tags/{tag}")
    url = run("gh", "release", "create", tag, str(PACKAGE), "--repo", repository,
              "--verify-tag", "--latest", "--title", f"init_mono {tag}", "--generate-notes")
    published = api(repository, "releases/latest")
    if published["tag_name"] != tag or not has_package(published, digest):
        raise ValueError(f"latest Release does not contain the expected {tag} ZIP")
    print(f"Published and verified {tag} at {commit}: {url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("commit")
    args = parser.parse_args()
    try:
        publish(args.repository, args.commit)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")
