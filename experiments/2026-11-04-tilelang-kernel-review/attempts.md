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

The first port of #3710 omitted the `is_cache_enabled` import. This is a porting
error, not an upstream result. Its diff and failing receipts are preserved.
`pr3710-v2` adds the import; it changes no native libraries.

The first GPU matrix attempt refused the busy local GPU lock, before launching
any test. Another sp8 diagnostic held the node. The reservation/request protocol
was followed; no foreign hold was changed.
