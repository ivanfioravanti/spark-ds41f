"""Build independent one-change compiler variants and freeze their source/libraries."""

from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time

BASE = Path.home() / "spark-lab/tilelang-review-20261104"
EXPERIMENT = BASE / "deployment/experiments/2026-11-04-tilelang-kernel-review"
WORK = BASE / "work-source"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def native(paths):
    return any(p.startswith("src/") and not p.startswith("src/tl_templates/") for p in paths)


def main():
    cases = json.loads((EXPERIMENT / "cases.json").read_text())
    cases.sort(key=lambda x: ([3710, 3190, 3661, 3605, 3690, 3537, 3568, 3490].index(x["number"])))
    jobs = [{"name": "pr" + str(x["number"]), "patch": BASE / "deployment" / x["ported_patch"], "tree": x["ported_tree"]} for x in cases]
    for item in json.loads((EXPERIMENT / "merged-cases.json").read_text()):
        jobs.append({"name": item["variant"], "patch": BASE / "deployment" / item["patch"], "tree": item["tree"]})
    previous = []
    for job in jobs:
        name, patch = job["name"], job["patch"]
        print("START", name, flush=True)
        for relative in previous:
            destination = WORK / relative
            original = BASE / "variants/base" / relative
            if original.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
            elif destination.exists():
                destination.unlink()
        delta = subprocess.check_output(["git", "apply", "--numstat", str(patch)], cwd=WORK, text=True)
        changed = [line.split("\t", 2)[2] for line in delta.splitlines()]
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=WORK, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=WORK, check=True)
        record = {"name": name, "started_utc": now(), "tree": job["tree"], "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(), "changed": changed}
        log = BASE / ("build-" + name + ".log")
        result = 0
        if native(previous + changed):
            command = ["docker", "exec", "tilelang-review-build-20261104", "cmake", "--build", "/review/work-source/build", "--parallel", "8"]
            record["command"] = command
            with log.open("w") as output:
                process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
                with (BASE / "build-memory.jsonl").open("a") as monitor:
                    while process.poll() is None:
                        info = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
                        available = int(info["MemAvailable"].split()[0]) * 1024
                        monitor.write(json.dumps({"utc": now(), "case": name, "available_bytes": available}) + "\n")
                        monitor.flush()
                        if available < 24 * 1024**3:
                            subprocess.run(["docker", "kill", "tilelang-review-build-20261104"], check=False)
                            record["memory_aborted"] = True
                            break
                        time.sleep(1)
                result = process.wait()
        destination = BASE / "variants" / name
        if not result:
            shutil.copytree(BASE / "variants/base", destination, copy_function=os.link)
            for relative in changed:
                target = destination / relative
                if target.exists():
                    target.unlink()
                if (WORK / relative).exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(WORK / relative, target)
            for source in (WORK / "build/lib").iterdir():
                if source.is_file():
                    target = destination / "build/lib" / source.name
                    if target.exists():
                        target.unlink()
                    shutil.copyfile(source, target)
            libraries = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (destination / "build/lib").glob("*.so")}
            metadata = destination / "native-libraries.json"
            metadata.unlink()
            metadata.write_text(json.dumps(libraries, indent=2) + "\n")
            record["libraries"] = libraries
        record.update(exit_code=result, ended_utc=now())
        (BASE / ("build-" + name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
        print("END", name, result, flush=True)
        previous = changed


if __name__ == "__main__":
    main()
