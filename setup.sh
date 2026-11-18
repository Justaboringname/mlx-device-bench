#!/usr/bin/env bash
# Prepare ./upstream: a checkout of ml-explore/mlx-swift-examples at the pinned
# commit, with the benchmark patch applied.
#
#   ./setup.sh
#
# Steps:
#   1. clone https://github.com/ml-explore/mlx-swift-examples into ./upstream
#      (or reuse an existing clean clone) and check out the pinned commit;
#   2. copy patch/Benchmark.swift to upstream/Applications/LLMEval/;
#   3. apply patch/llmeval-bench.patch (LLMEvalApp.swift + project.pbxproj).
#
# Idempotent: running it again on an already-patched ./upstream does nothing.
# It refuses to touch an ./upstream with any other local changes.
#
# Environment overrides:
#   UPSTREAM_URL  where to clone from (default: the GitHub repository; any git
#                 URL or local path that contains the pinned commit works)
#   UPSTREAM      target directory (default: ./upstream)
set -euo pipefail

PINNED_COMMIT=ef1084dd5692611a8758b24b07efdad5404ac3ce
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM="${UPSTREAM:-$ROOT/upstream}"
UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/ml-explore/mlx-swift-examples.git}"
PATCH="$ROOT/patch/llmeval-bench.patch"
BENCH_SWIFT="$ROOT/patch/Benchmark.swift"
TARGET_SWIFT="Applications/LLMEval/Benchmark.swift"

say() { echo "setup: $*"; }
die() { echo "setup: error: $*" >&2; exit 1; }

[[ -f "$PATCH" && -f "$BENCH_SWIFT" ]] || die "patch files missing under $ROOT/patch"

if [[ ! -e "$UPSTREAM" ]]; then
    say "cloning $UPSTREAM_URL into $UPSTREAM"
    git clone --quiet "$UPSTREAM_URL" "$UPSTREAM"
fi
[[ -d "$UPSTREAM/.git" ]] || die "$UPSTREAM exists but is not a git checkout"

git_up() { git -C "$UPSTREAM" "$@"; }

PATCHED_FILES=(Applications/LLMEval/LLMEvalApp.swift mlx-swift-examples.xcodeproj/project.pbxproj)

# True only if ./upstream is exactly: pinned commit + Benchmark.swift + this patch, nothing else.
already_patched() {
    [[ "$(git_up rev-parse HEAD)" == "$PINNED_COMMIT" ]] || return 1
    cmp -s "$BENCH_SWIFT" "$UPSTREAM/$TARGET_SWIFT" || return 1
    cmp -s "$PATCH" <(git_up diff --no-color "$PINNED_COMMIT" -- "${PATCHED_FILES[@]}") || return 1
    local others
    others="$(git_up status --porcelain --untracked-files=all -- . \
        ":(exclude)$TARGET_SWIFT" ":(exclude)${PATCHED_FILES[0]}" ":(exclude)${PATCHED_FILES[1]}")"
    [[ -z "$others" ]]
}

if already_patched; then
    say "$UPSTREAM is already at $PINNED_COMMIT with the benchmark patch applied; nothing to do"
    exit 0
fi

if [[ -n "$(git_up status --porcelain --untracked-files=all)" ]]; then
    die "$UPSTREAM has local changes that are not exactly this patch; refusing to modify it (commit, stash or remove them first)"
fi

if [[ "$(git_up rev-parse HEAD)" != "$PINNED_COMMIT" ]]; then
    if ! git_up cat-file -e "$PINNED_COMMIT^{commit}" 2>/dev/null; then
        say "fetching $PINNED_COMMIT"
        git_up fetch --quiet origin "$PINNED_COMMIT" || git_up fetch --quiet origin
    fi
    say "checking out $PINNED_COMMIT"
    git_up -c advice.detachedHead=false checkout --quiet "$PINNED_COMMIT"
fi

git_up apply --check "$PATCH" || die "patch does not apply cleanly to $PINNED_COMMIT"
cp "$BENCH_SWIFT" "$UPSTREAM/$TARGET_SWIFT"
git_up apply "$PATCH"
say "patched $UPSTREAM at $PINNED_COMMIT"
say "next: DEVELOPMENT_TEAM=<team id> bench/run-mac.sh <label> ...   (see README)"
