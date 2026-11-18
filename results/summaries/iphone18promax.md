# Benchmark summary

Source: `iphone18promax.log`, session `3a117a97`, 88 events

## Device

iOS V64AP (iPhone19,3) · cpu n/a · Version 27.2.1 (Build 24B156) · RAM 11 GiB · GPU applegpu_g19p · build RELEASE · lowPowerMode False · thermalState 0 · availableMemory 6.43 GB

Args: models mlx-community/Qwen3-1.7B-4bit, mlx-community/Qwen3-4B-4bit; runs 3; cooldown 10 s; idle 60 s; sustain 100 s; sustain-prefill n/a (not recorded by this build); phase cooldown n/a (not recorded by this build); MLX env n/a (not recorded by this build)

## Throughput (measured runs; warm-up excluded from median)

| model | workload | metric | measured | median | spread | prompt tok | TTFT median s | peak GB | thermal | stop | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | gen | tokensPerSecond | 98.0 / 99.7 / 99.7 | 99.7 | 1.77% | 48 | 0.0884 | 1.05 | 0→0 | length | 799ec6e941b85604 |
| Qwen3-1.7B-4bit | prefill | promptTokensPerSecond | 2009.5 / 2006.7 / 2008.4 | 2008.4 | 0.14% | 10073 | 5.0156 | 2.65 | 0→0 | length | 0d02202ec08edfed |
| Qwen3-4B-4bit | gen | tokensPerSecond | 44.7 / 44.4 / 44.6 | 44.6 | 0.58% | 48 | 0.1399 | 2.36 | 0→0 | length | c563528899d11540 |
| Qwen3-4B-4bit | prefill | promptTokensPerSecond | 790.4 / 801.0 / 806.9 | 801.0 | 2.07% | 10073 | 12.5754 | 4.27 | 0→0, 1→1 | length | 49d1a6036bfc4348 |

## Model load

model files GB = downloaded snapshot size (download_progress totalUnitCount); gen × size = gen median tok/s × that size, in GB/s.

| model | resolve s | load s | total s | parameters | model files GB | gen × size GB/s | model peak GB | parameter dtypes | logits dtype | ok |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 12.57 | 0.367 | 12.94 | 1720574976 | 0.98 | 98 | 2.65 | n/a | n/a | True |
| Qwen3-4B-4bit | 21.71 | 0.688 | 22.40 | 4022468096 | 2.28 | 102 | 4.27 | n/a | n/a | True |

## Idle

60.1 s idle, thermalState 0→0

## Sustain (gen back-to-back, no cooldown)

overall tok/s = generated tokens / phase seconds (includes per-iteration prompt processing); iter median / first / last = library decode tok/s per iteration.

| model | iterations | tokens | seconds | overall tok/s | iter median tok/s | first iter tok/s | last iter tok/s | last vs first | gen median (ref) | thermal | outputHash |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B-4bit | 38 | 9728 | 100.7 | 96.6 | 99.2 | 99.2 | 99.1 | -0.1% | 99.7 | 0→0 (max 0) | 799ec6e941b85604 |
| Qwen3-4B-4bit | 16 | 4096 | 101.6 | 40.3 | 39.5 | 44.5 | 39.5 | -11.4% | 44.6 | 1→2 (max 2) | c563528899d11540 |

## Power (SystemLoad = what the device consumes)

32 snapshots, 31 intervals, median snapshot spacing 20 s, median host-minus-UpdateTime lag 2.6 s.

| phase | window s | whole intervals | SystemLoad samples | covered s | SystemLoad W | SystemPowerIn W | BatteryPower W | charging |
|---|---|---|---|---|---|---|---|---|
| idle | 60.1 | 2 | 40 | 40 | 1.91 | 1.91 | n/a | no (no BatteryPower samples); external input = 100% of SystemLoad; IsCharging False; battery 80% |
| sustain Qwen3-1.7B-4bit | 100.7 | 6 | 92 | 91 | 11.86 | 11.52 | n/a | no (no BatteryPower samples); external input = 97% of SystemLoad; IsCharging False; battery 80% |
| sustain Qwen3-4B-4bit | 101.6 | 4 | 80 | 80 | 11.03 | 10.66 | n/a | no (no BatteryPower samples); external input = 97% of SystemLoad; IsCharging False; battery 80% |

| phase | phase W | idle W | net W | tokens/s (overall) | per | J/token gross | J/token net |
|---|---|---|---|---|---|---|---|
| sustain Qwen3-1.7B-4bit | 11.86 | 1.91 | 9.95 | 96.6 | generated token | 0.1228 | 0.1030 |
| sustain Qwen3-4B-4bit | 11.03 | 1.91 | 9.12 | 40.3 | generated token | 0.2735 | 0.2262 |
