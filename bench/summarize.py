#!/usr/bin/env python3
# Part of mlx-device-bench.
"""Summarize an LLMEval benchmark log as Markdown.

    python3 bench/summarize.py <bench log> [power jsonl] [--session=<id>]

<bench log> is any text containing `BENCH {json}` lines (a results/*.log
or the app's Documents/bench-results.jsonl). If it holds several sessions, the
session of the last `device` event is used unless --session is given.

[power jsonl] is the output of bench/power-sample.py. Mean power for a phase
is computed only from registry-snapshot intervals that lie wholly inside the
phase window ([idle_start, idle_end] or a model's [sustain_start,
sustain_end]): sum(delta Accumulated*) / sum(delta *AccumulatorCount), each
quantity over its own accumulator. Phase windows come from the events' `ts`
and snapshots from `UpdateTime`; both are the phone's clock.
"""

import json
import statistics
import sys

POWER_QUANTITIES = [
    ("SystemLoad", "AccumulatedSystemLoad", "SystemLoadAccumulatorCount"),
    ("SystemPowerIn", "AccumulatedSystemPowerIn", "SystemPowerInAccumulatorCount"),
    ("BatteryPower", "AccumulatedBatteryPower", "BatteryPowerAccumulatorCount"),
]


# ---------------------------------------------------------------- parsing


def read_events(path):
    events, skipped = [], 0
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            index = line.find("BENCH {")
            if index < 0:
                continue
            try:
                events.append(json.loads(line[index + len("BENCH "):]))
            except json.JSONDecodeError:
                skipped += 1
    return events, skipped


def select_session(events, wanted):
    if wanted:
        return [e for e in events if e.get("session") == wanted], wanted
    devices = [e for e in events if e.get("event") == "device"]
    if not devices:
        return events, None
    session = devices[-1].get("session")
    return [e for e in events if e.get("session") == session], session


def read_power(path):
    """Return ("ios", snapshots) for bench/power-sample.py output or
    ("mac", samples) for bench/mac-power-sample.py output."""
    records, mac = [], []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record.get("UpdateTime"), (int, float)):
                records.append(record)
            elif isinstance(record.get("gpuW"), (int, float)) and "hostTime" in record:
                mac.append(record)
    if mac and not records:
        return "mac", mac
    records.sort(key=lambda r: (r["UpdateTime"], r.get("SystemLoadAccumulatorCount", 0)))
    unique, seen = [], set()
    for record in records:
        key = (record["UpdateTime"], record.get("SystemLoadAccumulatorCount"))
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return "ios", unique


# ---------------------------------------------------------------- formatting


def fmt(value, digits=1):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def gb(value):
    return "n/a" if value is None else f"{value / 1e9:.2f}"


def median(values):
    values = [v for v in values if isinstance(v, (int, float))]
    return statistics.median(values) if values else None


def spread(values):
    values = [v for v in values if isinstance(v, (int, float))]
    mid = median(values)
    if not values or not mid:
        return None
    return 100.0 * (max(values) - min(values)) / mid


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def ordered(items):
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


# ---------------------------------------------------------------- sections


def device_section(events):
    device = next((e for e in events if e.get("event") == "device"), None)
    if device is None:
        return "## Device\n\n(no `device` event)"
    args = device.get("args", {})
    memory = device.get("physicalMemory")
    parts = [
        f"{device.get('platform', '?')} {device.get('hwModel', '?')} ({device.get('hwMachine', '?')})",
        device.get("cpuBrand") or "cpu n/a",
        device.get("osVersion", "?"),
        f"RAM {memory / 2**30:.0f} GiB" if isinstance(memory, (int, float)) else "RAM n/a",
        f"GPU {device.get('gpuArchitecture', '?')}",
        f"build {device.get('buildConfiguration', '?')}",
        f"lowPowerMode {device.get('lowPowerMode')}",
        f"thermalState {device.get('thermalState')}",
    ]
    if "availableMemoryBytes" in device:
        parts.append(f"availableMemory {gb(device['availableMemoryBytes'])} GB")
    def arg(key):  # "n/a" when the build that wrote the log did not have this option
        return f"{args[key]} s" if key in args else "n/a (not recorded by this build)"

    argline = (
        f"models {', '.join(args.get('models', []))}; runs {args.get('runs')}; "
        f"cooldown {arg('cooldownSeconds')}; idle {arg('idleSeconds')}; "
        f"sustain {arg('sustainSeconds')}; "
        f"sustain-prefill {arg('sustainPrefillSeconds')}; "
        f"phase cooldown {arg('phaseCooldownSeconds')}"
    )
    argline += ("; MLX env " + (json.dumps(device["mlxEnvironment"], sort_keys=True)
                                if "mlxEnvironment" in device else "n/a (not recorded by this build)"))
    return "## Device\n\n" + " · ".join(str(p) for p in parts) + "\n\nArgs: " + argline


