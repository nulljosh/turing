// SamanthaGUI: a real window instead of a terminal. Drives chat_pipe.py, her real answer chain, over stdin/stdout.
// One file, no Xcode project, matching menubar/PaintBar.swift's pattern.
// Build: ./build.sh   Self-check: ./build/SamanthaGUI.app/Contents/MacOS/SamanthaGUI --check
import SwiftUI
import Foundation

/// One line she sent back, parsed. Pure, so --check can exercise it with no process, no model.
enum PipeMessage: Equatable {
    case working(String)
    case confirm(name: String, args: [String])
    case answer(String)
}

/// One line of chat_pipe.py's protocol into a PipeMessage, or nil if it is not JSON shaped the way she sends it.
func parseLine(_ line: String) -> PipeMessage? {
    guard let data = line.data(using: .utf8),
          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
    if let working = obj["working"] as? String { return .working(working) }
    if let answer = obj["answer"] as? String { return .answer(answer) }
    if let confirm = obj["confirm"] as? [String: Any], let name = confirm["name"] as? String {
        return .confirm(name: name, args: (confirm["args"] as? [Any])?.map { "\($0)" } ?? [])
    }
    return nil
}

/// One line to send her: {"ask": text} or {"yes": bool}, exactly what chat_pipe.py expects.
func askLine(_ text: String) -> String {
    let data = try! JSONSerialization.data(withJSONObject: ["ask": text])
    return String(data: data, encoding: .utf8)! + "\n"
}

func yesLine(_ yes: Bool) -> String {
    let data = try! JSONSerialization.data(withJSONObject: ["yes": yes])
    return String(data: data, encoding: .utf8)! + "\n"
}

@MainActor
final class Samantha: ObservableObject {
    @Published var transcript: [String] = []
    @Published var busy = false
    @Published var pending: (name: String, args: [String])?
    @Published var status = "Starting…"
    private var job: Process?
    private var stdin: FileHandle?
    private var buffer = ""

    private let pythonPath = (Bundle.main.object(forInfoDictionaryKey: "PythonPath") as? String) ?? "/usr/bin/python3"
    private let pipePath = (Bundle.main.object(forInfoDictionaryKey: "ChatPipePath") as? String) ?? ""

    /// Launch chat_pipe.py once and keep it running for the whole session: her model stays loaded, same as the
    /// terminal's own streaming chat, never reloaded per message.
    func start() {
        guard job == nil else { return }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: pythonPath)
        p.arguments = ["-u", pipePath]
        let out = Pipe(), inp = Pipe()
        p.standardOutput = out
        p.standardInput = inp
        p.standardError = Pipe()  // Fetching-progress noise on first load; not shown, not fatal
        stdin = inp.fileHandleForWriting
        out.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor in self?.feed(text) }
        }
        p.terminationHandler = { [weak self] proc in
            Task { @MainActor in self?.status = "Samantha stopped (exit \(proc.terminationStatus)). Relaunch the app." }
        }
        do {
            try p.run()
            job = p
            status = "Ready"
        } catch {
            status = "Could not start Python: \(error.localizedDescription)"
        }
    }

    /// New bytes off the pipe: buffered until a full line, each parsed and applied in order.
    private func feed(_ text: String) {
        buffer += text
        while let range = buffer.range(of: "\n") {
            let line = String(buffer[..<range.lowerBound])
            buffer.removeSubrange(..<range.upperBound)
            if let msg = parseLine(line) { apply(msg) }
        }
    }

    private func apply(_ msg: PipeMessage) {
        switch msg {
        case .working(let text): transcript.append("  [\(text)]")
        case .confirm(let name, let args): pending = (name, args)
        case .answer(let text):
            transcript.append("Samantha: \(text)")
            busy = false
        }
    }

    func send(_ text: String) {
        let text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !busy, pending == nil, let stdin else { return }
        transcript.append("You: \(text)")
        busy = true
        stdin.write(askLine(text).data(using: .utf8)!)
    }

    func reply(_ yes: Bool) {
        guard let stdin, pending != nil else { return }
        pending = nil
        stdin.write(yesLine(yes).data(using: .utf8)!)
    }
}

/// One line, styled the way Messages.app tells "you" from "her": a tool step recedes to secondary and monospace,
/// a real turn gets a bubble aligned to whichever side spoke.
private struct MessageRow: View {
    let line: String

    private var isWorking: Bool { line.hasPrefix("  [") }
    private var isYou: Bool { line.hasPrefix("You: ") }
    private var body_: String {
        isYou ? String(line.dropFirst(5)) : (line.hasPrefix("Samantha: ") ? String(line.dropFirst(10)) : line)
    }

