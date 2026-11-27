#!/usr/bin/env python3
"""Publish the tested skill ZIP when it differs from the latest GitHub Release."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
from zipfile import BadZipFile, ZipFile


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


def version_parts(tag):
    match = re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag)
    if not match:
        raise ValueError(f"expected a vMAJOR.MINOR.PATCH tag: {tag!r}")
    return tuple(int(part) for part in match.groups())


def release_plan(repository):
    bundle = PACKAGE.read_bytes()
    digest = "sha256:" + hashlib.sha256(bundle).hexdigest()
    with ZipFile(io.BytesIO(bundle)) as archive:
        try:
            tag = archive.read("init_mono/VERSION").decode("utf-8").strip()
        except KeyError as error:
            raise ValueError("init_mono.zip lacks init_mono/VERSION; regenerate the ZIP") from error
    requested = version_parts(tag)
    latest = api(repository, "releases/latest")
    latest_tag = latest["tag_name"]
    if has_package(latest, digest):
        if tag != latest_tag:
            raise ValueError(f"ZIP declares {tag}, but the identical Release asset is tagged {latest_tag}")
        return tag, digest, False
    if requested <= version_parts(latest_tag):
        raise ValueError(f"ZIP changed; bump VERSION above {latest_tag} and regenerate init_mono.zip")
    return tag, digest, True


def publish(repository, commit):
    if run("git", "rev-parse", "HEAD") != commit:
        raise ValueError("the checked-out commit does not match the tested commit")
    if current_main(repository) != commit:
        print("main advanced since this run started. Its newer CI run will handle publishing.")
        return

    tag, digest, needs_release = release_plan(repository)
    if not needs_release:
        print(f"{tag} already contains the ZIP from main.")
        return

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
    parser.add_argument("commit", nargs="?")
    parser.add_argument("--check", action="store_true", help="check ZIP version against Releases without publishing")
    args = parser.parse_args()
    try:
        if args.check:
            if args.commit:
                parser.error("--check does not take a commit")
            tag, _, needs_release = release_plan(args.repository)
            print(f"ZIP declares {tag}. New Release needed: {needs_release}.")
        elif args.commit:
            publish(args.repository, args.commit)
        else:
            parser.error("provide the tested commit or --check")
    except (OSError, ValueError, BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")
