// Part of mlx-device-bench (MIT License, see LICENSE). Not part of upstream mlx-swift-examples.
//
// load() below is adapted from mlx-swift-examples
// Applications/LLMEval/ViewModels/LLMEvaluator.swift (performLoad()),
// Copyright © 2025 Apple Inc., used under the MIT License
// (Copyright (c) 2024 ml-explore; full text in LICENSE-mlx-swift-examples).
//
// Headless benchmark mode for LLMEval. Launch the app with `--bench` to run a
// fixed, greedy (temperature 0) workload against one or more models and emit
// one `BENCH {json}` line per event on stdout. The same lines are appended to
// `Documents/bench-results.jsonl` in the app container and shown on screen.
//
// Arguments:
//   --bench                         enable benchmark mode
//   --bench-models=<id>,<id>,...    Hugging Face model ids
//                                   (default: mlx-community/Qwen3-1.7B-4bit,mlx-community/Qwen3-4B-4bit)
//   --bench-runs=<n>                measured runs per workload (default 3)
//   --bench-cooldown=<seconds>      sleep before every measured run (default 10)
//   --bench-idle=<seconds>          idle phase before the first model load (default 0 = off)
//   --bench-sustain=<seconds>       per-model sustained `gen` phase (default 0 = off)
//   --bench-sustain-prefill=<seconds>  per-model sustained `prefill` phase after
//                                   the sustain phase (default 0 = off)
//   --bench-phase-cooldown=<seconds>  sleep before each sustained phase and
//                                   between models, to let the device cool
//                                   (default 0 = off)
//
// Workloads (per model): 1 warm-up run + N measured runs each of
//   gen      short prompt, maxTokens 256  -> decode speed
//   prefill  bundled LongPrompt.md, maxTokens 16 -> prompt-processing speed
// then, if --bench-sustain > 0, `gen` back-to-back with no cooldown until the
// phase has lasted that long (`run` events with "workload":"sustain"). The idle
// and sustain phases are long enough to be resolved by an external power meter.

import Foundation
import Hub
import HuggingFace
import MLX
import MLXHuggingFace
import MLXLLM
import MLXLMCommon
import Metal
import SwiftUI
import Tokenizers
import os

#if os(iOS)
    import UIKit
#endif

// MARK: - Configuration

struct BenchConfig: Sendable {
    static let defaultModels = [
        "mlx-community/Qwen3-1.7B-4bit",
        "mlx-community/Qwen3-4B-4bit",
    ]

    let models: [String]
    let runs: Int
    let cooldownSeconds: Double
    let idleSeconds: Double
    let sustainSeconds: Double
    let sustainPrefillSeconds: Double
    let phaseCooldownSeconds: Double
    /// Launch arguments without argv[0] (which contains a local path).
    let argv: [String]

    static func parse(_ arguments: [String]) -> BenchConfig {
        var models = defaultModels
        var runs = 3
        var cooldown = 10.0
        var idle = 0.0
        var sustain = 0.0
        var sustainPrefill = 0.0
        var phaseCooldown = 0.0

        for argument in arguments {
            if let value = value(of: "--bench-models=", in: argument) {
                let parsed =
                    value
                    .split(separator: ",")
                    .map { $0.trimmingCharacters(in: .whitespaces) }
                    .filter { !$0.isEmpty }
                if !parsed.isEmpty {
                    models = parsed
                }
            } else if let value = value(of: "--bench-runs=", in: argument), let n = Int(value) {
                runs = max(0, n)
            } else if let value = value(of: "--bench-cooldown=", in: argument),
                let seconds = Double(value)
            {
                cooldown = max(0, seconds)
            } else if let value = value(of: "--bench-idle=", in: argument),
                let seconds = Double(value)
            {
                idle = max(0, seconds)
            } else if let value = value(of: "--bench-sustain=", in: argument),
                let seconds = Double(value)
            {
                sustain = max(0, seconds)
            } else if let value = value(of: "--bench-sustain-prefill=", in: argument),
                let seconds = Double(value)
            {
                sustainPrefill = max(0, seconds)
            } else if let value = value(of: "--bench-phase-cooldown=", in: argument),
                let seconds = Double(value)
            {
                phaseCooldown = max(0, seconds)
            }
        }

        return BenchConfig(
            models: models, runs: runs, cooldownSeconds: cooldown,
            idleSeconds: idle, sustainSeconds: sustain, sustainPrefillSeconds: sustainPrefill,
            phaseCooldownSeconds: phaseCooldown,
            argv: Array(arguments.dropFirst()))
    }

