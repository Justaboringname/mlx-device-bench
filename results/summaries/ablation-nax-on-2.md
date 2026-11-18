# Benchmark summary

Source: `nax-on-2.log`, session `dc183e62`, 273 events

## Device

macOS Mac17,14 (arm64) · Apple M5 Max · Version 27.2.1 (Build 26B131) · RAM 36 GiB · GPU applegpu_g17s · build RELEASE · lowPowerMode False · thermalState 0

Args: models mlx-community/Qwen3-1.7B-4bit, mlx-community/Qwen3-4B-4bit; runs 3; cooldown 10 s; idle 30 s; sustain 100 s; sustain-prefill 60 s; phase cooldown n/a (not recorded by this build); MLX env {}

## Throughput (measured runs; warm-up excluded from median)

| model | workload | metric | measured | median | spread | prompt tok | TTFT median s | peak GB | thermal | stop | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | gen | tokensPerSecond | 272.1 / 274.7 / 271.8 | 272.1 | 1.07% | 48 | 0.0309 | 1.08 | 0→0 | length | 799ec6e941b85604 |
| Qwen3-1.7B-4bit | prefill | promptTokensPerSecond | 8216.5 / 8661.2 / 8646.7 | 8646.7 | 5.14% | 10073 | 1.1651 | 2.92 | 0→0 | length | 0d02202ec08edfed |
| Qwen3-4B-4bit | gen | tokensPerSecond | 145.0 / 142.0 / 145.9 | 145.0 | 2.72% | 48 | 0.0495 | 2.42 | 0→0 | length | c563528899d11540 |
| Qwen3-4B-4bit | prefill | promptTokensPerSecond | 3679.9 / 3534.1 / 3646.4 | 3646.4 | 4.00% | 10073 | 2.7625 | 4.42 | 0→0 | length | 49d1a6036bfc4348 |

## Model load

model files GB = downloaded snapshot size (download_progress totalUnitCount); gen × size = gen median tok/s × that size, in GB/s.

| model | resolve s | load s | total s | parameters | model files GB | gen × size GB/s | model peak GB | parameter dtypes | logits dtype | ok |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 0.05 | 0.327 | 0.38 | 1720574976 | 0.98 | 267 | 2.94 | bfloat16 507, uint32 197 | bfloat16 | True |
| Qwen3-4B-4bit | 0.04 | 0.339 | 0.38 | 4022468096 | 2.28 | 330 | 4.42 | bfloat16 651, uint32 253 | bfloat16 | True |

## Idle

30.3 s idle, thermalState 0→0

## Sustain (gen back-to-back, no cooldown)

overall tok/s = generated tokens / phase seconds (includes per-iteration prompt processing); iter median / first / last = library decode tok/s per iteration.

| model | iterations | tokens | seconds | overall tok/s | iter median tok/s | first iter tok/s | last iter tok/s | last vs first | gen median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 115 | 29440 | 100.2 | 293.7 | 300.9 | 301.4 | 300.7 | -0.2% | 272.1 | 0→0 (max 0) | 799ec6e941b85604 |
| Qwen3-4B-4bit | 53 | 13568 | 100.4 | 135.1 | 138.9 | 142.8 | 142.9 | 0.1% | 145.0 | 0→0 (max 0) | c563528899d11540 |

## Sustain prefill (prefill back-to-back, no cooldown)

overall prompt tok/s = prompt tokens / phase seconds (includes the 16 generated tokens and overhead of each iteration); iter median / first / last = library prompt tok/s per iteration.

| model | iterations | prompt tokens | seconds | overall prompt tok/s | iter median prompt tok/s | first iter prompt tok/s | last iter prompt tok/s | last vs first | prefill median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 46 | 463358 | 60.1 | 7705.7 | 8784.5 | 8817.3 | 8625.6 | -2.2% | 8646.7 | 0→0 (max 0) | 0d02202ec08edfed |
| Qwen3-4B-4bit | 21 | 211533 | 62.8 | 3369.0 | 3669.2 | 3664.9 | 3635.5 | -0.8% | 3646.4 | 0→0 (max 0) | 49d1a6036bfc4348 |

## Mac power (fanctl; host clock)

478 samples, median spacing 1.06 s; the first 3 s of each phase are skipped. "System" = Mac body (SMC PSTR minus USB-port output), so devices charged from this Mac are excluded.

| phase | window s | samples | GPU W | CPU W | DRAM W | ANE W | Mac body W | PSTR W | USB out W |
|---|---|---|---|---|---|---|---|---|---|
| idle | 30.3 | 25 | 0.31 | 3.39 | 0.52 | 0.00 | 17.50 | 33.23 | 15.73 |
| sustain Qwen3-1.7B-4bit | 100.2 | 91 | 29.45 | 9.67 | 7.65 | 0.00 | 84.06 | 100.32 | 16.25 |
| sustain Qwen3-4B-4bit | 100.4 | 91 | 29.90 | 12.59 | 8.62 | 0.00 | 89.57 | 93.20 | 3.62 |
| sustain_prefill Qwen3-1.7B-4bit | 60.1 | 53 | 79.58 | 9.31 | 3.33 | 0.00 | 132.21 | 147.40 | 15.19 |
| sustain_prefill Qwen3-4B-4bit | 62.8 | 56 | 87.46 | 14.78 | 3.19 | 0.00 | 153.28 | 157.17 | 3.90 |

| phase | tokens/s (overall) | per | GPU W | net GPU W | J/token GPU gross | J/token GPU net | system W | J/token system gross | J/token system net |
|---|---|---|---|---|---|---|---|---|---|
| sustain Qwen3-1.7B-4bit | 293.7 | generated token | 29.45 | 29.14 | 0.1003 | 0.0992 | 84.06 | 0.2862 | 0.2266 |
| sustain Qwen3-4B-4bit | 135.1 | generated token | 29.90 | 29.59 | 0.2213 | 0.2190 | 89.57 | 0.6629 | 0.5333 |
| sustain_prefill Qwen3-1.7B-4bit | 7705.7 | prompt token | 79.58 | 79.27 | 0.0103 | 0.0103 | 132.21 | 0.0172 | 0.0149 |
| sustain_prefill Qwen3-4B-4bit | 3369.0 | prompt token | 87.46 | 87.15 | 0.0260 | 0.0259 | 153.28 | 0.0455 | 0.0403 |
