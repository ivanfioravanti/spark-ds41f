"""Request the short remaining window after an earlier sp8 request is accepted."""

from pathlib import Path
import datetime
import json
import os
import time

base = Path.home() / "spark-lab/tilelang-review-20261104"
holder = "tilelang-standalone-review-20261104"
specification = json.loads((base / "deployment/experiments/2026-11-04-tilelang-kernel-review/matrix-gpu-resume.json").read_text())
request = Path.home() / "spark-request.json"
hold = Path.home() / "spark-hold.json"
while True:
    pending = [j for j in specification["jobs"] if not (base / "runs" / j["label"] / "result.json").exists()]
    if not pending:
        break
    if hold.exists():
        current = json.loads(hold.read_text())
        if current.get("holder") == holder:
            break
        if not request.exists():
            record = {"who": holder, "why": f"Finish {len(pending)} remaining standalone TileLang checks; no serving changes",
                      "how_long": "about 3 minutes, then release sp8",
                      "requested_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            temporary = Path.home() / ".spark-request-tilelang-review.tmp"
            temporary.write_text(json.dumps(record, indent=2) + "\n")
            try:
                os.link(temporary, request)  # atomic, and never replaces another request
                (base / "request-resume.json").write_text(json.dumps(record, indent=2) + "\n")
                print(json.dumps(record), flush=True)
                break
            except FileExistsError:
                pass
            finally:
                temporary.unlink()
    time.sleep(5)
