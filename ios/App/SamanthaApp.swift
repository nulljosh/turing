// Samantha for iPhone: a thin client to your own Mac. The Mac does the thinking; this is the window.
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

/// Everything the screens share: the open chat, the past ones, the pairing, and the turn in flight.
@Observable
final class Store {
    var chats: [Chat] = ChatStore.load()
    var current = Chat()
    var pairing = Pairing.load()
    var working: String? = nil           // "time_in(tokyo)" while she runs a tool
    var pendingConfirm: (name: String, args: [String], note: String?)? = nil
    var busy = false
    var error: String? = nil
    var useMock = ProcessInfo.processInfo.arguments.contains("--mock")

    var client: BridgeClient { useMock || !pairing.isSet ? MockClient() : RealClient(pairing: pairing) }

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

    /// One turn: your line goes in, her events come back, the answer lands as a message.
    func send(_ text: String) {
        let line = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !line.isEmpty, !busy else { return }
        current.messages.append(Message(role: .user, text: line))
        if current.messages.count == 1 { current.retitle() }
        busy = true; error = nil
        Task { await run(line) }
    }

    @MainActor
    private func run(_ line: String) async {
        defer { busy = false; working = nil; ChatStore.save(current); reloadChats() }
        do {
            for try await event in client.ask(line) {
                switch event {
                case .working(let w): working = w
                case .confirm(let name, let args, let note): hideKeyboard(); pendingConfirm = (name, args, note); working = nil
                case .mode: break
                case .answer(let a):
                    working = nil
                    let (text, model) = split(a)
                    current.messages.append(Message(role: .assistant, text: text, model: model))
                }
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// The last user line, asked again.
    func retry() {
        guard let last = current.messages.last(where: { $0.role == .user })?.text else { return }
        if current.messages.last?.role == .assistant { current.messages.removeLast() }
        current.messages.removeAll { $0.role == .user && $0.text == last && $0.id == current.messages.last(where: { $0.role == .user })?.id }
        send(last)
    }

    func answerConfirm(_ yes: Bool) {
        pendingConfirm = nil
        Task { try? await client.confirm(yes) }
    }

    /// "(Answered by Qwen3.5-9B on this Mac, not by me.)" becomes a label under the reply instead of a sentence inside it.
    private func split(_ answer: String) -> (String, String?) {
        let pattern = #"\s*\(Answered by (.+?) on this Mac(?:, not by me)?\.\)\s*$"#
        guard let re = try? NSRegularExpression(pattern: pattern), let m = re.firstMatch(in: answer, range: NSRange(answer.startIndex..., in: answer)),
              let modelRange = Range(m.range(at: 1), in: answer), let whole = Range(m.range, in: answer) else { return (answer, nil) }
        return (String(answer[..<whole.lowerBound]), String(answer[modelRange]))
    }
}
