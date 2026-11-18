# mlx-device-bench

English | [简体中文](README.zh-CN.md)

This repository adds a headless benchmark mode to the LLMEval example app from Apple's [mlx-swift-examples](https://github.com/ml-explore/mlx-swift-examples) and uses it to run the same fixed, greedy workload on a Mac Studio (M5 Max) and an iPhone 18 Pro Max, reading power while the workload runs. With Qwen3-1.7B-4bit and Qwen3-4B-4bit, the Mac generates text 3.1–3.3× faster and processes a 10,073-token prompt 4.4–4.6× faster than the phone, and both devices produce identical output hashes. During 100 s of continuous generation the whole phone draws 11.0–11.9 W; on the Mac, switching off MLX's neural-accelerator matmul path (NAX) cuts prompt processing to 0.28–0.31× of normal speed (depending on the metric), while per-iteration decode speed during sustained generation changes by about 2 % (short-run medians are noisier, up to -9 % for 4B).

All numbers in the tables are computed from the files in [`results/`](results) with `python3 bench/summarize.py <log> [power.jsonl]` (its output for every run is in [`results/summaries/`](results/summaries)). Ratios, products and per-token energies are arithmetic on that output; the quiet-idle baseline in section 2 is computed directly from the Mac power file, as described there. Some statements rest on notes taken during the work that are not included in this repository: how the NAX switch was verified (build commands, binary symbols, stack samples), the process checks around the final Mac run, and the phone setup (case, cooler, brightness).

## 1. Mac vs iPhone

Medians of 3 measured runs after one warm-up run. "gen" = 256 generated tokens after a 48-token prompt; "prefill" = a 10,073-token prompt followed by 16 generated tokens. TTFT = wall time from the start of generation to the first text chunk. Peak memory = the MLX allocator's peak for the model (load + all runs), not the process's total memory.

| | Mac Studio (M5 Max) | iPhone run 1 | iPhone run 2 (cooled) |
|---|---|---|---|
| **Qwen3-1.7B-4bit** gen, tokens/s | 304.7 | 99.7 | 99.8 |
| prefill, prompt tokens/s | 8,757 | 2,008 | 2,010 |
| TTFT for the 10,073-token prompt, s | 1.15 | 5.02 | 5.01 |
| peak memory, GB | 2.94 | 2.65 | 2.65 |
| **Qwen3-4B-4bit** gen, tokens/s | 147.9 | 44.6 | 44.7 |
| prefill, prompt tokens/s | 3,720 | 801 | 816 |
| TTFT for the 10,073-token prompt, s | 2.71 | 12.58 | 12.34 |
| peak memory, GB | 4.42 | 4.27 | 4.27 |

Generation uses temperature 0 (greedy). Each build gave the same text in every run, and the output hashes (64-bit FNV-1a of the generated text) are identical on both devices: 1.7B gen `799ec6e941b85604`, 1.7B prefill `0d02202ec08edfed`, 4B gen `c563528899d11540`, 4B prefill `49d1a6036bfc4348`. The Mac column comes from a single session (see caveats).

Devices: Mac Studio (`Mac17,14`, Apple M5 Max, GPU `applegpu_g17s`), macOS 27.2.1 (Build 26B131); iPhone 18 Pro Max (`iPhone19,3` / `V64AP`, GPU `applegpu_g19p`), iOS 27.2.1 (Build 24B156).

## 2. Sustained load and power

After the short runs, each model generates the same 256-token reply back to back for 100 s ("sustain"). On the Mac a second phase then repeats the 10,073-token prefill back to back for 60 s ("sustain-prefill"). "Overall" tokens/s = tokens produced ÷ phase length, so it includes the prompt processing of every iteration. J/token = mean power over the phase ÷ overall tokens/s; "gross" uses the measured power, "net" subtracts the idle baseline measured at the start of the same run.

**The two devices are measured differently and the watts are not directly comparable.** iPhone figures are whole-device power: `SystemLoad`, an undocumented AppleSmartBattery field that we read as the total the phone consumes (SoC, memory, display, radios). Mac figures are GPU-only power, which excludes DRAM (7.6 W and 8.6 W during sustained decode of the 1.7B and 4B model), with whole-Mac power alongside ("system" = SMC system power minus USB-port output). The Mac is a Mac Studio, so "system" also excludes the external display, which has its own power supply.