    private static func value(of prefix: String, in argument: String) -> String? {
        guard argument.hasPrefix(prefix) else { return nil }
        return String(argument.dropFirst(prefix.count))
    }
}

// MARK: - Output (stdout + jsonl file + on-screen log)

/// On-screen log shown by ``BenchView``.
@Observable
@MainActor
final class BenchLog {
    var lines: [String] = []
    var status = "starting"
    var finished = false
}

/// Serializes events to `BENCH {json}` lines and writes them to stdout, to
/// `Documents/bench-results.jsonl` and to the on-screen log.
final class BenchEmitter: @unchecked Sendable {
    static let resultsFileName = "bench-results.jsonl"

    private let lock = NSLock()
    private let session: String
    private let fileHandle: FileHandle?
    private let log: BenchLog

    init(log: BenchLog) {
        self.log = log
        self.session = String(UUID().uuidString.prefix(8)).lowercased()

        var handle: FileHandle?
        if let documents = FileManager.default.urls(
            for: .documentDirectory, in: .userDomainMask
        ).first {
            try? FileManager.default.createDirectory(
                at: documents, withIntermediateDirectories: true)
            let url = documents.appendingPathComponent(Self.resultsFileName)
            if !FileManager.default.fileExists(atPath: url.path) {
                FileManager.default.createFile(atPath: url.path, contents: nil)
            }
            handle = try? FileHandle(forWritingTo: url)
            _ = try? handle?.seekToEnd()
        }
        self.fileHandle = handle
    }

    /// Emit one event. `fields` must contain only JSON-compatible values
    /// (String, Bool, Int, Double, arrays/dictionaries of those).
    func emit(_ event: String, _ fields: [String: Any] = [:]) {
        var object = fields
        object["event"] = event
        object["session"] = session
        object["ts"] = Date().timeIntervalSince1970

        let line = "BENCH " + Self.serialize(object)

        lock.lock()
        fputs(line + "\n", stdout)
        fflush(stdout)
        if let fileHandle, let data = (line + "\n").data(using: .utf8) {
            try? fileHandle.write(contentsOf: data)
        }
        lock.unlock()

        let log = self.log
        DispatchQueue.main.async {
            MainActor.assumeIsolated {
                log.lines.append(line)
            }
        }
    }

    /// Update the on-screen status line (not written to stdout or the file).
    func status(_ text: String) {
        let log = self.log
        DispatchQueue.main.async {
            MainActor.assumeIsolated {
                log.status = text
            }
        }
    }

    func finish() {
        lock.lock()
        try? fileHandle?.synchronize()
        try? fileHandle?.close()
        fflush(stdout)
        lock.unlock()

        let log = self.log
        DispatchQueue.main.async {
            MainActor.assumeIsolated {
                log.finished = true
                log.status = "done"
            }
        }
    }

    private static func serialize(_ object: [String: Any]) -> String {
        // JSONSerialization raises an (uncatchable) ObjC exception for NaN/Inf,
        // so replace non-finite numbers with null and validate before encoding.
        let clean = sanitize(object)
        if JSONSerialization.isValidJSONObject(clean),
            let data = try? JSONSerialization.data(
                withJSONObject: clean, options: [.sortedKeys, .withoutEscapingSlashes]),
            let text = String(data: data, encoding: .utf8)
        {
            return text
        }
        return #"{"event":"error","message":"unserializable event","where":"emit"}"#
    }

