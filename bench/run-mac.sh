#!/usr/bin/env bash
# Part of mlx-device-bench. Runs the LLMEval benchmark patch (see ../setup.sh).
#
# Build LLMEval (Release, macOS arm64) and run the headless benchmark on this Mac.
#
#   DEVELOPMENT_TEAM=<team id> bench/run-mac.sh <label> [--bench-models=...] [--bench-runs=N] [--bench-cooldown=S] [--bench-idle=S] [--bench-sustain=S] [--bench-sustain-prefill=S] [--bench-phase-cooldown=S]
#
# Raw benchmark output (not the build log) is teed to results/<label>.log,
# with the team id and $HOME redacted. Optional environment:
#   UPSTREAM=<dir>             patched mlx-swift-examples checkout (default ./upstream)
#   PROJECT=<path>             .xcodeproj to build (default $UPSTREAM/mlx-swift-examples.xcodeproj)
#   RESULTS_DIR=<dir>          where logs go (default ./results)
#   SKIP_BUILD=1               reuse the last build
#   CODE_SIGN_ENTITLEMENTS=..  absolute path of an entitlements file to sign with
#   DERIVED_DATA=<dir>         build into / run from this -derivedDataPath
#   EXTRA_XCODE_ARGS=<lines>   extra xcodebuild arguments, ONE PER LINE (so values
#                              may contain spaces), e.g. a build-setting override
#   POWER=1                    sample CPU/GPU/system power at ~1 Hz with
#                              bench/mac-power-sample.py (needs the `fanctl` CLI)
#                              into results/<label>.power.jsonl
set -euo pipefail

usage() {
    echo "usage: DEVELOPMENT_TEAM=<team id> $0 <label> [extra --bench-* args]" >&2
    exit 64
}

[[ $# -ge 1 ]] || usage
: "${DEVELOPMENT_TEAM:?set DEVELOPMENT_TEAM to your signing team id}"

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
    -destination 'platform=macOS,arch=arm64'
    -allowProvisioningUpdates
    -skipMacroValidation
    -skipPackagePluginValidation
    "DEVELOPMENT_TEAM=$DEVELOPMENT_TEAM"
)
if [[ -n "${CODE_SIGN_ENTITLEMENTS:-}" ]]; then
    XCODE_ARGS+=("CODE_SIGN_ENTITLEMENTS=$CODE_SIGN_ENTITLEMENTS")
fi
if [[ -n "${DERIVED_DATA:-}" ]]; then
    XCODE_ARGS+=(-derivedDataPath "$DERIVED_DATA")
fi
if [[ -n "${EXTRA_XCODE_ARGS:-}" ]]; then
    while IFS= read -r extra; do
        [[ -n "$extra" ]] && XCODE_ARGS+=("$extra")
    done <<< "$EXTRA_XCODE_ARGS"
fi

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
    echo "==> building (Release, macOS)" >&2
    xcodebuild "${XCODE_ARGS[@]}" -quiet build
fi

BUILD_DIR="$(xcodebuild "${XCODE_ARGS[@]}" -showBuildSettings 2>/dev/null \
    | awk -F' = ' '/^ *TARGET_BUILD_DIR = / { print $2; exit }')"
APP="$BUILD_DIR/LLMEval.app"
BIN="$APP/Contents/MacOS/LLMEval"
[[ -x "$BIN" ]] || { echo "built app not found at $APP" >&2; exit 1; }
echo "==> app: $APP" >&2

redact() {
    # Team id, home directory and the login name (which also appears in temp/derived-data paths).
    sed -l -e "s|$DEVELOPMENT_TEAM|<TEAM>|g" -e "s|$HOME|~|g" -e "s|${USER:-$(id -un)}|<USER>|g"
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
    python3 "$ROOT/bench/mac-power-sample.py" "$POWER_LOG" &
    SAMPLER_PID=$!
fi

echo "==> running benchmark, log: $RESULTS/$LABEL.log" >&2
"$BIN" --bench "$@" 2>&1 | redact | tee "$LOG"

if [[ -n "$SAMPLER_PID" ]]; then
    sleep 2
    stop_sampler
fi