### iPhone (whole device)

| | run 1 | run 2 (cooled) |
|---|---|---|
| idle baseline, W | 1.91 | 0.65 |
| **1.7B** sustain power, W | 11.86 | 11.29 |
| overall tokens/s | 96.6 | 97.2 |
| first → last iteration, tokens/s | 99.2 → 99.1 (-0.1 %) | 99.2 → 99.4 (0.2 %) |
| thermal state start → end (max) | 0→0 (0) | 0→0 (0) |
| J/token, gross / net | 0.123 / 0.103 | 0.116 / 0.109 |
| **4B** sustain power, W | 11.03 | 11.68 |
| overall tokens/s | 40.3 | 43.8 |
| first → last iteration, tokens/s | 44.5 → 39.5 (-11.4 %) | 44.7 → 44.7 (0.1 %) |
| thermal state start → end (max) | 1→2 (2) | 0→0 (0) |
| J/token, gross / net | 0.274 / 0.226 | 0.267 / 0.252 |

Thermal state is iOS's `ProcessInfo.thermalState` (0 nominal, 1 fair, 2 serious, 3 critical). The two phone runs differ in several ways at once:

| | run 1 | run 2 |
|---|---|---|
| phone case | on | off |
| external cooling | none | separately powered cooler |
| screen brightness | default | lowered by hand |
| pause before each sustained phase and between models | none | 60 s (`--bench-phase-cooldown=60`) |
| idle phase, requested / measured | 60 s / 60.1 s | 90 s / 95.9 s |
| app build | earlier build of `Benchmark.swift` (see caveats) | same events and options as the published `Benchmark.swift` |

In run 1 the 4B model's per-iteration speed went from 44.5 to 39.5 tokens/s (-11.4 %) over the 100 s while the thermal state rose to 2; in run 2 it stayed flat at thermal state 0. In both runs the phone was on USB power and not charging (battery level 80 %); external input covered 97–100 % of `SystemLoad`.

### Mac Studio, M5 Max (GPU only; DRAM and whole-Mac system power alongside)

| | Qwen3-1.7B-4bit | Qwen3-4B-4bit |
|---|---|---|
| sustain overall tokens/s | 295.8 | 144.8 |
| first → last iteration, tokens/s | 302.8 → 304.0 | 147.3 → 148.0 |
| GPU W / DRAM W / system W | 28.1 / 7.6 / 80.8 | 31.6 / 8.6 / 79.8 |
| J/token GPU, gross / net | 0.095 / 0.095 | 0.218 / 0.218 |
| J/token system, gross / net (net understated †) | 0.273 / 0.177 | 0.551 / 0.355 |
| J/token system, net with quiet-idle baseline ‡ | 0.235 | 0.474 |
| sustain-prefill overall prompt tokens/s | 7,751 | 3,441 |
| sustain-prefill GPU W / DRAM W / system W | 76.0 / 3.2 / 126.8 | 88.7 / 2.6 / 134.2 |
| sustain-prefill mJ per prompt token, GPU gross / net | 9.81 / 9.81 | 25.76 / 25.76 |
| sustain-prefill mJ per prompt token, system gross / net (net understated †) | 16.36 / 12.69 | 39.00 / 30.73 |
| sustain-prefill mJ per prompt token, system net with quiet-idle baseline ‡ | 14.92 | 35.75 |

Idle baseline in the same run (24 samples): GPU 0.00 W, system 28.5 W.

- † **Net system figures are understated.** An unrelated process ran a CPU burst during the first part of the idle phase: CPU 24–28 W until about 16 s into the phase. That inflates the whole-phase system baseline, which is the method used everywhere else.
- ‡ **Quiet-idle baseline.** This row uses the mean of the 11 idle samples with CPU power below 5 W, all taken 18 s or later into the phase, after the burst: 11.2 W. It is computed directly from `results/mac-m5max.power.jsonl`, not by summarize.py.

The GPU baseline is unaffected. Thermal state stayed at 0 throughout. The phones were not run with the sustain-prefill phase.

## 3. Ablation: MLX's neural-accelerator path on the Mac

MLX can route matrix multiplications, quantized matrix multiplications and attention through kernels that use the GPU's neural accelerators ("NAX" in the MLX source). It does so when `metal::is_nax_available()` in `backend/metal/device.h` accepts the GPU. Compiling MLX with `MLX_METAL_NO_NAX` defined makes that function return false, so the regular GPU kernels are used instead.

