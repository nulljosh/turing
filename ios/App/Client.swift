// The wire to the Mac: app/phone_bridge.py's routes, signed per request, answers as Server-Sent Events.
// MockClient plays the same protocol with no Mac, for previews and the first screenshots.
import CryptoKit
import Foundation

/// One line of the bridge's stream, the exact chat_pipe messages.
enum BridgeEvent: Equatable {
    case working(String)
    case confirm(name: String, args: [String], note: String?)
    case mode(voice: Bool, face: Bool)
    case answer(String)

    init?(json: [String: Any]) {
        if let w = json["working"] as? String { self = .working(w) }
        else if let c = json["confirm"] as? [String: Any] {
            self = .confirm(name: c["name"] as? String ?? "", args: (c["args"] as? [Any] ?? []).map { "\($0)" }, note: c["note"] as? String)
        } else if let m = json["mode"] as? [String: Any] { self = .mode(voice: m["voice"] as? Bool ?? false, face: m["face"] as? Bool ?? false) }
        else if let a = json["answer"] as? String { self = .answer(a) }
        else { return nil }
    }
}

enum BridgeError: LocalizedError {
    case notPaired, unauthorized, busy, http(Int), noAnswer, noModel

    var errorDescription: String? {
        switch self {
        case .notPaired: return "Pair with your Mac first (Settings)."
        case .unauthorized: return "Your Mac did not accept the pairing secret. Check the token in Settings."
        case .busy: return "She is still on the last question."
        case .http(let code): return "Your Mac answered with an error (\(code))."
        case .noAnswer: return "The connection dropped before she answered."
        case .noModel: return "My models are not on this phone yet. Download them in Settings."
        }
    }
}

protocol BridgeClient {
    /// Streams the events of one turn; ends after the answer.
    func ask(_ text: String) -> AsyncThrowingStream<BridgeEvent, Error>
    /// The phone's reply to a confirm event.
    func confirm(_ yes: Bool) async throws
    /// True when the Mac answers a signed ping.
    func ping() async throws -> String
}

/// Talks to app/phone_bridge.py.
struct RealClient: BridgeClient {
    let pairing: Pairing

    private func signed(_ method: String, _ path: String, body: Data) throws -> URLRequest {
        guard let base = pairing.baseURL, let url = URL(string: path, relativeTo: base) else { throw BridgeError.notPaired }
        let stamp = String(Int(Date().timeIntervalSince1970))
        let nonce = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        let bodyHash = SHA256.hash(data: body).map { String(format: "%02x", $0) }.joined()
        let message = "\(method)|\(path)|\(stamp)|\(nonce)|\(bodyHash)"
        let key = SymmetricKey(data: Data(pairing.token.utf8))
        let sig = HMAC<SHA256>.authenticationCode(for: Data(message.utf8), using: key).map { String(format: "%02x", $0) }.joined()
        var req = URLRequest(url: url, timeoutInterval: 300)
        req.httpMethod = method
        req.httpBody = body.isEmpty ? nil : body
        req.setValue(stamp, forHTTPHeaderField: "X-Samantha-Time")
        req.setValue(nonce, forHTTPHeaderField: "X-Samantha-Nonce")
        req.setValue(sig, forHTTPHeaderField: "X-Samantha-Sig")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return req
    }

    func ask(_ text: String) -> AsyncThrowingStream<BridgeEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let body = try JSONSerialization.data(withJSONObject: ["ask": text])
                    let req = try signed("POST", "/v1/ask", body: body)
                    let (bytes, response) = try await URLSession.shared.bytes(for: req)
                    let code = (response as? HTTPURLResponse)?.statusCode ?? 0
                    if code == 401 { throw BridgeError.unauthorized }
                    if code == 409 { throw BridgeError.busy }
                    if code != 200 { throw BridgeError.http(code) }
                    var answered = false
                    for try await line in bytes.lines where line.hasPrefix("data: ") {
                        let payload = Data(line.dropFirst(6).utf8)
                        if let json = try? JSONSerialization.jsonObject(with: payload) as? [String: Any], let event = BridgeEvent(json: json) {
                            continuation.yield(event)
                            if case .answer = event { answered = true; break }
                        }
                    }
                    if !answered { throw BridgeError.noAnswer }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    func confirm(_ yes: Bool) async throws {
        let body = try JSONSerialization.data(withJSONObject: ["yes": yes])
        let (_, response) = try await URLSession.shared.data(for: try signed("POST", "/v1/confirm", body: body))
        let code = (response as? HTTPURLResponse)?.statusCode ?? 0
        if code == 401 { throw BridgeError.unauthorized }
        if code != 200 { throw BridgeError.http(code) }
    }

    func ping() async throws -> String {
        let (data, response) = try await URLSession.shared.data(for: try signed("GET", "/v1/ping", body: Data()))
        let code = (response as? HTTPURLResponse)?.statusCode ?? 0
        if code == 401 { throw BridgeError.unauthorized }
        if code != 200 { throw BridgeError.http(code) }
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        return json?["version"] as? String ?? "?"
    }
}

/// No Mac needed: a scripted Samantha for previews and screenshots. Says "working" first, asks before a "delete".
struct MockClient: BridgeClient {
    func ask(_ text: String) -> AsyncThrowingStream<BridgeEvent, Error> {
        AsyncThrowingStream { continuation in
            Task {
                try? await Task.sleep(for: .milliseconds(400))
                if text.lowercased().contains("delete") {
                    continuation.yield(.working("trash_file(~/Downloads/old.zip)"))
                    try? await Task.sleep(for: .milliseconds(400))
                    continuation.yield(.confirm(name: "trash_file", args: ["~/Downloads/old.zip"], note: nil))
                    continuation.finish()
                    return
                }
                continuation.yield(.working("thinking"))
                try? await Task.sleep(for: .milliseconds(900))
                let answer = text.lowercased().contains("haiku")
                    ? "Rain on the window,\nthe kettle hums its one note,\nevening settles in."
                    : "I am the stand-in Mac, so that one gets a stand-in answer. Pair a real Mac for the real thing."
                continuation.yield(.answer(answer + " (Answered by Qwen3.5-9B on this Mac.)"))
                continuation.finish()
            }
        }
    }

    func confirm(_ yes: Bool) async throws {}
    func ping() async throws -> String { "mock" }
}
