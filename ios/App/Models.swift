// Chats and messages, saved as JSON in the app's Documents folder, one file per chat, like the Mac app's ~/.samantha/chats.
import Foundation

struct Message: Identifiable, Codable, Equatable {
    enum Role: String, Codable { case user, assistant }
    var id = UUID()
    var role: Role
    var text: String
    var model: String? = nil   // "Qwen3.5-9B on this Mac" when a bigger model answered, so the app can say so
}

struct Chat: Identifiable, Codable, Equatable {
    var id = UUID()
    var title: String = "New chat"
    var created = Date()
    var messages: [Message] = []

    /// The first thing you said, trimmed, is the title.
    mutating func retitle() {
        if let first = messages.first(where: { $0.role == .user })?.text {
            title = String(first.prefix(48))
        }
    }
}

enum ChatStore {
    static var folder: URL {
        // ponytail: screenshot runs (--mock) get a fresh folder per launch so Recents never shows last run's chats
        let docs = ProcessInfo.processInfo.arguments.contains("--mock")
            ? FileManager.default.temporaryDirectory.appendingPathComponent("mock-\(ProcessInfo.processInfo.processIdentifier)")
            : FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let dir = docs.appendingPathComponent("chats", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    static func load() -> [Chat] {
        let files = (try? FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil)) ?? []
        let chats = files.filter { $0.pathExtension == "json" }.compactMap { url -> Chat? in
            guard let data = try? Data(contentsOf: url) else { return nil }
            return try? JSONDecoder().decode(Chat.self, from: data)
        }
        return chats.sorted { $0.created > $1.created }
    }

    static func save(_ chat: Chat) {
        guard !chat.messages.isEmpty, let data = try? JSONEncoder().encode(chat) else { return }
        try? data.write(to: folder.appendingPathComponent("\(chat.id.uuidString).json"), options: .atomic)
    }

    static func delete(_ chat: Chat) {
        try? FileManager.default.removeItem(at: folder.appendingPathComponent("\(chat.id.uuidString).json"))
    }
}

/// Where the Mac is and how to prove it is you. The token is the pairing secret the bridge printed.
struct Pairing: Codable, Equatable {
    var host = ""
    var port = 8128
    var token = ""

    var isSet: Bool { !host.isEmpty && !token.isEmpty }
    var baseURL: URL? { URL(string: "http://\(host):\(port)") }

    static func load() -> Pairing {
        guard let data = UserDefaults.standard.data(forKey: "pairing"), let p = try? JSONDecoder().decode(Pairing.self, from: data) else { return Pairing() }
        return p
    }

    func save() {
        if let data = try? JSONEncoder().encode(self) { UserDefaults.standard.set(data, forKey: "pairing") }
    }

    /// samantha://pair?host=...&port=...&token=... from the bridge's terminal line.
    static func from(url: URL) -> Pairing? {
        guard url.scheme == "samantha", url.host == "pair", let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems else { return nil }
        var p = Pairing()
        for item in items {
            switch item.name {
            case "host": p.host = item.value ?? ""
            case "port": p.port = Int(item.value ?? "") ?? 8128
            case "token": p.token = item.value ?? ""
            default: break
            }
        }
        return p.isSet ? p : nil
    }
}