    private static func sanitize(_ value: Any) -> Any {
        switch value {
        case let v as Bool: return v
        case let v as Double: return v.isFinite ? v : NSNull()
        case let v as Float: return v.isFinite ? Double(v) : NSNull()
        case let v as [String: Any]: return v.mapValues { sanitize($0) }
        case let v as [Any]: return v.map { sanitize($0) }
        default: return value
        }
    }
}

// MARK: - Benchmark runner

private struct BenchWorkload: Sendable {
    let name: String
    let prompt: String?
    let maxTokens: Int
}

private struct BenchError: Error, CustomStringConvertible {
    let stage: String
    let underlying: Error

    var description: String { "\(underlying)" }
}

private struct MissingResource: Error, CustomStringConvertible {
    let description: String
}

private func monotonicSeconds() -> Double {
    Double(DispatchTime.now().uptimeNanoseconds) / 1_000_000_000
}

private func sysctlString(_ name: String) -> String {
    var size = 0
    guard sysctlbyname(name, nil, &size, nil, 0) == 0, size > 0 else { return "" }
    var buffer = [CChar](repeating: 0, count: size)
    guard sysctlbyname(name, &buffer, &size, nil, 0) == 0 else { return "" }
    let bytes = buffer.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }
    return String(decoding: bytes, as: UTF8.self)
}

private func thermalState() -> Int {
    ProcessInfo.processInfo.thermalState.rawValue
}

/// 64-bit FNV-1a of the UTF-8 output, used to check that every device
/// generated the same text.
private func fingerprint(_ text: String) -> String {
    var hash: UInt64 = 0xcbf2_9ce4_8422_2325
    for byte in text.utf8 {
        hash ^= UInt64(byte)
        hash = hash &* 0x0000_0100_0000_01b3
    }
    return String(format: "%016llx", hash)
}

enum BenchRunner {
    static let systemPrompt = "You are a helpful assistant"
    static let genPrompt =
        "Write a detailed story of at least 1000 words about a lighthouse keeper who finds a message in a bottle."

    @MainActor private static var started = false

    /// Start the benchmark once per process.
    @MainActor
    static func startIfNeeded(log: BenchLog) {
        guard !started else { return }
        started = true

        // Unbuffered stdout so lines reach `devicectl --console` / a pipe immediately.
        setvbuf(stdout, nil, _IONBF, 0)

        #if os(iOS)
            UIApplication.shared.isIdleTimerDisabled = true
        #endif

        let config = BenchConfig.parse(CommandLine.arguments)
        let emitter = BenchEmitter(log: log)

        Task.detached(priority: .userInitiated) {
            // Keep macOS from App-Napping / throttling a background window.
            let activity = ProcessInfo.processInfo.beginActivity(
                options: [.userInitiated, .latencyCritical, .idleSystemSleepDisabled],
                reason: "LLMEval benchmark")
            await run(config: config, emitter: emitter)
            ProcessInfo.processInfo.endActivity(activity)

            emitter.finish()
            try? await Task.sleep(nanoseconds: 1_000_000_000)
            exit(0)
        }
    }

