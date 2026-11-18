#!/usr/bin/env python3
# Part of mlx-device-bench.
"""Sample this Mac's CPU / GPU / ANE / DRAM / system power at ~1 Hz.

    python3 bench/mac-power-sample.py <output.jsonl>

REQUIRES the `fanctl` CLI on PATH (a separate local tool; it is not part of
this repository). Only `fanctl status` is ever called -- never `set`, `auto`
or `daemon` -- so fan control is not touched. `fanctl watch` is not used
because its output is block-buffered when piped.

Each `fanctl status` call reports CPU/GPU/ANE/DRAM power over a ~1 s
measurement window ending at the call, plus instantaneous SMC system power
(PSTR), USB-port output power and "Mac body" power (PSTR minus USB out, i.e.
excluding devices charged from this Mac). One JSON line is appended per call:

    {"hostTime": <epoch s at end of call>, "sampleMid": <hostTime - window/2>,
     "windowS", "cpuW", "gpuW", "aneW", "dramW", "pstrW", "usbOutW", "macBodyW"}

Stops cleanly on SIGTERM / SIGINT; a failed call is logged to stderr and
sampling continues. POWER_INTERVAL (default 1) sets the target period.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

POWER_RE = re.compile(
    r"Power:\s*CPU\s+([\d.]+)\s*W\s*\|\s*GPU\s+([\d.]+)\s*W\s*\|\s*ANE\s+([\d.]+)\s*W\s*\|\s*DRAM\s+([\d.]+)\s*W")
WINDOW_RE = re.compile(r"([\d.]+)s measurement window")
PSTR_RE = re.compile(r"System \(SMC PSTR\):\s*([\d.]+)\s*W")
USB_RE = re.compile(r"USB ports out[^:]*:\s*([\d.]+)\s*W")
BODY_RE = re.compile(r"Mac body[^:]*:\s*([\d.]+)\s*W")

_stop = False


def _request_stop(signum, frame):
    global _stop
    _stop = True


def log(message):
    print(f"[mac-power-sample {time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def parse(text):
    power = POWER_RE.search(text)
    if not power:
        return None
    record = {
        "cpuW": float(power.group(1)),
        "gpuW": float(power.group(2)),
        "aneW": float(power.group(3)),
        "dramW": float(power.group(4)),
    }
    for key, pattern in (("windowS", WINDOW_RE), ("pstrW", PSTR_RE),
                         ("usbOutW", USB_RE), ("macBodyW", BODY_RE)):
        match = pattern.search(text)
        if match:
            record[key] = float(match.group(1))
    return record


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 64
    tool = shutil.which("fanctl")
    if tool is None:
        log("fanctl not found on PATH; this sampler requires the fanctl CLI")
        return 69

    output_path = sys.argv[1]
    interval = float(os.environ.get("POWER_INTERVAL", "1"))
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    written = 0
    log(f"sampling every {interval:g}s -> {os.path.basename(output_path)}")
    with open(output_path, "a", encoding="utf-8") as output:
        while not _stop:
            started = time.monotonic()
            try:
                completed = subprocess.run([tool, "status"], capture_output=True, timeout=10)
                now = time.time()
                record = parse(completed.stdout.decode("utf-8", "replace"))
                if record is None:
                    log("no power line in fanctl output (still sampling?)")
                else:
                    record["hostTime"] = now
                    record["sampleMid"] = now - record.get("windowS", 1.0) / 2
                    output.write(json.dumps(record, sort_keys=True) + "\n")
                    output.flush()
                    written += 1
            except Exception as error:  # keep sampling through transient failures
                log(f"fanctl status failed: {error}")
            while not _stop and time.monotonic() - started < interval:
                time.sleep(0.05)

    log(f"stopped, {written} sample(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
