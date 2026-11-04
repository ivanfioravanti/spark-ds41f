# Standalone timing screen

Each value is µs/launch ± the within-process 95% interval. A and B are independent processes with fresh caches. These intervals do not include cross-process or serving variability. Negative change means the candidate is faster.

| Comparison | Run | Control | Candidate | Change |
|---|---|---:|---:|---:|
| WO-A reproducer, WS disabled → enabled | A | 161.579 ± 0.537 | 165.345 ± 0.501 | +2.33% |
| Reduction 256-128-sum | A | 0.833 ± 0.008 | 0.831 ± 0.008 | -0.32% |
| Reduction 256-128-max | A | 0.835 ± 0.006 | 0.877 ± 0.010 | +4.97% |
| Reduction 1024-256-sum | A | 1.010 ± 0.008 | 0.967 ± 0.006 | -4.25% |
| Reduction 1024-256-max | A | 1.018 ± 0.008 | 0.992 ± 0.007 | -2.50% |
| Clamp float32 | A | 0.916 ± 0.006 | 0.935 ± 0.005 | +2.06% |
| Clamp float16 | A | 0.819 ± 0.007 | 0.791 ± 0.007 | -3.42% |
| Clamp bfloat16 | A | 0.811 ± 0.007 | 0.782 ± 0.004 | -3.56% |
| WO-A reproducer, WS disabled → enabled | B | 160.531 ± 0.866 | 164.330 ± 0.718 | +2.37% |
| Reduction 256-128-sum | B | 0.868 ± 0.065 | 0.832 ± 0.008 | -4.18% |
| Reduction 256-128-max | B | 0.855 ± 0.048 | 0.870 ± 0.007 | +1.77% |
| Reduction 1024-256-sum | B | 1.003 ± 0.004 | 0.966 ± 0.006 | -3.72% |
| Reduction 1024-256-max | B | 1.002 ± 0.005 | 0.993 ± 0.008 | -0.98% |
| Clamp float32 | B | 0.922 ± 0.005 | 0.959 ± 0.057 | +4.01% |
| Clamp float16 | B | 0.827 ± 0.006 | 0.815 ± 0.081 | -1.53% |
| Clamp bfloat16 | B | 0.823 ± 0.007 | 0.779 ± 0.005 | -5.38% |
