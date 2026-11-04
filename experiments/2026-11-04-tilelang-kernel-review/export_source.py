"""Export one clean compiler commit and its pinned submodules without Git metadata."""

from pathlib import Path
import json
import subprocess
import sys


def archive(repo, revision, destination):
    destination.mkdir(parents=True, exist_ok=True)
    producer = subprocess.Popen(["git", "archive", revision], cwd=repo, stdout=subprocess.PIPE)
    try:
        subprocess.run(["tar", "-xf", "-", "-C", str(destination)], stdin=producer.stdout, check=True)
    finally:
        producer.stdout.close()
    if producer.wait():
        raise SystemExit("git archive failed")


def main():
    repo, destination = map(Path, sys.argv[1:3])
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip():
        raise SystemExit("refusing to export a dirty compiler tree")
    archive(repo, revision, destination)
    submodules = {}
    status = subprocess.check_output(["git", "submodule", "status", "--recursive"], cwd=repo, text=True)
    for line in status.splitlines():
        if line[0] != " ":
            raise SystemExit("submodule does not match its pinned commit: " + line)
        commit, name, *_ = line.strip().split()
        archive(repo / name, commit, destination / name)
        submodules[name] = commit
    (destination / ".git_commit.txt").write_text(revision + "\n")
    record = {"revision": revision, "tree": tree, "submodules": submodules}
    (destination.parent / "exported-source.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
