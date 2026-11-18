# Benchmark summary

Source: `iphone18promax-cooled.log`, session `a5546f5f`, 96 events

## Device

iOS V64AP (iPhone19,3) · cpu n/a · Version 27.2.1 (Build 24B156) · RAM 11 GiB · GPU applegpu_g19p · build RELEASE · lowPowerMode False · thermalState 0 · availableMemory 6.43 GB

Args: models mlx-community/Qwen3-1.7B-4bit, mlx-community/Qwen3-4B-4bit; runs 3; cooldown 10 s; idle 90 s; sustain 100 s; sustain-prefill 0 s; phase cooldown 60 s; MLX env {}

## Throughput (measured runs; warm-up excluded from median)

| model | workload | metric | measured | median | spread | prompt tok | TTFT median s | peak GB | thermal | stop | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | gen | tokensPerSecond | 99.9 / 99.8 / 99.8 | 99.8 | 0.13% | 48 | 0.0857 | 1.05 | 0→0 | length | 799ec6e941b85604 |
| Qwen3-1.7B-4bit | prefill | promptTokensPerSecond | 2009.6 / 2009.0 / 2009.7 | 2009.6 | 0.03% | 10073 | 5.0126 | 2.65 | 0→0 | length | 0d02202ec08edfed |
| Qwen3-4B-4bit | gen | tokensPerSecond | 44.7 / 44.7 / 44.7 | 44.7 | 0.06% | 48 | 0.1368 | 2.36 | 0→0 | length | c563528899d11540 |
| Qwen3-4B-4bit | prefill | promptTokensPerSecond | 817.1 / 816.0 / 815.8 | 816.0 | 0.16% | 10073 | 12.3445 | 4.27 | 0→0 | length | 49d1a6036bfc4348 |

## Model load

model files GB = downloaded snapshot size (download_progress totalUnitCount); gen × size = gen median tok/s × that size, in GB/s.

| model | resolve s | load s | total s | parameters | model files GB | gen × size GB/s | model peak GB | parameter dtypes | logits dtype | ok |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 9.51 | 0.352 | 9.86 | 1720574976 | 0.98 | 98 | 2.65 | bfloat16 507, uint32 197 | bfloat16 | True |
| Qwen3-4B-4bit | 24.47 | 0.683 | 25.15 | 4022468096 | 2.28 | 102 | 4.27 | bfloat16 651, uint32 253 | bfloat16 | True |

## Idle

95.9 s idle, thermalState 0→0

## Phase cooldowns (`--bench-phase-cooldown`)

| model | before | seconds | thermal before→after |
|---|---|---|---|
| Qwen3-1.7B-4bit | sustain | 61.7 | 0→0 |
| Qwen3-4B-4bit | model | 61.9 | 0→0 |
| Qwen3-4B-4bit | sustain | 61.5 | 0→0 |

## Sustain (gen back-to-back, no cooldown)

overall tok/s = generated tokens / phase seconds (includes per-iteration prompt processing); iter median / first / last = library decode tok/s per iteration.

| model | iterations | tokens | seconds | overall tok/s | iter median tok/s | first iter tok/s | last iter tok/s | last vs first | gen median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 38 | 9728 | 100.1 | 97.2 | 99.3 | 99.2 | 99.4 | 0.2% | 99.8 | 0→0 (max 0) | 799ec6e941b85604 |
| Qwen3-4B-4bit | 18 | 4608 | 105.2 | 43.8 | 44.7 | 44.7 | 44.7 | 0.1% | 44.7 | 0→0 (max 0) | c563528899d11540 |

## Power (SystemLoad = what the device consumes)

40 snapshots, 39 intervals, median snapshot spacing 20 s, median host-minus-UpdateTime lag 2.7 s.

| phase | window s | whole intervals | SystemLoad samples | covered s | SystemLoad W | SystemPowerIn W | BatteryPower W | charging |
|---|---|---|---|---|---|---|---|---|
| idle | 95.9 | 4 | 80 | 80 | 0.65 | 0.65 | n/a | no (no BatteryPower samples); external input = 100% of SystemLoad; IsCharging False; battery 80% |
| sustain Qwen3-1.7B-4bit | 100.1 | 4 | 80 | 80 | 11.29 | 11.21 | n/a | no (no BatteryPower samples); external input = 99% of SystemLoad; IsCharging False; battery 80% |
| sustain Qwen3-4B-4bit | 105.2 | 4 | 80 | 80 | 11.68 | 11.49 | n/a | no (no BatteryPower samples); external input = 98% of SystemLoad; IsCharging False; battery 80% |

| phase | phase W | idle W | net W | tokens/s (overall) | per | J/token gross | J/token net |
|---|---|---|---|---|---|---|---|
| sustain Qwen3-1.7B-4bit | 11.29 | 0.65 | 10.64 | 97.2 | generated token | 0.1161 | 0.1094 |
| sustain Qwen3-4B-4bit | 11.68 | 0.65 | 11.02 | 43.8 | generated token | 0.2665 | 0.2516 |
