// SamanthaGUI: a real window instead of a terminal. Drives chat_pipe.py, her real answer chain, over stdin/stdout.
// One file, no Xcode project, matching menubar/PaintBar.swift's pattern.
// Build: ./build.sh   Self-check: ./build/SamanthaGUI.app/Contents/MacOS/SamanthaGUI --check
import SwiftUI
import Foundation

/// One line she sent back, parsed. Pure, so --check can exercise it with no process, no model.
enum PipeMessage: Equatable {
    case working(String)
    case confirm(name: String, args: [String], note: String)
    case mode(voice: Bool, face: Bool)
    case answer(String)
}

/// One line of chat_pipe.py's protocol into a PipeMessage, or nil if it is not JSON shaped the way she sends it.
func parseLine(_ line: String) -> PipeMessage? {
    guard let data = line.data(using: .utf8),
          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return nil }
    if let working = obj["working"] as? String { return .working(working) }
    if let answer = obj["answer"] as? String { return .answer(answer) }
    if let confirm = obj["confirm"] as? [String: Any], let name = confirm["name"] as? String {
        return .confirm(name: name, args: (confirm["args"] as? [Any])?.map { "\($0)" } ?? [], note: confirm["note"] as? String ?? "")
    }
    if let mode = obj["mode"] as? [String: Any] {
        return .mode(voice: mode["voice"] as? Bool ?? false, face: mode["face"] as? Bool ?? false)
    }
    return nil
}

/// One line to send her: {"ask": text} or {"yes": bool}, exactly what chat_pipe.py expects.
func askLine(_ text: String) -> String {
    let data = try! JSONSerialization.data(withJSONObject: ["ask": text])
    return String(data: data, encoding: .utf8)! + "\n"
}

/// The sentence a Customize sheet sends: the same words she routes when you type them.
func customizeLine(_ kind: Customize, _ text: String) -> String {
    let text = text.trimmingCharacters(in: .whitespacesAndNewlines)
    return kind == .voice ? "change your voice to \(text)" : "change your look: \(text)"
}

/// Which Customize sheet is open.
enum Customize: String, Identifiable {
    case voice, look
    var id: String { rawValue }
}

func yesLine(_ yes: Bool) -> String {
    let data = try! JSONSerialization.data(withJSONObject: ["yes": yes])
    return String(data: data, encoding: .utf8)! + "\n"
}

/// Where the chat is kept between launches, and where "New Chat" files the old one away.
let chatDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".samantha")

/// The transcript as JSON at `file`. Failure is silent: a chat that cannot be saved is still a chat.
func saveChat(_ lines: [String], to file: URL) {
    try? FileManager.default.createDirectory(at: file.deletingLastPathComponent(), withIntermediateDirectories: true)
    if let data = try? JSONEncoder().encode(lines) { try? data.write(to: file, options: .atomic) }
}

/// The lines saved at `file`, or none.
func dayKey(_ date: Date) -> String {
    let d = Calendar.current.dateComponents([.year, .month, .day], from: date)
    return "\(d.year!)-\(d.month!)-\(d.day!)"
}
/// A brief is due before noon on a day that has not had one.
func briefDue(now: Date, lastDay: String?) -> Bool {
    Calendar.current.component(.hour, from: now) < 12 && lastDay != dayKey(now)
}

func loadChat(from file: URL) -> [String] {
    guard let data = try? Data(contentsOf: file), let lines = try? JSONDecoder().decode([String].self, from: data) else { return [] }
    return lines
}

@MainActor
final class Samantha: ObservableObject {
    @Published var transcript: [String] = loadChat(from: chatDir.appendingPathComponent("chat.json"))
    @Published var busy = false
    @Published var pending: (name: String, args: [String], note: String)?
    @Published var status = "Starting…"
    @Published var voiceOn = false
    @Published var faceOn = false
    @Published var customize: Customize?
    private var job: Process?
    private var stdin: FileHandle?
    private var buffer = ""