The function accepts the Mac's GPU (`applegpu_g17s`). By the same check it also accepts the iPhone's GPU (`applegpu_g19p`) on iOS 27.2.1 (Build 24B156), so the phone numbers above are presumably NAX-on as well. That is inferred from the source; it was not checked with symbols or stack samples on the phone.

The same benchmark (plus a 30 s idle phase, 100 s sustain and 60 s sustain-prefill) was run three times on the Mac, in the order NAX on, NAX off, NAX on. These three runs used an earlier revision of the patch that did not yet have `--bench-phase-cooldown` (not used in them). They also passed an extra `--bench-variant=nax-on` / `nax-off` label, which the argument parser ignores.

| model | metric | NAX on (1) | NAX off | NAX on (2) | off ÷ mean(on) | on(2) ÷ on(1) |
|---|---|---|---|---|---|---|
| 1.7B | gen median (short runs; noisy), tokens/s | 297.4 | 295.2 | 272.1 | 1.04 | 0.91 |
| 1.7B | prefill median (short runs), prompt tokens/s | 8,705 | 2,529 | 8,647 | 0.29 | 0.99 |
| 1.7B | sustain-prefill overall, prompt tokens/s | 7,741 | 2,386 | 7,706 | 0.31 | 1.00 |
| 1.7B | sustain-prefill per-iteration median, prompt tokens/s | 8,837 | 2,489 | 8,785 | 0.28 | 0.99 |
| 1.7B | sustain-prefill GPU W | 78.5 | 65.0 | 79.6 | | |
| 1.7B | sustain-prefill GPU mJ per prompt token (gross) | 10.15 | 27.24 | 10.33 | | |
| 1.7B | sustain decode, per-iteration median, tokens/s | 302.3 | 296.0 | 300.9 | 0.98 | 1.00 |
| 1.7B | sustain GPU W | 28.7 | 30.2 | 29.4 | | |
| 1.7B | sustain GPU J/token (gross) | 0.097 | 0.108 | 0.100 | | |
| 4B | gen median (short runs; noisy), tokens/s | 144.1 | 131.9 | 145.0 | 0.91 | 1.01 |
| 4B | prefill median (short runs), prompt tokens/s | 3,659 | 1,005 | 3,646 | 0.28 | 1.00 |
| 4B | sustain-prefill overall, prompt tokens/s | 3,355 | 1,004 | 3,369 | 0.30 | 1.00 |
| 4B | sustain-prefill per-iteration median, prompt tokens/s | 3,672 | 1,027 | 3,669 | 0.28 | 1.00 |
| 4B | sustain-prefill GPU W | 89.5 | 67.6 | 87.5 | | |
| 4B | sustain-prefill GPU mJ per prompt token (gross) | 26.67 | 67.32 | 25.96 | | |
| 4B | sustain decode, per-iteration median, tokens/s | 145.3 | 139.4 | 138.9 | 0.98 | 0.96 |
| 4B | sustain GPU W | 29.0 | 33.2 | 29.9 | | |
| 4B | sustain GPU J/token (gross) | 0.207 | 0.249 | 0.221 | | |

What the numbers show:

- **Prompt processing.**
  - With NAX off, prompt processing runs at 0.28–0.29× the NAX-on speed by the short-run prefill median and the per-iteration sustain-prefill median.
  - By the overall sustain-prefill rate it runs at 0.30–0.31×; that rate also contains each iteration's 16 generated tokens and fixed overhead.
  - The two NAX-on runs agree to within 0.7 % on these rows.
  - GPU power during sustained prefill is lower with NAX off: 65.0 W (1.7B) and 67.6 W (4B), against 78.5–79.6 W and 87.5–89.5 W with NAX on. So GPU energy per prompt token is 2.6–2.7× higher.
- **Decode.**
  - Per-iteration sustained decode with NAX off is 0.98× (1.7B, -1.9 %) and 0.98× (4B, -1.9 %) of the NAX-on mean.
  - The two NAX-on runs themselves differ by a factor of 1.00 (1.7B) and 0.96 (4B). For 1.7B the drop is larger than the gap between the two NAX-on runs. But with a single pair of NAX-on runs, and a 4.4 % gap between them for 4B, neither decode difference is resolved.
  - The short-run gen medians are noisier: on(2) ÷ on(1) is 0.91 for 1.7B, and the NAX-off 4B short runs spread by 10.7 % (gen) and 6.9 % (prefill).
  - During sustained decode the GPU drew 30.2 W (1.7B) and 33.2 W (4B) with NAX off, against 28.7–29.4 W and 29.0–29.9 W with NAX on.