def throughput_section(events):
    runs = [e for e in events if e.get("event") == "run"]
    rows = []
    for model in ordered(r.get("model") for r in runs):
        for workload, metric in (("gen", "tokensPerSecond"), ("prefill", "promptTokensPerSecond")):
            selected = [r for r in runs if r.get("model") == model and r.get("workload") == workload]
            if not selected:
                continue
            measured = [r for r in selected if not r.get("warmup")]
            values = [r.get(metric) for r in measured]
            hashes = ordered(r.get("outputHash") for r in selected)
            stops = ordered(r.get("stopReasonEffective", r.get("stopReason")) for r in selected)
            thermal = ordered(f"{r.get('thermalStateBefore')}→{r.get('thermalStateAfter')}" for r in selected)
            prompt_tokens = ordered(r.get("promptTokenCount") for r in measured)
            rows.append([
                model.split("/")[-1],
                workload,
                metric,
                " / ".join(fmt(v) for v in values) or "none",
                fmt(median(values)),
                (fmt(spread(values), 2) + "%") if spread(values) is not None else "n/a",
                ", ".join(str(p) for p in prompt_tokens),
                fmt(median([r.get("ttftWallSeconds") for r in measured]), 4),
                gb(max((r.get("peakMemoryBytes", 0) for r in selected), default=None)),
                ", ".join(thermal),
                ", ".join(str(s) for s in stops),
                ", ".join(str(h) for h in hashes) + (" **MISMATCH**" if len(hashes) > 1 else ""),
            ])
    header = ["model", "workload", "metric", "measured", "median", "spread", "prompt tok",
              "TTFT median s", "peak GB", "thermal", "stop", "outputHash"]
    if not rows:
        return "## Throughput\n\n(no gen/prefill runs)"
    return "## Throughput (measured runs; warm-up excluded from median)\n\n" + table(header, rows)


def load_section(events):
    loads = {e.get("model"): e for e in events if e.get("event") == "model_loaded"}
    done = {e.get("model"): e for e in events if e.get("event") == "model_done"}
    rows = []
    for model in ordered([e.get("model") for e in events if e.get("event") == "model_load_start"]):
        load, finished = loads.get(model, {}), done.get(model, {})
        # Size of the downloaded model snapshot (weights + config/tokenizer files).
        size = max((e.get("totalUnitCount", 0) for e in events if e.get("event") == "download_progress"
                    and e.get("model") == model), default=0) or None
        gen = median([e.get("tokensPerSecond") for e in events if e.get("event") == "run"
                      and e.get("model") == model and e.get("workload") == "gen"
                      and not e.get("warmup")])
        rows.append([
            model.split("/")[-1],
            fmt(load.get("resolveSeconds"), 2),
            fmt(load.get("loadSeconds"), 3),
            fmt(load.get("totalLoadSeconds"), 2),
            load.get("numParameters", "n/a"),
            gb(size),
            (f"{gen * size / 1e9:.0f}" if gen and size else "n/a"),
            gb(finished.get("peakMemoryBytes")),
            ", ".join(f"{k} {v}" for k, v in sorted(load.get("parameterDtypes", {}).items())) or "n/a",
            load.get("logitsDtype", "n/a"),
            finished.get("ok", "n/a"),
        ])
    if not rows:
        return ""
    return ("## Model load\n\nmodel files GB = downloaded snapshot size (download_progress "
            "totalUnitCount); gen × size = gen median tok/s × that size, in GB/s.\n\n" + table(
                ["model", "resolve s", "load s", "total s", "parameters", "model files GB",
                 "gen × size GB/s", "model peak GB", "parameter dtypes", "logits dtype", "ok"], rows))


