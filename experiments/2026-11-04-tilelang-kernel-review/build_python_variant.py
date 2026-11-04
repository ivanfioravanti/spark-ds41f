"""Freeze a corrected Python-only port while preserving the first attempt."""

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

base = Path.home() / "spark-lab/tilelang-review-20261104"
experiment = base / "deployment/experiments/2026-11-04-tilelang-kernel-review"
number = int(sys.argv[1])
case = next(c for c in json.loads((experiment / "cases.json").read_text()) if c["number"] == number)
patch = base / "deployment" / case["ported_patch"]
changed = [line.split("\t", 2)[2] for line in subprocess.check_output(["git", "apply", "--numstat", str(patch)], text=True).splitlines()]
assert not any(p.startswith("src/") for p in changed)
destination = base / "variants" / case["variant"]
shutil.copytree(base / "variants/base", destination, copy_function=os.link)
for relative in changed:
    original = base / "variants/base" / relative
    target = destination / relative
    if target.exists():
        target.unlink()
    if original.is_file():
        shutil.copyfile(original, target)
subprocess.run(["git", "apply", "--check", str(patch)], cwd=destination, check=True)
subprocess.run(["git", "apply", str(patch)], cwd=destination, check=True)
receipt = {"tree": case["ported_tree"], "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
           "changed": changed, "native_libraries": "unchanged from base", "command": sys.argv}
(base / ("build-" + case["variant"] + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