- **Output.** With NAX off, the 256-token generated text differs from the NAX-on text (1.7B `189c3a9519c9b492`, 4B `cae902a5673ea4ef`), while the 16-token prefill output is identical. Each build is deterministic across its own runs.

How the switch was verified (from notes not included in this repository):

- The arm64 compile commands for `backend/metal/matmul.cpp`, `quantized.cpp` and `scaled_dot_product_attention.cpp` read their defines from a response file. In the NAX-off build that file contains every define of the normal build plus `-DMLX_METAL_NO_NAX=1`.
- The normal app binary contains 110 NAX-related host symbols (for example `qmm_nax`, `get_qmm_nax_kernel`, `get_steel_attention_nax_kernel`) and 88 `_nax` kernel-name strings; the NAX-off binary contains none.
- Stack samples taken during the sustain-prefill phase of short smoke runs (Qwen3-0.6B-4bit) show `qmm_nax` and `get_steel_attention_nax_kernel` in the normal build, and `qmm` and `get_steel_attention_kernel` in the NAX-off build. These samples are from the smoke runs, not from the three runs in the table.

**Limits.**

- Decode differences of a few percent are not resolved by these three runs.
- **Interference:**
  - The first NAX-on run overlapped iPhone run 1, which was driven from the same Mac over USB.
  - During the second NAX-on run another program briefly compiled code, and an unrelated process was using a lot of CPU at its start.
  - No interference was observed during the NAX-off run, although its short runs were the noisiest.
- **USB-port output:** about 16 W of USB-port output (power the Mac supplied to other devices) was present in all three ablation runs: 16.3, 15.7 and 15.7 W during idle, against 0.9 W in the final Mac run. It is excluded from "system" and does not affect GPU figures.

## 4. An observation (inference, not a measurement)

Multiplying the median generation speed by the size of the downloaded model files gives similar numbers for both models on each device: within 13 % of each other on the Mac and 4 % on the iPhone in these runs.

| | model files, GB | Mac: gen × size, GB/s | iPhone run 1 | iPhone run 2 |
|---|---|---|---|---|
| Qwen3-1.7B-4bit | 0.98 | 299 | 98 | 98 |
| Qwen3-4B-4bit | 2.28 | 337 | 102 | 102 |

The file size is the snapshot size reported while downloading the model (`download_progress.totalUnitCount`, as recorded in the logs), and is dominated by the 4-bit weights. A similar product for both models is what one would expect if each generated token requires reading all the weights from memory once, i.e. if decoding is limited by memory bandwidth rather than by arithmetic. This benchmark did not measure memory bandwidth directly.

## 5. Method

**Workloads.** System message "You are a helpful assistant", chat template with `enable_thinking: false`, `GenerateParameters(maxTokens: N, temperature: 0)` (greedy):

- `gen`: user prompt "Write a detailed story of at least 1000 words about a lighthouse keeper who finds a message in a bottle." (48 tokens with the template), `maxTokens` 256.
- `prefill`: the `LongPrompt.md` file bundled with LLMEval (10,073 tokens with the template), `maxTokens` 16.

**Sequence per run.**

1. Optional idle phase (`--bench-idle`), with nothing loaded.
2. For each model:
   - download/load exactly as LLMEval does;
   - for each workload, one warm-up run, then `--bench-runs` (3) measured runs, each preceded by a 10 s cooldown;
   - then the optional sustained phases (`--bench-sustain`, `--bench-sustain-prefill`), optionally preceded by `--bench-phase-cooldown` pauses.

Each event is one `BENCH {json}` line on stdout and in `Documents/bench-results.jsonl` inside the app.

**Fields** (the `run` event):

- `promptTokenCount`, `generationTokenCount`, `promptTime`, `generateTime`, `promptTokensPerSecond`, `tokensPerSecond`: taken from MLX's own `GenerateCompletionInfo`.
- `ttftWallSeconds`: wall time from the `generate` call (which performs the whole prompt prefill) to the first non-empty text chunk.
- `peakMemoryBytes`: the MLX allocator peak, reset before each run.
- `thermalStateBefore` / `thermalStateAfter`.
- `outputHash`: a 64-bit FNV-1a hash of the generated text.
- `stopReason` / `stopReasonEffective` (see caveats).
- `elapsedInPhase`: present on sustained runs.

