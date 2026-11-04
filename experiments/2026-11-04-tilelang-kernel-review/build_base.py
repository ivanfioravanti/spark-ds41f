"""Build the pinned standalone compiler inside a CPU-only toolchain container."""

from pathlib import Path
import datetime
import json
import subprocess
import time

BASE = Path.home() / "spark-lab/tilelang-review-20261104"
BUILD = """set -eu
mkdir -p /review/tools
python3 -m pip download --no-deps --only-binary=:all: --dest /review/tools cmake==3.31.6 Cython==3.1.2
sha256sum /review/tools/*.whl > /review/tools/sha256.txt
python3 -m pip install --no-index --find-links /review/tools --no-deps cmake==3.31.6 Cython==3.1.2
python3 -m pip freeze > /review/tools/python-packages.txt
cmake --version
nvcc --version
g++ --version
cmake -S /review/work-source -B /review/work-source/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DUSE_CUDA=ON -DUSE_ROCM=OFF -DUSE_ASCEND=OFF -DUSE_LLVM=OFF -DUSE_LIBBACKTRACE=OFF -DPython_EXECUTABLE=/usr/bin/python3
cmake --build /review/work-source/build --parallel 8
"""


def main():
    for _ in range(180):
        if (BASE / "prepared.json").exists():
            break
        time.sleep(5)
    else:
        raise SystemExit("source preparation did not complete")
    image = subprocess.check_output(
        ["docker", "image", "inspect", "sha256:213ba4df68d0", "--format", "{{.Id}}"], text=True
    ).strip()
    name = "tilelang-review-build-20261104"
    command = [
        "docker", "run", "-d", "--name", name, "--runtime", "runc",
        "--memory", "64g", "--memory-swap", "64g", "--shm-size", "2g",
        "--env", "NVIDIA_VISIBLE_DEVICES=void", "--env", "CMAKE_BUILD_PARALLEL_LEVEL=8",
        "--mount", f"type=bind,source={BASE},target=/review", "--entrypoint", "sleep", image, "infinity",
    ]
    present = subprocess.run(["docker", "container", "inspect", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if present.returncode:
        print("COMMAND", json.dumps(command), flush=True)
        subprocess.run(command, check=True)
    command = ["docker", "exec", name, "bash", "-lc", BUILD]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print("COMMAND", json.dumps(command), flush=True)
    process = subprocess.Popen(command)
    memory_aborted = False
    with (BASE / "build-memory.jsonl").open("a") as monitor:
        while process.poll() is None:
            values = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
            available = int(values["MemAvailable"].split()[0]) * 1024
            monitor.write(json.dumps({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "available_bytes": available}) + "\n")
            monitor.flush()
            if available < 24 * 1024**3:
                subprocess.run(["docker", "kill", name], check=False)
                memory_aborted = True
                break
            time.sleep(1)
    result = process.wait()
    receipt = {
        "started_utc": started, "ended_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "image": image, "container": name, "command": command, "exit_code": result,
        "gpus_exposed": False, "memory_limit_gib": 64, "parallel_jobs": 8,
        "memory_aborted": memory_aborted, "host_memory_floor_gib": 24,
    }
    (BASE / "build-base.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("BUILD_EXIT", result, flush=True)
    raise SystemExit(result)


if __name__ == "__main__":
    main()
