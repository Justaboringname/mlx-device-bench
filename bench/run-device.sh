#!/usr/bin/env bash
# Part of mlx-device-bench. Runs the LLMEval benchmark patch (see ../setup.sh).
#
# Build LLMEval (Release) for a connected iPhone/iPad, install it and launch the
# headless benchmark with its stdout bridged back through devicectl.
#
#   DEVELOPMENT_TEAM=<team id> DEVICE_ID=<device UDID> bench/run-device.sh <label> [--bench-models=...] [--bench-runs=N] [--bench-cooldown=S] [--bench-idle=S] [--bench-sustain=S] [--bench-sustain-prefill=S] [--bench-phase-cooldown=S]
#
# Raw benchmark output (not the build log) is teed to results/<label>.log,
# with the team id, device id and $HOME redacted. Set SKIP_BUILD=1 to skip the
# build and install steps. Set CODE_SIGN_ENTITLEMENTS=<absolute path> to
# override the entitlements file.
#
# POWER=1 also samples the device's power telemetry over USB (bench/power-sample.py,
# needs libimobiledevice) into results/<label>.power.jsonl for the whole run,
# plus POWER_TAIL seconds (default 25) afterwards so the last ~20 s registry
# snapshot is captured. Summarize with: bench/summarize.py <log> <power jsonl>.
#
# UPSTREAM=<dir> (default ./upstream), PROJECT=<path> and RESULTS_DIR=<dir> (default
# ./results) override the locations used.
#
# The device must stay unlocked with the app in the foreground for the whole run.
# The jsonl copy stays in the app container at Documents/bench-results.jsonl.
set -euo pipefail

usage() {
    echo "usage: DEVELOPMENT_TEAM=<team id> DEVICE_ID=<device UDID> $0 <label> [extra --bench-* args]" >&2
    exit 64
}

[[ $# -ge 1 ]] || usage
: "${DEVELOPMENT_TEAM:?set DEVELOPMENT_TEAM to your signing team id}"
: "${DEVICE_ID:?set DEVICE_ID to the device UDID (used by devicectl, xcodebuild and idevicediagnostics)}"

LABEL="$1"
shift
[[ "$LABEL" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "label must match [A-Za-z0-9._-]+" >&2; exit 64; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${UPSTREAM:-$ROOT/upstream}"
PROJECT="${PROJECT:-$UPSTREAM/mlx-swift-examples.xcodeproj}"
RESULTS="${RESULTS_DIR:-$ROOT/results}"
[[ -d "$PROJECT" ]] || { echo "Xcode project not found at $PROJECT (run ./setup.sh, or set UPSTREAM / PROJECT)" >&2; exit 1; }
LOG="$RESULTS/$LABEL.log"
mkdir -p "$RESULTS"

XCODE_ARGS=(
    -project "$PROJECT"
    -scheme LLMEval
    -configuration Release
    -destination "id=$DEVICE_ID"
    -allowProvisioningUpdates
    -skipMacroValidation
    -skipPackagePluginValidation
    "DEVELOPMENT_TEAM=$DEVELOPMENT_TEAM"
)
if [[ -n "${CODE_SIGN_ENTITLEMENTS:-}" ]]; then
    XCODE_ARGS+=("CODE_SIGN_ENTITLEMENTS=$CODE_SIGN_ENTITLEMENTS")
fi

BUILD_DIR="$(xcodebuild "${XCODE_ARGS[@]}" -showBuildSettings 2>/dev/null \
    | awk -F' = ' '/^ *TARGET_BUILD_DIR = / { print $2; exit }')"
APP="$BUILD_DIR/LLMEval.app"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
    echo "==> building (Release, device)" >&2
    xcodebuild "${XCODE_ARGS[@]}" -quiet build
    [[ -d "$APP" ]] || { echo "built app not found at $APP" >&2; exit 1; }
    echo "==> installing" >&2
    xcrun devicectl device install app --device "$DEVICE_ID" "$APP" >&2
fi

[[ -f "$APP/Info.plist" ]] || { echo "built app not found at $APP" >&2; exit 1; }
BUNDLE_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Info.plist")"

redact() {
    sed -l -e "s|$DEVELOPMENT_TEAM|<TEAM>|g" -e "s|$DEVICE_ID|<DEVICE>|g" -e "s|$HOME|~|g" \
        -e "s|${USER:-$(id -un)}|<USER>|g"
}

SAMPLER_PID=""
stop_sampler() {
    if [[ -n "$SAMPLER_PID" ]] && kill -0 "$SAMPLER_PID" 2>/dev/null; then
        kill -TERM "$SAMPLER_PID" 2>/dev/null || true
        wait "$SAMPLER_PID" 2>/dev/null || true
    fi
    SAMPLER_PID=""
}
trap stop_sampler EXIT
trap 'exit 130' INT TERM

if [[ "${POWER:-0}" == "1" ]]; then
    POWER_LOG="$RESULTS/$LABEL.power.jsonl"
    : > "$POWER_LOG"
    echo "==> power sampling, log: $RESULTS/$LABEL.power.jsonl" >&2
    DEVICE_ID="$DEVICE_ID" python3 "$ROOT/bench/power-sample.py" "$POWER_LOG" &
    SAMPLER_PID=$!
fi

echo "==> launching benchmark, log: $RESULTS/$LABEL.log" >&2
xcrun devicectl device process launch \
    --device "$DEVICE_ID" \
    --console \
    --terminate-existing \
    "$BUNDLE_ID" \
    -- --bench "$@" 2>&1 | redact | tee "$LOG"

if [[ -n "$SAMPLER_PID" ]]; then
    echo "==> waiting ${POWER_TAIL:-25}s for the last power snapshot" >&2
    sleep "${POWER_TAIL:-25}"
    stop_sampler
fi