    static func run(config: BenchConfig, emitter: BenchEmitter) async {
        // Parity with LLMEvaluator.performLoad() as shipped.
        Memory.cacheLimit = 20 * 1024 * 1024

        emitter.emit("device", deviceInfo(config: config))

        let longPrompt: String? = Bundle.main.url(
            forResource: "LongPrompt", withExtension: "md"
        )
        .flatMap { try? String(contentsOf: $0, encoding: .utf8) }

        let workloads = [
            BenchWorkload(name: "gen", prompt: genPrompt, maxTokens: 256),
            BenchWorkload(name: "prefill", prompt: longPrompt, maxTokens: 16),
        ]

        if config.idleSeconds > 0 {
            // Baseline for power measurement: app in the foreground, nothing loaded.
            emitter.status("idle \(Int(config.idleSeconds))s")
            emitter.emit(
                "idle_start",
                ["targetSeconds": config.idleSeconds, "thermalState": thermalState()])
            let start = monotonicSeconds()
            try? await Task.sleep(nanoseconds: UInt64(config.idleSeconds * 1_000_000_000))
            emitter.emit(
                "idle_end",
                [
                    "targetSeconds": config.idleSeconds,
                    "seconds": monotonicSeconds() - start,
                    "thermalState": thermalState(),
                ])
        }

        for (modelIndex, modelId) in config.models.enumerated() {
            if modelIndex > 0 {
                await phaseCooldown(config: config, emitter: emitter, before: "model", model: modelId)
            }

            var modelPeak = 0
            var ok = true
            GPU.resetPeakMemory()

            do {
                modelPeak = try await benchModel(
                    id: modelId, workloads: workloads, config: config, emitter: emitter)
            } catch let error as BenchError {
                ok = false
                emitter.emit(
                    "error",
                    [
                        "model": modelId, "where": error.stage,
                        "message": String(describing: error.underlying),
                    ])
            } catch {
                ok = false
                emitter.emit(
                    "error",
                    ["model": modelId, "where": "model", "message": String(describing: error)])
            }

            // The container went out of scope with benchModel(); release cached buffers.
            Memory.clearCache()
            emitter.emit(
                "model_done",
                [
                    "model": modelId,
                    "ok": ok,
                    "peakMemoryBytes": max(modelPeak, Memory.peakMemory),
                    "activeMemoryBytesAfterClear": Memory.activeMemory,
                    "cacheMemoryBytesAfterClear": Memory.cacheMemory,
                ])
        }

        emitter.status("done")
        emitter.emit("done")
    }

    // MARK: device info

    private static func deviceInfo(config: BenchConfig) -> [String: Any] {
        let gpu = GPU.deviceInfo()
        let processInfo = ProcessInfo.processInfo

        #if DEBUG
            let buildConfiguration = "DEBUG"
        #else
            let buildConfiguration = "RELEASE"
        #endif

        #if os(iOS)
            let platform = "iOS"
        #elseif os(macOS)
            let platform = "macOS"
        #elseif os(visionOS)
            let platform = "visionOS"
        #else
            let platform = "other"
        #endif

        var info: [String: Any] = [
            "platform": platform,
            "hwMachine": sysctlString("hw.machine"),
            "hwModel": sysctlString("hw.model"),
            "cpuBrand": sysctlString("machdep.cpu.brand_string"),
            "osVersion": processInfo.operatingSystemVersionString,
            "physicalMemory": processInfo.physicalMemory,
            "gpuArchitecture": gpu.architecture,
            "gpuMemorySize": gpu.memorySize,
            "gpuMaxRecommendedWorkingSetSize": gpu.maxRecommendedWorkingSetSize,
            "lowPowerMode": processInfo.isLowPowerModeEnabled,
            "thermalState": thermalState(),
            "buildConfiguration": buildConfiguration,
            "mlxCacheLimit": Memory.cacheLimit,
            "resultsFile": "Documents/\(BenchEmitter.resultsFileName)",
            "args": [
                "models": config.models,
                "runs": config.runs,
                "cooldownSeconds": config.cooldownSeconds,
                "idleSeconds": config.idleSeconds,
                "sustainSeconds": config.sustainSeconds,
                "sustainPrefillSeconds": config.sustainPrefillSeconds,
                "phaseCooldownSeconds": config.phaseCooldownSeconds,
                "argv": config.argv,
            ] as [String: Any],
            // MLX_* environment variables in effect (e.g. MLX_ENABLE_TF32); {} if none.
            "mlxEnvironment": ProcessInfo.processInfo.environment.filter {
                $0.key.hasPrefix("MLX_")
            },
        ]

        #if os(iOS)
            info["availableMemoryBytes"] = os_proc_available_memory()
        #endif

        return info
    }

