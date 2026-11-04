"""Import the selected compiler before pytest changes paths to a reproducer's tree."""

from pathlib import Path
import json
import os
import sys

import tilelang

source = Path(os.environ["PYTHONPATH"]).resolve()
module = Path(tilelang.__file__).resolve()
assert module.is_relative_to(source), (module, source)
identity = {"tilelang_module": str(module), "native_libraries": json.loads((source / "native-libraries.json").read_text())}
Path("compiler.json").write_text(json.dumps(identity, indent=2) + "\n")
print(json.dumps(identity), flush=True)

import pytest

raise SystemExit(pytest.main(sys.argv[1:]))