    var body: some View {
        if isWorking {
            Text(line.trimmingCharacters(in: .whitespaces))
                .font(.caption.monospaced()).foregroundStyle(.tertiary)
                .frame(maxWidth: .infinity, alignment: .leading)
        } else {
            HStack {
                if isYou { Spacer(minLength: 40) }
                Text(body_).font(.body).foregroundStyle(.primary).padding(.horizontal, 12).padding(.vertical, 8)
                    .background(isYou ? Color.accentColor.opacity(0.18) : Color(nsColor: .controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                if !isYou { Spacer(minLength: 40) }
            }
        }
    }
}

/// Three dots that pulse while she is thinking, so a wait reads as alive, not frozen.
private struct TypingIndicator: View {
    @State private var phase = 0
    @State private var timer: Timer?

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3, id: \.self) { i in
                Circle().frame(width: 6, height: 6).foregroundStyle(.secondary)
                    .opacity(phase == i ? 1 : 0.3)
                    .animation(.easeInOut(duration: 0.4), value: phase)
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 8)
        .background(Color(nsColor: .controlBackgroundColor)).clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .onAppear {
            timer = Timer.scheduledTimer(withTimeInterval: 0.4, repeats: true) { _ in phase = (phase + 1) % 3 }
        }
        .onDisappear {
            timer?.invalidate()
            timer = nil
        }
    }
}

/// The confirm prompt, native-material, spring in and out: it appears exactly when a write needs a yes.
private struct ConfirmBar: View {
    let pending: (name: String, args: [String])
    let reply: (Bool) -> Void

    var body: some View {
        HStack {
            Text("Run \(pending.name)(\(pending.args.joined(separator: ", ")))?").font(.callout)
            Spacer()
            Button("No") { reply(false) }.keyboardShortcut(.cancelAction)
            Button("Yes") { reply(true) }.keyboardShortcut(.defaultAction).buttonStyle(.borderedProminent)
        }
        .padding(12).background(.thinMaterial)
        .transition(.move(edge: .bottom).combined(with: .opacity))
    }
}

struct ChatView: View {
    @ObservedObject var samantha: Samantha
    @State private var text = ""
    private var inputDisabled: Bool { samantha.busy || samantha.pending != nil }

    var body: some View {
        VStack(spacing: 0) {
            transcriptView
            if let pending = samantha.pending {
                ConfirmBar(pending: pending, reply: samantha.reply)
            }
            Divider()
            inputBar
            Text(samantha.status).font(.caption2).foregroundStyle(.tertiary).padding(.bottom, 6)
        }
        .frame(minWidth: 420, minHeight: 480)
        .animation(.spring(duration: 0.35), value: samantha.pending == nil)
        .onAppear { samantha.start() }
    }

    private var transcriptView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 8) {
                    ForEach(Array(samantha.transcript.enumerated()), id: \.offset) { i, line in
                        MessageRow(line: line).id(i)
                            .transition(.opacity.combined(with: .move(edge: .bottom)))
                    }
                    if samantha.busy {
                        HStack { TypingIndicator(); Spacer() }.id("typing")
                    }
                }
                .padding(14)
                .animation(.easeOut(duration: 0.2), value: samantha.transcript.count)
            }
            .onChange(of: samantha.transcript.count) { _, _ in scrollToEnd(proxy) }
            .onChange(of: samantha.busy) { _, _ in scrollToEnd(proxy) }
        }
    }

    private func scrollToEnd(_ proxy: ScrollViewProxy) {
        withAnimation(.easeOut(duration: 0.25)) {
            if samantha.busy { proxy.scrollTo("typing", anchor: .bottom) }
            else if let last = samantha.transcript.indices.last { proxy.scrollTo(last, anchor: .bottom) }
        }
    }

    private var inputBar: some View {
        HStack {
            TextField("Talk to Samantha", text: $text, onCommit: { samantha.send(text); text = "" })
                .textFieldStyle(.roundedBorder).disabled(inputDisabled)
            Button("Send") { samantha.send(text); text = "" }.disabled(text.isEmpty || inputDisabled)
        }.padding(10)
    }
}

/// No process, no model: prove the pure parsing and encoding, the exact same way PaintBar's --check works.
func runSelfCheck() -> Never {
    precondition(parseLine("{\"answer\": \"hi\"}") == .answer("hi"))
    precondition(parseLine("{\"working\": \"open_app(chrome)\"}") == .working("open_app(chrome)"))
    if case .confirm(let name, let args)? = parseLine("{\"confirm\": {\"name\": \"new_note\", \"args\": [\"buy milk\"]}}") {
        precondition(name == "new_note" && args == ["buy milk"])
    } else {
        fatalError("confirm did not parse")
    }
    precondition(parseLine("not json") == nil)
    precondition(askLine("hi") == "{\"ask\":\"hi\"}\n")
    precondition(yesLine(true) == "{\"yes\":true}\n")
    print("SamanthaGUI ok")
    exit(0)
}

@main
struct SamanthaGUIApp: App {
    @StateObject private var samantha = Samantha()

    init() {
        if CommandLine.arguments.contains("--check") { runSelfCheck() }
    }

    var body: some Scene {
        WindowGroup("Samantha") { ChatView(samantha: samantha) }
    }
}