def sustain_section(events):
    ends = [e for e in events if e.get("event") == "sustain_end"]
    if not ends:
        return ""
    rows = []
    for end in ends:
        model = end.get("model")
        sustain_runs = [e for e in events if e.get("event") == "run"
                        and e.get("model") == model and e.get("workload") == "sustain"]
        first, last = end.get("firstIterationTokensPerSecond"), end.get("lastIterationTokensPerSecond")
        change = (100.0 * (last - first) / first) if first and last is not None else None
        gen_median = median([e.get("tokensPerSecond") for e in events if e.get("event") == "run"
                             and e.get("model") == model and e.get("workload") == "gen"
                             and not e.get("warmup")])
        max_thermal = max([r.get("thermalStateAfter", 0) for r in sustain_runs]
                          + [end.get("thermalStateAfter", 0)])
        rows.append([
            model.split("/")[-1],
            end.get("iterations"),
            end.get("totalGeneratedTokens"),
            fmt(end.get("totalSeconds"), 1),
            fmt(end.get("overallTokensPerSecond")),
            fmt(median([r.get("tokensPerSecond") for r in sustain_runs])),
            fmt(first),
            fmt(last),
            (fmt(change, 1) + "%") if change is not None else "n/a",
            fmt(gen_median),
            f"{end.get('thermalStateBefore')}→{end.get('thermalStateAfter')} (max {max_thermal})",
            ", ".join(ordered(r.get("outputHash") for r in sustain_runs)),
        ])
    return ("## Sustain (gen back-to-back, no cooldown)\n\n"
            "overall tok/s = generated tokens / phase seconds (includes per-iteration prompt "
            "processing); iter median / first / last = library decode tok/s per iteration.\n\n"
            + table(["model", "iterations", "tokens", "seconds", "overall tok/s", "iter median tok/s",
                     "first iter tok/s", "last iter tok/s", "last vs first", "gen median (ref)",
                     "thermal", "outputHash"], rows))


def sustain_prefill_section(events):
    ends = [e for e in events if e.get("event") == "sustain_prefill_end"]
    if not ends:
        return ""
    rows = []
    for end in ends:
        model = end.get("model")
        phase_runs = [e for e in events if e.get("event") == "run"
                      and e.get("model") == model and e.get("workload") == "sustain_prefill"]
        first = end.get("firstIterationPromptTokensPerSecond")
        last = end.get("lastIterationPromptTokensPerSecond")
        change = (100.0 * (last - first) / first) if first and last is not None else None
        prefill_median = median([e.get("promptTokensPerSecond") for e in events
                                 if e.get("event") == "run" and e.get("model") == model
                                 and e.get("workload") == "prefill" and not e.get("warmup")])
        max_thermal = max([r.get("thermalStateAfter", 0) for r in phase_runs]
                          + [end.get("thermalStateAfter", 0)])
        rows.append([
            model.split("/")[-1],
            end.get("iterations"),
            end.get("totalPromptTokens"),
            fmt(end.get("totalSeconds"), 1),
            fmt(end.get("overallPromptTokensPerSecond")),
            fmt(median([r.get("promptTokensPerSecond") for r in phase_runs])),
            fmt(first),
            fmt(last),
            (fmt(change, 1) + "%") if change is not None else "n/a",
            fmt(prefill_median),
            f"{end.get('thermalStateBefore')}→{end.get('thermalStateAfter')} (max {max_thermal})",
            ", ".join(ordered(r.get("outputHash") for r in phase_runs)),
        ])
    return ("## Sustain prefill (prefill back-to-back, no cooldown)\n\n"
            "overall prompt tok/s = prompt tokens / phase seconds (includes the 16 generated "
            "tokens and overhead of each iteration); iter median / first / last = library prompt "
            "tok/s per iteration.\n\n"
            + table(["model", "iterations", "prompt tokens", "seconds", "overall prompt tok/s",
                     "iter median prompt tok/s", "first iter prompt tok/s", "last iter prompt tok/s",
                     "last vs first",
                     "prefill median (ref)", "thermal", "outputHash"], rows))


