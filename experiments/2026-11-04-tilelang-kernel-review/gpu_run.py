"""Run bounded standalone tests under sp8's local reservation; never run a server."""

from pathlib import Path
import datetime
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

BASE = Path.home() / "spark-lab/tilelang-review-20261104"
HOLDER = "tilelang-standalone-review-20261104"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def available_memory():
    values = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    return int(values["MemAvailable"].split()[0]) * 1024


def hottest():
    values = [int(p.read_text()) / 1000 for p in Path("/sys/class/thermal").glob("thermal_zone*/temp")]
    return max(values) if values else None


def main():
    specification = json.loads(Path(sys.argv[1]).read_text())
    if specification.get("host") != "sp8" or not specification.get("independent_sp8_authorized"):
        raise SystemExit("an explicit sp8-only authorization is required")
    lock = open("/tmp/spark-lab-gpu.lock", "w")
    hold = Path.home() / "spark-hold.json"
    started_waiting = time.monotonic()
    waiting_reported = False
    request = Path.home() / "spark-request.json"
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            foreign_request = request.exists() and json.loads(request.read_text()).get("who") != HOLDER
            if not hold.exists() and not foreign_request:
                break
            fcntl.flock(lock, fcntl.LOCK_UN)
        except BlockingIOError:
            pass
        if not specification.get("wait_for_window") or time.monotonic() - started_waiting > 1800:
            raise SystemExit("sp8 has an existing reservation; no GPU job launched")
        if not waiting_reported:
            print("WAIT for sp8's existing reservation; no GPU job launched", flush=True)
            waiting_reported = True
        time.sleep(5)
    if request.exists() and json.loads(request.read_text()).get("who") == HOLDER:
        request.unlink()
    processes = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid,process_name", "--format=csv,noheader"], text=True
    ).strip()
    if processes:
        raise SystemExit("sp8 already has GPU processes: " + processes)
    containers = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True).splitlines()
    serving = [name for name in containers if name in ("spark-ds41f", "dsv41-karmic-kraken")]
    if serving:
        raise SystemExit("refusing to test beside serving containers: " + repr(serving))
    record = {
        "holder": HOLDER, "since": now(), "expected_end": None, "heartbeat": now(), "pid": os.getpid(),
        "scope": "sp8 only; explicitly authorized independently of the foreign dgx1 hold",
        "rule": "exclusive standalone compiler/kernel tests; no serving or cluster changes",
    }
    hold.write_text(json.dumps(record, indent=2) + "\n")
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(15):
            record["heartbeat"] = now()
            temporary = hold.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(record, indent=2) + "\n")
            temporary.replace(hold)

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        image = subprocess.check_output(
            ["docker", "image", "inspect", "sha256:213ba4df68d0", "--format", "{{.Id}}"], text=True
        ).strip()
        for job in specification["jobs"]:
            request = Path.home() / "spark-request.json"
            if request.exists():
                print("YIELD requested after the previous job: " + request.read_text(), flush=True)
                break
            label = job["label"]
            output = BASE / "runs" / label
            output.mkdir(parents=True, exist_ok=False)
            start = time.monotonic()
            while hottest() is not None and hottest() >= 55:
                if time.monotonic() - start > 600:
                    raise SystemExit("sp8 did not cool below 55 C")
                time.sleep(5)
            source = job.get("source", "variants/base")
            cache = BASE / "cache" / label
            cache.mkdir(parents=True, exist_ok=False)
            name = "tl-review-" + label.replace("_", "-")
            arguments = job["args"]
            if arguments[:2] == ["-m", "pytest"]:
                arguments = ["/review/deployment/experiments/2026-11-04-tilelang-kernel-review/pytest_run.py", *arguments[2:]]
            command = [
                "docker", "run", "--rm", "--name", name, "--gpus", "all", "--network", "none",
                "--memory", "24g", "--memory-swap", "24g", "--shm-size", "2g", "--ulimit", "core=0",
                "--mount", f"type=bind,source={BASE},target=/review,readonly",
                "--mount", f"type=bind,source={output},target=/out",
                "--mount", f"type=bind,source={cache},target=/cache",
                "--env", f"PYTHONPATH=/review/{source}", "--env", "PYTHONDONTWRITEBYTECODE=1",
                "--env", "TILELANG_CACHE_DIR=/cache/tilelang", "--env", "CUDA_CACHE_PATH=/cache/driver",
                "--env", "VLLM_PLUGINS=", "--env", "NO_GIT_VERSION=1", "--workdir", "/out",
                "--entrypoint", "/usr/bin/timeout", image, str(job.get("timeout_seconds", 300)), "python3", *arguments,
            ]
            receipt = {
                "label": label, "started_utc": now(), "image": image, "source": source, "command": command,
                "before_memory_bytes": available_memory(), "start_hottest_c": hottest(),
                "independent_sp8_authorized": True, "dgx1_hold_modified": False, "serving_operations": [],
            }
            (output / "command.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print("START", label, flush=True)
            with (output / "output.txt").open("w") as log, (output / "memory.jsonl").open("w") as memory:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                aborted = False
                while process.poll() is None:
                    available = available_memory()
                    memory.write(json.dumps({"utc": now(), "available_bytes": available, "hottest_c": hottest()}) + "\n")
                    memory.flush()
                    if available < 24 * 1024**3:
                        subprocess.run(["docker", "kill", name], check=False)
                        aborted = True
                        break
                    time.sleep(1)
                receipt.update(exit_code=process.wait(), ended_utc=now(), memory_aborted=aborted)
            receipt["output_sha256"] = hashlib.sha256((output / "output.txt").read_bytes()).hexdigest()
            (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print("END", label, receipt["exit_code"], flush=True)
    finally:
        stop.set()
        thread.join()
        if hold.exists() and json.loads(hold.read_text()).get("holder") == HOLDER:
            hold.unlink()
        lock.close()


if __name__ == "__main__":
    main()
