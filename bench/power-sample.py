#!/usr/bin/env python3
# Part of mlx-device-bench.
"""Sample an iPhone/iPad's power telemetry over USB while a benchmark runs.

    DEVICE_ID=<udid> python3 bench/power-sample.py <output.jsonl>

Polls `idevicediagnostics ioregentry AppleSmartBattery` (libimobiledevice)
every POWER_INTERVAL seconds (default 5). The registry snapshot itself only
refreshes about every 20 s, so a JSON line is appended only when
SystemLoadAccumulatorCount changed since the last line written.

Only the whitelisted fields below are written (no serial numbers or other
identifiers). Power values are in mW; `Accumulated*` / `*AccumulatorCount`
advance by one sample per second, so the mean power between two lines is
delta(Accumulated*) / delta(*AccumulatorCount). `UpdateTime` is the phone's
epoch time of the snapshot (same clock as the benchmark's `ts`).

Stops cleanly on SIGTERM / SIGINT. A failed poll is logged to stderr and
sampling continues.
"""

import json
import os
import plistlib
import shutil
import signal
import subprocess
import sys
import time

TOP_LEVEL_FIELDS = [
    "UpdateTime",
    "Voltage",
    "InstantAmperage",
    "CurrentCapacity",
    "IsCharging",
    "ExternalConnected",
    "Temperature",
]
TELEMETRY_FIELDS = [
    "SystemLoad",
    "SystemPowerIn",
    "BatteryPower",
    "AccumulatedSystemLoad",
    "SystemLoadAccumulatorCount",
    "AccumulatedSystemPowerIn",
    "SystemPowerInAccumulatorCount",
    "AccumulatedBatteryPower",
    "BatteryPowerAccumulatorCount",
]
SCALAR_TYPES = (int, float, bool, str)

_stop = False


def _request_stop(signum, frame):
    global _stop
    _stop = True


def log(message):
    stamp = time.strftime("%H:%M:%S")
    print(f"[power-sample {stamp}] {message}", file=sys.stderr, flush=True)


def find_tool():
    tool = shutil.which("idevicediagnostics")
    if tool:
        return tool
    for candidate in ("/opt/homebrew/bin/idevicediagnostics", "/usr/local/bin/idevicediagnostics"):
        if os.access(candidate, os.X_OK):
            return candidate
    return None


def poll(tool, device_id):
    command = [tool]
    if device_id:
        command += ["-u", device_id]
    command += ["ioregentry", "AppleSmartBattery"]
    completed = subprocess.run(command, capture_output=True, timeout=20)
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip().splitlines()
        raise RuntimeError(f"idevicediagnostics exited {completed.returncode}: "
                           f"{detail[-1] if detail else 'no output'}")
    registry = plistlib.loads(completed.stdout).get("IORegistry")
    if not isinstance(registry, dict):
        raise RuntimeError("no IORegistry dictionary in output")
    return registry


def whitelist(registry):
    record = {"hostTime": time.time()}
    for key in TOP_LEVEL_FIELDS:
        value = registry.get(key)
        if isinstance(value, SCALAR_TYPES):
            record[key] = value
    telemetry = registry.get("PowerTelemetryData")
    if isinstance(telemetry, dict):
        for key in TELEMETRY_FIELDS:
            value = telemetry.get(key)
            if isinstance(value, SCALAR_TYPES):
                record[key] = value
    return record


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 64

    output_path = sys.argv[1]
    device_id = os.environ.get("DEVICE_ID", "")
    interval = float(os.environ.get("POWER_INTERVAL", "5"))

    tool = find_tool()
    if tool is None:
        log("idevicediagnostics not found (brew install libimobiledevice)")
        return 69

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    last_count = None
    written = 0
    log(f"sampling every {interval:g}s -> {os.path.basename(output_path)}")

    with open(output_path, "a", encoding="utf-8") as output:
        while not _stop:
            try:
                record = whitelist(poll(tool, device_id))
                count = record.get("SystemLoadAccumulatorCount")
                if count is not None and count != last_count:
                    output.write(json.dumps(record, sort_keys=True) + "\n")
                    output.flush()
                    last_count = count
                    written += 1
            except Exception as error:  # keep sampling through transient failures
                message = str(error)
                if device_id:
                    message = message.replace(device_id, "<DEVICE>")
                log(f"poll failed: {message}")

            deadline = time.monotonic() + interval
            while not _stop and time.monotonic() < deadline:
                time.sleep(0.2)

    log(f"stopped, {written} snapshot(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