Other events: `device`, `model_load_start`, `download_progress`, `model_loaded` (including parameter dtypes and the dtype of a 1-token forward pass), `sustain_start/_end`, `sustain_prefill_start/_end`, `phase_cooldown_start/_end`, `idle_start/_end`, `model_done`, `error` and `done`.

**iPhone power.**

- `bench/power-sample.py` polls `idevicediagnostics ioregentry AppleSmartBattery` ([libimobiledevice](https://libimobiledevice.org)) over USB every 5 s and keeps a whitelist of fields from `PowerTelemetryData`.
- The registry snapshot refreshes about every 20 s, but its accumulators (`AccumulatedSystemLoad`, `SystemLoadAccumulatorCount`, …) gain one sample per second. The mean power between two snapshots is therefore ΔAccumulatedSystemLoad ÷ ΔSystemLoadAccumulatorCount.
- A phase's power is computed only from snapshot intervals that lie wholly inside it; phase times and snapshot times are both on the phone's clock. The power window can therefore be shorter than the phase (here 80–91 s of each ~100 s sustain phase), while J/token divides by the rate over the whole phase.
- `SystemLoad` and `SystemPowerIn` are undocumented fields. We read `SystemLoad` as what the phone consumes and `SystemPowerIn` as what arrives from USB.

**Mac power.**

- `bench/mac-power-sample.py` calls [`fanctl`](https://github.com/Justaboringname/fanctl) `status` about once per second.
- Each call reports CPU, GPU, ANE and DRAM power over a ~1 s window, plus SMC system power (PSTR) and USB-port output power.
- "System" in this README = PSTR minus USB-port output.
- The first 3 s of each phase are skipped. A sample counts if the midpoint of its ~1 s window lies in the phase.

**Versions.**

| component | version |
|---|---|
| mlx-swift-examples | commit `ef1084d` |
| mlx-swift | 0.31.4 (MLX core 0.31.1) |
| mlx-swift-lm | 3.31.3 |
| Xcode | 27.2 (27B52) |
| macOS | 27.2.1 (Build 26B131) |
| iOS | 27.2.1 (Build 24B156) |
| Mac build configuration | Release |

At runtime each model's parameter tensors are bfloat16, plus uint32 tensors that pack the 4-bit weights, and the logits are bfloat16. No `MLX_*` environment variables were set (MLX enables TF32 by default). These fields are recorded in every log except iPhone run 1, which predates them.

## 6. Caveats

- **One run per phone condition.** The two iPhone runs differ in several ways at once (table in section 2). Run 1's idle baseline (1.91 W) had probably not settled. Run 2's was 0.65 W, but its idle phase overran the 90 s target by 5.9 s for an unknown reason. Net figures inherit that uncertainty.
- **Phone run 1 was produced by an earlier build.** It used an earlier build of `Benchmark.swift` than the one published:
  - it had no sustain-prefill or phase-cooldown options;
  - it did not record MLX environment variables or parameter/logits dtypes;
  - it did not run the dtype-probe forward pass after loading.

  Its workloads are the same; its idle phase was 60 s. Neither phone run includes the sustain-prefill phase.
- **Phone run 1 overlapped a Mac run.** It was made while the same Mac was running the first NAX-on ablation run (and driving the phone over USB). The phone's numbers are measured on the phone itself; whether the overlap affected them was not checked.
- **The Mac final run.** Its numbers are in `results/summaries/mac-m5max.md`; the process checks described here are not recorded in the repository.
  - The run was started only after two consecutive checks found no compiler, Xcode build, device tool or other process above 50 % CPU, and the same check ran every 30 s during it.
  - One check, in the first seconds of the idle phase, found an unrelated process above 50 % CPU. That is the CPU burst described in section 2. It affects the net system figures but not the GPU figures.
  - No other check during the run found anything.
  - An earlier attempt the same day, with more interference, was discarded.
- **The Mac column comes from one session.** The NAX-on ablation sessions on the same Mac the same day, which had interference, measured short-run gen medians up to 11 % lower.
- **Old pinned MLX.** These numbers are for mlx-swift 0.31.4 / MLX core 0.31.1 as pinned by `ef1084d`; newer MLX releases may behave differently.
- **`stopReason` mislabel.** In mlx-swift-lm 3.31.3, `generateLoopTask` checks the token count on an un-advanced copy of the iterator, so a stop at `maxTokens` is reported as `cancelled`. The benchmark records the library's value as `stopReason` and adds `stopReasonEffective` = "length" when the library says "cancelled" and `generationTokenCount >= maxTokens`. Every run in `results/` reached its token limit.
- **Log edits.** The run scripts redact the team id, device id, home directory and user name automatically at capture time. Two stderr lines were removed by hand afterwards:
  - a sandbox warning containing a local temporary path, from `results/ablation/nax-off.log`;
  - a system log line ("Successfully load keyboard extensions", with local time and process id), from `results/iphone18promax-cooled.log`.

  No other edits were made.
- **Signing.** A free personal Apple developer team works:
  - the bundle id becomes `mlx.LLMEval<team id>`;
  - provisioning profiles expire after 7 days;
  - in this setup, the profile included the `increased-memory-limit` entitlement that LLMEval requests.
- **Not comparable across devices:** iPhone watts are whole-device; Mac watts are GPU-only, or whole-Mac without the display.

## 7. Reproduce

Prerequisites:

- An Apple-silicon Mac with Xcode 27.2. The Metal shader compiler is a separate component: `xcodebuild -downloadComponent MetalToolchain`.
- A signing team id; a free personal team works.
- Python 3.
- For iPhone power: `brew install libimobiledevice` and a paired iPhone. For Mac power: the `fanctl` CLI on `PATH`.

Run from the repository root. `RESULTS_DIR=runs` keeps new logs out of `results/`; `runs/` is gitignored.

```bash
./setup.sh                                   # clones mlx-swift-examples at ef1084d into ./upstream and applies the patch

# Mac (about 8 min with the models cached; the first run downloads 3.3 GB)
DEVELOPMENT_TEAM=<team id> POWER=1 RESULTS_DIR=runs bench/run-mac.sh my-mac \
  --bench-idle=30 --bench-sustain=100 --bench-sustain-prefill=60

# iPhone (keep it unlocked with the app in the foreground; about 13 min for run 2's settings)
DEVELOPMENT_TEAM=<team id> DEVICE_ID=<device UDID> POWER=1 RESULTS_DIR=runs bench/run-device.sh my-iphone \
  --bench-idle=90 --bench-sustain=100 --bench-phase-cooldown=60

python3 bench/summarize.py runs/my-mac.log runs/my-mac.power.jsonl
```

To reproduce the NAX-off build, build into a separate derived-data directory with the define added to every C/C++ target:

```bash
DERIVED_DATA=<separate derived-data directory> \
EXTRA_XCODE_ARGS='GCC_PREPROCESSOR_DEFINITIONS=$(inherited) MLX_METAL_NO_NAX=1' \
DEVELOPMENT_TEAM=<team id> POWER=1 RESULTS_DIR=runs bench/run-mac.sh my-mac-nax-off \
  --bench-idle=30 --bench-sustain=100 --bench-sustain-prefill=60
```

`bench/tests/` holds synthetic logs and power files with known answers:

- `python3 bench/summarize.py bench/tests/fake-bench.log bench/tests/fake-power.jsonl` exercises the iPhone power path. It should report 3.00 W idle, 8.00 W sustain and 0.1600 / 0.1000 J/token.
- `python3 bench/summarize.py bench/tests/fake-mac-bench.log bench/tests/fake-mac-power.jsonl` exercises the Mac power path. It should report 21.00 W GPU in sustain and 0.2100 / 0.2000 J/token (GPU, gross / net), and 0.0610 / 0.0600 J per prompt token in sustain-prefill.

## License

MIT, see [LICENSE](LICENSE). `patch/llmeval-bench.patch` modifies, and `patch/Benchmark.swift` contains code adapted from, [mlx-swift-examples](https://github.com/ml-explore/mlx-swift-examples) (MIT License, Copyright (c) 2024 ml-explore; LLMEval source files © 2024–2025 Apple Inc.). Those portions remain under that license; its full text is in [LICENSE-mlx-swift-examples](LICENSE-mlx-swift-examples). MLX and the Qwen3 models are under their own licenses and are not included here.