    // MARK: per model

    /// Load one model, run all workloads, return the peak memory observed.
    /// The container is released when this returns.
    private static func benchModel(
        id: String, workloads: [BenchWorkload], config: BenchConfig, emitter: BenchEmitter
    ) async throws -> Int {
        emitter.status("loading \(id)")
        emitter.emit("model_load_start", ["model": id, "thermalState": thermalState()])

        let container: ModelContainer
        do {
            container = try await load(id: id, emitter: emitter)
        } catch {
            throw BenchError(stage: "load", underlying: error)
        }
        var modelPeak = Memory.peakMemory

        for workload in workloads {
            guard let prompt = workload.prompt else {
                throw BenchError(
                    stage: workload.name,
                    underlying: MissingResource(
                        description: "LongPrompt.md not found in app bundle"))
            }

            for run in 0 ... config.runs {
                let warmup = run == 0
                let label = warmup ? "warm-up" : "run \(run)/\(config.runs)"

                if !warmup && config.cooldownSeconds > 0 {
                    emitter.status("\(id) \(workload.name) \(label): cooldown")
                    try? await Task.sleep(
                        nanoseconds: UInt64(config.cooldownSeconds * 1_000_000_000))
                }

                emitter.status("\(id) \(workload.name) \(label)")
                do {
                    let result = try await runOnce(
                        container: container, modelId: id, workload: workload, prompt: prompt,
                        run: run, warmup: warmup, emitter: emitter)
                    modelPeak = max(modelPeak, result.peakMemoryBytes)
                } catch {
                    throw BenchError(stage: "\(workload.name) run \(run)", underlying: error)
                }
            }
        }

        if config.sustainSeconds > 0 {
            await phaseCooldown(config: config, emitter: emitter, before: "sustain", model: id)
            let peak = try await sustainPhase(
                name: "sustain",
                workload: BenchWorkload(name: "sustain", prompt: genPrompt, maxTokens: 256),
                seconds: config.sustainSeconds,
                container: container, modelId: id, emitter: emitter)
            modelPeak = max(modelPeak, peak)
        }

        if config.sustainPrefillSeconds > 0 {
            guard let prefill = workloads.first(where: { $0.name == "prefill" }), prefill.prompt != nil
            else {
                throw BenchError(
                    stage: "sustain_prefill",
                    underlying: MissingResource(
                        description: "LongPrompt.md not found in app bundle"))
            }
            await phaseCooldown(
                config: config, emitter: emitter, before: "sustain_prefill", model: id)
            let peak = try await sustainPhase(
                name: "sustain_prefill",
                workload: BenchWorkload(
                    name: "sustain_prefill", prompt: prefill.prompt, maxTokens: prefill.maxTokens),
                seconds: config.sustainPrefillSeconds,
                container: container, modelId: id, emitter: emitter)
            modelPeak = max(modelPeak, peak)
        }

        return modelPeak
    }

    /// Sleep for `--bench-phase-cooldown` seconds (no-op when 0) so the device can
    /// shed heat before the next sustained phase or model. `before` names what
    /// follows ("sustain", "sustain_prefill" or "model").
    private static func phaseCooldown(
        config: BenchConfig, emitter: BenchEmitter, before: String, model: String
    ) async {
        guard config.phaseCooldownSeconds > 0 else { return }
        emitter.status("cooldown \(Int(config.phaseCooldownSeconds))s before \(before)")
        emitter.emit(
            "phase_cooldown_start",
            [
                "before": before, "model": model,
                "targetSeconds": config.phaseCooldownSeconds, "thermalState": thermalState(),
            ])
        let start = monotonicSeconds()
        try? await Task.sleep(nanoseconds: UInt64(config.phaseCooldownSeconds * 1_000_000_000))
        emitter.emit(
            "phase_cooldown_end",
            [
                "before": before, "model": model,
                "targetSeconds": config.phaseCooldownSeconds,
                "seconds": monotonicSeconds() - start, "thermalState": thermalState(),
            ])
    }

