# Standalone TileLang kernel review

Screen the named compiler and kernel changes on sp8 without starting vLLM,
loading the checkpoint, or changing any serving cluster. `base.json` records
the published deployment/compiler identity. The runtime image supplies only
an isolated CUDA/PyTorch toolchain; its vLLM entrypoint is overridden.

Each case changes one compiler patch or template against the unreleased
TileLang candidate. Keep exact commands, source and native-library hashes,
all failures, GPU/host memory observations and every run. Each timing case
needs two fresh test processes, with repeated samples and an interval; these
are kernel measurements, not serving boots or end-to-end throughput claims.
Do not benchmark a released serving build again.

CPU build containers receive no GPU devices. GPU tests require the applicable
hold checks, the exclusive sp8 GPU lock, an idle node, memory limits and a
cool start. A foreign hold is never removed or overwritten. No command in
this work starts, stops, replaces, syncs or restores a vLLM service.

The cases cover producer visibility, reduction/barrier changes, symmetric
clamp arithmetic, shared-memory alignment, cache disabling, explicit compile
mode, consumer fences, async-copy waits, linear-layout/TMA correctness,
prefetch APIs and architecture-specific reduction lowering. Keep independent
cases separate; record an interaction explicitly if a combined fix is needed.

GPU qualification remains pending until its native receipts exist. Findings
from source inspection alone do not establish a speedup or numerical parity.
