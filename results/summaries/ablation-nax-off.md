# Benchmark summary

Source: `nax-off.log`, session `4de49277`, 221 events

## Device

macOS Mac17,14 (arm64) · Apple M5 Max · Version 27.2.1 (Build 26B131) · RAM 36 GiB · GPU applegpu_g17s · build RELEASE · lowPowerMode False · thermalState 0

Args: models mlx-community/Qwen3-1.7B-4bit, mlx-community/Qwen3-4B-4bit; runs 3; cooldown 10 s; idle 30 s; sustain 100 s; sustain-prefill 60 s; phase cooldown n/a (not recorded by this build); MLX env {}

## Throughput (measured runs; warm-up excluded from median)

| model | workload | metric | measured | median | spread | prompt tok | TTFT median s | peak GB | thermal | stop | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | gen | tokensPerSecond | 295.1 / 303.7 / 295.2 | 295.2 | 2.92% | 48 | 0.0404 | 1.08 | 0→0 | length | 189c3a9519c9b492 |
| Qwen3-1.7B-4bit | prefill | promptTokensPerSecond | 2513.3 / 2529.3 / 2549.1 | 2529.3 | 1.41% | 10073 | 3.9826 | 2.92 | 0→0 | length | 0d02202ec08edfed |
| Qwen3-4B-4bit | gen | tokensPerSecond | 128.7 / 142.9 / 131.9 | 131.9 | 10.72% | 48 | 0.0793 | 2.42 | 0→0 | length | cae902a5673ea4ef |
| Qwen3-4B-4bit | prefill | promptTokensPerSecond | 936.7 / 1006.4 / 1004.6 | 1004.6 | 6.94% | 10073 | 10.0264 | 4.42 | 0→0 | length | 49d1a6036bfc4348 |

## Model load

model files GB = downloaded snapshot size (download_progress totalUnitCount); gen × size = gen median tok/s × that size, in GB/s.

| model | resolve s | load s | total s | parameters | model files GB | gen × size GB/s | model peak GB | parameter dtypes | logits dtype | ok |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 0.05 | 0.314 | 0.36 | 1720574976 | 0.98 | 290 | 2.92 | bfloat16 507, uint32 197 | bfloat16 | True |
| Qwen3-4B-4bit | 0.04 | 0.404 | 0.44 | 4022468096 | 2.28 | 300 | 4.42 | bfloat16 651, uint32 253 | bfloat16 | True |

## Idle

30.3 s idle, thermalState 0→0

## Sustain (gen back-to-back, no cooldown)

overall tok/s = generated tokens / phase seconds (includes per-iteration prompt processing); iter median / first / last = library decode tok/s per iteration.

| model | iterations | tokens | seconds | overall tok/s | iter median tok/s | first iter tok/s | last iter tok/s | last vs first | gen median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 110 | 28160 | 100.3 | 280.6 | 296.0 | 300.9 | 303.3 | 0.8% | 295.2 | 0→0 (max 0) | 189c3a9519c9b492 |
| Qwen3-4B-4bit | 52 | 13312 | 100.0 | 133.1 | 139.4 | 139.1 | 146.0 | 4.9% | 131.9 | 0→0 (max 0) | cae902a5673ea4ef |

## Sustain prefill (prefill back-to-back, no cooldown)

overall prompt tok/s = prompt tokens / phase seconds (includes the 16 generated tokens and overhead of each iteration); iter median / first / last = library prompt tok/s per iteration.

| model | iterations | prompt tokens | seconds | overall prompt tok/s | iter median prompt tok/s | first iter prompt tok/s | last iter prompt tok/s | last vs first | prefill median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 15 | 151095 | 63.3 | 2385.6 | 2489.2 | 2541.4 | 2537.5 | -0.2% | 2529.3 | 0→0 (max 0) | 0d02202ec08edfed |
| Qwen3-4B-4bit | 6 | 60438 | 60.2 | 1004.0 | 1027.0 | 1027.1 | 1026.7 | -0.0% | 1004.6 | 0→0 (max 0) | 49d1a6036bfc4348 |

## Mac power (fanctl; host clock)

518 samples, median spacing 1.05 s; the first 3 s of each phase are skipped. "System" = Mac body (SMC PSTR minus USB-port output), so devices charged from this Mac are excluded.

| phase | window s | samples | GPU W | CPU W | DRAM W | ANE W | Mac body W | PSTR W | USB out W |
|---|---|---|---|---|---|---|---|---|---|
| idle | 30.3 | 25 | 0.09 | 2.28 | 0.41 | 0.00 | 14.76 | 30.42 | 15.66 |
| sustain Qwen3-1.7B-4bit | 100.3 | 91 | 30.22 | 12.02 | 7.63 | 0.00 | 88.01 | 103.89 | 15.88 |
| sustain Qwen3-4B-4bit | 100.0 | 91 | 33.21 | 7.35 | 8.50 | 0.04 | 87.11 | 103.27 | 16.16 |
| sustain_prefill Qwen3-1.7B-4bit | 63.3 | 56 | 65.00 | 5.95 | 1.78 | 0.00 | 103.72 | 119.39 | 15.67 |
| sustain_prefill Qwen3-4B-4bit | 60.2 | 53 | 67.59 | 2.95 | 1.28 | 0.00 | 100.65 | 117.66 | 17.00 |

| phase | tokens/s (overall) | per | GPU W | net GPU W | J/token GPU gross | J/token GPU net | system W | J/token system gross | J/token system net |
|---|---|---|---|---|---|---|---|---|---|
| sustain Qwen3-1.7B-4bit | 280.6 | generated token | 30.22 | 30.13 | 0.1077 | 0.1073 | 88.01 | 0.3136 | 0.2610 |
| sustain Qwen3-4B-4bit | 133.1 | generated token | 33.21 | 33.11 | 0.2495 | 0.2487 | 87.11 | 0.6544 | 0.5435 |
| sustain_prefill Qwen3-1.7B-4bit | 2385.6 | prompt token | 65.00 | 64.90 | 0.0272 | 0.0272 | 103.72 | 0.0435 | 0.0373 |
| sustain_prefill Qwen3-4B-4bit | 1004.0 | prompt token | 67.59 | 67.50 | 0.0673 | 0.0672 | 100.65 | 0.1002 | 0.0855 |