def phase_cooldown_section(events):
    starts = [e for e in events if e.get("event") == "phase_cooldown_start"]
    if not starts:
        return ""
    rows = []
    for start in starts:
        end = next((e for e in events if e.get("event") == "phase_cooldown_end"
                    and e.get("model") == start.get("model") and e.get("before") == start.get("before")
                    and e.get("ts", 0) >= start.get("ts", 0)), {})
        rows.append([
            (start.get("model") or "?").split("/")[-1],
            start.get("before", "?"),
            fmt(end.get("seconds"), 1) if end else "no end event",
            f"{start.get('thermalState')}→{end.get('thermalState', '?')}",
        ])
    return "## Phase cooldowns (`--bench-phase-cooldown`)\n\n" + table(
        ["model", "before", "seconds", "thermal before→after"], rows)


def idle_section(events):
    start = next((e for e in events if e.get("event") == "idle_start"), None)
    end = next((e for e in events if e.get("event") == "idle_end"), None)
    if not start or not end:
        return ""
    return (f"## Idle\n\n{fmt(end.get('seconds'), 1)} s idle, thermalState "
            f"{start.get('thermalState')}→{end.get('thermalState')}")


def errors_section(events):
    errors = [e for e in events if e.get("event") == "error"]
    if not errors:
        return ""
    lines = [f"- {e.get('model', '?')} @ {e.get('where', '?')}: {e.get('message', '')}" for e in errors]
    return "## Errors\n\n" + "\n".join(lines)


# ---------------------------------------------------------------- power


def intervals(records):
    out = []
    for a, b in zip(records, records[1:]):
        if b["UpdateTime"] > a["UpdateTime"]:
            out.append((a, b))
    return out


def phase_power(pairs, start, end):
    inside = [(a, b) for a, b in pairs if a["UpdateTime"] >= start and b["UpdateTime"] <= end]
    result = {"intervals": len(inside),
              "covered": sum(b["UpdateTime"] - a["UpdateTime"] for a, b in inside),
              "charging_flags": ordered(r.get("IsCharging") for pair in inside for r in pair),
              "battery_levels": ordered(r.get("CurrentCapacity") for pair in inside for r in pair
                                        if r.get("CurrentCapacity") is not None)}
    for name, acc_key, count_key in POWER_QUANTITIES:
        total_acc = total_count = 0
        for a, b in inside:
            if not all(k in r for r in (a, b) for k in (acc_key, count_key)):
                continue
            d_acc, d_count = b[acc_key] - a[acc_key], b[count_key] - a[count_key]
            if d_count <= 0:  # no samples or counter reset
                continue
            total_acc += d_acc
            total_count += d_count
        result[name] = (total_acc / total_count) if total_count > 0 else None
        result[name + "Samples"] = total_count
    return result


def watts(milliwatts, digits=2):
    return "n/a" if milliwatts is None else f"{milliwatts / 1000:.{digits}f}"


def find_phases(events):
    """[(label, end_event or None for idle, start_ts, end_ts, rate_key, unit)]"""
    phases = []
    idle_start = next((e for e in events if e.get("event") == "idle_start"), None)
    idle_end = next((e for e in events if e.get("event") == "idle_end"), None)
    if idle_start and idle_end:
        phases.append(("idle", None, idle_start["ts"], idle_end["ts"], None, None))
    for name, rate_key, unit in (("sustain", "overallTokensPerSecond", "generated token"),
                                 ("sustain_prefill", "overallPromptTokensPerSecond", "prompt token")):
        for start in [e for e in events if e.get("event") == f"{name}_start"]:
            end = next((e for e in events if e.get("event") == f"{name}_end"
                        and e.get("model") == start.get("model")
                        and e.get("ts", 0) >= start["ts"]), None)
            if end:
                label = f"{name} {start['model'].split('/')[-1]}"
                phases.append((label, end, start["ts"], end["ts"], rate_key, unit))
    return phases