    /// Run `workload` back-to-back (no cooldown) until at least `seconds` have
    /// elapsed, emitting `<name>_start`, one `run` per iteration (with
    /// `elapsedInPhase`) and `<name>_end`. Returns the peak memory observed.
    private static func sustainPhase(
        name: String, workload: BenchWorkload, seconds: Double,
        container: ModelContainer, modelId: String, emitter: BenchEmitter
    ) async throws -> Int {
        guard let prompt = workload.prompt else {
            throw BenchError(
                stage: name, underlying: MissingResource(description: "missing prompt"))
        }
        let thermalBefore = thermalState()

        emitter.emit(
            "\(name)_start",
            [
                "model": modelId,
                "targetSeconds": seconds,
                "thermalState": thermalBefore,
            ])

        let start = monotonicSeconds()
        var iterations = 0
        var totalGenerated = 0
        var totalPrompt = 0
        var first: RunResult?
        var last: RunResult?
        var peak = 0

        repeat {
            iterations += 1
            emitter.status(
                "\(modelId) \(name) #\(iterations) (\(Int(monotonicSeconds() - start))s / \(Int(seconds))s)"
            )
            do {
                let result = try await runOnce(
                    container: container, modelId: modelId, workload: workload,
                    prompt: prompt, run: iterations, warmup: false, emitter: emitter,
                    phaseStart: start)
                totalGenerated += result.generationTokenCount
                totalPrompt += result.promptTokenCount
                if first == nil {
                    first = result
                }
                last = result
                peak = max(peak, result.peakMemoryBytes)
            } catch {
                throw BenchError(stage: "\(name) run \(iterations)", underlying: error)
            }
        } while monotonicSeconds() - start < seconds

        let totalSeconds = monotonicSeconds() - start
        var fields: [String: Any] = [
            "model": modelId,
            "targetSeconds": seconds,
            "iterations": iterations,
            "totalGeneratedTokens": totalGenerated,
            "totalPromptTokens": totalPrompt,
            "totalSeconds": totalSeconds,
            "overallTokensPerSecond": Double(totalGenerated) / totalSeconds,
            "overallPromptTokensPerSecond": Double(totalPrompt) / totalSeconds,
            "thermalStateBefore": thermalBefore,
            "thermalStateAfter": thermalState(),
            "peakMemoryBytes": peak,
        ]
        if let value = first?.tokensPerSecond {
            fields["firstIterationTokensPerSecond"] = value
        }
        if let value = last?.tokensPerSecond {
            fields["lastIterationTokensPerSecond"] = value
        }
        if let value = first?.promptTokensPerSecond {
            fields["firstIterationPromptTokensPerSecond"] = value
        }
        if let value = last?.promptTokensPerSecond {
            fields["lastIterationPromptTokensPerSecond"] = value
        }
        emitter.emit("\(name)_end", fields)

        return peak
    }

