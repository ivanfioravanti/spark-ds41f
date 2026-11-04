# Attempts and corrections

The initial native configure stopped because the toolchain image has no Git.
The corrected build uses deterministic Git archives of every pinned submodule,
so source provenance is retained without Git metadata in the compiler container.
Both configure receipts are retained on sp8.

An initial CPU import had no CUDA driver library in the CPU-only container.
CPU-only checks now use CUDA's link stub; GPU containers use the real driver.

The first CPU matrix allowed pytest's reproducer directory to precede the
selected compiler on Python's search path. Cross-variant comparisons from
`cpu-*-a` / `cpu-*-b` are invalid. The rerun imports and asserts the requested
compiler before pytest starts, recording its module path and library hashes.
The v2 CPU pass stopped at the identity guard because TileLang prepends TVM to
`PYTHONPATH` during import. The v3 guard captures the requested path before
import, then checks the loaded module against it. No v2 test body ran.

The first port of #3710 omitted the `is_cache_enabled` import. This is a porting
error, not an upstream result. Its diff and failing receipts are preserved.
`pr3710-v2` adds the import; it changes no native libraries.

The first GPU matrix attempt refused the busy local GPU lock, before launching
any test. Another sp8 diagnostic held the node. The reservation/request protocol
was followed; no foreign hold was changed.

The first GPU batch yielded at a test boundary when another request arrived.
Its waiting resume process then deferred to that hold and the older request.
After the prior holder released the node, the request file remained while no
reservation or GPU process was present for several minutes. Under the GPU
lock, only our waiting process was replaced. The final short batch preserved
that old request, honored any new or changed request, and completed the 17
remaining processes. `queue-transition.json` and `completion.json` record the
transition and cleanup. No foreign request or hold was removed or overwritten.