    private let pythonPath = (Bundle.main.object(forInfoDictionaryKey: "PythonPath") as? String) ?? "/usr/bin/python3"
    private let pipePath = (Bundle.main.object(forInfoDictionaryKey: "ChatPipePath") as? String) ?? ""
    // Set only in the packaged, distributed build (gui/package.sh): a bundled script, resolved at
    // launch time relative to Resources/, that finds or creates her env in Application Support and
    // installs requirements.txt on first run. The dev build (gui/build.sh) leaves this unset and
    // execs PythonPath/ChatPipePath directly against this checkout's own .venv, as before.
    private let launcherScript = (Bundle.main.object(forInfoDictionaryKey: "LauncherScript") as? String)

    /// Launch chat_pipe.py once and keep it running for the whole session: her model stays loaded, same as the
    /// terminal's own streaming chat, never reloaded per message. A packaged build's first run has no venv yet,
    /// so the launcher shows a plain "setting up" line (a normal .working message) before she is ready.
    func start() {
        guard job == nil else { return }
        let p = Process()
        if let launcherScript, let resources = Bundle.main.resourceURL {
            p.executableURL = resources.appendingPathComponent(launcherScript)
        } else {
            p.executableURL = URL(fileURLWithPath: pythonPath)
            p.arguments = ["-u", pipePath]
        }
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
        case .working(let text):
            transcript.append("  [\(text)]")
            // first-run setup ("Setting up Samantha, about two minutes...") reads in the status line; a tool name does not
            status = text.hasPrefix("Setting up") ? text : "Ready"
        case .confirm(let name, let args, let note): pending = (name, args, note)
        case .mode(let voice, let face):
            voiceOn = voice
            faceOn = face
        case .answer(let text):
            transcript.append("Samantha: \(text)")
            busy = false
            saveChat(transcript, to: chatDir.appendingPathComponent("chat.json"))
        }
    }

    func send(_ text: String) {
        let text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !busy, pending == nil, let stdin else { return }
        transcript.append("You: \(text)")
        busy = true
        stdin.write(askLine(text).data(using: .utf8)!)
    }

    /// 7.0, she comes to you: the first time she opens each morning she asks herself for the morning brief (the
    /// date, then what needs you), so it is on screen before you type. Her own line, no "You:" above it. Once a
    /// day, mornings only; the day is kept in UserDefaults so a relaunch does not repeat it.
    func morningBrief(now: Date = Date()) {
        guard briefDue(now: now, lastDay: UserDefaults.standard.string(forKey: "briefDay")), !busy, let stdin else { return }
        UserDefaults.standard.set(dayKey(now), forKey: "briefDay")
        busy = true
        stdin.write(askLine("morning brief").data(using: .utf8)!)
    }

    /// File > New Chat: the current chat is kept as chats/<time>.json, then the window starts empty.
    func newChat() {
        guard !busy, !transcript.isEmpty else { return }
        let stamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        saveChat(transcript, to: chatDir.appendingPathComponent("chats/\(stamp).json"))
        transcript = []
        try? FileManager.default.removeItem(at: chatDir.appendingPathComponent("chat.json"))
    }

    /// The Voice and Face buttons: the same /voice and /face switches the terminal chat understands.
    func toggle(_ which: String) { send("/\(which)") }

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
            // "time_in(tokyo)", quietly, no brackets: what she is doing, not a log line
            Text(line.trimmingCharacters(in: CharacterSet(charactersIn: " []")))
                .font(.caption.monospaced()).foregroundStyle(.tertiary)
                .frame(maxWidth: .infinity, alignment: .leading)
        } else if isYou {
            HStack {
                Spacer(minLength: 40)
                Text(body_).font(.body).padding(.horizontal, 12).padding(.vertical, 8)
                    .background(Color.accentColor.opacity(0.18))
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            }
        } else {
            // Her replies: prose with inline Markdown, every fenced block as real code with its own Copy button,
            // and "(Answered by X on this Mac.)" as a small line under the reply instead of a sentence inside it.
            let (text, model) = splitModelLabel(body_)
            VStack(alignment: .leading, spacing: 10) {
                ForEach(Array(replySegments(text).enumerated()), id: \.offset) { _, seg in
                    if let lang = seg.lang {
                        CodeBlock(code: seg.text, lang: lang)
                    } else {
                        Text(inlineMarkdown(seg.text)).font(.body).textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                if let model { Text("Answered by \(model) on this Mac").font(.caption).foregroundStyle(.secondary) }
            }
            .padding(.horizontal, 12).padding(.vertical, 8)
        }
    }
}

