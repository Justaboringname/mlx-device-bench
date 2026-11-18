# Benchmark summary

Source: `nax-on-1.log`, session `48c86caa`, 276 events

## Device

macOS Mac17,14 (arm64) · Apple M5 Max · Version 27.2.1 (Build 26B131) · RAM 36 GiB · GPU applegpu_g17s · build RELEASE · lowPowerMode False · thermalState 0

Args: models mlx-community/Qwen3-1.7B-4bit, mlx-community/Qwen3-4B-4bit; runs 3; cooldown 10 s; idle 30 s; sustain 100 s; sustain-prefill 60 s; phase cooldown n/a (not recorded by this build); MLX env {}

## Throughput (measured runs; warm-up excluded from median)

| model | workload | metric | measured | median | spread | prompt tok | TTFT median s | peak GB | thermal | stop | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | gen | tokensPerSecond | 287.9 / 297.4 / 300.7 | 297.4 | 4.29% | 48 | 0.0306 | 1.08 | 0→0 | length | 799ec6e941b85604 |
| Qwen3-1.7B-4bit | prefill | promptTokensPerSecond | 8704.8 / 8705.5 / 8690.6 | 8704.8 | 0.17% | 10073 | 1.1573 | 2.92 | 0→0 | length | 0d02202ec08edfed |
| Qwen3-4B-4bit | gen | tokensPerSecond | 144.1 / 144.5 / 137.9 | 144.1 | 4.55% | 48 | 0.0496 | 2.42 | 0→0 | length | c563528899d11540 |
| Qwen3-4B-4bit | prefill | promptTokensPerSecond | 3659.3 / 3616.3 / 3662.5 | 3659.3 | 1.26% | 10073 | 2.7528 | 4.42 | 0→0 | length | 49d1a6036bfc4348 |

## Model load

model files GB = downloaded snapshot size (download_progress totalUnitCount); gen × size = gen median tok/s × that size, in GB/s.

| model | resolve s | load s | total s | parameters | model files GB | gen × size GB/s | model peak GB | parameter dtypes | logits dtype | ok |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 0.05 | 0.367 | 0.42 | 1720574976 | 0.98 | 292 | 2.94 | bfloat16 507, uint32 197 | bfloat16 | True |
| Qwen3-4B-4bit | 0.04 | 0.364 | 0.41 | 4022468096 | 2.28 | 328 | 4.42 | bfloat16 651, uint32 253 | bfloat16 | True |

## Idle

31.4 s idle, thermalState 0→0

## Sustain (gen back-to-back, no cooldown)

overall tok/s = generated tokens / phase seconds (includes per-iteration prompt processing); iter median / first / last = library decode tok/s per iteration.

| model | iterations | tokens | seconds | overall tok/s | iter median tok/s | first iter tok/s | last iter tok/s | last vs first | gen median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 116 | 29696 | 100.5 | 295.5 | 302.3 | 301.0 | 303.1 | 0.7% | 297.4 | 0→0 (max 0) | 799ec6e941b85604 |
| Qwen3-4B-4bit | 55 | 14080 | 100.3 | 140.3 | 145.3 | 139.7 | 146.4 | 4.8% | 144.1 | 0→0 (max 0) | c563528899d11540 |

## Sustain prefill (prefill back-to-back, no cooldown)

overall prompt tok/s = prompt tokens / phase seconds (includes the 16 generated tokens and overhead of each iteration); iter median / first / last = library prompt tok/s per iteration.

| model | iterations | prompt tokens | seconds | overall prompt tok/s | iter median prompt tok/s | first iter prompt tok/s | last iter prompt tok/s | last vs first | prefill median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 47 | 473431 | 61.2 | 7740.5 | 8837.5 | 8847.0 | 8689.7 | -1.8% | 8704.8 | 0→0 (max 0) | 0d02202ec08edfed |
| Qwen3-4B-4bit | 20 | 201460 | 60.1 | 3354.8 | 3671.7 | 3711.7 | 3715.4 | 0.1% | 3659.3 | 0→0 (max 0) | 49d1a6036bfc4348 |

## Mac power (fanctl; host clock)

477 samples, median spacing 1.06 s; the first 3 s of each phase are skipped. "System" = Mac body (SMC PSTR minus USB-port output), so devices charged from this Mac are excluded.

| phase | window s | samples | GPU W | CPU W | DRAM W | ANE W | Mac body W | PSTR W | USB out W |
|---|---|---|---|---|---|---|---|---|---|
| idle | 31.4 | 27 | 0.49 | 3.09 | 0.58 | 0.00 | 17.16 | 33.43 | 16.27 |
| sustain Qwen3-1.7B-4bit | 100.5 | 91 | 28.66 | 8.91 | 7.67 | 0.00 | 82.58 | 107.29 | 24.71 |
| sustain Qwen3-4B-4bit | 100.3 | 90 | 29.00 | 7.91 | 8.62 | 0.01 | 83.80 | 108.98 | 25.18 |
| sustain_prefill Qwen3-1.7B-4bit | 61.2 | 54 | 78.54 | 8.71 | 3.34 | 0.00 | 132.24 | 157.20 | 24.96 |
| sustain_prefill Qwen3-4B-4bit | 60.1 | 53 | 89.46 | 8.96 | 3.04 | 0.00 | 142.95 | 168.53 | 25.59 |

| phase | tokens/s (overall) | per | GPU W | net GPU W | J/token GPU gross | J/token GPU net | system W | J/token system gross | J/token system net |
|---|---|---|---|---|---|---|---|---|---|
| sustain Qwen3-1.7B-4bit | 295.5 | generated token | 28.66 | 28.16 | 0.0970 | 0.0953 | 82.58 | 0.2795 | 0.2214 |
| sustain Qwen3-4B-4bit | 140.3 | generated token | 29.00 | 28.50 | 0.2066 | 0.2031 | 83.80 | 0.5971 | 0.4748 |
| sustain_prefill Qwen3-1.7B-4bit | 7740.5 | prompt token | 78.54 | 78.04 | 0.0101 | 0.0101 | 132.24 | 0.0171 | 0.0149 |
| sustain_prefill Qwen3-4B-4bit | 3354.8 | prompt token | 89.46 | 88.97 | 0.0267 | 0.0265 | 142.95 | 0.0426 | 0.0375 |