def power_section(events, records, power_path):
    if not records:
        return f"## Power\n\nNo usable snapshots in {power_path}."
    pairs = intervals(records)
    cadence = median([b["UpdateTime"] - a["UpdateTime"] for a, b in pairs])
    lag = median([r["hostTime"] - r["UpdateTime"] for r in records if "hostTime" in r])
    device = next((e for e in events if e.get("event") == "device"), {})

    phases = [(label, end, start_ts, end_ts) for label, end, start_ts, end_ts, _, _
              in find_phases(events)]
    rate_info = {label: (rate_key, unit) for label, _, _, _, rate_key, unit in find_phases(events)}

    lines = ["## Power (SystemLoad = what the device consumes)", ""]
    lines.append(f"{len(records)} snapshots, {len(pairs)} intervals, median snapshot spacing "
                 f"{fmt(cadence, 1)} s, median host-minus-UpdateTime lag {fmt(lag, 1)} s.")
    if device.get("platform") not in (None, "iOS"):
        lines.append(f"\n**Warning:** the log's platform is {device.get('platform')}; "
                     "phase times and power snapshots are only comparable on the same device clock.")
    if not phases:
        lines.append("\nNo idle or sustain phases in the log, so no phase power can be computed.")
        return "\n".join(lines)

    rows, results = [], {}
    for label, _, start, end in phases:
        stats = phase_power(pairs, start, end)
        results[label] = stats
        if stats["intervals"] == 0:
            rows.append([label, fmt(end - start, 1), 0, 0, 0,
                         "no whole snapshot interval in phase", "", "", ""])
            continue
        battery = stats["BatteryPower"]
        flags, power_in, load = stats["charging_flags"], stats["SystemPowerIn"], stats["SystemLoad"]
        if battery is None and flags and all(f is False for f in flags) and power_in and load:
            charging = (f"no (no BatteryPower samples); external input = "
                        f"{100 * power_in / load:.0f}% of SystemLoad")
        elif battery is None:
            charging = "unknown (no BatteryPower samples)"
        elif battery > 0:
            charging = f"yes (battery +{watts(battery)} W)"
        else:
            charging = f"no (battery {watts(battery)} W)"
        rows.append([
            label, fmt(end - start, 1), stats["intervals"], stats["SystemLoadSamples"],
            fmt(float(stats["covered"]), 0), watts(stats["SystemLoad"]),
            watts(stats["SystemPowerIn"]), watts(battery),
            f"{charging}; IsCharging {', '.join(str(f) for f in stats['charging_flags'])}; "
            f"battery {', '.join(f'{b}%' for b in stats['battery_levels']) or 'n/a'}",
        ])
    lines += ["", table(["phase", "window s", "whole intervals", "SystemLoad samples", "covered s",
                         "SystemLoad W", "SystemPowerIn W", "BatteryPower W", "charging"], rows)]

    idle = results.get("idle", {}).get("SystemLoad")
    energy_rows = []
    for label, end_event, _, _ in phases:
        if end_event is None:
            continue
        rate_key, unit = rate_info[label]
        load = results[label]["SystemLoad"]
        rate = end_event.get(rate_key)
        if load is None:
            energy_rows.append([label, "no whole snapshot interval in phase", "", "", fmt(rate),
                                unit, "", ""])
            continue
        gross_w = load / 1000
        net_w = (load - idle) / 1000 if idle is not None else None
        energy_rows.append([
            label,
            f"{gross_w:.2f}",
            watts(idle) if idle is not None else "no idle interval",
            f"{net_w:.2f}" if net_w is not None else "n/a",
            fmt(rate),
            unit,
            f"{gross_w / rate:.4f}" if rate else "n/a",
            f"{net_w / rate:.4f}" if (rate and net_w is not None) else "n/a",
        ])
    if energy_rows:
        lines += ["", table(["phase", "phase W", "idle W", "net W", "tokens/s (overall)", "per",
                             "J/token gross", "J/token net"], energy_rows)]
    return "\n".join(lines)


MAC_SKIP_SECONDS = 3.0
MAC_FIELDS = [("gpuW", "GPU W"), ("cpuW", "CPU W"), ("dramW", "DRAM W"), ("aneW", "ANE W"),
              ("macBodyW", "Mac body W"), ("pstrW", "PSTR W"), ("usbOutW", "USB out W")]


def mac_phase_means(samples, start, end):
    inside = [s for s in samples if start + MAC_SKIP_SECONDS <= s.get("sampleMid", s["hostTime"]) <= end]
    means = {"n": len(inside)}
    for key, _ in MAC_FIELDS:
        values = [s[key] for s in inside if isinstance(s.get(key), (int, float))]
        means[key] = statistics.mean(values) if values else None
    return means


