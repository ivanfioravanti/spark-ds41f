"""Summarize saved receipts, including unsuccessful and invalid setup attempts."""

from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET


def main():
    root = Path(sys.argv[1])
    summary = {"runs": {}, "builds": {}}
    for path in sorted(root.glob("build-*.json")):
        summary["builds"][path.stem] = json.loads(path.read_text())
    for path in sorted((root / "runs").glob("*/result.json")):
        directory = path.parent
        result = json.loads(path.read_text())
        label = directory.name
        valid = not label.startswith("cpu-") or label.endswith("-v3")
        result["valid_for_comparison"] = valid
        if not valid:
            result["invalid_reason"] = "pytest source precedence (v1) or environment identity guard (v2); see attempts.md"
        junit = directory / "junit.xml"
        if junit.exists():
            xml = ET.parse(junit)
            result["pytest"] = xml.find("testsuite").attrib
            result["failed_tests"] = [{"name": case.attrib["name"], "message": failure.attrib.get("message", "")}
                                      for case in xml.findall(".//testcase") for failure in case.findall("failure")]
            result["skipped_tests"] = [{"name": case.attrib["name"], "message": skipped.attrib.get("message", "")}
                                       for case in xml.findall(".//testcase") for skipped in case.findall("skipped")]
        for filename, key in [("standalone.json", "checks"), ("compiler.json", "compiler")]:
            if (directory / filename).exists():
                result[key] = json.loads((directory / filename).read_text())
        memory = directory / "memory.jsonl"
        if memory.exists():
            samples = [json.loads(line) for line in memory.read_text().splitlines()]
            if samples:
                result["min_host_available_bytes"] = min(sample["available_bytes"] for sample in samples)
                temperatures = [sample["hottest_c"] for sample in samples if sample.get("hottest_c") is not None]
                result["max_hottest_c"] = max(temperatures) if temperatures else None
        result["files"] = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                           for p in sorted(directory.iterdir()) if p.is_file()}
        summary["runs"][label] = result
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
