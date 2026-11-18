# Benchmark summary

Source: `mac-m5max.log`, session `fd500604`, 279 events

## Device

macOS Mac17,14 (arm64) · Apple M5 Max · Version 27.2.1 (Build 26B131) · RAM 36 GiB · GPU applegpu_g17s · build RELEASE · lowPowerMode False · thermalState 0

Args: models mlx-community/Qwen3-1.7B-4bit, mlx-community/Qwen3-4B-4bit; runs 3; cooldown 10 s; idle 30 s; sustain 100 s; sustain-prefill 60 s; phase cooldown 0 s; MLX env {}

## Throughput (measured runs; warm-up excluded from median)

| model | workload | metric | measured | median | spread | prompt tok | TTFT median s | peak GB | thermal | stop | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | gen | tokensPerSecond | 304.0 / 304.7 / 305.9 | 304.7 | 0.63% | 48 | 0.0300 | 1.08 | 0→0 | length | 799ec6e941b85604 |
| Qwen3-1.7B-4bit | prefill | promptTokensPerSecond | 8755.8 / 8764.2 / 8757.5 | 8757.5 | 0.10% | 10073 | 1.1503 | 2.92 | 0→0 | length | 0d02202ec08edfed |
| Qwen3-4B-4bit | gen | tokensPerSecond | 147.9 / 148.3 / 147.7 | 147.9 | 0.43% | 48 | 0.0497 | 2.42 | 0→0 | length | c563528899d11540 |
| Qwen3-4B-4bit | prefill | promptTokensPerSecond | 3720.4 / 3721.2 / 3715.2 | 3720.4 | 0.16% | 10073 | 2.7076 | 4.42 | 0→0 | length | 49d1a6036bfc4348 |

## Model load

model files GB = downloaded snapshot size (download_progress totalUnitCount); gen × size = gen median tok/s × that size, in GB/s.

| model | resolve s | load s | total s | parameters | model files GB | gen × size GB/s | model peak GB | parameter dtypes | logits dtype | ok |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 0.07 | 0.327 | 0.40 | 1720574976 | 0.98 | 299 | 2.94 | bfloat16 507, uint32 197 | bfloat16 | True |
| Qwen3-4B-4bit | 0.04 | 0.319 | 0.36 | 4022468096 | 2.28 | 337 | 4.42 | bfloat16 651, uint32 253 | bfloat16 | True |

## Idle

30.3 s idle, thermalState 0→0

## Sustain (gen back-to-back, no cooldown)

overall tok/s = generated tokens / phase seconds (includes per-iteration prompt processing); iter median / first / last = library decode tok/s per iteration.

| model | iterations | tokens | seconds | overall tok/s | iter median tok/s | first iter tok/s | last iter tok/s | last vs first | gen median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 116 | 29696 | 100.4 | 295.8 | 303.8 | 302.8 | 304.0 | 0.4% | 304.7 | 0→0 (max 0) | 799ec6e941b85604 |
| Qwen3-4B-4bit | 57 | 14592 | 100.8 | 144.8 | 148.0 | 147.3 | 148.0 | 0.5% | 147.9 | 0→0 (max 0) | c563528899d11540 |

## Sustain prefill (prefill back-to-back, no cooldown)

overall prompt tok/s = prompt tokens / phase seconds (includes the 16 generated tokens and overhead of each iteration); iter median / first / last = library prompt tok/s per iteration.

| model | iterations | prompt tokens | seconds | overall prompt tok/s | iter median prompt tok/s | first iter prompt tok/s | last iter prompt tok/s | last vs first | prefill median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 47 | 473431 | 61.1 | 7750.6 | 8811.2 | 8825.6 | 8815.9 | -0.1% | 8757.5 | 0→0 (max 0) | 0d02202ec08edfed |
| Qwen3-4B-4bit | 21 | 211533 | 61.5 | 3441.4 | 3724.2 | 3729.1 | 3718.5 | -0.3% | 3720.4 | 0→0 (max 0) | 49d1a6036bfc4348 |

## Mac power (fanctl; host clock)

450 samples, median spacing 1.14 s; the first 3 s of each phase are skipped. "System" = Mac body (SMC PSTR minus USB-port output), so devices charged from this Mac are excluded.

| phase | window s | samples | GPU W | CPU W | DRAM W | ANE W | Mac body W | PSTR W | USB out W |
|---|---|---|---|---|---|---|---|---|---|
| idle | 30.3 | 24 | 0.00 | 13.66 | 0.54 | 0.00 | 28.46 | 29.39 | 0.93 |
| sustain Qwen3-1.7B-4bit | 100.4 | 86 | 28.09 | 10.36 | 7.62 | 0.00 | 80.81 | 81.78 | 0.97 |
| sustain Qwen3-4B-4bit | 100.8 | 87 | 31.63 | 4.98 | 8.60 | 0.00 | 79.82 | 80.80 | 0.98 |
| sustain_prefill Qwen3-1.7B-4bit | 61.1 | 52 | 76.01 | 9.22 | 3.21 | 0.00 | 126.80 | 127.76 | 0.96 |
| sustain_prefill Qwen3-4B-4bit | 61.5 | 52 | 88.66 | 4.18 | 2.63 | 0.00 | 134.21 | 135.16 | 0.95 |

| phase | tokens/s (overall) | per | GPU W | net GPU W | J/token GPU gross | J/token GPU net | system W | J/token system gross | J/token system net |
|---|---|---|---|---|---|---|---|---|---|
| sustain Qwen3-1.7B-4bit | 295.8 | generated token | 28.09 | 28.09 | 0.0950 | 0.0950 | 80.81 | 0.2731 | 0.1769 |
| sustain Qwen3-4B-4bit | 144.8 | generated token | 31.63 | 31.63 | 0.2184 | 0.2184 | 79.82 | 0.5511 | 0.3546 |
| sustain_prefill Qwen3-1.7B-4bit | 7750.6 | prompt token | 76.01 | 76.01 | 0.0098 | 0.0098 | 126.80 | 0.0164 | 0.0127 |
| sustain_prefill Qwen3-4B-4bit | 3441.4 | prompt token | 88.66 | 88.66 | 0.0258 | 0.0258 | 134.21 | 0.0390 | 0.0307 |
