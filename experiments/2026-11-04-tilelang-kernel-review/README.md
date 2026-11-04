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

## Evidence status

The native base compiler and all ten independent variants built on sp8. There
are **66 completed, valid test processes**, with all planned repeats and clamp
edge checks complete. Another 28 invalid setup processes are retained and
excluded from comparisons. This is standalone screening, not serving
qualification or promotion. Our test containers and local hold are removed;
foreign reservations and requests are preserved.

The carried MXFP8, MXFP4, NVFP4 and IKET suites passed **203 tests in each of two
fresh processes**. Each process skipped two tests restricted to SM120. All four
new exact-result shared-scale selector regressions passed twice. Prepare/freeze
also passed twice on the base and each JIT port with its default settings.

## Findings

| Item | Standalone evidence | Consequence for this stack |
|---|---|---|
| [#3661](https://github.com/tile-ai/tilelang/pull/3661), synchronous producer stores | The base produces wrong BF16 GEMM results with warp specialization in one process; the other process passes, demonstrating the race's intermittent nature. The port passes the 200-launch poisoned-output reproducer twice; disabling specialization also passes twice. Fixed specialization is 2.33% and 2.37% slower than disabled. | A useful correctness fix. Keep our specialization workaround until an actual WO-A kernel shows a benefit. |
| [#3715](https://github.com/tile-ai/tilelang/pull/3715), crosswarp reduction | Max outputs retain their bits. FP32 sum changes 43/64 and 47/64 output rows at widths 256 and 1024; maximum differences are 32 and 14 ULP. Both versions meet tolerance and repeat their own output bits across processes. Width-1024 sum improves 4.25%/3.72%; width-256 max regresses 4.97%/1.77%. | Already in the refresh. Record the addition-order change and retain the numerical/quality gate; speed depends on the reduction shape and operation. |
| [#3761](https://github.com/tile-ai/tilelang/pull/3761), partial barriers | All 98 thread-sync cases pass twice, split between CPU and GPU-required checks. Removing the change makes the pipeline reuse assertion see two IDs instead of one; ten other failures concern the combined-scope API. | Keep the already-merged change. This establishes barrier reuse, not a measured mHC or serving speedup. |
| [#3605](https://github.com/tile-ai/tilelang/pull/3605), symmetric clamp | Both processes match tested finite bits, subnormals, NaN propagation and signed zeros for FP32, FP16 and BF16. Short edge kernels preserve input NaN sign/payload in compare/select, while the new instruction canonicalizes them in all three dtypes, twice. The cache-hot microkernel improves FP16 1.53–3.42% and BF16 3.56–5.38%, but regresses FP32 2.06–4.01%. | Keep out of a strictly bit-preserving stack. Its NaN semantics must be accepted explicitly before use, and any speed claim needs our fused kernel's workload. |
| [#3690](https://github.com/tile-ai/tilelang/pull/3690), shared alignment | **19/19 pass twice**. The base fails six assertions about unnecessarily large alignment. Exact swizzled TMA copy checks pass. | A sound smaller-alignment candidate; no speedup is established by these tests. |
| [#3710](https://github.com/tile-ai/tilelang/pull/3710), cache disabling | **5/5 pass twice**; the base fails the fresh-wrapper-kernel assertion twice. Our default prepare/freeze check also passes twice. | Useful for trustworthy fresh compilation tests. The first port's missing import was corrected and its failed receipts retained. |
| [#3190](https://github.com/tile-ai/tilelang/pull/3190), strict compilation | **40 CPU tests plus one real CUDA execution pass twice**. Our default prepare/freeze API works, but enabling strict mode after our `prepare` fails twice because the explicit-specialization registry is not populated. | A compatible default mode, with further integration required before enabling strict mode in our runtime. |
| [#3537](https://github.com/tile-ai/tilelang/pull/3537), consumer release fence | Both processes pass the two generated-code fence assertions and numerical fast-math reproducer. The base fails both fence assertions twice but passes that numerical workload twice. Hopper-only WGMMA cases are excluded. | A useful synchronization candidate. The missing fences are demonstrated; numerical failure was not observed in this sample. |
| [#3568](https://github.com/tile-ai/tilelang/pull/3568), async waits | **3/3 transform regressions pass twice**; all three fail on the base. A same-stage consumer gets `wait<0>` instead of the base's insufficient `wait<1>`. | A clear compiler correctness candidate. No serving process is required to demonstrate it. |
| [#3571](https://github.com/tile-ai/tilelang/issues/3571), linear layout with TMA | Explicit linear shared layout plus TMA and warp specialization gives wrong results in both processes: the three launch mismatch counts are `[1024, 307, 12157]` and `[2978, 0, 26883]`. Inferred/swizzled layouts and the TMA-disabled linear layout are exact twice. | Avoid that combination. Our carried vLLM patches do not request `make_linear_layout`. |
| [#3490](https://github.com/tile-ai/tilelang/pull/3490), prefetch API | All three policies compile, emit the requested PTX and preserve the input/output twice. All six saved PTX instruction checks pass. | Useful API coverage; it supplies no demonstrated benefit over our existing bulk L2 prefetch. |
| [#3692](https://github.com/tile-ai/tilelang/pull/3692), FP32 redux | Both processes generate five shuffles and no FP32 redux for SM121a. SM103a emits FP32 redux; integer max emits redux on both. SM103 code is never launched on sp8. | No FP32 hardware-reduction benefit for GB10. |

## Workloads and interpretation

`matrix-cpu-v3.json` and `matrix-gpu-v2.json` contain the exact argument vectors;
`matrix-gpu-resume.json` contains the completed repeat and clamp-edge batch.
Each source is an independent patch against the unreleased compiler candidate.
The warp-specialization flag comparison is an explicit interaction check on
the same fixed compiler, rather than a cumulative stack of proposed fixes.

The reduction screen uses 64 rows, widths 256/1024 and 128/256 threads, seed 17,
with FP64 reference error and output bits recorded. The clamp screen uses
65,536 elements, limit 7 and seed 41. The layout reproducer uses 1024³ FP16
GEMM, small exact integer inputs, seed 29 and three poisoned outputs per case.
The upstream reproducers retain their pinned workloads in each port's source.

Timing captures 100 launches in one CUDA graph and measures nine samples of
ten replays. Values are µs/launch with a Student-t 95% interval within each
fresh process. Clocks are not locked; intervals do not quantify serving or
cross-process variability. [timings.md](timings.md) records both processes and
their intervals for every timing comparison. The runner cools all exposed thermal sensors below
55 °C before each GPU process and records temperatures and host memory. The
completed GPU runs kept at least 112.89 GiB host memory available; the native
build kept at least 108.48 GiB. One sampled sensor reached 59.6 °C during a run.

## Reproducibility and boundaries

`provenance.json` maps batches to published harness commits. `cases.json` and
`merged-cases.json` pin upstream heads, experimental diffs and exact resulting
trees. `validation/source-check.json` verifies every port in a fresh tree.
`results.json` indexes all run receipts, failures, skips, timings, module paths,
native-library hashes and memory observations. `evidence.tar.gz` preserves raw
commands, logs, generated CUDA/PTX and JUnit files. Its initial setup errors and
invalid harness attempts are explained in `attempts.md` and excluded from
comparisons. The sources, build products and isolated caches remain on sp8 at
`/home/chris/spark-lab/tilelang-review-20261104`.

`bin/spark doctor` passes. `bin/spark build check` reports that the full vLLM
build tree is absent; this experiment builds the compiler in an existing
toolchain image and does not produce a new serving image. Production
configuration, published baselines and reference benchmarks are untouched.
No vLLM engine, checkpoint load or cluster operation is part of these commands.
