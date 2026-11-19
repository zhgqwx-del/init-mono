#!/usr/bin/env python3
"""Build and check the portable init_mono skill bundle."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".agents/skills/init_mono"


def package(output, check):
    expected = {
        str(Path("init_mono") / path.relative_to(SKILL)): path.read_bytes()
        for path in sorted(SKILL.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    if check:
        with ZipFile(output) as archive:
            if archive.testzip() is not None or set(archive.namelist()) != set(expected):
                raise ValueError("bundle structure differs from skill sources")
            for name, value in expected.items():
                if archive.read(name) != value:
                    raise ValueError("bundle is outdated: " + name)
        print("Skill bundle matches source files.")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, value in expected.items():
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, value)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "init_mono.zip")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    package(args.output.resolve(), args.check)
