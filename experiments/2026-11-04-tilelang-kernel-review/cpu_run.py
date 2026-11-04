"""Run compiler/JIT checks in the existing CPU-only builder, without GPU devices."""

from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

BASE = Path.home() / "spark-lab/tilelang-review-20261104"


def main():
    stubs = BASE / "cpu-stubs"
    stubs.mkdir(exist_ok=True)
    driver = stubs / "libcuda.so.1"
    if not driver.is_symlink():
        driver.symlink_to("/usr/local/cuda/lib64/stubs/libcuda.so")
    specification = json.loads(Path(sys.argv[1]).read_text())
    for job in specification["jobs"]:
        label = job["label"]
        output = BASE / "runs" / label
        output.mkdir(parents=True, exist_ok=False)
        arguments = job["args"]
        if arguments[:2] == ["-m", "pytest"]:
            arguments = [str(Path("/review/deployment/experiments/2026-11-04-tilelang-kernel-review/pytest_run.py")), *arguments[2:]]
        command = ["docker", "exec", "--workdir", "/review/runs/" + label,
                   "--env", "PYTHONPATH=/review/" + job["source"],
                   "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "NO_GIT_VERSION=1",
                   "--env", "TILELANG_CACHE_DIR=/review/cache/" + label,
                   "--env", "LD_LIBRARY_PATH=/review/cpu-stubs:/usr/local/cuda/lib64",
                   "tilelang-review-build-20261104", "/usr/bin/timeout", "180", "python3",
                   *[a.replace("/out/", "/review/runs/" + label + "/") for a in arguments]]
        receipt = {"label": label, "source": job["source"], "command": command,
                   "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "gpu_devices": [], "driver": "CUDA link stub, CPU checks only"}
        print("START", label, flush=True)
        with (output / "output.txt").open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        receipt.update(exit_code=result.returncode, ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       output_sha256=hashlib.sha256((output / "output.txt").read_bytes()).hexdigest())
        (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print("END", label, result.returncode, flush=True)


if __name__ == "__main__":
    main()