/// (reply, model) from a reply that ends in "(Answered by X on this Mac.)" or "(... on this Mac, not by me.)".
func splitModelLabel(_ s: String) -> (String, String?) {
    guard let m = s.range(of: #"\s*\(Answered by (.+?) on this Mac(?:, not by me)?\.\)\s*$"#, options: .regularExpression) else { return (s, nil) }
    let tag = String(s[m]).trimmingCharacters(in: .whitespacesAndNewlines)
    let model = tag.replacingOccurrences(of: #"^\(Answered by |\s+on this Mac.*$"#, with: "", options: .regularExpression)
    return (String(s[..<m.lowerBound]), model)
}

/// One code block: monospaced, selectable, scrolls sideways instead of wrapping, with a Copy button that says Copied.
private struct CodeBlock: View {
    let code: String
    let lang: String
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text(lang.isEmpty ? "code" : lang).font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(code, forType: .string)
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
                } label: {
                    Label(copied ? "Copied" : "Copy", systemImage: copied ? "checkmark" : "doc.on.doc").font(.caption)
                }
                .buttonStyle(.borderless).help("Copy this code")
            }
            .padding(.horizontal, 10).padding(.vertical, 6)
            Divider()
            ScrollView(.horizontal, showsIndicators: false) {
                Text(highlight(code, lang: lang)).font(.system(.callout, design: .monospaced)).textSelection(.enabled)
                    .fixedSize(horizontal: true, vertical: false).padding(10)
            }
        }
        .background(Color(nsColor: .textBackgroundColor))
        .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(Color(nsColor: .separatorColor)))
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
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
    let pending: (name: String, args: [String], note: String)
    let reply: (Bool) -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("Run \(pending.name)(\(pending.args.joined(separator: ", ")))?").font(.callout)
                if !pending.note.isEmpty { Text(pending.note).font(.caption).foregroundStyle(.secondary) }
            }
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
    @FocusState private var fieldFocused: Bool  // a disabled field drops focus; it comes back when she is done (QA 2026-10-11)
    private var inputDisabled: Bool { samantha.busy || samantha.pending != nil }

    var body: some View {
        VStack(spacing: 0) {
            if samantha.transcript.isEmpty && !samantha.busy { emptyState } else { transcriptView }
            if let pending = samantha.pending {
                ConfirmBar(pending: pending, reply: samantha.reply)
            }
            Divider()
            inputBar
            // Only while something is worth saying: setup, or a stopped process. "Ready" says nothing, so it shows nothing.
            if samantha.status != "Ready" { Text(samantha.status).font(.caption2).foregroundStyle(.tertiary).padding(.bottom, 6) }
        }
        .frame(minWidth: 420, minHeight: 480)
        .toolbar {
            ToolbarItemGroup {
                Toggle(isOn: Binding(get: { samantha.voiceOn }, set: { _ in samantha.toggle("voice") })) {
                    Label("Voice", systemImage: "waveform")
                }.help("Say her replies out loud").disabled(inputDisabled)
                Toggle(isOn: Binding(get: { samantha.faceOn }, set: { _ in samantha.toggle("face") })) {
                    Label("Face", systemImage: "person.crop.square")
                }.help("Show her face").disabled(inputDisabled)
            }
        }
        .sheet(item: $samantha.customize) { kind in CustomizeSheet(kind: kind, samantha: samantha) }
        .animation(.spring(duration: 0.35), value: samantha.pending == nil)
        .onAppear { samantha.start(); samantha.morningBrief() }
    }

    /// A fresh chat: her icon and a greeting for the time of day, the same first screen as the phone.
    private var emptyState: some View {
        let hour = Calendar.current.component(.hour, from: Date())
        return VStack(spacing: 12) {
            Image(nsImage: NSApp.applicationIconImage).resizable().interpolation(.high).frame(width: 72, height: 72)
            Text(hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening").font(.title2.weight(.semibold))
            Text("Ask me anything, or tell me to do something on this Mac.").foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
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

    /// Return and the Send button both go through this, so the field clears exactly the same way either time.
    private func submit() {
        samantha.send(text)
        text = ""
    }

    private var inputBar: some View {
        HStack {
            TextField("Talk to Samantha", text: $text)
                .textFieldStyle(.roundedBorder).disabled(inputDisabled)
                .focused($fieldFocused)
                .onSubmit(submit)
                .onAppear { fieldFocused = true }
                .onChange(of: inputDisabled) { _, disabled in if !disabled { fieldFocused = true } }
            Button("Send", action: submit).disabled(text.isEmpty || inputDisabled)
        }.padding(10)
    }
}

/// Change voice... and Change look...: one line of words, sent as the sentence she already routes.
private struct CustomizeSheet: View {
    let kind: Customize
    @ObservedObject var samantha: Samantha
    @State private var text = ""
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(kind == .voice ? "Change her voice" : "Change her look").font(.headline)
            Text(kind == .voice ? "A premade ElevenLabs voice by name, like George."
                                : "Describe it, like ginger with glasses. A new portrait costs a few cents; keeping it costs about $1.40.")
                .font(.caption).foregroundStyle(.secondary)
            TextField(kind == .voice ? "Voice name" : "Describe the look", text: $text).textFieldStyle(.roundedBorder).onSubmit(go)
            HStack {
                if kind == .voice { Button("What voices?") { samantha.send("what voices do you have"); dismiss() } }
                Spacer()
                Button("Cancel") { dismiss() }.keyboardShortcut(.cancelAction)
                Button("Send", action: go).keyboardShortcut(.defaultAction).disabled(text.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(16).frame(width: 380)
    }

    private func go() {
        guard !text.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        samantha.send(customizeLine(kind, text))
        dismiss()
    }
}

/// No process, no model: prove the pure parsing and encoding, the exact same way PaintBar's --check works.
func runSelfCheck() -> Never {
    precondition(highlightSelfTest(), "code colors (gui/Highlight.swift) failed its self-test")
    precondition(parseLine("{\"answer\": \"hi\"}") == .answer("hi"))
    precondition(parseLine("{\"working\": \"open_app(chrome)\"}") == .working("open_app(chrome)"))
    if case .confirm(let name, let args, let note)? = parseLine("{\"confirm\": {\"name\": \"new_note\", \"args\": [\"buy milk\"]}}") {
        precondition(name == "new_note" && args == ["buy milk"] && note.isEmpty)
    } else {
        fatalError("confirm did not parse")
    }
    if case .confirm(_, _, let note)? = parseLine("{\"confirm\": {\"name\": \"keep_look\", \"args\": [], \"note\": \"about $1.40\"}}") {
        precondition(note == "about $1.40")
    } else {
        fatalError("confirm note did not parse")
    }
    precondition(parseLine("{\"mode\": {\"voice\": true, \"face\": false}}") == .mode(voice: true, face: false))
    precondition(customizeLine(.voice, " George ") == "change your voice to George")
    precondition(customizeLine(.look, "ginger") == "change your look: ginger")
    precondition(parseLine("not json") == nil)
    precondition(askLine("hi") == "{\"ask\":\"hi\"}\n")
    precondition(yesLine(true) == "{\"yes\":true}\n")
    let tmp = FileManager.default.temporaryDirectory.appendingPathComponent("samantha-chat-check/chat.json")
    saveChat(["You: hi", "Samantha: hello"], to: tmp)
    precondition(loadChat(from: tmp) == ["You: hi", "Samantha: hello"])
    precondition(loadChat(from: tmp.deletingLastPathComponent().appendingPathComponent("none.json")).isEmpty)
    let nine = Calendar.current.date(bySettingHour: 9, minute: 0, second: 0, of: Date())!, three = Calendar.current.date(bySettingHour: 15, minute: 0, second: 0, of: Date())!
    precondition(briefDue(now: nine, lastDay: nil) && briefDue(now: nine, lastDay: "2020-1-1") && !briefDue(now: nine, lastDay: dayKey(nine)) && !briefDue(now: three, lastDay: nil))
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
            .commands {
                CommandGroup(replacing: .newItem) { Button("New Chat") { samantha.newChat() }.keyboardShortcut("n") }
                CommandMenu("Customize") {
                    Button("Change voice...") { samantha.customize = .voice }
                    Button("Change look...") { samantha.customize = .look }
                }
            }
    }
}