    /// Download + load exactly as `LLMEvaluator.performLoad()` does.
    private static func load(id: String, emitter: BenchEmitter) async throws -> ModelContainer {
        Memory.cacheLimit = 20 * 1024 * 1024

        let configuration = ModelConfiguration(id: id)
        let start = monotonicSeconds()

        let downloader = #hubDownloader()
        let lastDecile = OSAllocatedUnfairLock<Int>(initialState: -1)

        let resolved = try await resolve(
            configuration: configuration, from: downloader, useLatest: false
        ) { progress in
            let fraction = progress.fractionCompleted
            let decile = Int((fraction * 10).rounded(.down))
            let shouldEmit = lastDecile.withLock { (last: inout Int) -> Bool in
                guard decile > last else { return false }
                last = decile
                return true
            }
            if shouldEmit {
                emitter.emit(
                    "download_progress",
                    [
                        "model": id,
                        "fraction": fraction,
                        "completedUnitCount": progress.completedUnitCount,
                        "totalUnitCount": progress.totalUnitCount,
                    ])
            }
        }
        let resolveSeconds = monotonicSeconds() - start

        // Same sanity check as LLMEvaluator.performLoad().
        let fileManager = FileManager.default
        let directoryExists = fileManager.fileExists(atPath: resolved.modelDirectory.path)
        let contents =
            (try? fileManager.contentsOfDirectory(atPath: resolved.modelDirectory.path)) ?? []
        let hasSafetensors = contents.contains { $0.hasSuffix(".safetensors") }
        if !directoryExists || !hasSafetensors {
            throw NSError(
                domain: "LLMEvalBenchmark",
                code: -1,
                userInfo: [
                    NSLocalizedDescriptionKey:
                        "Model download failed. Please check your network connection and try again."
                ]
            )
        }

        let loadStart = monotonicSeconds()
        let modelContainer = try await LLMModelFactory.shared.loadContainer(
            from: resolved.modelDirectory,
            using: #huggingFaceTokenizerLoader())
        let numParams = await modelContainer.perform { $0.model.numParameters() }
        let end = monotonicSeconds()

        let activeAfterLoad = Memory.activeMemory
        let peakAfterLoad = Memory.peakMemory

        // Dtype probe (after the load timer, before any warm-up): parameter
        // tensor count per dtype, and the dtype of the logits of a 1-token
        // forward pass (the activation dtype the matmul kernels see).
        let parameterDtypes = await modelContainer.perform { context -> [String: Int] in
            var counts: [String: Int] = [:]
            for (_, array) in context.model.parameters().flattened() {
                counts[String(describing: array.dtype), default: 0] += 1
            }
            return counts
        }
        let logitsDtype = await modelContainer.perform { context -> String in
            let logits = context.model(MLXArray([Int32(0)]).reshaped(1, 1), cache: nil)
            eval(logits)
            return String(describing: logits.dtype)
        }

        emitter.emit(
            "model_loaded",
            [
                "model": id,
                "resolveSeconds": resolveSeconds,
                "loadSeconds": end - loadStart,
                "totalLoadSeconds": end - start,
                "numParameters": numParams,
                "activeMemoryBytes": activeAfterLoad,
                "peakMemoryBytes": peakAfterLoad,
                "parameterDtypes": parameterDtypes,
                "logitsDtype": logitsDtype,
                "thermalState": thermalState(),
            ])

        return modelContainer
    }

    // MARK: per run

    private struct RunResult {
        let peakMemoryBytes: Int
        let generationTokenCount: Int
        let promptTokenCount: Int
        let tokensPerSecond: Double?
        let promptTokensPerSecond: Double?
    }

    /// One generation; emits a `run` event. `phaseStart` (monotonic seconds)
    /// adds `elapsedInPhase` = seconds from the phase start to the end of this run.
    private static func runOnce(
        container: ModelContainer, modelId: String, workload: BenchWorkload, prompt: String,
        run: Int, warmup: Bool, emitter: BenchEmitter, phaseStart: Double? = nil
    ) async throws -> RunResult {
        let parameters = GenerateParameters(maxTokens: workload.maxTokens, temperature: 0)
        let userInput = UserInput(
            chat: [
                .system(systemPrompt),
                .user(prompt),
            ],
            additionalContext: ["enable_thinking": false]
        )

        let thermalBefore = thermalState()
        GPU.resetPeakMemory()

        let prepareStart = monotonicSeconds()
        let lmInput = try await container.prepare(input: userInput)
        let preparedTokens = lmInput.text.tokens.size

        // Clock starts before generate(): its TokenIterator runs the whole
        // prefill before the stream is returned (same as the stock app).
        let generateStart = monotonicSeconds()
        let stream = try await container.generate(input: lmInput, parameters: parameters)

        var firstChunkTime: Double?
        var completion: GenerateCompletionInfo?
        var output = ""
        var chunkCount = 0
        var toolCallCount = 0

        for await item in stream {
            switch item {
            case .chunk(let text):
                if firstChunkTime == nil && !text.isEmpty {
                    firstChunkTime = monotonicSeconds()
                }
                output += text
                chunkCount += 1
            case .info(let info):
                completion = info
            case .toolCall:
                toolCallCount += 1
            }
        }
        let end = monotonicSeconds()

        let peak = Memory.peakMemory

        var fields: [String: Any] = [
            "model": modelId,
            "workload": workload.name,
            "run": run,
            "warmup": warmup,
            "maxTokens": workload.maxTokens,
            "preparedPromptTokens": preparedTokens,
            "prepareWallSeconds": generateStart - prepareStart,
            "generateWallSeconds": end - generateStart,
            "totalWallSeconds": end - prepareStart,
            "thermalStateBefore": thermalBefore,
            "thermalStateAfter": thermalState(),
            "peakMemoryBytes": peak,
            "activeMemoryBytes": Memory.activeMemory,
            "cacheMemoryBytes": Memory.cacheMemory,
            "chunkCount": chunkCount,
            "toolCallCount": toolCallCount,
            "outputChars": output.count,
            "outputHash": fingerprint(output),
            "outputHead": String(output.prefix(80)),
        ]
        if let firstChunkTime {
            fields["ttftWallSeconds"] = firstChunkTime - generateStart
        }
        if let phaseStart {
            fields["elapsedInPhase"] = end - phaseStart
        }
        if let info = completion {
            fields["promptTokenCount"] = info.promptTokenCount
            fields["generationTokenCount"] = info.generationTokenCount
            fields["promptTime"] = info.promptTime
            fields["generateTime"] = info.generateTime
            fields["promptTokensPerSecond"] = info.promptTokensPerSecond
            fields["tokensPerSecond"] = info.tokensPerSecond
            let stopReason = String(describing: info.stopReason)
            fields["stopReason"] = stopReason
            // mlx-swift-lm 3.31.3 `generateLoopTask` reads `tokenCount` from the un-advanced
            // iterator copy, so max-token stops are mislabelled as "cancelled".
            fields["stopReasonEffective"] =
                (info.stopReason == .cancelled && info.generationTokenCount >= workload.maxTokens)
                ? "length" : stopReason
        } else {
            fields["missingCompletionInfo"] = true
        }

        emitter.emit("run", fields)
        return RunResult(
            peakMemoryBytes: peak,
            generationTokenCount: completion?.generationTokenCount ?? 0,
            promptTokenCount: completion?.promptTokenCount ?? 0,
            tokensPerSecond: completion?.tokensPerSecond,
            promptTokensPerSecond: completion?.promptTokensPerSecond)
    }
}

// MARK: - View

struct BenchView: View {
    @State private var log = BenchLog()

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("LLMEval benchmark")
                .font(.headline)
            HStack(spacing: 6) {
                if !log.finished {
                    ProgressView()
                        .controlSize(.small)
                }
                Text(log.status)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(log.lines.enumerated()), id: \.offset) { index, line in
                            Text(line)
                                .font(.system(.caption2, design: .monospaced))
                                .textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .id(index)
                        }
                    }
                }
                .onChange(of: log.lines.count) { _, count in
                    if count > 0 {
                        proxy.scrollTo(count - 1, anchor: .bottom)
                    }
                }
            }
        }
        .padding()
        .task {
            BenchRunner.startIfNeeded(log: log)
        }
    }
}
