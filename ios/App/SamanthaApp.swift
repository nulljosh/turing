// Samantha for iPhone. Her models run on the phone; the Mac is optional and lends its bigger model and its own tools.
import SwiftUI

@main
struct SamanthaApp: App {
    @State private var store = Store()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .onOpenURL { url in
                    if let p = Pairing.from(url: url) { store.pairing = p; p.save() }
                }
        }
    }
}

/// Everything the screens share: the open chat, the past ones, the pairing, the models, and the turn in flight.
@Observable
final class Store {
    var chats: [Chat] = ChatStore.load()
    var current = Chat()
    var pairing = Pairing.load()
    let model = LocalModel()
    var working: String? = nil           // "time_in(tokyo)" while she runs a tool
    var pendingConfirm: (name: String, args: [String], note: String?)? = nil
    var busy = false
    var error: String? = nil
    var useMock = ProcessInfo.processInfo.arguments.contains("--mock")

    private var bridge: BridgeClient { useMock ? MockClient() : RealClient(pairing: pairing) }
    private var macPaired: Bool { useMock || pairing.isSet }

    func newChat() {
        if !current.messages.isEmpty { ChatStore.save(current); reloadChats() }
        current = Chat()
    }

    func open(_ chat: Chat) {
        if !current.messages.isEmpty && current.id != chat.id { ChatStore.save(current) }
        current = chat
    }

    func delete(_ chat: Chat) {
        ChatStore.delete(chat)
        if current.id == chat.id { current = Chat() }
        reloadChats()
    }

    private func reloadChats() { chats = ChatStore.load() }

    /// One turn: your line goes in, her answer lands as a message.
    func send(_ text: String) {
        let line = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !line.isEmpty, !busy else { return }
        current.messages.append(Message(role: .user, text: line))
        if current.messages.count == 1 { current.retitle() }
        busy = true; error = nil
        Task { await run(line) }
    }

    /// Exact tools first (instant, offline), then her models on the phone, then the Mac when it is paired.
    @MainActor
    private func run(_ line: String) async {
        defer { busy = false; working = nil; ChatStore.save(current); reloadChats() }
        let twins = Twins.shared
        switch twins.route(line) {
        case .tool(let tool, let arg) where twins.runsHere(tool):
            working = "\(tool)(\(arg))"
            try? await Task.sleep(for: .milliseconds(150))
            reply(twins.run(tool, arg) ?? "That did not work.", model: nil)
            return
        case .tool, .agent:
            if macPaired { await askMac(line) } else { reply("That one needs your Mac. Pair it in Settings and ask again.", model: nil) }
            return
        case .none:
            break
        }
        if model.isReady {
            await askPhone(line)
        } else if macPaired {
            await askMac(line)
        } else {
            reply("I can answer that once my models are on this phone. Download them in Settings, or pair your Mac.", model: nil)
        }
    }

    /// Her picker on the phone chooses a tool; an exact twin runs it, anything else goes to the instruct model.
    @MainActor
    private func askPhone(_ line: String) async {
        do {
            working = "thinking"
            if let (tool, arg) = try await model.pick(line) {
                if Twins.shared.runsHere(tool) {
                    working = "\(tool)(\(arg))"
                    reply(Twins.shared.run(tool, arg) ?? "That did not work.", model: nil)
                    return
                }
                if macPaired { await askMac(line); return }
            }
            working = nil
            var text = ""
            let message = Message(role: .assistant, text: "")
            current.messages.append(message)
            for try await piece in model.answer(line) {
                text += piece
                if let i = current.messages.firstIndex(where: { $0.id == message.id }) { current.messages[i].text = text }
            }
            if let i = current.messages.firstIndex(where: { $0.id == message.id }) { current.messages[i].model = "Qwen2.5 1.5B on this phone" }
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// The paired Mac answers: its own tools, its bigger model, and its ask-before-writing rule carried over.
    @MainActor
    private func askMac(_ line: String) async {
        do {
            for try await event in bridge.ask(line) {
                switch event {
                case .working(let w): working = w
                case .confirm(let name, let args, let note): hideKeyboard(); pendingConfirm = (name, args, note); working = nil
                case .mode: break
                case .answer(let a):
                    working = nil
                    let (text, model) = split(a)
                    reply(text, model: model.map { "\($0) on your Mac" })
                }
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func reply(_ text: String, model: String?) {
        current.messages.append(Message(role: .assistant, text: text, model: model))
    }

    /// The last user line, asked again.
    func retry() {
        guard let last = current.messages.last(where: { $0.role == .user })?.text else { return }
        if current.messages.last?.role == .assistant { current.messages.removeLast() }
        if current.messages.last?.role == .user { current.messages.removeLast() }
        send(last)
    }

    func answerConfirm(_ yes: Bool) {
        pendingConfirm = nil
        Task { try? await bridge.confirm(yes) }
    }

    /// "(Answered by Qwen3.5-9B on this Mac, not by me.)" becomes a label under the reply instead of a sentence inside it.
    private func split(_ answer: String) -> (String, String?) {
        let pattern = #"\s*\(Answered by (.+?) on this Mac(?:, not by me)?\.\)\s*$"#
        guard let re = try? NSRegularExpression(pattern: pattern), let m = re.firstMatch(in: answer, range: NSRange(answer.startIndex..., in: answer)),
              let modelRange = Range(m.range(at: 1), in: answer), let whole = Range(m.range, in: answer) else { return (answer, nil) }
        return (String(answer[..<whole.lowerBound]), String(answer[modelRange]))
    }
}