def mac_power_section(events, samples, power_path):
    if not samples:
        return f"## Mac power\n\nNo usable samples in {power_path}."
    samples = sorted(samples, key=lambda s: s.get("sampleMid", s["hostTime"]))
    spacing = median([b["hostTime"] - a["hostTime"] for a, b in zip(samples, samples[1:])])
    phases = find_phases(events)
    lines = ["## Mac power (fanctl; host clock)", "",
             f"{len(samples)} samples, median spacing {fmt(spacing, 2)} s; the first "
             f"{MAC_SKIP_SECONDS:g} s of each phase are skipped. \"System\" = Mac body "
             "(SMC PSTR minus USB-port output), so devices charged from this Mac are excluded."]
    if not phases:
        lines.append("\nNo idle or sustain phases in the log, so no phase power can be computed.")
        return "\n".join(lines)

    results, rows = {}, []
    for label, _, start, end, _, _ in phases:
        means = mac_phase_means(samples, start, end)
        results[label] = means
        if means["n"] == 0:
            rows.append([label, fmt(end - start, 1), 0, "no samples in phase"] + [""] * (len(MAC_FIELDS) - 1))
            continue
        rows.append([label, fmt(end - start, 1), means["n"]]
                    + [fmt(means[key], 2) for key, _ in MAC_FIELDS])
    lines += ["", table(["phase", "window s", "samples"] + [title for _, title in MAC_FIELDS], rows)]

    idle = results.get("idle")
    idle_ok = idle is not None and idle["n"] > 0
    energy_rows = []
    for label, end_event, _, _, rate_key, unit in phases:
        if end_event is None:
            continue
        means, rate = results[label], end_event.get(rate_key)
        if means["n"] == 0 or not rate:
            energy_rows.append([label, "no samples in phase" if means["n"] == 0 else "no rate"]
                               + [""] * 8)
            continue
        gpu, body = means["gpuW"], means["macBodyW"]
        net_gpu = gpu - idle["gpuW"] if idle_ok and gpu is not None and idle["gpuW"] is not None else None
        net_body = (body - idle["macBodyW"]
                    if idle_ok and body is not None and idle["macBodyW"] is not None else None)

        def per_token(value):
            return f"{value / rate:.4f}" if value is not None else "n/a"

        energy_rows.append([
            label, fmt(rate), unit,
            fmt(gpu, 2), fmt(net_gpu, 2) if net_gpu is not None else "no idle",
            per_token(gpu), per_token(net_gpu),
            fmt(body, 2), per_token(body), per_token(net_body),
        ])
    if energy_rows:
        lines += ["", table(["phase", "tokens/s (overall)", "per", "GPU W", "net GPU W",
                             "J/token GPU gross", "J/token GPU net", "system W",
                             "J/token system gross", "J/token system net"], energy_rows)]
    return "\n".join(lines)


# ---------------------------------------------------------------- main


def main(argv):
    session_arg = None
    paths = []
    for arg in argv[1:]:
        if arg.startswith("--session="):
            session_arg = arg.split("=", 1)[1]
        else:
            paths.append(arg)
    if not 1 <= len(paths) <= 2:
        print(__doc__, file=sys.stderr)
        return 64

    events, skipped = read_events(paths[0])
    events, session = select_session(events, session_arg)
    if not events:
        print(f"no BENCH events found in {paths[0]}", file=sys.stderr)
        return 1

    sections = [f"# Benchmark summary\n\nSource: `{paths[0].split('/')[-1]}`, session `{session}`, "
                f"{len(events)} events" + (f", {skipped} unparsable lines skipped" if skipped else "")
                + (", **no `done` event (run incomplete)**"
                   if not any(e.get("event") == "done" for e in events) else "")]
    sections += [device_section(events), throughput_section(events), load_section(events),
                 idle_section(events), phase_cooldown_section(events), sustain_section(events),
                 sustain_prefill_section(events),
                 errors_section(events)]
    if len(paths) == 2:
        kind, records = read_power(paths[1])
        name = paths[1].split("/")[-1]
        if kind == "mac":
            sections.append(mac_power_section(events, records, name))
        else:
            sections.append(power_section(events, records, name))
    print("\n\n".join(s for s in sections if s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
